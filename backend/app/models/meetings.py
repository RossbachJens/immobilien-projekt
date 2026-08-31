# backend/app/models/meetings.py
from datetime import date, datetime, time

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OwnerMeeting(Base):
    """Eigentümerversammlung (Präsenz/Online) oder Umlaufbeschluss - einheitliche
    Struktur, da beide rechtlich derselbe Ablauf sind (Einladung/Aufforderung
    -> Tagesordnung -> Beschlussfassung -> Niederschrift), nur Termin vs.
    Frist zur Stimmabgabe unterscheiden sich."""

    __tablename__ = "owner_meetings"
    __table_args__ = (
        CheckConstraint("status IN ('Geplant', 'Eingeladen', 'Durchgeführt', 'Protokolliert')"),
    )

    meeting_id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.property_id"))
    meeting_type: Mapped[str] = mapped_column(String(50))
    meeting_date: Mapped[date]
    meeting_time: Mapped[time | None]
    location: Mapped[str | None] = mapped_column(String(200))
    invitation_date: Mapped[date | None]
    agenda_intro: Mapped[str | None] = mapped_column(Text)
    minutes_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="Geplant")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MeetingAgendaItem(Base):
    __tablename__ = "meeting_agenda_items"
    __table_args__ = (UniqueConstraint("meeting_id", "position"),)

    item_id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("owner_meetings.meeting_id"))
    position: Mapped[int]
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())