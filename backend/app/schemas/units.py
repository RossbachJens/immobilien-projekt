# backend/app/schemas/units.py
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UnitType = Literal["Wohnung", "Stellplatz", "Gewerbe"]


class UnitCreate(BaseModel):
    property_id: int
    unit_number: str = Field(min_length=1, max_length=20)
    floor: str | None = Field(default=None, max_length=20)
    square_meters: float = Field(gt=0)
    unit_type: UnitType | None = None


class UnitUpdate(BaseModel):
    unit_number: str | None = Field(default=None, min_length=1, max_length=20)
    floor: str | None = Field(default=None, max_length=20)
    square_meters: float | None = Field(default=None, gt=0)
    unit_type: UnitType | None = None


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unit_id: int
    property_id: int
    unit_number: str
    floor: str | None
    square_meters: float
    unit_type: str | None


class OwnerAssignmentCreate(BaseModel):
    owner_id: int
    ownership_share: float = Field(gt=0)
    valid_from: date
    valid_to: date | None = None


class OwnerAssignmentUpdate(BaseModel):
    ownership_share: float | None = Field(default=None, gt=0)
    valid_to: date | None = None


class OwnerAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    history_id: int
    unit_id: int
    owner_id: int
    ownership_share: float
    valid_from: date
    valid_to: date | None