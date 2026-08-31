# backend/app/schemas/allocation_keys.py
from pydantic import BaseModel, ConfigDict, Field


class AllocationKeyCreate(BaseModel):
    property_id: int
    unit_id: int
    key_type: str = Field(min_length=1, max_length=50)
    numerator_value: float = Field(ge=0)
    denominator_value: float = Field(gt=0)
    valid_from_year: int = Field(ge=2000, le=2100)
    valid_to_year: int | None = Field(default=None, ge=2000, le=2100)


class AllocationKeyClose(BaseModel):
    valid_to_year: int = Field(ge=2000, le=2100)


class AllocationKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key_id: int
    property_id: int
    unit_id: int
    key_type: str
    numerator_value: float
    denominator_value: float
    valid_from_year: int
    valid_to_year: int | None