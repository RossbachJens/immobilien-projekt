# backend/app/schemas/settlement.py
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SettlementStatus = Literal["Entwurf", "Beschlossen", "Inaktiv"]


class SettlementPeriodCreate(BaseModel):
    property_id: int
    fiscal_year: int = Field(ge=2000, le=2100)
    period_start: date
    period_end: date
    title: str = Field(min_length=1, max_length=150)
    resolution_id: int | None = None


class SettlementPeriodStatusUpdate(BaseModel):
    status: SettlementStatus
    resolution_id: int | None = None


class SettlementPeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    settlement_id: int
    property_id: int
    fiscal_year: int
    period_start: date
    period_end: date
    title: str
    status: str
    resolution_id: int | None
    created_at: datetime


class SettlementPositionCreate(BaseModel):
    # Mehrere Konten pro Position ("Pooling") - z.B. Heizkosten aus
    # Brennstoff + Wartung + Messdienst-Gebühr zu einer Position bündeln,
    # bevor nach HeizkostenV verteilt wird. Mindestens ein Konto Pflicht.
    account_ids: list[int] = Field(min_length=1)
    description: str | None = Field(default=None, max_length=150)
    allocation_key_type: str = Field(min_length=1, max_length=50)
    is_apportionable: bool = False

    @field_validator("account_ids")
    @classmethod
    def _dedupe_account_ids(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))

class UnitSettlementShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    share_id: int
    position_id: int
    unit_id: int
    allocated_actual_amount: float

class SettlementPositionUpdate(BaseModel):
    """PATCH-Semantik wie bei BudgetPositionUpdate - nur mitgeschickte Felder
    werden geändert. Nur zulässig, solange die Abrechnung im Status
    'Entwurf' ist (siehe Router). Bei jeder Änderung wird der Ist-Betrag neu
    aus den Buchungen ermittelt und die Verteilung auf Einheiten komplett
    neu berechnet."""

    account_ids: list[int] | None = None
    description: str | None = Field(default=None, max_length=150)
    allocation_key_type: str | None = Field(default=None, min_length=1, max_length=50)
    is_apportionable: bool | None = None

    @field_validator("account_ids")
    @classmethod
    def _validate_account_ids(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        if len(value) == 0:
            raise ValueError("account_ids darf nicht leer sein, wenn angegeben.")
        return list(dict.fromkeys(value))

class SettlementPositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position_id: int
    settlement_id: int
    account_ids: list[int]
    description: str | None
    actual_amount: float
    allocation_key_type: str
    is_apportionable: bool
    unit_shares: list[UnitSettlementShareOut] = Field(default_factory=list)

class UnitSettlementSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary_id: int
    settlement_id: int
    unit_id: int
    total_actual_costs: float
    total_prepayments: float
    # total_actual_costs - total_prepayments: negativ = Erstattung,
    # positiv = Nachzahlung/Abrechnungsspitze (Vorzeichen wie in der
    # Muster-Einzelabrechnung: "-70,85 € (Erstattung)").
    balance: float