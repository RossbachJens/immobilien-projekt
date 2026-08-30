# backend/app/schemas/special_assessments.py
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SpecialAssessmentStatus = Literal["Geplant", "Eingefordert", "Storniert"]


class SpecialAssessmentCreate(BaseModel):
    property_id: int
    title: str = Field(min_length=1, max_length=150)
    total_required_amount: float = Field(gt=0)
    due_date: date
    allocation_key_type: str = Field(min_length=1, max_length=50)
    # Für individuelle Umlageschlüssel (unit_allocation_keys) wird ein
    # Bezugsjahr benötigt. Beim Wirtschaftsplan liefert fiscal_year das
    # automatisch - eine Sonderumlage kann jederzeit im Jahr anfallen, daher
    # hier explizit anzugeben (Default sinnvollerweise das Jahr von due_date).
    reference_year: int = Field(ge=2000, le=2100)
    resolution_id: int | None = None


class SpecialAssessmentStatusUpdate(BaseModel):
    status: SpecialAssessmentStatus


class UnitShareStatusUpdate(BaseModel):
    is_paid: bool


class UnitSpecialAssessmentShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unit_assessment_id: int
    assessment_id: int
    unit_id: int
    allocated_assessment_amount: float
    is_paid: bool


class SpecialAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assessment_id: int
    property_id: int
    resolution_id: int | None
    title: str
    total_required_amount: float
    due_date: date
    status: str
    created_at: datetime
    unit_shares: list[UnitSpecialAssessmentShareOut] = Field(default_factory=list)