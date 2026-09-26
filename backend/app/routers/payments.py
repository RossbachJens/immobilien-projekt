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

# Getrennte Forderungskonten statt einer 1:1 payment_type -> Konto-
# Zuordnung (Chat vom 24.09.2026, "Trennung beim Zahlungseingang"): Miete
# trennt Kaltmiete (1200) von Nebenkostenvorauszahlung (1210), Hausgeld
# trennt Bewirtschaftungskosten (1220) von Instandhaltungsrücklage (1225).
COLD_RENT_ACCOUNT_NUMBER = "1200"
ADDITIONAL_COSTS_ACCOUNT_NUMBER = "1210"
HAUSGELD_OPERATING_ACCOUNT_NUMBER = "1220"
HAUSGELD_RESERVE_ACCOUNT_NUMBER = "1225"


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


def _get_global_account(db: Session, account_number: str, purpose_label: str) -> Account:
    account = db.scalar(
        select(Account).where(Account.account_number == account_number, Account.property_id.is_(None))
    )
    if account is None or not account.is_active:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Forderungskonto {account_number} ({purpose_label}) nicht im globalen Kontenrahmen "
            "gefunden - wurde Migration 0018 ausgeführt?",
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


def _hausgeld_account_ids_by_purpose(db: Session, property_id: int) -> tuple[list[int], list[int]]:
    """(operating_ids, reserve_ids) - globale + ggf. liegenschaftseigene
    Konten 1220 (Bewirtschaftung) bzw. 1225 (Instandhaltungsrücklage)."""
    operating_ids = list(
        db.scalars(
            select(Account.account_id).where(
                Account.account_number == HAUSGELD_OPERATING_ACCOUNT_NUMBER,
                or_(Account.property_id.is_(None), Account.property_id == property_id),
            )
        )
    )
    reserve_ids = list(
        db.scalars(
            select(Account.account_id).where(
                Account.account_number == HAUSGELD_RESERVE_ACCOUNT_NUMBER,
                or_(Account.property_id.is_(None), Account.property_id == property_id),
            )
        )
    )
    return operating_ids, reserve_ids


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
    # (Konto, Betrag)-Paare für die Haben-Seite - ein bis zwei Zeilen, je
    # nachdem, ob beide Anteile > 0 sind. Nur Zeilen mit amount > 0 werden
    # gebaut - entry_lines hat CHECK(amount > 0).
    credit_parts: list[tuple[Account, float]] = []

    if payload.payment_type == PaymentType.miete:
        if payload.lease_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Für Mietzahlungen ist lease_id erforderlich.")
        lease = _resolve_lease(db, payload.lease_id, unit.unit_id)

        cold_rent_amount = payload.cold_rent_amount or 0.0
        additional_costs_amount = payload.additional_costs_amount or 0.0
        if cold_rent_amount > 0:
            credit_parts.append(
                (_get_global_account(db, COLD_RENT_ACCOUNT_NUMBER, "Kaltmiete"), cold_rent_amount)
            )
        if additional_costs_amount > 0:
            credit_parts.append(
                (
                    _get_global_account(db, ADDITIONAL_COSTS_ACCOUNT_NUMBER, "Nebenkostenvorauszahlung"),
                    additional_costs_amount,
                )
            )
    else:
        if payload.lease_id is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "lease_id ist nur bei Mietzahlungen zulässig.")

        operating_amount = payload.operating_amount or 0.0
        reserve_amount = payload.reserve_amount or 0.0
        if operating_amount > 0:
            credit_parts.append(
                (
                    _get_global_account(db, HAUSGELD_OPERATING_ACCOUNT_NUMBER, "Bewirtschaftungskosten"),
                    operating_amount,
                )
            )
        if reserve_amount > 0:
            credit_parts.append(
                (
                    _get_global_account(db, HAUSGELD_RESERVE_ACCOUNT_NUMBER, "Instandhaltungsrücklage"),
                    reserve_amount,
                )
            )

    total_amount = sum(amount for _, amount in credit_parts)
    bank_account = _resolve_bank_account(db, payload.property_id, payload.payment_date, payload.bank_account_id)

    type_label = "Hausgeld" if payload.payment_type == PaymentType.hausgeld else "Miete"
    entry = JournalEntry(
        property_id=payload.property_id,
        entry_date=payload.payment_date,
        document_reference=payload.document_reference,
        description=(
            f"Zahlungseingang {type_label} – {unit.unit_number}"
            + (f" (Vertrag #{lease.lease_id})" if lease else "")
        ),
        created_by=current_user.user_id,
    )
    db.add(entry)
    db.flush()

    entry_lines = [
        EntryLine(
            entry_id=entry.entry_id,
            account_id=bank_account.account_id,
            property_id=payload.property_id,
            unit_id=None,
            lease_id=None,
            amount=total_amount,
            direction=EntryDirection.debit,
        )
    ]
    for account, amount in credit_parts:
        entry_lines.append(
            EntryLine(
                entry_id=entry.entry_id,
                account_id=account.account_id,
                property_id=payload.property_id,
                unit_id=unit.unit_id,
                lease_id=lease.lease_id if lease else None,
                amount=amount,
                direction=EntryDirection.credit,
            )
        )
    db.add_all(entry_lines)

    try:
        db.commit()
    except (IntegrityError, DataError) as exc:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Zahlungseingang konnte nicht gebucht werden.") from exc

    db.refresh(entry)
    result_lines = list(db.scalars(select(EntryLine).where(EntryLine.entry_id == entry.entry_id)))
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
        lines=[EntryLineOut.model_validate(line) for line in result_lines],
    )


