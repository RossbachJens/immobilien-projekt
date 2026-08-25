from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.db.session import get_db
from app.models.password_reset import PasswordResetToken
from app.models.stammdaten import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ResetPasswordRequest,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "access_token"


def _now_naive_utc() -> datetime:
    """users/-reset_tokens-Spalten sind TIMESTAMP WITHOUT TIME ZONE (siehe
    01_schema.sql) - hier bewusst konsistent naive UTC-Werte erzeugen, statt
    tz-aware datetimes, die psycopg sonst unklar interpretieren wuerde."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _find_user_by_identifier(db: Session, identifier: str) -> User | None:
    return db.scalar(
        select(User).where(
            or_(User.email == identifier, User.name == identifier),
            User.deleted_at.is_(None),
        )
    )


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    user = _find_user_by_identifier(db, payload.identifier)

    # Bewusst dieselbe Fehlermeldung fuer "User existiert nicht" und
    # "Passwort falsch" -> verhindert User-Enumeration.
    if user is None or user.password_hash is None or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Anmeldedaten falsch")

    token = create_access_token(subject=str(user.user_id))
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return user


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> ForgotPasswordResponse:
    """Legt bei Treffer einen Reset-Token an. Antwortet IMMER identisch,
    unabhaengig davon ob ein Konto gefunden wurde - verhindert
    User-Enumeration (gleiches Prinzip wie beim Login)."""
    user = _find_user_by_identifier(db, payload.identifier)

    dev_token: str | None = None
    if user is not None:
        raw_token = generate_reset_token()
        db.add(
            PasswordResetToken(
                user_id=user.user_id,
                token_hash=hash_reset_token(raw_token),
                expires_at=_now_naive_utc()
                + timedelta(minutes=settings.password_reset_token_expire_minutes),
            )
        )
        db.commit()

        # Ersatz fuer noch fehlenden E-Mail-Versand (PROJECTPLAN.md, Phase 7).
        # NIEMALS in Produktion den Rohtoken herausgeben.
        if settings.environment != "production":
            dev_token = raw_token

    return ForgotPasswordResponse(
        detail="Falls ein Konto zu diesen Angaben existiert, wurde ein Reset-Link erstellt.",
        dev_reset_token=dev_token,
    )


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    token_hash = hash_reset_token(payload.token)
    reset_token = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )

    now = _now_naive_utc()
    if reset_token is None or reset_token.used_at is not None or reset_token.expires_at < now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token ungültig oder abgelaufen")

    user = db.get(User, reset_token.user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token ungültig oder abgelaufen")

    user.password_hash = hash_password(payload.new_password)
    # Nutzer hat jetzt selbst ein Passwort gesetzt - kein Erzwingen mehr noetig.
    user.must_change_password = False
    reset_token.used_at = now

    # Alle anderen noch offenen Tokens desselben Users invalidieren, damit
    # nicht mehrere gueltige Reset-Links gleichzeitig im Umlauf sind.
    other_tokens = db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.user_id,
            PasswordResetToken.token_id != reset_token.token_id,
            PasswordResetToken.used_at.is_(None),
        )
    )
    for t in other_tokens:
        t.used_at = now

    db.commit()
    return {"status": "ok"}