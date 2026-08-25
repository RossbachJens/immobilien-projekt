from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.stammdaten import User


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Liest das httpOnly-Cookie 'access_token', dekodiert das JWT und laedt
    den zugehoerigen User. Wirft 401, wenn irgendein Schritt fehlschlaegt."""
    if access_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nicht angemeldet")

    user_id = decode_access_token(access_token)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token ungueltig oder abgelaufen")

    user = db.get(User, int(user_id))
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Benutzer nicht gefunden")

    return user
