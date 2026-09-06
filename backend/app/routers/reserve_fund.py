# backend/app/routers/reserve_fund.py
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.access import accessible_property_ids
from app.core.allocation import distribute_amount
from app.core.deps import get_current_user
from app.core.reserve_accounts import cumulative_balance, reserve_account_ids
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.abrechnung import SettlementPeriod
from app.models.buchhaltung import Account
from app.models.reserve_fund import (
    ReserveFundPosition,
    ReserveFundPositionAccount,
    ReserveFundStatement,
    ReserveFundStatementOperatingAccount,
    ReserveFundUnitShare,
)
from app.models.stammdaten import Property, User
from app.schemas.reserve_fund import (
    OperatingAccountsUpdate,
    ReserveFundPositionCreate,
    ReserveFundPositionOut,
    ReserveFundPositionUpdate,
    ReserveFundStatementOut,
    ReserveFundUnitShareOut,
)

router = APIRouter(prefix="/settlement-periods/{settlement_id}/reserve-fund", tags=["reserve-fund"])


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen die Rücklagendarstellung pflegen.",
        )


def _get_readable_settlement(db: Session, settlement_id: int, current_user: User) -> SettlementPeriod:
    settlement = db.get(SettlementPeriod, settlement_id)
    if settlement is None or settlement.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Abrechnung nicht gefunden")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and settlement.property_id not in property_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Abrechnung nicht gefunden")
    return settlement


def _require_draft(settlement: SettlementPeriod) -> None:
    if settlement.status != "Entwurf":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Die Rücklagendarstellung kann nur bearbeitet werden, solange die zugehörige "
            "Abrechnung im Entwurf ist.",
        )


def _get_or_create_statement(db: Session, settlement: SettlementPeriod) -> ReserveFundStatement:
    statement = db.scalar(
        select(ReserveFundStatement).where(ReserveFundStatement.settlement_id == settlement.settlement_id)
    )
    if statement is None:
        statement = ReserveFundStatement(settlement_id=settlement.settlement_id)
        db.add(statement)
        db.commit()
        db.refresh(statement)
    return statement


def _get_readable_statement(db: Session, settlement: SettlementPeriod) -> ReserveFundStatement:
    statement = db.scalar(
        select(ReserveFundStatement).where(ReserveFundStatement.settlement_id == settlement.settlement_id)
    )
    if statement is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Für diese Abrechnung wurde noch keine Rücklagendarstellung angelegt.",
        )
    return statement


def _validate_counter_accounts(db: Session, account_ids: list[int], property_id: int) -> None:
    accounts = list(db.scalars(select(Account).where(Account.account_id.in_(account_ids))))
    found_ids = {a.account_id for a in accounts}
    missing = set(account_ids) - found_ids
    if missing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unbekannte Konto-ID(s): {sorted(missing)}")
    invalid = [
        a.account_id
        for a in accounts
        if not a.is_active
        or (a.property_id is not None and a.property_id != property_id)
        or a.is_reserve_account
    ]
    if invalid:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Konto-ID(s) als Gegenkonto nicht nutzbar (inaktiv, fremde Liegenschaft oder selbst "
            f"ein Rücklagenkonto): {sorted(invalid)}",
        )


def _validate_operating_accounts(db: Session, account_ids: list[int], property_id: int) -> None:
    if not account_ids:
        return
    accounts = list(db.scalars(select(Account).where(Account.account_id.in_(account_ids))))
    found_ids = {a.account_id for a in accounts}
    missing = set(account_ids) - found_ids
    if missing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unbekannte Konto-ID(s): {sorted(missing)}")
    invalid = [
        a.account_id
        for a in accounts
        if not a.is_active or (a.property_id is not None and a.property_id != property_id)
    ]
    if invalid:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Konto-ID(s) als Bewirtschaftungskonto nicht nutzbar (inaktiv oder fremde "
            f"Liegenschaft): {sorted(invalid)}",
        )


