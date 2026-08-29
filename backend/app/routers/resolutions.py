# backend/app/routers/resolutions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.access import accessible_property_ids
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.stammdaten import Owner, Property, User
from app.models.wirtschaftsplan import ResolutionCollection
from app.schemas.resolutions import ResolutionCreate, ResolutionOut

router = APIRouter(prefix="/resolutions", tags=["resolutions"])


def _require_write_role(current_user: User) -> None:
    # Gleiches Muster wie in properties.py/units.py/accounts.py - noch kein
    # gemeinsamer Ort dafür.
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Beschlüsse erfassen.",
        )


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> None:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    
def _require_read_access(current_user: User) -> None:
    """Beschluss-Sammlung ist Eigentümern/Verwaltern/Admins vorbehalten - anders
    als bei properties/units haben Mieter hier kein Einsichtsrecht."""
    if resolve_role(current_user) == "mieter":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Mieter haben keinen Zugriff auf die Beschluss-Sammlung.",
        )

@router.get("", response_model=list[ResolutionOut])
def list_resolutions(
    property_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ResolutionCollection]:
    _require_read_access(current_user)
    query = select(ResolutionCollection).where(ResolutionCollection.deleted_at.is_(None))

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None:
        query = query.where(ResolutionCollection.property_id.in_(property_ids))
    if property_id is not None:
        query = query.where(ResolutionCollection.property_id == property_id)

    query = query.order_by(ResolutionCollection.resolution_date.desc())
    return list(db.scalars(query))


@router.post("", response_model=ResolutionOut, status_code=status.HTTP_201_CREATED)
def create_resolution(
    payload: ResolutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResolutionCollection:
    _require_write_role(current_user)
    _check_property_accessible(db, payload.property_id, current_user)

    if payload.proposed_by_owner_id is not None:
        owner = db.get(Owner, payload.proposed_by_owner_id)
        if owner is None or owner.deleted_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannter Eigentümer")

    resolution = ResolutionCollection(**payload.model_dump())
    db.add(resolution)
    db.commit()
    db.refresh(resolution)
    return resolution