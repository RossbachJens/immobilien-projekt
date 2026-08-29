# backend/app/schemas/resolutions.py
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ResolutionCreate(BaseModel):
    property_id: int
    resolution_date: date
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    # z.B. 'Eigentuemerversammlung', 'Umlaufbeschluss' - bewusst kein Enum,
    # da die genaue Terminologie je WEG-Ordnung variieren kann.
    resolution_type: str | None = Field(default=None, max_length=50)
    proposed_by_owner_id: int | None = None


class ResolutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resolution_id: int
    property_id: int
    resolution_date: date
    title: str
    description: str | None
    resolution_type: str | None
    proposed_by_owner_id: int | None
    created_at: datetime