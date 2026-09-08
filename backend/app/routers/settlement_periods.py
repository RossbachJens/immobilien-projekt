# backend/app/routers/settlement_periods.py
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from io import BytesIO

from app.core.access import accessible_property_ids
from app.core.allocation import compute_unit_fractions, distribute_amount
from app.core.deps import get_current_user
from app.core.reserve_accounts import cumulative_balance, reserve_account_ids
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.abrechnung import (
    SettlementPeriod,
    SettlementPosition,
    SettlementPositionAccount,
    UnitSettlementShare,
    UnitSettlementSummary,
    UnitSettlementTaxShare,
)
from app.models.buchhaltung import Account, AccountType, EntryDirection, EntryLine, JournalEntry
from app.models.reserve_fund import (
    MOVEMENT_TYPE_LABELS,
    ReserveFundPosition,
    ReserveFundStatement,
    ReserveFundStatementOperatingAccount,
    ReserveFundUnitShare,
)
from app.models.stammdaten import Property, Unit, User
from app.models.wirtschaftsplan import ResolutionCollection
from app.schemas.settlement import (
    SettlementPeriodCreate,
    SettlementPeriodOut,
    SettlementPeriodStatusUpdate,
    SettlementPositionCreate,
    SettlementPositionOut,
    SettlementPositionUpdate,
    UnitSettlementShareOut,
    UnitSettlementSummaryOut,
    UnitSettlementTaxShareOut,
)
from app.models.stammdaten import Owner
from app.models.zuordnungen import UnitOwnerHistory
from app.services.settlement_pdf import (
    ReserveFundPdfData,
    ReserveFundPdfPosition,
    TaxCertificatePdfPosition,
    build_settlement_pdf,
)

router = APIRouter(prefix="/settlement-periods", tags=["settlement-periods"])

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "Entwurf": {"Beschlossen", "Inaktiv"},
    "Beschlossen": {"Inaktiv"},
    "Inaktiv": set(),
}

HAUSGELD_FORDERUNG_NUMBER = "1220"


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Abrechnungen pflegen.",
        )


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> Property:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    return property_


def _get_readable_period(db: Session, settlement_id: int, current_user: User) -> SettlementPeriod:
    settlement = db.get(SettlementPeriod, settlement_id)
    if settlement is None or settlement.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Abrechnung nicht gefunden")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and settlement.property_id not in property_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Abrechnung nicht gefunden")
    return settlement


def _validate_resolution(db: Session, resolution_id: int, property_id: int) -> None:
    resolution = db.get(ResolutionCollection, resolution_id)
    if resolution is None or resolution.deleted_at is not None or resolution.property_id != property_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannter Beschluss für diese Liegenschaft.")


def _compute_actual_amount(
    db: Session, property_id: int, account_ids: list[int], period_start, period_end
) -> float:
    """Ist-Kosten je Position = Soll-Summe minus Haben-Summe im Zeitraum,
    über ALLE gepoolten Konten dieser Position hinweg summiert - nettet
    Stornos automatisch heraus (siehe
    app/routers/journal_entries.py::storno_journal_entry)."""
    debit_sum, credit_sum = db.execute(
        select(
            func.coalesce(func.sum(case((EntryLine.direction == EntryDirection.debit, EntryLine.amount), else_=0)), 0),
            func.coalesce(func.sum(case((EntryLine.direction == EntryDirection.credit, EntryLine.amount), else_=0)), 0),
        )
        .select_from(EntryLine)
        .join(JournalEntry, JournalEntry.entry_id == EntryLine.entry_id)
        .where(
            EntryLine.account_id.in_(account_ids),
            EntryLine.property_id == property_id,
            JournalEntry.entry_date >= period_start,
            JournalEntry.entry_date <= period_end,
        )
    ).one()
    return float(debit_sum) - float(credit_sum)

def _load_position_account_ids(db: Session, position_ids: list[int]) -> dict[int, list[int]]:
    if not position_ids:
        return {}
    rows = list(
        db.scalars(
            select(SettlementPositionAccount).where(
                SettlementPositionAccount.position_id.in_(position_ids)
            )
        )
    )
    result: dict[int, list[int]] = {}
    for row in rows:
        result.setdefault(row.position_id, []).append(row.account_id)
    return result


