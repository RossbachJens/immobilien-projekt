# backend/app/routers/accounts.py
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.access import accessible_property_ids
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.buchhaltung import Account, AccountType, EntryDirection, EntryLine, JournalEntry
from app.models.stammdaten import Property, User
from app.schemas.accounts import (
    AccountCreate,
    AccountLedgerLineOut,
    AccountLedgerOut,
    AccountOut,
    AccountUpdate,
)

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


@router.get("/{account_id}/ledger", response_model=AccountLedgerOut)
def get_account_ledger(
    account_id: int,
    property_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountLedgerOut:
    """
    Kontenblatt: alle Buchungszeilen eines Kontos für eine Liegenschaft,
    chronologisch mit laufendem Saldo (Soll - Haben, positiv = Soll-Saldo).
    property_id ist Pflicht - ein globales SKR04-Konto wird von mehreren
    Liegenschaften genutzt, entry_lines.property_id grenzt hier auf die
    Buchungen EINER Liegenschaft ein (nicht das Konto selbst). Bei gesetztem
    date_from wird zusätzlich ein Saldovortrag aus allen früheren Buchungen
    ermittelt, analog dem Prinzip in app/core/reserve_accounts.py.
    """
    _check_property_accessible(db, property_id, current_user)

    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Konto nicht gefunden")
    if account.property_id is not None and account.property_id != property_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Konto nicht gefunden")

    if date_from is not None and date_to is not None and date_to < date_from:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "date_to darf nicht vor date_from liegen")

    opening_balance = 0.0
    if date_from is not None:
        debit_sum, credit_sum = db.execute(
            select(
                func.coalesce(
                    func.sum(case((EntryLine.direction == EntryDirection.debit, EntryLine.amount), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((EntryLine.direction == EntryDirection.credit, EntryLine.amount), else_=0)), 0
                ),
            )
            .select_from(EntryLine)
            .join(JournalEntry, JournalEntry.entry_id == EntryLine.entry_id)
            .where(
                EntryLine.account_id == account_id,
                EntryLine.property_id == property_id,
                JournalEntry.entry_date < date_from,
            )
        ).one()
        opening_balance = float(debit_sum) - float(credit_sum)

    query = (
        select(EntryLine, JournalEntry)
        .join(JournalEntry, JournalEntry.entry_id == EntryLine.entry_id)
        .where(EntryLine.account_id == account_id, EntryLine.property_id == property_id)
    )
    if date_from is not None:
        query = query.where(JournalEntry.entry_date >= date_from)
    if date_to is not None:
        query = query.where(JournalEntry.entry_date <= date_to)
    query = query.order_by(JournalEntry.entry_date, EntryLine.line_id)

    running_balance = opening_balance
    lines: list[AccountLedgerLineOut] = []
    for entry_line, journal_entry in db.execute(query).all():
        signed_amount = (
            float(entry_line.amount)
            if entry_line.direction == EntryDirection.debit
            else -float(entry_line.amount)
        )
        running_balance = round(running_balance + signed_amount, 2)
        lines.append(
            AccountLedgerLineOut(
                line_id=entry_line.line_id,
                entry_id=journal_entry.entry_id,
                entry_date=journal_entry.entry_date,
                document_reference=journal_entry.document_reference,
                description=journal_entry.description,
                unit_id=entry_line.unit_id,
                direction=entry_line.direction,
                amount=float(entry_line.amount),
                balance=running_balance,
            )
        )

    return AccountLedgerOut(
        account_id=account.account_id,
        account_number=account.account_number,
        account_name=account.account_name,
        property_id=property_id,
        date_from=date_from,
        date_to=date_to,
        opening_balance=round(opening_balance, 2),
        closing_balance=running_balance,
        lines=lines,
    )