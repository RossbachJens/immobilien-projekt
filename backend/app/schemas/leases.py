# backend/app/schemas/leases.py
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.zuordnungen import LeaseStatus


class LeaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lease_id: int
    unit_id: int
    tenant_id: int
    start_date: date
    end_date: date | None
    cold_rent: float
    additional_costs_prepayment: float
    status: LeaseStatus
    created_at: datetime