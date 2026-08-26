# backend/app/routers/properties.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.access import accessible_property_ids
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.stammdaten import Property, Unit, User
from app.schemas.properties import PropertyCreate, PropertyOut, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["properties"])


def _get_readable_property(db: Session, property_id: int, current_user: User) -> Property:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liegenschaft nicht gefunden")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_.property_id not in property_ids:
        # Bewusst 404 statt 403 - kein Enumeration-Leak (gleiches Prinzip wie
        # beim Login, siehe app/routers/auth.py).
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liegenschaft nicht gefunden")

    return property_


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Liegenschaften bearbeiten.",
        )


@router.get("", response_model=list[PropertyOut])
def list_properties(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Property]:
    property_ids = accessible_property_ids(db, current_user)
    query = select(Property).where(Property.deleted_at.is_(None))
    if property_ids is not None:
        query = query.where(Property.property_id.in_(property_ids))
    return list(db.scalars(query))


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Property:
    return _get_readable_property(db, property_id, current_user)


@router.post("", response_model=PropertyOut, status_code=201)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Property:
    _require_write_role(current_user)
    property_ = Property(**payload.model_dump())
    db.add(property_)
    db.commit()
    db.refresh(property_)
    return property_


@router.patch("/{property_id}", response_model=PropertyOut)
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Property:
    property_ = _get_readable_property(db, property_id, current_user)
    _require_write_role(current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(property_, field, value)
    property_.updated_at = func.now()
    db.commit()
    db.refresh(property_)
    return property_


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