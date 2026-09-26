# backend/app/schemas/settlement.py
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SettlementStatus = Literal["Entwurf", "Beschlossen", "Inaktiv"]
TaxCategory = Literal["keine", "haushaltsnahe_dienstleistung", "handwerkerleistung"]


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


class UnitSettlementShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    share_id: int
    position_id: int
    unit_id: int
    allocated_actual_amount: float


class UnitSettlementTaxShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    share_id: int
    position_id: int
    unit_id: int
    allocated_deductible_amount: float


class UnitSettlementTenantShareOut(BaseModel):
    """Taggenaue Verteilung einer umlagefähigen Position auf einen
    Mietvertrag - siehe app/models/abrechnung.py::UnitSettlementTenantShare."""

    model_config = ConfigDict(from_attributes=True)

    share_id: int
    position_id: int
    lease_id: int
    allocated_amount: float


class SettlementPositionCreate(BaseModel):
    account_ids: list[int] = Field(min_length=1)
    description: str | None = Field(default=None, max_length=150)
    allocation_key_type: str = Field(min_length=1, max_length=50)
    is_apportionable: bool = False
    tax_category: TaxCategory = "keine"
    deductible_amount: float | None = Field(default=None, ge=0)

    @field_validator("account_ids")
    @classmethod
    def _dedupe_account_ids(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


class SettlementPositionUpdate(BaseModel):
    account_ids: list[int] | None = None
    description: str | None = Field(default=None, max_length=150)
    allocation_key_type: str | None = Field(default=None, min_length=1, max_length=50)
    is_apportionable: bool | None = None
    tax_category: TaxCategory | None = None
    deductible_amount: float | None = Field(default=None, ge=0)

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
    tax_category: TaxCategory
    deductible_amount: float | None
    unit_shares: list[UnitSettlementShareOut] = Field(default_factory=list)
    tax_shares: list[UnitSettlementTaxShareOut] = Field(default_factory=list)
    tenant_shares: list[UnitSettlementTenantShareOut] = Field(default_factory=list)


class UnitSettlementSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary_id: int
    settlement_id: int
    unit_id: int
    total_actual_costs: float
    total_prepayments: float
    balance: float


class LeaseSettlementSummaryOut(BaseModel):
    """Ergebnis je Mietvertrag - siehe app/models/abrechnung.py::LeaseSettlementSummary.
    Mietername und Vertragszeitraum sind denormalisiert mitgegeben (Chat vom
    24.09.2026), damit das Frontend ohne zusätzliche Requests eine sprechende
    Bezeichnung anzeigen kann - LeaseSettlementSummary selbst kennt weder
    tenant_id noch die Vertragsdaten, nur lease_id."""

    model_config = ConfigDict(from_attributes=True)

    summary_id: int
    settlement_id: int
    lease_id: int
    unit_id: int
    total_actual_costs: float
    total_prepayments: float
    balance: float
    tenant_first_name: str
    tenant_last_name: str
    lease_start_date: date
    lease_end_date: date | None