def _load_position_tax_shares(db: Session, position_ids: list[int]) -> dict[int, list[UnitSettlementTaxShare]]:
    if not position_ids:
        return {}
    rows = list(
        db.scalars(select(UnitSettlementTaxShare).where(UnitSettlementTaxShare.position_id.in_(position_ids)))
    )
    result: dict[int, list[UnitSettlementTaxShare]] = {}
    for row in rows:
        result.setdefault(row.position_id, []).append(row)
    return result


def _validate_tax_category(tax_category: str, deductible_amount: float | None, actual_amount: float) -> None:
    if tax_category == "keine":
        return
    if deductible_amount is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Bei haushaltsnahen Dienstleistungen/Handwerkerleistungen ist der Lohnanteil "
            "(deductible_amount) anzugeben.",
        )
    if deductible_amount > actual_amount:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Der Lohnanteil ({deductible_amount:.2f} €) darf die Ist-Kosten der Position "
            f"({actual_amount:.2f} €) nicht übersteigen.",
        )


def _replace_tax_shares(
    db: Session, property_: Property, settlement: SettlementPeriod, position: SettlementPosition
) -> list[UnitSettlementTaxShare]:
    """Löscht bestehende §35a-Anteile der Position und legt sie bei
    tax_category != 'keine' neu an - gleiche Verteilungslogik wie bei den
    Ist-Kosten-Anteilen (unit_settlement_shares), nur mit deductible_amount
    statt actual_amount als zu verteilendem Gesamtbetrag."""
    db.query(UnitSettlementTaxShare).filter(UnitSettlementTaxShare.position_id == position.position_id).delete()

    if position.tax_category == "keine" or not position.deductible_amount:
        return []

    unit_amounts = distribute_amount(
        db, property_, position.deductible_amount, position.allocation_key_type, settlement.fiscal_year
    )
    tax_shares = [
        UnitSettlementTaxShare(
            position_id=position.position_id, unit_id=unit_id, allocated_deductible_amount=amount
        )
        for unit_id, amount in unit_amounts
    ]
    db.add_all(tax_shares)
    db.flush()
    for s in tax_shares:
        db.refresh(s)
    return tax_shares


def _validate_settlement_accounts(db: Session, account_ids: list[int], property_id: int) -> None:
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
        or (a.type != AccountType.aufwand and not a.is_reserve_account)
    ]
    if invalid:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Konto-ID(s) für eine Abrechnungsposition nicht nutzbar (inaktiv, fremde "
            f"Liegenschaft oder weder Aufwands- noch Rücklagenkonto): {sorted(invalid)}",
        )

def _hausgeld_forderung_account_ids(db: Session, property_id: int) -> list[int]:
    return list(
        db.scalars(
            select(Account.account_id).where(
                Account.account_number == HAUSGELD_FORDERUNG_NUMBER,
                or_(Account.property_id.is_(None), Account.property_id == property_id),
            )
        )
    )


def _sum_unit_prepayments(db: Session, unit_id: int, account_ids: list[int], period_start, period_end) -> float:
    if not account_ids:
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


