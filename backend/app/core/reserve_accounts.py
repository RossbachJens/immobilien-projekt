# backend/app/core/reserve_accounts.py
"""
Gemeinsame Salden-Hilfsfunktionen für Rücklagen- und Bewirtschaftungskonten -
von app/routers/reserve_fund.py (Pflege der Rücklagendarstellung) und
app/routers/settlement_periods.py (PDF-Export je Einheit) genutzt. Anders als
z.B. _hausgeld_forderung_account_ids (bewusst dupliziert in payments.py und
settlement_periods.py, da dort nur ähnliche, nicht identische Logik nötig
ist) lohnt hier die Zentralisierung, weil beide Aufrufer exakt dieselbe
Berechnung brauchen.
"""
from datetime import date

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.buchhaltung import Account, EntryDirection, EntryLine, JournalEntry


def reserve_account_ids(db: Session, property_id: int) -> list[int]:
    """Alle Rücklagenkonten (global + liegenschaftseigen) dieser Liegenschaft."""
    return list(
        db.scalars(
            select(Account.account_id).where(
                Account.is_reserve_account.is_(True),
                or_(Account.property_id.is_(None), Account.property_id == property_id),
            )
        )
    )


def cumulative_balance(db: Session, property_id: int, account_ids: list[int], as_of: date) -> float:
    """Saldo (DEBIT - CREDIT) der angegebenen Konten, kumuliert über alle
    Buchungen bis einschließlich 'as_of' - der Bestand zu einem Stichtag,
    gleichermaßen für Rücklagen- wie Bewirtschaftungskonten genutzt."""
    if not account_ids:
        return 0.0
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
            EntryLine.account_id.in_(account_ids),
            JournalEntry.property_id == property_id,
            JournalEntry.entry_date <= as_of,
        )
    ).one()
    return float(debit_sum) - float(credit_sum)