from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rls import apply_rls_context
from app.core.roles import resolve_role
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.stammdaten import User


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Liest das httpOnly-Cookie 'access_token', dekodiert das JWT und laedt
    den zugehoerigen User. Wirft 401, wenn irgendein Schritt fehlschlaegt.
    Setzt zusätzlich den RLS-Kontext (app/core/rls.py) für die restliche
    Dauer des Requests, sobald die Rolle feststeht - zweite
    Verteidigungslinie neben der Query-Filterung in app/core/access.py."""
    if access_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nicht angemeldet")

    user_id = decode_access_token(access_token)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token ungueltig oder abgelaufen")

    user = db.get(User, int(user_id))
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Benutzer nicht gefunden")

    apply_rls_context(db, user.user_id, resolve_role(user))

    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Wie get_current_user, verlangt zusaetzlich is_admin=True. Fuer alle
    Endpoints der globalen Nutzerverwaltung (app/routers/users.py)."""
    if not current_user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Nur für Administratoren")
    return current_user