def _recompute_summaries(db: Session, settlement: SettlementPeriod) -> None:
    positions = list(
        db.scalars(select(SettlementPosition).where(SettlementPosition.settlement_id == settlement.settlement_id))
    )
    position_ids = [p.position_id for p in positions]
    shares = (
        list(db.scalars(select(UnitSettlementShare).where(UnitSettlementShare.position_id.in_(position_ids))))
        if position_ids
        else []
    )
    costs_by_unit: dict[int, float] = {}
    for s in shares:
        costs_by_unit[s.unit_id] = costs_by_unit.get(s.unit_id, 0.0) + float(s.allocated_actual_amount)

    units = list(
        db.scalars(select(Unit).where(Unit.property_id == settlement.property_id, Unit.deleted_at.is_(None)))
    )
    hausgeld_account_ids = _hausgeld_forderung_account_ids(db, settlement.property_id)

    for unit in units:
        total_costs = round(costs_by_unit.get(unit.unit_id, 0.0), 2)
        total_prepayments = round(
            _sum_unit_prepayments(db, unit.unit_id, hausgeld_account_ids, settlement.period_start, settlement.period_end),
            2,
        )
        balance = round(total_costs - total_prepayments, 2)

        existing = db.scalar(
            select(UnitSettlementSummary).where(
                UnitSettlementSummary.settlement_id == settlement.settlement_id,
                UnitSettlementSummary.unit_id == unit.unit_id,
            )
        )
        if existing is not None:
            existing.total_actual_costs = total_costs
            existing.total_prepayments = total_prepayments
            existing.balance = balance
        else:
            db.add(
                UnitSettlementSummary(
                    settlement_id=settlement.settlement_id,
                    unit_id=unit.unit_id,
                    total_actual_costs=total_costs,
                    total_prepayments=total_prepayments,
                    balance=balance,
                )
            )
    db.commit()


def _position_to_out(
    position: SettlementPosition,
    account_ids: list[int],
    shares: list[UnitSettlementShare],
    tax_shares: list[UnitSettlementTaxShare] | None = None,
) -> SettlementPositionOut:
    return SettlementPositionOut(
        position_id=position.position_id,
        settlement_id=position.settlement_id,
        account_ids=account_ids,
        description=position.description,
        actual_amount=position.actual_amount,
        allocation_key_type=position.allocation_key_type,
        is_apportionable=position.is_apportionable,
        tax_category=position.tax_category,
        deductible_amount=position.deductible_amount,
        unit_shares=[UnitSettlementShareOut.model_validate(s) for s in shares],
        tax_shares=[UnitSettlementTaxShareOut.model_validate(s) for s in (tax_shares or [])],
    )

def _get_current_owner(db: Session, unit_id: int) -> Owner | None:
    return db.scalar(
        select(Owner)
        .join(UnitOwnerHistory, UnitOwnerHistory.owner_id == Owner.owner_id)
        .where(UnitOwnerHistory.unit_id == unit_id, UnitOwnerHistory.valid_to.is_(None))
        .limit(1)
    )


def _build_reserve_fund_pdf_data(
    db: Session, settlement: SettlementPeriod, property_: Property, unit_id: int
) -> ReserveFundPdfData | None:
    """Bündelt alle für den PDF-Export einer Einheit nötigen Rücklagen-/
    Vermögensdaten - liefert None, wenn für diese Abrechnung (noch) keine
    Rücklagendarstellung angelegt wurde (siehe app/routers/reserve_fund.py)."""
    statement = db.scalar(
        select(ReserveFundStatement).where(ReserveFundStatement.settlement_id == settlement.settlement_id)
    )
    if statement is None:
        return None

    reserve_ids = reserve_account_ids(db, settlement.property_id)
    day_before_start = settlement.period_start - timedelta(days=1)

    reserve_balance_start = cumulative_balance(db, settlement.property_id, reserve_ids, day_before_start)
    reserve_balance_end = cumulative_balance(db, settlement.property_id, reserve_ids, settlement.period_end)

    # Der Rücklagenbestand selbst folgt gesetzlich immer den Miteigentums-
    # anteilen (§ 16 WEG), unabhängig vom Verteilerschlüssel einzelner
    # Positionen - daher hier fest "MEA".
    mea_fractions = compute_unit_fractions(db, property_, "MEA", settlement.fiscal_year)
    unit_fraction = mea_fractions.get(unit_id, 0.0)

    positions = list(
        db.scalars(
            select(ReserveFundPosition).where(ReserveFundPosition.statement_id == statement.statement_id)
        )
    )
    position_ids = [p.position_id for p in positions]
    unit_shares = (
        list(
            db.scalars(
                select(ReserveFundUnitShare).where(
                    ReserveFundUnitShare.position_id.in_(position_ids),
                    ReserveFundUnitShare.unit_id == unit_id,
                )
            )
        )
        if position_ids
        else []
    )
    unit_share_by_position = {s.position_id: s.allocated_amount for s in unit_shares}

    pdf_positions = [
        ReserveFundPdfPosition(
            movement_type_label=MOVEMENT_TYPE_LABELS.get(p.movement_type, p.movement_type),
            description=p.description,
            allocation_key_type=p.allocation_key_type,
            actual_amount=p.actual_amount,
            unit_share=unit_share_by_position.get(p.position_id, 0.0),
        )
        for p in positions
    ]

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

    return ReserveFundPdfData(
        reserve_balance_start=round(reserve_balance_start, 2),
        reserve_balance_start_unit_share=round(reserve_balance_start * unit_fraction, 2),
        reserve_balance_end=round(reserve_balance_end, 2),
        reserve_balance_end_unit_share=round(reserve_balance_end * unit_fraction, 2),
        positions=pdf_positions,
        operating_balance_start=round(operating_balance_start, 2),
        operating_balance_end=round(operating_balance_end, 2),
    )


