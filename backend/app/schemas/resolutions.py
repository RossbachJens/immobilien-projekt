# backend/app/schemas/resolutions.py
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ResolutionCreate(BaseModel):
    property_id: int
    resolution_date: date
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    resolution_type: str | None = Field(default=None, max_length=50)
    meeting_location: str | None = Field(default=None, max_length=200)
    agenda_item: str | None = Field(default=None, max_length=50)
    proposed_by_owner_id: int | None = None
    meeting_id: int | None = None
    # NEU - präzise TOP-Verknüpfung + Abstimmungsergebnis für die Niederschrift.
    agenda_item_id: int | None = None
    votes_yes: float | None = Field(default=None, ge=0)
    votes_no: float | None = Field(default=None, ge=0)
    votes_abstain: float | None = Field(default=None, ge=0)
    court_name: str | None = Field(default=None, max_length=200)
    court_case_number: str | None = Field(default=None, max_length=100)
    court_decision_date: date | None = None
    court_ruling_text: str | None = None
    court_parties: str | None = Field(default=None, max_length=300)
    status_note: str | None = None
    refers_to_resolution_id: int | None = None


class ResolutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resolution_id: int
    property_id: int
    lfd_nr: int
    resolution_date: date
    title: str
    description: str | None
    resolution_type: str | None
    meeting_location: str | None
    agenda_item: str | None
    proposed_by_owner_id: int | None
    meeting_id: int | None
    agenda_item_id: int | None
    votes_yes: float | None
    votes_no: float | None
    votes_abstain: float | None
    court_name: str | None
    court_case_number: str | None
    court_decision_date: date | None
    court_ruling_text: str | None
    court_parties: str | None
    status_note: str | None
    created_by: int | None
    refers_to_resolution_id: int | None
    created_at: datetime