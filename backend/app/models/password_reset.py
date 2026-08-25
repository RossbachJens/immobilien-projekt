from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PasswordResetToken(Base):
    """Speichert nur den Hash des Tokens (SHA-256, s. app/core/security.py),
    nie den Token selbst - siehe Kommentar in 01_schema.sql."""

    __tablename__ = "password_reset_tokens"

    token_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    token_hash: Mapped[str]
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())