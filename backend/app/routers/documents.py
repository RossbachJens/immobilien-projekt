# backend/app/routers/documents.py
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.orm import Session, defer

from app.core.access import accessible_property_ids
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.documents import Document
from app.models.stammdaten import Property, User
from app.models.zuordnungen import Lease, LeaseStatus, UnitOwnerHistory
from app.schemas.documents import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])

# 20 MB - großzügig für gescannte Rechnungen/Kontoauszüge, verhindert aber,
# dass jemand versehentlich ein Vielfaches davon direkt in die DB lädt
# (Grundsatzentscheidung "Dateiinhalt als BYTEA", Chat vom 07.09.2026).
MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024

CATEGORIES = {"Kontoauszug", "Rechnung", "Angebot", "Versicherung", "Vertrag", "Protokoll", "Sonstiges"}
VISIBILITIES = {"intern", "eigentuemer", "alle"}


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Dokumente hochladen oder pflegen.",
        )


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> Property:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    return property_


def _apply_visibility_filter(query, current_user: User):
    """Admin/Verwalter (Personal) sehen alles innerhalb ihrer zugeordneten
    Liegenschaften ohne weitere Einschränkung. Eigentümer/Mieter sehen ein
    Dokument nur, wenn es entweder KEINER konkreten Person/Einheit
    zugeordnet ist (liegenschaftsweites Dokument) ODER explizit ihnen/ihrer
    Einheit zugeordnet ist - unabhängig von der visibility-Stufe schützt das
    z.B. ein einem bestimmten Mieter zugeordnetes Dokument vor anderen
    Mietern derselben Liegenschaft."""
    role = resolve_role(current_user)
    if role in ("admin", "verwalter"):
        return query

    unrelated = and_(Document.owner_id.is_(None), Document.tenant_id.is_(None), Document.unit_id.is_(None))

    if role == "eigentuemer":
        own_unit_ids = select(UnitOwnerHistory.unit_id).where(
            UnitOwnerHistory.owner_id == current_user.owner_id, UnitOwnerHistory.valid_to.is_(None)
        )
        return query.where(
            Document.visibility != "intern",
            or_(unrelated, Document.owner_id == current_user.owner_id, Document.unit_id.in_(own_unit_ids)),
        )

    if role == "mieter":
        own_unit_ids = select(Lease.unit_id).where(
            Lease.tenant_id == current_user.tenant_id,
            Lease.deleted_at.is_(None),
            Lease.status == LeaseStatus.aktiv,
        )
        return query.where(
            Document.visibility == "alle",
            or_(unrelated, Document.tenant_id == current_user.tenant_id, Document.unit_id.in_(own_unit_ids)),
        )

    return query.where(false())


def _get_visible_document(db: Session, document_id: int, current_user: User) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dokument nicht gefunden")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and document.property_id not in property_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dokument nicht gefunden")

    # Dieselbe Sichtbarkeitsregel wie in list_documents erneut anwenden -
    # sonst könnte jemand ein für ihn nicht sichtbares Dokument über eine
    # bekannte/erratene document_id direkt abrufen.
    visible_id = db.scalar(
        _apply_visibility_filter(select(Document.document_id), current_user).where(
            Document.document_id == document_id
        )
    )
    if visible_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dokument nicht gefunden")
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(
    property_id: int | None = None,
    category: str | None = None,
    unit_id: int | None = None,
    settlement_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Document]:
    query = select(Document).options(defer(Document.content)).where(Document.deleted_at.is_(None))

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None:
        query = query.where(Document.property_id.in_(property_ids))
    if property_id is not None:
        _check_property_accessible(db, property_id, current_user)
        query = query.where(Document.property_id == property_id)
    if category is not None:
        query = query.where(Document.category == category)
    if unit_id is not None:
        query = query.where(Document.unit_id == unit_id)
    if settlement_id is not None:
        query = query.where(Document.settlement_id == settlement_id)

    query = _apply_visibility_filter(query, current_user)
    query = query.order_by(Document.created_at.desc())
    return list(db.scalars(query))


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    property_id: int = Form(...),
    category: str = Form(...),
    title: str = Form(...),
    visibility: str = Form("intern"),
    unit_id: int | None = Form(None),
    owner_id: int | None = Form(None),
    tenant_id: int | None = Form(None),
    settlement_id: int | None = Form(None),
    journal_entry_id: int | None = Form(None),
    meeting_id: int | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    _require_write_role(current_user)
    _check_property_accessible(db, property_id, current_user)

    if category not in CATEGORIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unbekannte Kategorie: {category}")
    if visibility not in VISIBILITIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unbekannte Sichtbarkeit: {visibility}")

    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Datei ist leer")
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Datei zu groß (max. {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB).",
        )

    document = Document(
        property_id=property_id,
        category=category,
        unit_id=unit_id,
        owner_id=owner_id,
        tenant_id=tenant_id,
        settlement_id=settlement_id,
        journal_entry_id=journal_entry_id,
        meeting_id=meeting_id,
        title=title,
        original_filename=file.filename or "unbenannt",
        mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(content),
        content=content,
        visibility=visibility,
        uploaded_by=current_user.user_id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    document = _get_visible_document(db, document_id, current_user)
    return Response(
        content=document.content,
        media_type=document.mime_type,
        headers={"Content-Disposition": f'inline; filename="{document.original_filename}"'},
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    _require_write_role(current_user)
    document = db.get(Document, document_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dokument nicht gefunden")
    _check_property_accessible(db, document.property_id, current_user)

    document.deleted_at = func.now()
    db.commit()