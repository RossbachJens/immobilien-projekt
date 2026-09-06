# backend/app/schemas/reserve_fund.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MovementType = Literal[
    "Zufuehrung", "Entnahme", "Zinsen", "Kapitalertragsteuer", "Solidaritaetszuschlag", "Sonstiges"
]


class ReserveFundPositionCreate(BaseModel):
    movement_type: MovementType
    description: str | None = Field(default=None, max_length=150)
    allocation_key_type: str = Field(default="MEA", min_length=1, max_length=50)
    # Gegenkonto(en) - NICHT das Rücklagenkonto selbst, sondern die
    # Buchungsgegenseite (z.B. Zinsertragskonto), über die die Position von
    # anderen Rücklagenbewegungen unterschieden wird (siehe
    # app/models/reserve_fund.py::ReserveFundPosition).
    account_ids: list[int] = Field(min_length=1)

    @field_validator("account_ids")
    @classmethod
    def _dedupe(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


class ReserveFundPositionUpdate(BaseModel):
    movement_type: MovementType | None = None
    description: str | None = Field(default=None, max_length=150)
    allocation_key_type: str | None = Field(default=None, min_length=1, max_length=50)
    account_ids: list[int] | None = None

    @field_validator("account_ids")
    @classmethod
    def _validate(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        if len(value) == 0:
            raise ValueError("account_ids darf nicht leer sein, wenn angegeben.")
        return list(dict.fromkeys(value))


class ReserveFundUnitShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    share_id: int
    position_id: int
    unit_id: int
    allocated_amount: float


class ReserveFundPositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position_id: int
    statement_id: int
    movement_type: str
    description: str | None
    allocation_key_type: str
    actual_amount: float
    account_ids: list[int]
    unit_shares: list[ReserveFundUnitShareOut] = Field(default_factory=list)


class OperatingAccountsUpdate(BaseModel):
    account_ids: list[int]

    @field_validator("account_ids")
    @classmethod
    def _dedupe(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


class ReserveFundStatementOut(BaseModel):
    statement_id: int
    settlement_id: int
    created_at: datetime
    operating_account_ids: list[int]
    reserve_balance_start: float
    reserve_balance_end: float
    positions_sum: float
    # reserve_balance_end - reserve_balance_start - positions_sum; 0, wenn
    # alle Bewegungen einer Position zugeordnet sind. Rein informativ, siehe
    # app/routers/reserve_fund.py.
    control_difference: float
    operating_balance_start: float
    operating_balance_end: float
    positions: list[ReserveFundPositionOut] = Field(default_factory=list)