# backend/app/schemas/journal_entries.py
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.buchhaltung import EntryDirection


class EntryLineCreate(BaseModel):
    account_id: int
    unit_id: int | None = None
    lease_id: int | None = None
    amount: float = Field(gt=0)
    direction: EntryDirection


class EntryLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_id: int
    account_id: int
    property_id: int | None
    unit_id: int | None
    lease_id: int | None
    amount: float
    direction: EntryDirection


class JournalEntryCreate(BaseModel):
    property_id: int
    entry_date: date
    document_reference: str | None = Field(default=None, max_length=100)
    description: str = Field(min_length=1)
    # Mindestens 2 Zeilen (eine Soll-, eine Haben-Zeile) - die eigentliche
    # Summenprüfung (Soll == Haben) übernimmt der DB-Trigger bei COMMIT
    # (siehe 02_triggers.sql), hier nur der offensichtlichste Vorab-Check.
    lines: list[EntryLineCreate] = Field(min_length=2)

    @field_validator("lines")
    @classmethod
    def _require_both_directions(cls, lines: list[EntryLineCreate]) -> list[EntryLineCreate]:
        directions = {line.direction for line in lines}
        if EntryDirection.debit not in directions or EntryDirection.credit not in directions:
            raise ValueError("Eine Buchung braucht mindestens eine Soll- und eine Haben-Zeile.")
        return lines


class JournalEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entry_id: int
    property_id: int
    entry_date: date
    document_reference: str | None
    description: str
    created_by: int | None
    created_at: datetime
    locked_at: datetime | None
    reversed_entry_id: int | None
    # JournalEntry hat bewusst KEINE ORM-relationship() zu EntryLine (siehe
    # app/models/buchhaltung.py) - die Zeilen werden im Router separat
    # geladen und hier manuell mitgegeben, nicht automatisch über
    # from_attributes aufgelöst.
    lines: list[EntryLineOut]