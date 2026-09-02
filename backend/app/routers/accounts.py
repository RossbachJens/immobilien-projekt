# backend/app/routers/accounts.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.access import accessible_property_ids
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.buchhaltung import Account, AccountType
from app.models.stammdaten import Property, User
from app.schemas.accounts import AccountCreate, AccountOut, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Konten pflegen.",
        )


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> Property:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    return property_


def _get_editable_account(db: Session, account_id: int, current_user: User) -> Account:
    """Nur liegenschaftseigene Konten (property_id gesetzt) sind über die API
    editierbar - der globale SKR04-Basisrahmen (property_id IS NULL) wird
    ausschließlich über Alembic-Migrationen/Seed-Daten gepflegt (siehe
    PROJECTPLAN.md, Grundsatzentscheidung 'Kontenrahmen')."""
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Konto nicht gefunden")
    if account.property_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Der globale SKR04-Basisrahmen kann nicht über die API geändert werden.",
        )
    _check_property_accessible(db, account.property_id, current_user)
    return account


@router.get("", response_model=list[AccountOut])
def list_accounts(
    property_id: int | None = None,
    type: AccountType | None = None,  # noqa: A002 - Name spiegelt den Query-Parameter
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Account]:
    """Ohne property_id: nur der globale SKR04-Basisrahmen. Mit property_id:
    global + liegenschaftseigene Konten zusammen - Grundlage für Buchungs-,
    Wirtschaftsplan- und Abrechnungsformulare (siehe PROJECTPLAN.md)."""
    query = select(Account)

    if property_id is not None:
        _check_property_accessible(db, property_id, current_user)
        query = query.where(or_(Account.property_id.is_(None), Account.property_id == property_id))
    else:
        query = query.where(Account.property_id.is_(None))

    if type is not None:
        query = query.where(Account.type == type)
    if is_active is not None:
        query = query.where(Account.is_active == is_active)

    query = query.order_by(Account.account_number)
    return list(db.scalars(query))


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Account:
    _require_write_role(current_user)
    _check_property_accessible(db, payload.property_id, current_user)

    account = Account(
        account_number=payload.account_number,
        account_name=payload.account_name,
        # SKR04-Kontenklasse (0-8) entspricht der ersten Ziffer der
        # Kontonummer - wird nicht vom Client mitgeschickt (siehe
        # AccountCreate), sondern hier abgeleitet.
        account_class=payload.account_number[0],
        type=payload.type,
        is_active=True,
        is_reserve_account=payload.is_reserve_account,
        property_id=payload.property_id,
    )
    db.add(account)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Kontonummer {payload.account_number} ist für diese Liegenschaft bereits vergeben.",
        ) from exc

    db.refresh(account)
    return account


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Account:
    """account_number ist bewusst nicht änderbar (könnte sonst bestehende
    Buchungszeilen fachlich verfälschen) - siehe AccountUpdate-Schema."""
    _require_write_role(current_user)
    account = _get_editable_account(db, account_id, current_user)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)

    db.commit()
    db.refresh(account)
    return account
