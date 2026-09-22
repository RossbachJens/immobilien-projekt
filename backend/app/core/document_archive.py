# backend/app/core/document_archive.py
"""
Gemeinsamer Helper zum automatischen Ablegen generierter PDFs (Einladung,
Niederschrift, Abrechnung) im DMS (documents) - genutzt von
app/routers/meetings.py und app/routers/settlement_periods.py.

Jede Generierung überschreibt die vorherige Fassung: Suche nach einem
bereits vorhandenen, nicht gelöschten Dokument mit denselben Verknüpfungen
und aktualisiert dessen Inhalt in place, statt einen neuen Verlaufseintrag
anzulegen - kein DSGVO-Aufbewahrungskonflikt, da es sich um vom System
selbst reproduzierbare Dokumente handelt, nicht um Originalbelege.

match_owner_id steuert, ob owner_id Teil des Abgleichs ist:
  - Einladungen: True - dieselbe meeting_id hat mehrere Empfänger, ohne
    owner_id im Abgleich wären sie nicht unterscheidbar (auch die generische,
    unadressierte Einladung mit owner_id=None muss von den adressierten
    Einzelbriefen getrennt bleiben).
  - Abrechnungen: False (Default) - unit_id + settlement_id sind bereits
    eindeutig; bewusst OHNE owner_id im Abgleich, damit ein Eigentümerwechsel
    dieselbe Dokumentzeile weiterführt statt eine zweite anzulegen.
  - Niederschrift: False (Default) - ohnehin nur eine Fassung je meeting_id.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.documents import Document


def archive_generated_pdf(
    db: Session,
    *,
    property_id: int,
    category: str,
    title: str,
    filename: str,
    content: bytes,
    visibility: str = "eigentuemer",
    unit_id: int | None = None,
    owner_id: int | None = None,
    settlement_id: int | None = None,
    meeting_id: int | None = None,
    match_owner_id: bool = False,
    uploaded_by: int | None = None,
) -> Document:
    conditions = [
        Document.property_id == property_id,
        Document.category == category,
        Document.deleted_at.is_(None),
        Document.unit_id == unit_id if unit_id is not None else Document.unit_id.is_(None),
        Document.settlement_id == settlement_id
        if settlement_id is not None
        else Document.settlement_id.is_(None),
        Document.meeting_id == meeting_id if meeting_id is not None else Document.meeting_id.is_(None),
    ]
    if match_owner_id:
        conditions.append(Document.owner_id == owner_id if owner_id is not None else Document.owner_id.is_(None))

    existing = db.scalar(select(Document).where(*conditions))

    if existing is not None:
        existing.title = title
        existing.original_filename = filename
        existing.mime_type = "application/pdf"
        existing.file_size_bytes = len(content)
        existing.content = content
        existing.visibility = visibility
        existing.owner_id = owner_id
        existing.uploaded_by = uploaded_by
        existing.created_at = func.now()
        return existing

    document = Document(
        property_id=property_id,
        category=category,
        unit_id=unit_id,
        owner_id=owner_id,
        tenant_id=None,
        settlement_id=settlement_id,
        journal_entry_id=None,
        meeting_id=meeting_id,
        title=title,
        original_filename=filename,
        mime_type="application/pdf",
        file_size_bytes=len(content),
        content=content,
        visibility=visibility,
        uploaded_by=uploaded_by,
    )
    db.add(document)
    return document