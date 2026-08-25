from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.stammdaten import Property, User
from app.schemas.properties import PropertyCreate, PropertyOut

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=list[PropertyOut])
def list_properties(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: ARG001 (erzwingt Login)
) -> list[Property]:
    # TODO (spaeter in Phase 2/6): nach user_properties filtern, sobald das
    # Rollenmodell steht (siehe PROJECTPLAN.md, Defense-in-Depth mit RLS).
    return list(db.scalars(select(Property).where(Property.deleted_at.is_(None))))


@router.post("", response_model=PropertyOut, status_code=201)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> Property:
    property_ = Property(**payload.model_dump())
    db.add(property_)
    db.commit()
    db.refresh(property_)
    return property_