def _compute_position_amount(
    db: Session,
    property_id: int,
    reserve_ids: list[int],
    counter_account_ids: list[int],
    period_start: date,
    period_end: date,
) -> float:
    """Summe der rücklagenseitigen Buchungszeilen (DEBIT - CREDIT) aller
    Buchungssätze im Zeitraum, die SOWOHL eine Zeile auf einem Rücklagenkonto
    ALS AUCH eine Zeile auf einem der Gegenkonten dieser Position enthalten.
    Trennt so z.B. eine Zinsgutschrift (Gegenkonto: Zinsertragskonto) von
    einer Zuführung (Gegenkonto: Girokonto), auch wenn beide dasselbe
    Rücklagenkonto betreffen."""
    from sqlalchemy import case, func

    from app.models.buchhaltung import EntryDirection, EntryLine, JournalEntry

    if not reserve_ids or not counter_account_ids:
        return 0.0

    counter_line = EntryLine.__table__.alias("counter_line")
    has_counter_line = (
        select(1)
        .select_from(counter_line)
        .where(
            counter_line.c.entry_id == EntryLine.entry_id,
            counter_line.c.account_id.in_(counter_account_ids),
        )
        .exists()
    )

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
            EntryLine.account_id.in_(reserve_ids),
            JournalEntry.property_id == property_id,
            JournalEntry.entry_date >= period_start,
            JournalEntry.entry_date <= period_end,
            has_counter_line,
        )
    ).one()
    return float(debit_sum) - float(credit_sum)


def _load_position_account_ids(db: Session, position_ids: list[int]) -> dict[int, list[int]]:
    if not position_ids:
        return {}
    rows = list(
        db.scalars(
            select(ReserveFundPositionAccount).where(
                ReserveFundPositionAccount.position_id.in_(position_ids)
            )
        )
    )
    result: dict[int, list[int]] = {}
    for row in rows:
        result.setdefault(row.position_id, []).append(row.account_id)
    return result


def _position_to_out(
    position: ReserveFundPosition, account_ids: list[int], shares: list[ReserveFundUnitShare]
) -> ReserveFundPositionOut:
    return ReserveFundPositionOut(
        position_id=position.position_id,
        statement_id=position.statement_id,
        movement_type=position.movement_type,
        description=position.description,
        allocation_key_type=position.allocation_key_type,
        actual_amount=position.actual_amount,
        account_ids=account_ids,
        unit_shares=[ReserveFundUnitShareOut.model_validate(s) for s in shares],
    )


def _build_statement_out(
    db: Session, settlement: SettlementPeriod, statement: ReserveFundStatement
) -> ReserveFundStatementOut:
    reserve_ids = reserve_account_ids(db, settlement.property_id)
    day_before_start = settlement.period_start - timedelta(days=1)

    reserve_balance_start = cumulative_balance(db, settlement.property_id, reserve_ids, day_before_start)
    reserve_balance_end = cumulative_balance(db, settlement.property_id, reserve_ids, settlement.period_end)

    operating_account_ids = list(
        db.scalars(
            select(ReserveFundStatementOperatingAccount.account_id).where(
                ReserveFundStatementOperatingAccount.statement_id == statement.statement_id
            )
        )
    )
    operating_balance_start = cumulative_balance(
        db, settlement.property_id, operating_account_ids, day_before_start
    )
    operating_balance_end = cumulative_balance(
        db, settlement.property_id, operating_account_ids, settlement.period_end
    )

    positions = list(
        db.scalars(
            select(ReserveFundPosition).where(ReserveFundPosition.statement_id == statement.statement_id)
        )
    )
    position_ids = [p.position_id for p in positions]
    accounts_by_position = _load_position_account_ids(db, position_ids)
    all_shares = (
        list(
            db.scalars(
                select(ReserveFundUnitShare).where(ReserveFundUnitShare.position_id.in_(position_ids))
            )
        )
        if position_ids
        else []
    )
    shares_by_position: dict[int, list[ReserveFundUnitShare]] = {}
    for s in all_shares:
        shares_by_position.setdefault(s.position_id, []).append(s)

    positions_sum = round(sum(p.actual_amount for p in positions), 2)

    return ReserveFundStatementOut(
        statement_id=statement.statement_id,
        settlement_id=statement.settlement_id,
        created_at=statement.created_at,
        operating_account_ids=operating_account_ids,
        reserve_balance_start=round(reserve_balance_start, 2),
        reserve_balance_end=round(reserve_balance_end, 2),
        positions_sum=positions_sum,
        control_difference=round(reserve_balance_end - reserve_balance_start - positions_sum, 2),
        operating_balance_start=round(operating_balance_start, 2),
        operating_balance_end=round(operating_balance_end, 2),
        positions=[
            _position_to_out(
                p, accounts_by_position.get(p.position_id, []), shares_by_position.get(p.position_id, [])
            )
            for p in positions
        ],
    )