def _build_tax_certificate_pdf_data(
    db: Session, unit_id: int, positions: list[SettlementPosition]
) -> list[TaxCertificatePdfPosition]:
    """§35a-relevante Positionen dieser Abrechnung, für eine Einheit
    aufbereitet - reine Projektion der bereits beim Anlegen/Aktualisieren
    berechneten unit_settlement_tax_shares (siehe _replace_tax_shares), kein
    erneutes distribute_amount hier."""
    relevant = [p for p in positions if p.tax_category != "keine" and p.deductible_amount]
    if not relevant:
        return []

    position_ids = [p.position_id for p in relevant]
    tax_shares = list(
        db.scalars(
            select(UnitSettlementTaxShare).where(
                UnitSettlementTaxShare.position_id.in_(position_ids),
                UnitSettlementTaxShare.unit_id == unit_id,
            )
        )
    )
    share_by_position = {s.position_id: s for s in tax_shares}

    return [
        TaxCertificatePdfPosition(
            description=p.description or "Position",
            tax_category=p.tax_category,
            is_apportionable=p.is_apportionable,
            allocation_key_type=p.allocation_key_type,
            total_deductible_amount=float(p.deductible_amount),
            unit_deductible_amount=float(share_by_position[p.position_id].allocated_deductible_amount)
            if p.position_id in share_by_position
            else 0.0,
        )
        for p in relevant
    ]


@router.get("", response_model=list[SettlementPeriodOut])
def list_settlement_periods(
    property_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SettlementPeriod]:
    query = select(SettlementPeriod).where(SettlementPeriod.deleted_at.is_(None))

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None:
        query = query.where(SettlementPeriod.property_id.in_(property_ids))
    if property_id is not None:
        query = query.where(SettlementPeriod.property_id == property_id)

    query = query.order_by(SettlementPeriod.fiscal_year.desc())
    return list(db.scalars(query))


@router.post("", response_model=SettlementPeriodOut, status_code=status.HTTP_201_CREATED)
def create_settlement_period(
    payload: SettlementPeriodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SettlementPeriod:
    _require_write_role(current_user)
    _check_property_accessible(db, payload.property_id, current_user)

    if payload.resolution_id is not None:
        _validate_resolution(db, payload.resolution_id, payload.property_id)

    settlement = SettlementPeriod(**payload.model_dump())
    db.add(settlement)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Für {payload.fiscal_year} existiert bereits eine Abrechnung dieser Liegenschaft.",
        ) from exc

    db.refresh(settlement)
    return settlement


@router.patch("/{settlement_id}", response_model=SettlementPeriodOut)
def update_settlement_period_status(
    settlement_id: int,
    payload: SettlementPeriodStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SettlementPeriod:
    _require_write_role(current_user)
    settlement = _get_readable_period(db, settlement_id, current_user)

    if payload.status != settlement.status and payload.status not in ALLOWED_STATUS_TRANSITIONS.get(
        settlement.status, set()
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Statuswechsel von '{settlement.status}' zu '{payload.status}' nicht erlaubt.",
        )

    if payload.resolution_id is not None:
        _validate_resolution(db, payload.resolution_id, settlement.property_id)
        settlement.resolution_id = payload.resolution_id

    effective_resolution_id = payload.resolution_id if payload.resolution_id is not None else settlement.resolution_id
    if payload.status == "Beschlossen" and effective_resolution_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Eine Abrechnung kann erst nach Zuordnung eines Beschlusses aus der Beschluss-Sammlung beschlossen werden.",
        )

    settlement.status = payload.status
    db.commit()
    db.refresh(settlement)
    return settlement


