# backend/app/routers/properties.py
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, defer

from app.core.access import accessible_property_ids
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.stammdaten import Property, Unit, User
from app.schemas.properties import PropertyCreate, PropertyOut, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["properties"])

# Logo im Seitenkopf, bewusst deutlich kleiner als das 20-MB-Limit der
# allgemeinen Dokumentenverwaltung (documents) - eine Kopfgrafik braucht
# keine mehrseitigen Scans.
MAX_LOGO_SIZE_BYTES = 2 * 1024 * 1024
ALLOWED_LOGO_CONTENT_TYPES = {"image/png", "image/jpeg"}


def _get_readable_property(db: Session, property_id: int, current_user: User) -> Property:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liegenschaft nicht gefunden")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_.property_id not in property_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liegenschaft nicht gefunden")

    return property_


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Liegenschaften bearbeiten.",
        )


def _to_property_out(property_: Property, has_logo: bool) -> PropertyOut:
    return PropertyOut(
        property_id=property_.property_id,
        name=property_.name,
        address=property_.address,
        total_square_meters=property_.total_square_meters,
        construction_year=property_.construction_year,
        total_mea=property_.total_mea,
        description=property_.description,
        created_at=property_.created_at,
        has_logo=has_logo,
    )


@router.get("", response_model=list[PropertyOut])
def list_properties(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PropertyOut]:
    # logo_content wird NICHT mitgeladen (defer) - stattdessen liefert eine
    # separate, serverseitig ausgewertete Spalte nur das IS-NOT-NULL-Bit.
    # Verhindert, dass jede Listenabfrage potenziell mehrere MB Bilddaten
    # durch die DB-Verbindung schaufelt (analog defer(Document.content)).
    query = (
        select(Property, Property.logo_content.isnot(None))
        .options(defer(Property.logo_content))
        .where(Property.deleted_at.is_(None))
    )

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None:
        query = query.where(Property.property_id.in_(property_ids))

    return [_to_property_out(prop, has_logo) for prop, has_logo in db.execute(query).all()]


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PropertyOut:
    property_ = _get_readable_property(db, property_id, current_user)
    return _to_property_out(property_, has_logo=property_.logo_content is not None)


@router.post("", response_model=PropertyOut, status_code=201)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PropertyOut:
    _require_write_role(current_user)
    property_ = Property(**payload.model_dump())
    db.add(property_)
    db.commit()
    db.refresh(property_)
    return _to_property_out(property_, has_logo=False)


@router.patch("/{property_id}", response_model=PropertyOut)
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PropertyOut:
    property_ = _get_readable_property(db, property_id, current_user)
    _require_write_role(current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(property_, field, value)
    property_.updated_at = func.now()
    db.commit()
    db.refresh(property_)
    return _to_property_out(property_, has_logo=property_.logo_content is not None)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    property_ = _get_readable_property(db, property_id, current_user)
    _require_write_role(current_user)

    has_active_units = db.scalar(
        select(Unit.unit_id).where(Unit.property_id == property_id, Unit.deleted_at.is_(None))
    )
    if has_active_units is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Liegenschaft hat noch aktive Einheiten - diese zuerst löschen.",
        )

    property_.deleted_at = func.now()
    db.commit()


@router.put("/{property_id}/logo", response_model=PropertyOut)
async def upload_property_logo(
    property_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PropertyOut:
    """Lädt das Verwalter-Logo für den Seitenkopf der generierten PDFs
    (Abrechnung, Einladung, Niederschrift) hoch bzw. ersetzt es. PNG/JPEG,
    max. 2 MB - passend für eine Kopfzeile, kein allgemeiner Dokumenten-
    Upload (dafür app/routers/documents.py)."""
    property_ = _get_readable_property(db, property_id, current_user)
    _require_write_role(current_user)

    if file.content_type not in ALLOWED_LOGO_CONTENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nur PNG oder JPEG als Logo zulässig.")

    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Datei ist leer")
    if len(content) > MAX_LOGO_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Logo zu groß (max. {MAX_LOGO_SIZE_BYTES // (1024 * 1024)} MB).",
        )

    property_.logo_content = content
    property_.logo_mime_type = file.content_type
    property_.updated_at = func.now()
    db.commit()
    db.refresh(property_)
    return _to_property_out(property_, has_logo=True)


@router.delete("/{property_id}/logo", status_code=status.HTTP_204_NO_CONTENT)
def delete_property_logo(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    property_ = _get_readable_property(db, property_id, current_user)
    _require_write_role(current_user)

    property_.logo_content = None
    property_.logo_mime_type = None
    property_.updated_at = func.now()
    db.commit()


@router.get("/{property_id}/logo")
def get_property_logo(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Liefert das aktuelle Logo roh aus - fürs Vorschaubild im Frontend
    (<img src=.../logo>). Kein Content-Disposition: attachment, soll inline
    als Bild angezeigt werden."""
    property_ = _get_readable_property(db, property_id, current_user)
    if not property_.logo_content or not property_.logo_mime_type:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kein Logo hinterlegt")
    return Response(content=property_.logo_content, media_type=property_.logo_mime_type)