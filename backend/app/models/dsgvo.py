from datetime import datetime

from sqlalchemy import ForeignKey, Text,func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccessLog(Base):
    """Rechenschaftspflicht (Art. 30 DSGVO). Wird ab Phase 1 durch eine
    FastAPI-Middleware bei jedem Request auf personenbezogene Daten befüllt."""

    __tablename__ = "access_log"

    log_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    accessed_table: Mapped[str]
    accessed_record_id: Mapped[int | None]
    action: Mapped[str]
    accessed_at: Mapped[datetime] = mapped_column(server_default=func.now())


class GdprDeletionLog(Base):
    """Dokumentation bearbeiteter Löschanfragen (Art. 15/17 DSGVO)."""

    __tablename__ = "gdpr_deletion_log"

    request_id: Mapped[int] = mapped_column(primary_key=True)
    subject_type: Mapped[str]
    subject_id: Mapped[int]
    requested_at: Mapped[datetime] = mapped_column(server_default=func.now())
    legal_basis_for_retention: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None]
    outcome: Mapped[str | None]