@router.get("/{settlement_id}/positions", response_model=list[SettlementPositionOut])
def list_settlement_positions(
    settlement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SettlementPositionOut]:
    settlement = _get_readable_period(db, settlement_id, current_user)
    positions = list(
        db.scalars(select(SettlementPosition).where(SettlementPosition.settlement_id == settlement.settlement_id))
    )
    if not positions:
        return []

    position_ids = [p.position_id for p in positions]
    all_shares = list(db.scalars(select(UnitSettlementShare).where(UnitSettlementShare.position_id.in_(position_ids))))
    shares_by_position: dict[int, list[UnitSettlementShare]] = {}
    for s in all_shares:
        shares_by_position.setdefault(s.position_id, []).append(s)

    accounts_by_position = _load_position_account_ids(db, position_ids)
    tax_shares_by_position = _load_position_tax_shares(db, position_ids)

    return [
        _position_to_out(
            p,
            accounts_by_position.get(p.position_id, []),
            shares_by_position.get(p.position_id, []),
            tax_shares_by_position.get(p.position_id, []),
        )
        for p in positions
    ]


@router.post(
    "/{settlement_id}/positions", response_model=SettlementPositionOut, status_code=status.HTTP_201_CREATED
)
def create_settlement_position(
    settlement_id: int,
    payload: SettlementPositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SettlementPositionOut:
    _require_write_role(current_user)
    settlement = _get_readable_period(db, settlement_id, current_user)

    if settlement.status != "Entwurf":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Positionen können nur bearbeitet werden, solange die Abrechnung im Entwurf ist.",
        )

    _validate_settlement_accounts(db, payload.account_ids, settlement.property_id)

    actual_amount = _compute_actual_amount(
        db, settlement.property_id, payload.account_ids, settlement.period_start, settlement.period_end
    )
    _validate_tax_category(payload.tax_category, payload.deductible_amount, actual_amount)

    property_ = db.get(Property, settlement.property_id)
    unit_amounts = distribute_amount(
        db, property_, actual_amount, payload.allocation_key_type, settlement.fiscal_year
    )

    position = SettlementPosition(
        settlement_id=settlement.settlement_id,
        description=payload.description,
        actual_amount=actual_amount,
        allocation_key_type=payload.allocation_key_type,
        is_apportionable=payload.is_apportionable,
        tax_category=payload.tax_category,
        deductible_amount=payload.deductible_amount if payload.tax_category != "keine" else None,
    )
    db.add(position)
    db.flush()  # vergibt position.position_id, wird für Konten-Zuordnung und Shares gebraucht

    db.add_all(
        SettlementPositionAccount(position_id=position.position_id, account_id=account_id)
        for account_id in payload.account_ids
    )

    shares = [
        UnitSettlementShare(position_id=position.position_id, unit_id=unit_id, allocated_actual_amount=amount)
        for unit_id, amount in unit_amounts
    ]
    db.add_all(shares)
    db.flush()
    for s in shares:
        db.refresh(s)

    tax_shares = _replace_tax_shares(db, property_, settlement, position)

    db.commit()
    db.refresh(position)
    for s in shares:
        db.refresh(s)
    for s in tax_shares:
        db.refresh(s)

    _recompute_summaries(db, settlement)

    return _position_to_out(position, payload.account_ids, shares, tax_shares)