@router.get("", response_model=ReserveFundStatementOut)
def get_reserve_fund_statement(
    settlement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReserveFundStatementOut:
    settlement = _get_readable_settlement(db, settlement_id, current_user)
    statement = _get_readable_statement(db, settlement)
    return _build_statement_out(db, settlement, statement)


@router.post("", response_model=ReserveFundStatementOut, status_code=status.HTTP_201_CREATED)
def create_reserve_fund_statement(
    settlement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReserveFundStatementOut:
    _require_write_role(current_user)
    settlement = _get_readable_settlement(db, settlement_id, current_user)
    statement = _get_or_create_statement(db, settlement)
    return _build_statement_out(db, settlement, statement)


@router.put("/operating-accounts", response_model=ReserveFundStatementOut)
def set_operating_accounts(
    settlement_id: int,
    payload: OperatingAccountsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReserveFundStatementOut:
    _require_write_role(current_user)
    settlement = _get_readable_settlement(db, settlement_id, current_user)
    _require_draft(settlement)
    statement = _get_or_create_statement(db, settlement)

    _validate_operating_accounts(db, payload.account_ids, settlement.property_id)

    db.query(ReserveFundStatementOperatingAccount).filter(
        ReserveFundStatementOperatingAccount.statement_id == statement.statement_id
    ).delete()
    db.add_all(
        ReserveFundStatementOperatingAccount(statement_id=statement.statement_id, account_id=aid)
        for aid in payload.account_ids
    )
    db.commit()
    return _build_statement_out(db, settlement, statement)


@router.post("/positions", response_model=ReserveFundPositionOut, status_code=status.HTTP_201_CREATED)
def create_reserve_fund_position(
    settlement_id: int,
    payload: ReserveFundPositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReserveFundPositionOut:
    _require_write_role(current_user)
    settlement = _get_readable_settlement(db, settlement_id, current_user)
    _require_draft(settlement)
    statement = _get_or_create_statement(db, settlement)

    _validate_counter_accounts(db, payload.account_ids, settlement.property_id)

    reserve_ids = reserve_account_ids(db, settlement.property_id)
    actual_amount = _compute_position_amount(
        db,
        settlement.property_id,
        reserve_ids,
        payload.account_ids,
        settlement.period_start,
        settlement.period_end,
    )

    position = ReserveFundPosition(
        statement_id=statement.statement_id,
        movement_type=payload.movement_type,
        description=payload.description,
        allocation_key_type=payload.allocation_key_type,
        actual_amount=actual_amount,
    )
    db.add(position)
    db.flush()  # vergibt position.position_id, wird für Konten-Zuordnung und Shares gebraucht

    db.add_all(
        ReserveFundPositionAccount(position_id=position.position_id, account_id=aid)
        for aid in payload.account_ids
    )

    property_ = db.get(Property, settlement.property_id)
    unit_amounts = distribute_amount(
        db, property_, actual_amount, payload.allocation_key_type, settlement.fiscal_year
    )
    shares = [
        ReserveFundUnitShare(position_id=position.position_id, unit_id=unit_id, allocated_amount=amount)
        for unit_id, amount in unit_amounts
    ]
    db.add_all(shares)
    db.commit()
    db.refresh(position)
    for s in shares:
        db.refresh(s)

    return _position_to_out(position, payload.account_ids, shares)


@router.patch("/positions/{position_id}", response_model=ReserveFundPositionOut)
def update_reserve_fund_position(
    settlement_id: int,
    position_id: int,
    payload: ReserveFundPositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReserveFundPositionOut:
    _require_write_role(current_user)
    settlement = _get_readable_settlement(db, settlement_id, current_user)
    _require_draft(settlement)
    statement = _get_readable_statement(db, settlement)

    position = db.get(ReserveFundPosition, position_id)
    if position is None or position.statement_id != statement.statement_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Position nicht gefunden")

    account_ids = payload.account_ids
    if account_ids is not None:
        _validate_counter_accounts(db, account_ids, settlement.property_id)

    update_data = payload.model_dump(exclude_unset=True, exclude={"account_ids"})
    for field, value in update_data.items():
        setattr(position, field, value)

    if account_ids is not None:
        db.query(ReserveFundPositionAccount).filter(
            ReserveFundPositionAccount.position_id == position.position_id
        ).delete()
        db.add_all(
            ReserveFundPositionAccount(position_id=position.position_id, account_id=aid)
            for aid in account_ids
        )
        effective_account_ids = account_ids
    else:
        effective_account_ids = _load_position_account_ids(db, [position.position_id]).get(
            position.position_id, []
        )

    reserve_ids = reserve_account_ids(db, settlement.property_id)
    position.actual_amount = _compute_position_amount(
        db,
        settlement.property_id,
        reserve_ids,
        effective_account_ids,
        settlement.period_start,
        settlement.period_end,
    )

    property_ = db.get(Property, settlement.property_id)
    db.query(ReserveFundUnitShare).filter(ReserveFundUnitShare.position_id == position.position_id).delete()
    unit_amounts = distribute_amount(
        db, property_, position.actual_amount, position.allocation_key_type, settlement.fiscal_year
    )
    shares = [
        ReserveFundUnitShare(position_id=position.position_id, unit_id=unit_id, allocated_amount=amount)
        for unit_id, amount in unit_amounts
    ]
    db.add_all(shares)
    db.commit()
    db.refresh(position)
    for s in shares:
        db.refresh(s)

    return _position_to_out(position, effective_account_ids, shares)


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reserve_fund_position(
    settlement_id: int,
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    _require_write_role(current_user)
    settlement = _get_readable_settlement(db, settlement_id, current_user)
    _require_draft(settlement)
    statement = _get_readable_statement(db, settlement)

    position = db.get(ReserveFundPosition, position_id)
    if position is None or position.statement_id != statement.statement_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Position nicht gefunden")

    db.query(ReserveFundUnitShare).filter(ReserveFundUnitShare.position_id == position.position_id).delete()
    db.query(ReserveFundPositionAccount).filter(
        ReserveFundPositionAccount.position_id == position.position_id
    ).delete()
    db.delete(position)
    db.commit()


@router.post("/recalculate", response_model=list[ReserveFundPositionOut])
def recalculate_reserve_fund(
    settlement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReserveFundPositionOut]:
    _require_write_role(current_user)
    settlement = _get_readable_settlement(db, settlement_id, current_user)
    _require_draft(settlement)
    statement = _get_readable_statement(db, settlement)

    reserve_ids = reserve_account_ids(db, settlement.property_id)
    property_ = db.get(Property, settlement.property_id)

    positions = list(
        db.scalars(
            select(ReserveFundPosition).where(ReserveFundPosition.statement_id == statement.statement_id)
        )
    )
    accounts_by_position = _load_position_account_ids(db, [p.position_id for p in positions])

    result: list[ReserveFundPositionOut] = []
    for position in positions:
        account_ids = accounts_by_position.get(position.position_id, [])
        position.actual_amount = _compute_position_amount(
            db,
            settlement.property_id,
            reserve_ids,
            account_ids,
            settlement.period_start,
            settlement.period_end,
        )
        db.query(ReserveFundUnitShare).filter(
            ReserveFundUnitShare.position_id == position.position_id
        ).delete()

        unit_amounts = distribute_amount(
            db, property_, position.actual_amount, position.allocation_key_type, settlement.fiscal_year
        )
        shares = [
            ReserveFundUnitShare(position_id=position.position_id, unit_id=unit_id, allocated_amount=amount)
            for unit_id, amount in unit_amounts
        ]
        db.add_all(shares)
        db.flush()
        for s in shares:
            db.refresh(s)
        result.append(_position_to_out(position, account_ids, shares))

    db.commit()
    return result