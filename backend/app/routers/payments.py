# backend/app/routers/payments.py
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.core.access import accessible_property_ids
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.bank_accounts import BankAccountPurpose, PropertyBankAccount
from app.models.buchhaltung import Account, EntryDirection, EntryLine, JournalEntry
from app.models.stammdaten import Owner, Property, Unit, User
from app.models.wirtschaftsplan import BudgetPlan, BudgetPosition, UnitBudgetShare
from app.models.zuordnungen import Lease, UnitOwnerHistory
from app.schemas.journal_entries import EntryLineOut, JournalEntryOut
from app.schemas.payments import (
    HausgeldPaymentOut,
    PaymentCreate,
    PaymentType,
    UnitHausgeldOverviewOut,
)
router = APIRouter(prefix="/payments", tags=["payments"])

FORDERUNG_ACCOUNT_NUMBERS: dict[PaymentType, str] = {
    PaymentType.hausgeld: "1220",
    PaymentType.miete: "1200",
}


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Zahlungseingänge erfassen.",
        )


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> Property:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    return property_


def _get_forderung_account(db: Session, payment_type: PaymentType) -> Account:
    account_number = FORDERUNG_ACCOUNT_NUMBERS[payment_type]
    account = db.scalar(
        select(Account).where(Account.account_number == account_number, Account.property_id.is_(None))
    )
    if account is None or not account.is_active:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Forderungskonto {account_number} nicht im globalen Kontenrahmen gefunden.",
        )
    return account


def _resolve_unit(db: Session, unit_id: int, property_id: int) -> Unit:
    unit = db.get(Unit, unit_id)
    if unit is None or unit.deleted_at is not None or unit.property_id != property_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Einheit für diese Liegenschaft")
    return unit


def _resolve_lease(db: Session, lease_id: int, unit_id: int) -> Lease:
    lease = db.get(Lease, lease_id)
    if lease is None or lease.deleted_at is not None or lease.unit_id != unit_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannter Mietvertrag für diese Einheit")
    return lease


def _resolve_bank_account(
    db: Session, property_id: int, payment_date: date, bank_account_id: int | None
) -> PropertyBankAccount:
    if bank_account_id is not None:
        bank_account = db.get(PropertyBankAccount, bank_account_id)
        if bank_account is None or bank_account.property_id != property_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekanntes Bankkonto für diese Liegenschaft")
        if not (
            bank_account.valid_from <= payment_date
            and (bank_account.valid_to is None or bank_account.valid_to >= payment_date)
        ):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bankkonto ist am Zahlungsdatum nicht gültig.")
        return bank_account

    candidates = list(
        db.scalars(
            select(PropertyBankAccount).where(
                PropertyBankAccount.property_id == property_id,
                PropertyBankAccount.account_purpose == BankAccountPurpose.girokonto,
                PropertyBankAccount.valid_from <= payment_date,
                (PropertyBankAccount.valid_to.is_(None)) | (PropertyBankAccount.valid_to >= payment_date),
            )
        )
    )
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Kein am Zahlungsdatum gültiges Girokonto für diese Liegenschaft hinterlegt - "
            "bitte zuerst unter Bankkonten anlegen oder bank_account_id angeben.",
        )
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST, "Mehr als ein gültiges Girokonto gefunden - bitte bank_account_id angeben."
    )
    
    
# backend/app/routers/payments.py — neue Helper ergänzen (nach den bestehenden _resolve_*-Funktionen)

def _hausgeld_forderung_account_ids(db: Session, property_id: int) -> list[int]:
    """Globales + ggf. liegenschaftseigenes Konto 1220 - dieselbe Logik wie in
    app/routers/settlement_periods.py, hier lokal dupliziert (noch kein
    gemeinsamer Ort dafür, siehe _require_write_role)."""
    return list(
        db.scalars(
            select(Account.account_id).where(
                Account.account_number == "1220",
                or_(Account.property_id.is_(None), Account.property_id == property_id),
            )
        )
    )


