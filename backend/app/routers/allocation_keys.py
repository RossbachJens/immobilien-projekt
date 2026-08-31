# backend/app/routers/allocation_keys.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.access import accessible_property_ids
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.stammdaten import Property, Unit, User
from app.models.zuordnungen import UnitAllocationKey
from app.schemas.allocation_keys import AllocationKeyClose, AllocationKeyCreate, AllocationKeyOut

router = APIRouter(prefix="/allocation-keys", tags=["allocation-keys"])


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Umlageschlüssel pflegen.",
        )


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> Property:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    return property_


def _resolve_unit(db: Session, unit_id: int, property_id: int) -> Unit:
    unit = db.get(Unit, unit_id)
    if unit is None or unit.deleted_at is not None or unit.property_id != property_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Einheit für diese Liegenschaft")
    return unit


def _get_editable_key(db: Session, key_id: int, current_user: User) -> UnitAllocationKey:
    key = db.get(UnitAllocationKey, key_id)
    if key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Umlageschlüssel nicht gefunden")
    _check_property_accessible(db, key.property_id, current_user)
    return key


@router.get("", response_model=list[AllocationKeyOut])
def list_allocation_keys(
    property_id: int | None = None,
    unit_id: int | None = None,
    key_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UnitAllocationKey]:
    query = select(UnitAllocationKey)

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None:
        query = query.where(UnitAllocationKey.property_id.in_(property_ids))
    if property_id is not None:
        _check_property_accessible(db, property_id, current_user)
        query = query.where(UnitAllocationKey.property_id == property_id)
    if unit_id is not None:
        query = query.where(UnitAllocationKey.unit_id == unit_id)
    if key_type is not None:
        query = query.where(UnitAllocationKey.key_type == key_type)

    query = query.order_by(
        UnitAllocationKey.unit_id, UnitAllocationKey.key_type, UnitAllocationKey.valid_from_year.desc()
    )
    return list(db.scalars(query))


@router.post("", response_model=AllocationKeyOut, status_code=status.HTTP_201_CREATED)
def create_allocation_key(
    payload: AllocationKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnitAllocationKey:
    _require_write_role(current_user)
    _check_property_accessible(db, payload.property_id, current_user)
    _resolve_unit(db, payload.unit_id, payload.property_id)

    if payload.valid_to_year is not None and payload.valid_to_year < payload.valid_from_year:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "valid_to_year darf nicht vor valid_from_year liegen")

    key = UnitAllocationKey(**payload.model_dump())
    db.add(key)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Für diese Einheit/diesen Schlüsseltyp existiert bereits ein überlappender "
            "Gültigkeitszeitraum - bitte zuerst den bisherigen Schlüssel schließen (PATCH, valid_to_year).",
        ) from exc

    db.refresh(key)
    return key


@router.patch("/{key_id}", response_model=AllocationKeyOut)
def close_allocation_key(
    key_id: int,
    payload: AllocationKeyClose,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnitAllocationKey:
    _require_write_role(current_user)
    key = _get_editable_key(db, key_id, current_user)

    if payload.valid_to_year < key.valid_from_year:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "valid_to_year darf nicht vor valid_from_year liegen")

    key.valid_to_year = payload.valid_to_year
    db.commit()
    db.refresh(key)
    return key