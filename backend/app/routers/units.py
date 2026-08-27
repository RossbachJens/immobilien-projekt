# backend/app/routers/units.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.access import accessible_property_ids
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.stammdaten import Owner, Property, Unit, User
from app.models.zuordnungen import UnitOwnerHistory
from app.schemas.units import (
    OwnerAssignmentCreate,
    OwnerAssignmentOut,
    OwnerAssignmentUpdate,
    UnitCreate,
    UnitOut,
    UnitUpdate,
)

router = APIRouter(prefix="/units", tags=["units"])


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Einheiten bearbeiten.",
        )


def _get_readable_unit(db: Session, unit_id: int, current_user: User) -> Unit:
    unit = db.get(Unit, unit_id)
    if unit is None or unit.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Einheit nicht gefunden")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and unit.property_id not in property_ids:
        # 404 statt 403 - kein Enumeration-Leak, gleiches Prinzip wie bei properties.py
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Einheit nicht gefunden")

    return unit


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> None:
    """Für Create: stellt sicher, dass die Ziel-Liegenschaft existiert UND für
    den aktuellen User zugreifbar ist - sonst könnte ein Verwalter Einheiten
    in fremden Liegenschaften anlegen, nur weil er die property_id kennt."""
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")


@router.get("", response_model=list[UnitOut])
def list_units(
    property_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Unit]:
    query = select(Unit).where(Unit.deleted_at.is_(None))

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None:
        query = query.where(Unit.property_id.in_(property_ids))

    if property_id is not None:
        query = query.where(Unit.property_id == property_id)

    return list(db.scalars(query))


@router.get("/{unit_id}", response_model=UnitOut)
def get_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Unit:
    return _get_readable_unit(db, unit_id, current_user)


@router.post("", response_model=UnitOut, status_code=status.HTTP_201_CREATED)
def create_unit(
    payload: UnitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Unit:
    _require_write_role(current_user)
    _check_property_accessible(db, payload.property_id, current_user)

    duplicate = db.scalar(
        select(Unit).where(
            Unit.property_id == payload.property_id,
            Unit.unit_number == payload.unit_number,
            Unit.deleted_at.is_(None),
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Einheit '{payload.unit_number}' existiert bereits in dieser Liegenschaft",
        )

    unit = Unit(**payload.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.patch("/{unit_id}", response_model=UnitOut)
def update_unit(
    unit_id: int,
    payload: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Unit:
    unit = _get_readable_unit(db, unit_id, current_user)
    _require_write_role(current_user)
    update_data = payload.model_dump(exclude_unset=True)

    if "unit_number" in update_data:
        duplicate = db.scalar(
            select(Unit).where(
                Unit.property_id == unit.property_id,
                Unit.unit_number == update_data["unit_number"],
                Unit.deleted_at.is_(None),
                Unit.unit_id != unit_id,
            )
        )
        if duplicate is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Einheit existiert bereits in dieser Liegenschaft")

    for field, value in update_data.items():
        setattr(unit, field, value)
    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    unit = _get_readable_unit(db, unit_id, current_user)
    _require_write_role(current_user)
    unit.deleted_at = func.now()
    db.commit()


# --- Eigentümerzuordnung (unit_owner_history) -------------------------------

@router.get("/{unit_id}/owners", response_model=list[OwnerAssignmentOut])
def list_unit_owners(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UnitOwnerHistory]:
    _get_readable_unit(db, unit_id, current_user)
    return list(
        db.scalars(
            select(UnitOwnerHistory)
            .where(UnitOwnerHistory.unit_id == unit_id)
            .order_by(UnitOwnerHistory.valid_from.desc())
        )
    )


@router.post(
    "/{unit_id}/owners", response_model=OwnerAssignmentOut, status_code=status.HTTP_201_CREATED
)
def assign_owner(
    unit_id: int,
    payload: OwnerAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnitOwnerHistory:
    _get_readable_unit(db, unit_id, current_user)
    _require_write_role(current_user)

    owner = db.get(Owner, payload.owner_id)
    if owner is None or owner.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannter Eigentümer")

    if payload.valid_to is not None and payload.valid_to <= payload.valid_from:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "valid_to muss nach valid_from liegen")

    history = UnitOwnerHistory(unit_id=unit_id, **payload.model_dump())
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


@router.patch("/{unit_id}/owners/{history_id}", response_model=OwnerAssignmentOut)
def update_owner_assignment(
    unit_id: int,
    history_id: int,
    payload: OwnerAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnitOwnerHistory:
    _get_readable_unit(db, unit_id, current_user)
    _require_write_role(current_user)

    history = db.get(UnitOwnerHistory, history_id)
    if history is None or history.unit_id != unit_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zuordnung nicht gefunden")

    update_data = payload.model_dump(exclude_unset=True)
    if update_data.get("valid_to") is not None and update_data["valid_to"] <= history.valid_from:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "valid_to muss nach valid_from liegen")

    for field, value in update_data.items():
        setattr(history, field, value)
    db.commit()
    db.refresh(history)
    return history


@router.delete("/{unit_id}/owners/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_owner_assignment(
    unit_id: int,
    history_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Hartes Löschen - unit_owner_history hat kein deleted_at, da hier nur
    Fehlerfassungen korrigiert werden. Für einen echten Eigentümerwechsel
    stattdessen PATCH nutzen (valid_to setzen), damit die Historie bleibt."""
    _get_readable_unit(db, unit_id, current_user)
    _require_write_role(current_user)

    history = db.get(UnitOwnerHistory, history_id)
    if history is None or history.unit_id != unit_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zuordnung nicht gefunden")
    db.delete(history)
    db.commit()