def _sum_unit_payments_in_range(
    db: Session, unit_id: int, account_ids: list[int], period_start: date, period_end: date
) -> float:
    if not account_ids or period_end < period_start:
        return 0.0
    result = db.scalar(
        select(func.coalesce(func.sum(EntryLine.amount), 0))
        .select_from(EntryLine)
        .join(JournalEntry, JournalEntry.entry_id == EntryLine.entry_id)
        .where(
            EntryLine.unit_id == unit_id,
            EntryLine.account_id.in_(account_ids),
            EntryLine.direction == EntryDirection.credit,
            JournalEntry.entry_date >= period_start,
            JournalEntry.entry_date <= period_end,
        )
    )
    return float(result or 0)


def _get_current_owner_id(db: Session, unit_id: int) -> int | None:
    return db.scalar(
        select(UnitOwnerHistory.owner_id)
        .where(UnitOwnerHistory.unit_id == unit_id, UnitOwnerHistory.valid_to.is_(None))
        .limit(1)
    )



@router.post("", response_model=JournalEntryOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JournalEntryOut:
    _require_write_role(current_user)
    _check_property_accessible(db, payload.property_id, current_user)
    unit = _resolve_unit(db, payload.unit_id, payload.property_id)

    lease: Lease | None = None
    if payload.payment_type == PaymentType.miete:
        if payload.lease_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Für Mietzahlungen ist lease_id erforderlich.")
        lease = _resolve_lease(db, payload.lease_id, unit.unit_id)
    elif payload.lease_id is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "lease_id ist nur bei Mietzahlungen zulässig.")

    forderung_account = _get_forderung_account(db, payload.payment_type)
    bank_account = _resolve_bank_account(db, payload.property_id, payload.payment_date, payload.bank_account_id)

    type_label = "Hausgeld" if payload.payment_type == PaymentType.hausgeld else "Miete"
    entry = JournalEntry(
        property_id=payload.property_id,
        entry_date=payload.payment_date,
        document_reference=payload.reference,
        description=(
            f"Zahlungseingang {type_label} – {unit.unit_number}"
            + (f" (Vertrag #{lease.lease_id})" if lease else "")
        ),
        created_by=current_user.user_id,
    )
    db.add(entry)
    db.flush()

    db.add_all(
        [
            EntryLine(
                entry_id=entry.entry_id,
                account_id=bank_account.account_id,
                property_id=payload.property_id,
                # Bankseite bleibt bewusst liegenschaftsebene (kein unit_id) -
                # das Geld liegt auf dem gemeinsamen Konto, erst die
                # Forderungsseite ist einheitenscharf.
                unit_id=None,
                lease_id=None,
                amount=payload.amount,
                direction=EntryDirection.debit,
            ),
            EntryLine(
                entry_id=entry.entry_id,
                account_id=forderung_account.account_id,
                property_id=payload.property_id,
                unit_id=unit.unit_id,
                lease_id=lease.lease_id if lease else None,
                amount=payload.amount,
                direction=EntryDirection.credit,
            ),
        ]
    )

    try:
        db.commit()
    except (IntegrityError, DataError) as exc:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Zahlungseingang konnte nicht gebucht werden.") from exc

    db.refresh(entry)
    lines = list(db.scalars(select(EntryLine).where(EntryLine.entry_id == entry.entry_id)))
    return JournalEntryOut(
        entry_id=entry.entry_id,
        property_id=entry.property_id,
        entry_date=entry.entry_date,
        document_reference=entry.document_reference,
        description=entry.description,
        created_by=entry.created_by,
        created_at=entry.created_at,
        locked_at=entry.locked_at,
        reversed_entry_id=entry.reversed_entry_id,
        lines=[EntryLineOut.model_validate(line) for line in lines],
    )

# backend/app/routers/payments.py — zwei neue Endpunkte ergänzen (nach create_payment)

