# backend/app/schemas/budget_plans.py — vollständig ersetzen
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BudgetPlanStatus = Literal["Entwurf", "Beschlossen", "Inaktiv"]


class BudgetPlanCreate(BaseModel):
    property_id: int
    fiscal_year: int = Field(ge=2000, le=2100)
    title: str = Field(min_length=1, max_length=150)
    # Optional bereits bei Anlage verknüpfbar (z.B. bei einem bereits
    # vorliegenden Rahmenbeschluss) - im Normalfall wird der Beschluss erst
    # beim Statuswechsel zu "Beschlossen" zugeordnet.
    resolution_id: int | None = None


class BudgetPlanStatusUpdate(BaseModel):
    status: BudgetPlanStatus
    # Kann hier mitgegeben werden, um Verknüpfung + Statuswechsel zu
    # "Beschlossen" in einem Schritt durchzuführen.
    resolution_id: int | None = None


class BudgetPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    budget_id: int
    property_id: int
    fiscal_year: int
    title: str
    status: str
    resolution_id: int | None
    created_at: datetime


class UnitBudgetShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    share_id: int
    position_id: int
    unit_id: int
    allocated_planned_amount: float
    monthly_installment: float


class BudgetPositionCreate(BaseModel):
    account_id: int
    # Freitext-Bezeichnung, z.B. "Hausmeister", "Haftpflichtversicherung",
    # "Gebäudeversicherung" - unterscheidet Positionen, die auf dasselbe
    # generische Konto gebucht werden.
    description: str | None = Field(default=None, max_length=150)
    planned_amount: float = Field(ge=0)
    allocation_key_type: str = Field(min_length=1, max_length=50)


class BudgetPositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position_id: int
    budget_id: int
    account_id: int
    description: str | None
    planned_amount: float
    allocation_key_type: str
    unit_shares: list[UnitBudgetShareOut] = Field(default_factory=list)