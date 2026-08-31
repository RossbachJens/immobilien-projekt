# backend/app/routers/bank_accounts.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.access import accessible_property_ids
from app.core.crypto import encrypt_value, iban_last4
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.bank_accounts import PropertyBankAccount
from app.models.buchhaltung import Account, AccountType
from app.models.stammdaten import Property, User
from app.schemas.bank_accounts import BankAccountCreate, BankAccountOut, BankAccountUpdate

router = APIRouter(prefix="/bank-accounts", tags=["bank-accounts"])


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Bankkonten pflegen.",
        )


def _require_read_access(current_user: User) -> None:
    """Wie die Beschluss-Sammlung: Mieter haben kein Einsichtsrecht in die
    realen WEG-Finanzkonten."""
    if resolve_role(current_user) == "mieter":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Mieter haben keinen Zugriff auf die Bankkonten der Liegenschaft.",
        )


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> Property:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    return property_


def _validate_account(db: Session, account_id: int, property_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None or not account.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekanntes oder inaktives Konto")
    if account.property_id is not None and account.property_id != property_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Konto gehört zu einer anderen Liegenschaft")
    if account.type != AccountType.aktiv:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Ein reales Bankkonto muss mit einem Aktivkonto (Bestandskonto) verknüpft sein.",
        )
    return account


def _get_editable_bank_account(
    db: Session, bank_account_id: int, current_user: User
) -> PropertyBankAccount:
    bank_account = db.get(PropertyBankAccount, bank_account_id)
    if bank_account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bankkonto nicht gefunden")
    _check_property_accessible(db, bank_account.property_id, current_user)
    return bank_account


@router.get("", response_model=list[BankAccountOut])
def list_bank_accounts(
    property_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PropertyBankAccount]:
    _require_read_access(current_user)
    query = select(PropertyBankAccount)

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None:
        query = query.where(PropertyBankAccount.property_id.in_(property_ids))
    if property_id is not None:
        _check_property_accessible(db, property_id, current_user)
        query = query.where(PropertyBankAccount.property_id == property_id)

    query = query.order_by(PropertyBankAccount.property_id, PropertyBankAccount.account_purpose)
    return list(db.scalars(query))


@router.post("", response_model=BankAccountOut, status_code=status.HTTP_201_CREATED)
def create_bank_account(
    payload: BankAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PropertyBankAccount:
    _require_write_role(current_user)
    _check_property_accessible(db, payload.property_id, current_user)
    _validate_account(db, payload.account_id, payload.property_id)

    bank_account = PropertyBankAccount(
        property_id=payload.property_id,
        account_id=payload.account_id,
        account_purpose=payload.account_purpose,
        purpose_detail=payload.purpose_detail,
        bank_name=payload.bank_name,
    )
    if payload.iban:
        bank_account.iban_encrypted = encrypt_value(db, payload.iban)
        bank_account.iban_last4 = iban_last4(payload.iban)
    if payload.bic:
        bank_account.bic_encrypted = encrypt_value(db, payload.bic)

    db.add(bank_account)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Für dieses SKR04-Konto existiert bereits ein aktives reales Bankkonto.",
        ) from exc

    db.refresh(bank_account)
    return bank_account


@router.patch("/{bank_account_id}", response_model=BankAccountOut)
def update_bank_account(
    bank_account_id: int,
    payload: BankAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PropertyBankAccount:
    _require_write_role(current_user)
    bank_account = _get_editable_bank_account(db, bank_account_id, current_user)

    update_data = payload.model_dump(exclude_unset=True, exclude={"iban", "bic"})
    for field, value in update_data.items():
        setattr(bank_account, field, value)

    unset = payload.model_fields_set
    if "iban" in unset:
        if payload.iban:
            bank_account.iban_encrypted = encrypt_value(db, payload.iban)
            bank_account.iban_last4 = iban_last4(payload.iban)
        else:
            bank_account.iban_encrypted = None
            bank_account.iban_last4 = None
    if "bic" in unset:
        bank_account.bic_encrypted = encrypt_value(db, payload.bic) if payload.bic else None

    bank_account.updated_at = func.now()

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Für dieses SKR04-Konto existiert bereits ein aktives reales Bankkonto.",
        ) from exc

    db.refresh(bank_account)
    return bank_account