@router.get("/hausgeld-overview", response_model=list[UnitHausgeldOverviewOut])
def hausgeld_overview(
    property_id: int,
    fiscal_year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UnitHausgeldOverviewOut]:
    """Soll/Ist je Einheit für ein Wirtschaftsjahr - bewusst nur für
    Admin/Verwalter (keine Eigentümersicht). Soll kommt aus dem BESCHLOSSENEN
    Wirtschaftsplan des Jahres (Summe monthly_installment über alle
    Positionen × vergangene Monate), Ist aus den tatsächlichen
    Zahlungseingängen auf das Hausgeld-Forderungskonto 1220."""
    _require_write_role(current_user)
    _check_property_accessible(db, property_id, current_user)

    plan = db.scalar(
        select(BudgetPlan).where(
            BudgetPlan.property_id == property_id,
            BudgetPlan.fiscal_year == fiscal_year,
            BudgetPlan.status == "Beschlossen",
            BudgetPlan.deleted_at.is_(None),
        )
    )

    units = list(
        db.scalars(select(Unit).where(Unit.property_id == property_id, Unit.deleted_at.is_(None)))
    )

    monthly_target_by_unit: dict[int, float] = {u.unit_id: 0.0 for u in units}
    if plan is not None:
        position_ids = list(
            db.scalars(select(BudgetPosition.position_id).where(BudgetPosition.budget_id == plan.budget_id))
        )
        if position_ids:
            shares = list(
                db.scalars(select(UnitBudgetShare).where(UnitBudgetShare.position_id.in_(position_ids)))
            )
            for s in shares:
                monthly_target_by_unit[s.unit_id] = (
                    monthly_target_by_unit.get(s.unit_id, 0.0) + float(s.monthly_installment)
                )

    period_start = date(fiscal_year, 1, 1)
    today = date.today()
    if fiscal_year < today.year:
        period_end, elapsed_months = date(fiscal_year, 12, 31), 12
    elif fiscal_year == today.year:
        period_end, elapsed_months = today, today.month
    else:
        period_end, elapsed_months = period_start, 0

    forderung_ids = _hausgeld_forderung_account_ids(db, property_id)

    result: list[UnitHausgeldOverviewOut] = []
    for unit in units:
        monthly_target = round(monthly_target_by_unit.get(unit.unit_id, 0.0), 2)
        target_amount = round(monthly_target * elapsed_months, 2)
        paid_amount = round(
            _sum_unit_payments_in_range(db, unit.unit_id, forderung_ids, period_start, period_end), 2
        )
        result.append(
            UnitHausgeldOverviewOut(
                unit_id=unit.unit_id,
                unit_number=unit.unit_number,
                owner_id=_get_current_owner_id(db, unit.unit_id),
                monthly_target=monthly_target,
                target_amount=target_amount,
                paid_amount=paid_amount,
                balance=round(target_amount - paid_amount, 2),
                has_budget_plan=plan is not None,
            )
        )
    return result


@router.get("/hausgeld-payments", response_model=list[HausgeldPaymentOut])
def list_hausgeld_payments(
    property_id: int,
    unit_id: int,
    fiscal_year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HausgeldPaymentOut]:
    """Chronologische Zahlungsliste für die Aufklapp-Ansicht je Einheit."""
    _require_write_role(current_user)
    _check_property_accessible(db, property_id, current_user)
    unit = _resolve_unit(db, unit_id, property_id)

    forderung_ids = _hausgeld_forderung_account_ids(db, property_id)
    period_start = date(fiscal_year, 1, 1)
    period_end = date(fiscal_year, 12, 31)

    rows = db.execute(
        select(JournalEntry.entry_id, JournalEntry.entry_date, JournalEntry.document_reference, EntryLine.amount)
        .select_from(EntryLine)
        .join(JournalEntry, JournalEntry.entry_id == EntryLine.entry_id)
        .where(
            EntryLine.unit_id == unit.unit_id,
            EntryLine.account_id.in_(forderung_ids),
            EntryLine.direction == EntryDirection.credit,
            JournalEntry.entry_date >= period_start,
            JournalEntry.entry_date <= period_end,
        )
        .order_by(JournalEntry.entry_date)
    ).all()

    return [
        HausgeldPaymentOut(
            entry_id=r.entry_id, entry_date=r.entry_date, amount=float(r.amount), document_reference=r.document_reference
        )
        for r in rows
    ]