# backend/app/schemas/properties.py
from datetime import datetime

from pydantic import BaseModel, Field


class PropertyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1)
    total_square_meters: float | None = Field(default=None, gt=0)
    construction_year: int | None = None
    total_mea: float | None = Field(default=None, gt=0)
    description: str | None = None


class PropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=1)
    total_square_meters: float | None = Field(default=None, gt=0)
    construction_year: int | None = None
    total_mea: float | None = Field(default=None, gt=0)
    description: str | None = None


class PropertyOut(BaseModel):
    # Bewusst kein ConfigDict(from_attributes=True)/model_validate direkt aus
    # dem ORM-Objekt - has_logo ist kein Attribut auf Property, sondern wird
    # im Router explizit berechnet (siehe app/routers/properties.py::
    # _to_property_out), damit Listenabfragen logo_content NICHT laden
    # müssen (defer, analog documents.content).
    property_id: int
    name: str
    address: str
    total_square_meters: float | None
    construction_year: int | None
    total_mea: float | None
    description: str | None
    created_at: datetime
    has_logo: bool