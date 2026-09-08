# backend/app/schemas/documents.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    """Bewusst OHNE content-Feld - die Liste soll keine Dateiinhalte
    übertragen, nur die Metadaten. Der Download läuft über einen separaten
    Endpoint (siehe app/routers/documents.py::download_document)."""

    model_config = ConfigDict(from_attributes=True)

    document_id: int
    property_id: int
    category: str
    unit_id: int | None
    owner_id: int | None
    tenant_id: int | None
    settlement_id: int | None
    journal_entry_id: int | None
    meeting_id: int | None
    title: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    visibility: str
    uploaded_by: int | None
    created_at: datetime