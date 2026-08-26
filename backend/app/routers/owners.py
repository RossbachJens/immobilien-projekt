# backend/app/routers/owners.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_value, iban_last4
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.stammdaten import Owner, User
from app.models.zuordnungen import UnitOwnerHistory
from app.schemas.owners import OwnerCreate, OwnerOut, OwnerUpdate

router = APIRouter(prefix="/owners", tags=["owners"])


def _get_active_owner(db: Session, owner_id: int) -> Owner:
    owner = db.get(Owner, owner_id)
    if owner is None or owner.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Eigentümer nicht gefunden")
    return owner


def _to_owner_out(db: Session, owner: Owner) -> OwnerOut:
    has_user = (
        db.scalar(select(User.user_id).where(User.owner_id == owner.owner_id, User.deleted_at.is_(None)))
        is not None
    )
    return OwnerOut(
        owner_id=owner.owner_id,
        first_name=owner.first_name,
        last_name=owner.last_name,
        company_name=owner.company_name,
        email=owner.email,
        phone=owner.phone,
        street_and_number=owner.street_and_number,
        postal_code=owner.postal_code,
        city=owner.city,
        bank_name=owner.bank_name,
        iban_last4=owner.iban_last4,
        sepa_mandate_reference=owner.sepa_mandate_reference,
        sepa_granted_at=owner.sepa_granted_at,
        created_at=owner.created_at,
        has_online_access=has_user,
    )


@router.get("", response_model=list[OwnerOut])
def list_owners(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> list[OwnerOut]:
    owners = list(db.scalars(select(Owner).where(Owner.deleted_at.is_(None))))
    return [_to_owner_out(db, o) for o in owners]


@router.get("/{owner_id}", response_model=OwnerOut)
def get_owner(
    owner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> OwnerOut:
    return _to_owner_out(db, _get_active_owner(db, owner_id))


@router.post("", response_model=OwnerOut, status_code=status.HTTP_201_CREATED)
def create_owner(
    payload: OwnerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> OwnerOut:
    owner = Owner(**payload.model_dump(exclude={"iban", "bic"}))

    if payload.iban:
        owner.iban_encrypted = encrypt_value(db, payload.iban)
        owner.iban_last4 = iban_last4(payload.iban)
    if payload.bic:
        owner.bic_encrypted = encrypt_value(db, payload.bic)

    db.add(owner)
    db.commit()
    db.refresh(owner)
    return _to_owner_out(db, owner)


@router.patch("/{owner_id}", response_model=OwnerOut)
def update_owner(
    owner_id: int,
    payload: OwnerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> OwnerOut:
    owner = _get_active_owner(db, owner_id)
    for field, value in payload.model_dump(exclude_unset=True, exclude={"iban", "bic"}).items():
        setattr(owner, field, value)

    unset = payload.model_fields_set
    if "iban" in unset:
        if payload.iban:
            owner.iban_encrypted = encrypt_value(db, payload.iban)
            owner.iban_last4 = iban_last4(payload.iban)
        else:
            owner.iban_encrypted = None
            owner.iban_last4 = None
    if "bic" in unset:
        owner.bic_encrypted = encrypt_value(db, payload.bic) if payload.bic else None

    owner.updated_at = func.now()
    db.commit()
    db.refresh(owner)
    return _to_owner_out(db, owner)


@router.delete("/{owner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_owner(
    owner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> None:
    owner = _get_active_owner(db, owner_id)

    if db.scalar(
        select(UnitOwnerHistory.history_id).where(
            UnitOwnerHistory.owner_id == owner_id, UnitOwnerHistory.valid_to.is_(None)
        )
    ) is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Eigentümer hat noch aktive Einheiten-Zuordnungen - diese zuerst beenden.",
        )

    if db.scalar(
        select(User.user_id).where(User.owner_id == owner_id, User.deleted_at.is_(None))
    ) is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Eigentümer ist noch mit einem aktiven User-Login verknüpft - diese "
            "Verknüpfung zuerst über PATCH /users/{user_id} entfernen.",
        )

    owner.deleted_at = func.now()
    db.commit()