@router.patch("/{settlement_id}/positions/{position_id}", response_model=SettlementPositionOut)
def update_settlement_position(
    settlement_id: int,
    position_id: int,
    payload: SettlementPositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SettlementPositionOut:
    _require_write_role(current_user)
    settlement = _get_readable_period(db, settlement_id, current_user)

    if settlement.status != "Entwurf":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Positionen können nur bearbeitet werden, solange die Abrechnung im Entwurf ist.",
        )

    position = db.get(SettlementPosition, position_id)
    if position is None or position.settlement_id != settlement.settlement_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Position nicht gefunden")

    account_ids = payload.account_ids
    if account_ids is not None:
        _validate_settlement_accounts(db, account_ids, settlement.property_id)

    update_data = payload.model_dump(exclude_unset=True, exclude={"account_ids"})
    for field, value in update_data.items():
        setattr(position, field, value)

    if account_ids is not None:
        db.query(SettlementPositionAccount).filter(
            SettlementPositionAccount.position_id == position.position_id
        ).delete()
        db.add_all(
            SettlementPositionAccount(position_id=position.position_id, account_id=aid)
            for aid in account_ids
        )
        effective_account_ids = account_ids
    else:
        effective_account_ids = _load_position_account_ids(db, [position.position_id]).get(
            position.position_id, []
        )

    # Konten und/oder Verteilerschlüssel können sich geändert haben - Ist-Betrag
    # und Verteilung auf Einheiten daher komplett neu ermitteln (analog
    # recalculate_settlement, nur für eine einzelne Position).
    position.actual_amount = _compute_actual_amount(
        db, settlement.property_id, effective_account_ids, settlement.period_start, settlement.period_end
    )

    # tax_category ohne (neue) Angabe von deductible_amount würde sonst den
    # alten Wert stehen lassen, auch wenn die Kategorie inzwischen auf
    # 'keine' zurückgesetzt wurde - deshalb bei 'keine' immer explizit löschen.
    if position.tax_category == "keine":
        position.deductible_amount = None
    _validate_tax_category(position.tax_category, position.deductible_amount, position.actual_amount)

    property_ = db.get(Property, settlement.property_id)
    db.query(UnitSettlementShare).filter(UnitSettlementShare.position_id == position.position_id).delete()
    unit_amounts = distribute_amount(
        db, property_, position.actual_amount, position.allocation_key_type, settlement.fiscal_year
    )
    shares = [
        UnitSettlementShare(position_id=position.position_id, unit_id=unit_id, allocated_actual_amount=amount)
        for unit_id, amount in unit_amounts
    ]
    db.add_all(shares)
    db.flush()
    for s in shares:
        db.refresh(s)

    tax_shares = _replace_tax_shares(db, property_, settlement, position)

    db.commit()
    db.refresh(position)
    for s in shares:
        db.refresh(s)
    for s in tax_shares:
        db.refresh(s)

    _recompute_summaries(db, settlement)

    return _position_to_out(position, effective_account_ids, shares, tax_shares)