@router.get("/hausgeld-overview", response_model=list[UnitHausgeldOverviewOut])
def hausgeld_overview(
    property_id: int,
    fiscal_year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UnitHausgeldOverviewOut]:
    """Soll/Ist je Einheit, jetzt zusätzlich nach Bewirtschaftung/
    Instandhaltungsrücklage getrennt. Soll-Trennung kommt aus
    accounts.is_reserve_account je Wirtschaftsplan-Position, Ist-Trennung
    aus den Forderungskonten 1220 (Bewirtschaftung) bzw. 1225 (Rücklage)."""
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
    monthly_target_reserve_by_unit: dict[int, float] = {u.unit_id: 0.0 for u in units}
    if plan is not None:
        positions = list(
            db.scalars(select(BudgetPosition).where(BudgetPosition.budget_id == plan.budget_id))
        )
        position_ids = [p.position_id for p in positions]
        is_reserve_by_position: dict[int, bool] = {}
        if positions:
            account_ids = {p.account_id for p in positions}
            accounts = list(db.scalars(select(Account).where(Account.account_id.in_(account_ids))))
            is_reserve_by_account = {a.account_id: a.is_reserve_account for a in accounts}
            is_reserve_by_position = {
                p.position_id: is_reserve_by_account.get(p.account_id, False) for p in positions
            }
        if position_ids:
            shares = list(
                db.scalars(select(UnitBudgetShare).where(UnitBudgetShare.position_id.in_(position_ids)))
            )
            for s in shares:
                monthly_target_by_unit[s.unit_id] = (
                    monthly_target_by_unit.get(s.unit_id, 0.0) + float(s.monthly_installment)
                )
                if is_reserve_by_position.get(s.position_id, False):
                    monthly_target_reserve_by_unit[s.unit_id] = (
                        monthly_target_reserve_by_unit.get(s.unit_id, 0.0) + float(s.monthly_installment)
                    )

    period_start = date(fiscal_year, 1, 1)
    today = date.today()
    if fiscal_year < today.year:
        period_end, elapsed_months = date(fiscal_year, 12, 31), 12
    elif fiscal_year == today.year:
        period_end, elapsed_months = today, today.month
    else:
        period_end, elapsed_months = period_start, 0

    operating_ids, reserve_ids = _hausgeld_account_ids_by_purpose(db, property_id)

    result: list[UnitHausgeldOverviewOut] = []
    for unit in units:
        monthly_target = round(monthly_target_by_unit.get(unit.unit_id, 0.0), 2)
        monthly_target_reserve = round(monthly_target_reserve_by_unit.get(unit.unit_id, 0.0), 2)
        target_amount = round(monthly_target * elapsed_months, 2)
        target_reserve_amount = round(monthly_target_reserve * elapsed_months, 2)

        paid_operating = _sum_unit_payments_in_range(db, unit.unit_id, operating_ids, period_start, period_end)
        paid_reserve = _sum_unit_payments_in_range(db, unit.unit_id, reserve_ids, period_start, period_end)
        paid_amount = round(paid_operating + paid_reserve, 2)
        paid_reserve_amount = round(paid_reserve, 2)

        result.append(
            UnitHausgeldOverviewOut(
                unit_id=unit.unit_id,
                unit_number=unit.unit_number,
                owner_id=_get_current_owner_id(db, unit.unit_id),
                monthly_target=monthly_target,
                monthly_target_reserve=monthly_target_reserve,
                target_amount=target_amount,
                target_reserve_amount=target_reserve_amount,
                paid_amount=paid_amount,
                paid_reserve_amount=paid_reserve_amount,
                balance=round(target_amount - paid_amount, 2),
                balance_reserve=round(target_reserve_amount - paid_reserve_amount, 2),
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
    """Chronologische Zahlungsliste für die Aufklapp-Ansicht je Einheit - eine
    gesplittete Zahlung erscheint jetzt als zwei Zeilen (Bewirtschaftung +
    Rücklage), da beide Anteile getrennte entry_lines sind."""
    _require_write_role(current_user)
    _check_property_accessible(db, property_id, current_user)
    unit = _resolve_unit(db, unit_id, property_id)

    operating_ids, reserve_ids = _hausgeld_account_ids_by_purpose(db, property_id)
    forderung_ids = operating_ids + reserve_ids
    reserve_id_set = set(reserve_ids)
    period_start = date(fiscal_year, 1, 1)
    period_end = date(fiscal_year, 12, 31)

    rows = db.execute(
        select(
            JournalEntry.entry_id,
            JournalEntry.entry_date,
            JournalEntry.document_reference,
            EntryLine.amount,
            EntryLine.account_id,
        )
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
            entry_id=r.entry_id,
            entry_date=r.entry_date,
            amount=float(r.amount),
            document_reference=r.document_reference,
            purpose="Instandhaltungsruecklage" if r.account_id in reserve_id_set else "Bewirtschaftung",
        )
        for r in rows
    ]