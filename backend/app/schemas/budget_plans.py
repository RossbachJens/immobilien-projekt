# backend/app/schemas/budget_plans.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BudgetPlanStatus = Literal["Entwurf", "Beschlossen", "Inaktiv"]


class BudgetPlanCreate(BaseModel):
    property_id: int
    fiscal_year: int = Field(ge=2000, le=2100)
    title: str = Field(min_length=1, max_length=150)


class BudgetPlanStatusUpdate(BaseModel):
    status: BudgetPlanStatus


class BudgetPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    budget_id: int
    property_id: int
    fiscal_year: int
    title: str
    status: str
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
    planned_amount: float = Field(ge=0)
    # z.B. 'MEA', 'Wohnflaeche' oder ein individueller key_type aus
    # unit_allocation_keys (z.B. 'Heizkosten_Verbrauch') - bewusst kein Enum,
    # da individuelle Schlüssel je Liegenschaft frei benannt werden können.
    allocation_key_type: str = Field(min_length=1, max_length=50)


class BudgetPositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position_id: int
    budget_id: int
    account_id: int
    planned_amount: float
    allocation_key_type: str
    unit_shares: list[UnitBudgetShareOut] = Field(default_factory=list)