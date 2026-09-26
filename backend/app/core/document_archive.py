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

lease_id (Chat vom 24.09.2026, mieterseitige Betriebskostenabrechnung) geht
- wie unit_id/settlement_id/meeting_id - immer als fester Teil des Abgleichs
ein: NULL für Eigentümer-PDFs, gesetzt für Mieter-PDFs je Vertrag. Ein
Mieterwechsel bekommt dadurch bewusst eine NEUE Dokumentzeile (anders als
match_owner_id=False bei Eigentümer-Abrechnungen) - die Beträge unterscheiden
sich ja tatsächlich je Vertrag (taggenaue Verteilung), es ist also kein
"derselbe" Brief mit nur neuem Namen.

match_owner_id steuert, ob owner_id Teil des Abgleichs ist - unverändert
gegenüber der bisherigen Logik (siehe Docstring-Details in den bisherigen
Aufrufern).
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
    tenant_id: int | None = None,
    lease_id: int | None = None,
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
        Document.lease_id == lease_id if lease_id is not None else Document.lease_id.is_(None),
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
        existing.tenant_id = tenant_id
        existing.uploaded_by = uploaded_by
        existing.created_at = func.now()
        return existing

    document = Document(
        property_id=property_id,
        category=category,
        unit_id=unit_id,
        owner_id=owner_id,
        tenant_id=tenant_id,
        lease_id=lease_id,
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