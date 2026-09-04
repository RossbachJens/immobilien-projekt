# backend/app/schemas/meetings.py
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MeetingStatus = Literal["Geplant", "Eingeladen", "Durchgeführt", "Protokolliert"]


class MeetingCreate(BaseModel):
    property_id: int
    meeting_type: str = Field(min_length=1, max_length=50)
    meeting_date: date
    meeting_time: time | None = None
    location: str | None = Field(default=None, max_length=200)
    agenda_intro: str | None = None


class MeetingUpdate(BaseModel):
    meeting_type: str | None = Field(default=None, min_length=1, max_length=50)
    meeting_date: date | None = None
    meeting_time: time | None = None
    location: str | None = Field(default=None, max_length=200)
    invitation_date: date | None = None
    agenda_intro: str | None = None
    minutes_text: str | None = None
    status: MeetingStatus | None = None
    # Niederschrift-Kopfdaten - erst nach der Versammlung bekannt, daher
    # eigenes Update statt Pflichtfeld bei Anlage.
    chairperson: str | None = Field(default=None, max_length=150)
    minute_taker: str | None = Field(default=None, max_length=150)
    end_time: time | None = None
    represented_shares: float | None = Field(default=None, ge=0)
    quorum_met: bool | None = None
    voting_key: str | None = Field(default=None, max_length=100)


class MeetingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meeting_id: int
    property_id: int
    meeting_type: str
    meeting_date: date
    meeting_time: time | None
    location: str | None
    invitation_date: date | None
    agenda_intro: str | None
    minutes_text: str | None
    status: str
    created_by: int | None
    created_at: datetime
    chairperson: str | None
    minute_taker: str | None
    end_time: time | None
    represented_shares: float | None
    quorum_met: bool | None
    voting_key: str | None


class AgendaItemCreate(BaseModel):
    position: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None


class AgendaItemUpdate(BaseModel):
    """Für die Pflege NACH der Versammlung - i.d.R. nur protocol_text, aber
    Titel/Beschreibung/Position bleiben ebenfalls korrigierbar."""

    position: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    protocol_text: str | None = None


class AgendaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    meeting_id: int
    position: int
    title: str
    description: str | None
    protocol_text: str | None