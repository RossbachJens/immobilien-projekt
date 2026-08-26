# backend/app/schemas/properties.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PropertyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1)
    total_square_meters: float | None = Field(default=None, gt=0)
    construction_year: int | None = None
    description: str | None = None


class PropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=1)
    total_square_meters: float | None = Field(default=None, gt=0)
    construction_year: int | None = None
    description: str | None = None


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    property_id: int
    name: str
    address: str
    total_square_meters: float | None
    construction_year: int | None
    description: str | None
    created_at: datetime