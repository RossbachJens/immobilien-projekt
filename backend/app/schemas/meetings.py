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


class AgendaItemCreate(BaseModel):
    position: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None


class AgendaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    meeting_id: int
    position: int
    title: str
    description: str | None