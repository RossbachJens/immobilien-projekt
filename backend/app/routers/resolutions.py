# backend/app/routers/resolutions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
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
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Beschlüsse erfassen.",
        )


def _require_read_access(current_user: User) -> None:
    """Beschluss-Sammlung ist Eigentümern/Verwaltern/Admins vorbehalten - anders
    als bei properties/units haben Mieter hier kein Einsichtsrecht."""
    if resolve_role(current_user) == "mieter":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Mieter haben keinen Zugriff auf die Beschluss-Sammlung.",
        )


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> None:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")


def _next_lfd_nr(db: Session, property_id: int) -> int:
    """Nächste laufende Nummer für diese Liegenschaft. Bewusst ohne
    deleted_at-Filter und ohne Wiederverwendung nach Soft-Delete - siehe
    Docstring am Model. Kein explizites Row-Locking: bei der geringen
    Schreibfrequenz einer WEG-Verwaltung ist das Kollisionsrisiko
    vernachlässigbar; der UNIQUE-Constraint (Migration 0002) verhindert im
    Zweifel trotzdem doppelte Nummern (siehe IntegrityError-Handling unten).
    """
    current_max = db.scalar(
        select(func.max(ResolutionCollection.lfd_nr)).where(
            ResolutionCollection.property_id == property_id
        )
    )
    return (current_max or 0) + 1


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

    # Sortierung nach lfd_nr statt resolution_date - die laufende Nummer IST
    # die gesetzlich vorgeschriebene Eintragungsreihenfolge (kann vom
    # fachlichen Beschlussdatum abweichen, z.B. bei nachträglich erfassten
    # Umlaufbeschlüssen).
    query = query.order_by(ResolutionCollection.lfd_nr)
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

    if payload.refers_to_resolution_id is not None:
        referenced = db.get(ResolutionCollection, payload.refers_to_resolution_id)
        if referenced is None or referenced.property_id != payload.property_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Referenzierter Beschluss existiert nicht in dieser Liegenschaft.",
            )

    resolution = ResolutionCollection(
        **payload.model_dump(),
        lfd_nr=_next_lfd_nr(db, payload.property_id),
        created_by=current_user.user_id,
    )
    db.add(resolution)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Laufende Nummer wurde zwischenzeitlich vergeben - bitte erneut versuchen.",
        ) from exc

    db.refresh(resolution)
    return resolution