# backend/app/routers/special_assessments.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.access import accessible_property_ids
from app.core.allocation import distribute_amount
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.stammdaten import Property, User
from app.models.wirtschaftsplan import ResolutionCollection, SpecialAssessment, UnitSpecialAssessmentShare
from app.schemas.special_assessments import (
    SpecialAssessmentCreate,
    SpecialAssessmentOut,
    SpecialAssessmentStatusUpdate,
    UnitShareStatusUpdate,
    UnitSpecialAssessmentShareOut,
)

router = APIRouter(prefix="/special-assessments", tags=["special-assessments"])

# Kein Rückweg von "Eingefordert" - eine bereits eingeforderte Sonderumlage
# wird nicht zurückgeplant, nur storniert (analog Storno-Prinzip bei Buchungen).
ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "Geplant": {"Eingefordert", "Storniert"},
    "Eingefordert": {"Storniert"},
    "Storniert": set(),
}


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Sonderumlagen erfassen.",
        )


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> Property:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    return property_


def _get_readable_assessment(db: Session, assessment_id: int, current_user: User) -> SpecialAssessment:
    assessment = db.get(SpecialAssessment, assessment_id)
    if assessment is None or assessment.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sonderumlage nicht gefunden")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and assessment.property_id not in property_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sonderumlage nicht gefunden")
    return assessment


def _load_shares(db: Session, assessment_id: int) -> list[UnitSpecialAssessmentShare]:
    return list(
        db.scalars(
            select(UnitSpecialAssessmentShare).where(
                UnitSpecialAssessmentShare.assessment_id == assessment_id
            )
        )
    )


def _to_out(assessment: SpecialAssessment, shares: list[UnitSpecialAssessmentShare]) -> SpecialAssessmentOut:
    return SpecialAssessmentOut(
        assessment_id=assessment.assessment_id,
        property_id=assessment.property_id,
        resolution_id=assessment.resolution_id,
        title=assessment.title,
        total_required_amount=assessment.total_required_amount,
        due_date=assessment.due_date,
        status=assessment.status,
        created_at=assessment.created_at,
        unit_shares=[UnitSpecialAssessmentShareOut.model_validate(s) for s in shares],
    )


@router.get("", response_model=list[SpecialAssessmentOut])
def list_special_assessments(
    property_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SpecialAssessmentOut]:
    query = select(SpecialAssessment).where(SpecialAssessment.deleted_at.is_(None))

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None:
        query = query.where(SpecialAssessment.property_id.in_(property_ids))
    if property_id is not None:
        query = query.where(SpecialAssessment.property_id == property_id)

    query = query.order_by(SpecialAssessment.due_date.desc())
    assessments = list(db.scalars(query))
    if not assessments:
        return []

    assessment_ids = [a.assessment_id for a in assessments]
    all_shares = list(
        db.scalars(
            select(UnitSpecialAssessmentShare).where(
                UnitSpecialAssessmentShare.assessment_id.in_(assessment_ids)
            )
        )
    )
    shares_by_assessment: dict[int, list[UnitSpecialAssessmentShare]] = {}
    for s in all_shares:
        shares_by_assessment.setdefault(s.assessment_id, []).append(s)

    return [_to_out(a, shares_by_assessment.get(a.assessment_id, [])) for a in assessments]


@router.post("", response_model=SpecialAssessmentOut, status_code=status.HTTP_201_CREATED)
def create_special_assessment(
    payload: SpecialAssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SpecialAssessmentOut:
    _require_write_role(current_user)
    property_ = _check_property_accessible(db, payload.property_id, current_user)

    if payload.resolution_id is not None:
        resolution = db.get(ResolutionCollection, payload.resolution_id)
        if (
            resolution is None
            or resolution.deleted_at is not None
            or resolution.property_id != payload.property_id
        ):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannter Beschluss für diese Liegenschaft.")

    unit_amounts = distribute_amount(
        db, property_, payload.total_required_amount, payload.allocation_key_type, payload.reference_year
    )

    assessment = SpecialAssessment(
        property_id=payload.property_id,
        resolution_id=payload.resolution_id,
        title=payload.title,
        total_required_amount=payload.total_required_amount,
        due_date=payload.due_date,
        status="Geplant",
    )
    db.add(assessment)
    db.flush()  # vergibt assessment.assessment_id, wird für die Shares gebraucht

    shares = [
        UnitSpecialAssessmentShare(
            assessment_id=assessment.assessment_id,
            unit_id=unit_id,
            allocated_assessment_amount=amount,
        )
        for unit_id, amount in unit_amounts
    ]
    db.add_all(shares)
    db.commit()
    db.refresh(assessment)
    for s in shares:
        db.refresh(s)

    return _to_out(assessment, shares)


@router.patch("/{assessment_id}", response_model=SpecialAssessmentOut)
def update_special_assessment_status(
    assessment_id: int,
    payload: SpecialAssessmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SpecialAssessmentOut:
    _require_write_role(current_user)
    assessment = _get_readable_assessment(db, assessment_id, current_user)

    if payload.status != assessment.status and payload.status not in ALLOWED_STATUS_TRANSITIONS.get(
        assessment.status, set()
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Statuswechsel von '{assessment.status}' zu '{payload.status}' nicht erlaubt.",
        )

    assessment.status = payload.status
    db.commit()
    db.refresh(assessment)
    return _to_out(assessment, _load_shares(db, assessment.assessment_id))


@router.patch(
    "/{assessment_id}/shares/{unit_assessment_id}", response_model=UnitSpecialAssessmentShareOut
)
def update_share_payment_status(
    assessment_id: int,
    unit_assessment_id: int,
    payload: UnitShareStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnitSpecialAssessmentShare:
    """Zahlungseingang je Einheit erfassen - eigener, schlanker Endpunkt statt
    Teil des Status-Updates, da Zahlungseingänge laufend passieren, unabhängig
    vom Gesamtstatus der Sonderumlage."""
    _require_write_role(current_user)
    assessment = _get_readable_assessment(db, assessment_id, current_user)

    share = db.get(UnitSpecialAssessmentShare, unit_assessment_id)
    if share is None or share.assessment_id != assessment.assessment_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zuordnung nicht gefunden")

    share.is_paid = payload.is_paid
    db.commit()
    db.refresh(share)
    return share