@router.delete("/{settlement_id}/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_settlement_position(
    settlement_id: int,
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Hartes Löschen - Positionen sind reine Planungsartefakte ohne
    Bindungswirkung, solange die Abrechnung im Entwurf ist (analog
    Budget-Positionen). Nach Beschluss nicht mehr möglich."""
    _require_write_role(current_user)
    settlement = _get_readable_period(db, settlement_id, current_user)

    if settlement.status != "Entwurf":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Positionen können nur gelöscht werden, solange die Abrechnung im Entwurf ist.",
        )

    position = db.get(SettlementPosition, position_id)
    if position is None or position.settlement_id != settlement.settlement_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Position nicht gefunden")

    db.query(UnitSettlementShare).filter(UnitSettlementShare.position_id == position.position_id).delete()
    db.query(UnitSettlementTaxShare).filter(UnitSettlementTaxShare.position_id == position.position_id).delete()
    db.query(SettlementPositionAccount).filter(
        SettlementPositionAccount.position_id == position.position_id
    ).delete()
    db.delete(position)
    db.commit()

    _recompute_summaries(db, settlement)

@router.post("/{settlement_id}/recalculate", response_model=list[SettlementPositionOut])
def recalculate_settlement(
    settlement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SettlementPositionOut]:
    _require_write_role(current_user)
    settlement = _get_readable_period(db, settlement_id, current_user)

    if settlement.status != "Entwurf":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nur Abrechnungen im Entwurf können neu berechnet werden.")

    property_ = db.get(Property, settlement.property_id)
    positions = list(
        db.scalars(select(SettlementPosition).where(SettlementPosition.settlement_id == settlement.settlement_id))
    )
    accounts_by_position = _load_position_account_ids(db, [p.position_id for p in positions])

    result: list[SettlementPositionOut] = []
    for position in positions:
        account_ids = accounts_by_position.get(position.position_id, [])
        position.actual_amount = _compute_actual_amount(
            db, settlement.property_id, account_ids, settlement.period_start, settlement.period_end
        )

        # Automatische Neuberechnung darf nicht an einem inzwischen zu hohen,
        # manuell erfassten Lohnanteil scheitern - defensives Kappen statt
        # Fehler, da recalculate mehrere Positionen in einem Rutsch verarbeitet.
        if position.deductible_amount is not None and position.deductible_amount > position.actual_amount:
            position.deductible_amount = position.actual_amount

        db.query(UnitSettlementShare).filter(UnitSettlementShare.position_id == position.position_id).delete()

        unit_amounts = distribute_amount(
            db, property_, position.actual_amount, position.allocation_key_type, settlement.fiscal_year
        )
        shares = [
            UnitSettlementShare(position_id=position.position_id, unit_id=unit_id, allocated_actual_amount=amount)
            for unit_id, amount in unit_amounts
        ]
        db.add_all(shares)
        db.flush()
        for s in shares:
            db.refresh(s)

        tax_shares = _replace_tax_shares(db, property_, settlement, position)
        result.append(_position_to_out(position, account_ids, shares, tax_shares))

    db.commit()
    _recompute_summaries(db, settlement)
    return result


@router.get("/{settlement_id}/summaries", response_model=list[UnitSettlementSummaryOut])
def list_unit_summaries(
    settlement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UnitSettlementSummary]:
    settlement = _get_readable_period(db, settlement_id, current_user)
    return list(
        db.scalars(
            select(UnitSettlementSummary).where(UnitSettlementSummary.settlement_id == settlement.settlement_id)
        )
    )
    
    

@router.get("/{settlement_id}/units/{unit_id}/export")
def export_unit_settlement_pdf(
    settlement_id: int,
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    settlement = _get_readable_period(db, settlement_id, current_user)

    unit = db.get(Unit, unit_id)
    if unit is None or unit.deleted_at is not None or unit.property_id != settlement.property_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Einheit gehört nicht zu dieser Abrechnung")

    property_ = db.get(Property, settlement.property_id)
    owner = _get_current_owner(db, unit_id)

    positions = list(
        db.scalars(select(SettlementPosition).where(SettlementPosition.settlement_id == settlement.settlement_id))
    )
    position_ids = [p.position_id for p in positions]
    accounts_by_position = _load_position_account_ids(db, position_ids)
    shares = (
        list(
            db.scalars(
                select(UnitSettlementShare).where(
                    UnitSettlementShare.position_id.in_(position_ids), UnitSettlementShare.unit_id == unit_id
                )
            )
        )
        if position_ids
        else []
    )
    shares_by_position = {s.position_id: s for s in shares}

    summary = db.scalar(
        select(UnitSettlementSummary).where(
            UnitSettlementSummary.settlement_id == settlement.settlement_id,
            UnitSettlementSummary.unit_id == unit_id,
        )
    )
    resolution = db.get(ResolutionCollection, settlement.resolution_id) if settlement.resolution_id else None

    reserve_fund_data = _build_reserve_fund_pdf_data(db, settlement, property_, unit_id)
    tax_certificate_positions = _build_tax_certificate_pdf_data(db, unit_id, positions)

    pdf_bytes = build_settlement_pdf(
        settlement=settlement,
        property_=property_,
        unit=unit,
        owner=owner,
        positions=positions,
        accounts_by_position=accounts_by_position,
        shares_by_position=shares_by_position,
        summary=summary,
        resolution=resolution,
        reserve_fund=reserve_fund_data,
        tax_certificate_positions=tax_certificate_positions,
    )
    
    filename = f"Abrechnung_{settlement.fiscal_year}_{unit.unit_number.replace(' ', '_')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )