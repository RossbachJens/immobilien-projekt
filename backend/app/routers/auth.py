from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.google_oauth import (
    STATE_COOKIE_MAX_AGE_SECONDS,
    STATE_COOKIE_NAME,
    build_authorization_url,
    exchange_code_for_userinfo,
    generate_state,
    require_google_configured,
)
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


def _issue_login_cookie(response: Response, user: User) -> None:
    """Gemeinsame Cookie-Logik für Passwort- und Google-Login (siehe
    google_callback unten) - identische Parameter, damit beide Anmeldewege
    für den Browser ununterscheidbar sind (gleicher Cookie-Name, gleiche
    Gültigkeit, gleiches SameSite-Verhalten). RedirectResponse ist eine
    Response-Unterklasse, set_cookie funktioniert für beide identisch."""
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


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    user = _find_user_by_identifier(db, payload.identifier)

    # Bewusst dieselbe Fehlermeldung fuer "User existiert nicht" und
    # "Passwort falsch" -> verhindert User-Enumeration.
    if user is None or user.password_hash is None or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Anmeldedaten falsch")

    _issue_login_cookie(response, user)
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


# ---------------------------------------------------------------------
# Google SSO (Phase 7) - Authorization-Code-Flow, siehe app/core/google_oauth.py
# ---------------------------------------------------------------------


@router.get("/google/login")
def google_login() -> RedirectResponse:
    """Leitet den Browser zu Googles Consent-Screen weiter. Das Frontend
    ruft diesen Endpunkt per window.location.href auf, NICHT per axios
    (siehe LoginPage.tsx) - der Consent-Screen braucht einen echten
    Browser-Kontext, keinen XHR-Request."""
    require_google_configured()

    state = generate_state()
    redirect = RedirectResponse(
        url=build_authorization_url(state), status_code=status.HTTP_302_FOUND
    )
    redirect.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        max_age=STATE_COOKIE_MAX_AGE_SECONDS,
        path="/auth/google",
    )
    return redirect


@router.get("/google/callback")
def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    google_oauth_state: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """
    Rückweg von Google. Antwortet IMMER mit einem Redirect zum Frontend
    (nie mit JSON/HTTPException) - ein Browser, der gerade von Google
    zurückkommt, kann keine JSON-Fehlerantwort sinnvoll darstellen. Fehler
    werden stattdessen als '?google_error=<code>'-Query-Parameter an
    /login übergeben (siehe LoginPage.tsx für die Anzeige der Meldung).

    Kontoverknüpfung (Chat-Entscheidung vom 2026-09-13): Ein bestehendes,
    per Passwort angelegtes Konto wird bei ERSTER erfolgreicher
    Google-Anmeldung automatisch anhand der - bei Google verifizierten -
    E-Mail-Adresse verknüpft (google_sub_id wird einmalig gesetzt).
    Alternative wäre eine manuelle Admin-Freigabe gewesen; dafür fehlt
    aktuell aber die UI-Unterstützung (PATCH /users kennt google_sub_id
    nicht).
    """

    def _fail(reason: str) -> RedirectResponse:
        redirect = RedirectResponse(
            url=f"{settings.frontend_base_url}/login?google_error={reason}",
            status_code=status.HTTP_302_FOUND,
        )
        redirect.delete_cookie(STATE_COOKIE_NAME, path="/auth/google")
        return redirect

    if not settings.google_client_id or not settings.google_client_secret:
        return _fail("not_configured")
    if error is not None:
        return _fail("denied")
    if code is None or state is None or google_oauth_state is None or state != google_oauth_state:
        return _fail("state_mismatch")

    try:
        userinfo = exchange_code_for_userinfo(code)
    except HTTPException:
        return _fail("google_error")

    if not userinfo.email_verified:
        return _fail("email_not_verified")

    user = db.scalar(
        select(User).where(User.google_sub_id == userinfo.sub, User.deleted_at.is_(None))
    )

    if user is None:
        user = db.scalar(
            select(User).where(
                func.lower(User.email) == func.lower(userinfo.email),
                User.deleted_at.is_(None),
            )
        )
        if user is None:
            return _fail("no_matching_account")
        if user.google_sub_id is not None and user.google_sub_id != userinfo.sub:
            # Sollte praktisch nie vorkommen (google_sub_id ist pro
            # Google-Konto stabil) - Sicherheitsnetz gegen inkonsistente
            # Daten statt eine bestehende Verknüpfung stillschweigend zu
            # überschreiben.
            return _fail("account_conflict")
        user.google_sub_id = userinfo.sub

    # Erfolgreicher Google-Login ersetzt ein eventuell noch ausstehendes
    # "Passwort ändern" - die Person hat sich gerade über einen anderen,
    # vertrauenswürdigen Kanal authentifiziert (analog reset_password()).
    user.must_change_password = False
    user.last_login_at = _now_naive_utc()
    db.commit()

    redirect = RedirectResponse(url=settings.frontend_base_url, status_code=status.HTTP_302_FOUND)
    _issue_login_cookie(redirect, user)
    redirect.delete_cookie(STATE_COOKIE_NAME, path="/auth/google")
    return redirect