# backend/app/models/documents.py
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Document(Base):
    """
    Dokumentenverwaltung (DMS): Kontoauszüge, Rechnungen, Angebote, Verträge,
    Protokolle etc. Dateiinhalt liegt direkt als BYTEA in Postgres (siehe
    Migration 0013). Soft-Delete wie bei den übrigen Stammdaten (nicht
    append-only wie resolution_collection).
    """

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "category IN ('Kontoauszug', 'Rechnung', 'Angebot', 'Versicherung', 'Vertrag', "
            "'Protokoll', 'Sonstiges')"
        ),
        CheckConstraint("visibility IN ('intern', 'eigentuemer', 'alle')"),
        CheckConstraint("file_size_bytes > 0"),
    )

    document_id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.property_id"))
    category: Mapped[str] = mapped_column(String(30))

    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.unit_id"))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("owners.owner_id"))
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.tenant_id"))
    settlement_id: Mapped[int | None] = mapped_column(ForeignKey("settlement_periods.settlement_id"))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.entry_id"))
    meeting_id: Mapped[int | None] = mapped_column(ForeignKey("owner_meetings.meeting_id"))

    title: Mapped[str] = mapped_column(String(200))
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size_bytes: Mapped[int]
    # Wird bewusst NICHT in der Listen-Antwort mitgeladen (siehe Router,
    # nächster Schritt) - dort werden gezielt nur die Metadaten-Spalten
    # abgefragt, damit eine Dokumentenliste nicht bei jedem Aufruf alle
    # Dateiinhalte durch die DB-Verbindung schaufelt. Nur der Download-
    # Endpoint lädt content.
    content: Mapped[bytes] = mapped_column(LargeBinary)

    visibility: Mapped[str] = mapped_column(String(20), default="intern")
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    deleted_at: Mapped[datetime | None]
    
    