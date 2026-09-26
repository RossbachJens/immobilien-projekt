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
from app.core.document_archive import archive_generated_pdf
from app.core.tenant_allocation import compute_lease_day_fractions, distribute_amount_by_lease

from app.core.reserve_accounts import cumulative_balance, reserve_account_ids
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.abrechnung import (
    LeaseSettlementSummary,
    SettlementPeriod,
    SettlementPosition,
    SettlementPositionAccount,
    UnitSettlementShare,
    UnitSettlementSummary,
    UnitSettlementTaxShare,
    UnitSettlementTenantShare,
)
from app.models.buchhaltung import Account, AccountType, EntryDirection, EntryLine, JournalEntry
from app.models.reserve_fund import (
    MOVEMENT_TYPE_LABELS,
    ReserveFundPosition,
    ReserveFundStatement,
    ReserveFundStatementOperatingAccount,
    ReserveFundUnitShare,
)
from app.models.stammdaten import Owner, Property, Tenant, Unit, User
from app.models.wirtschaftsplan import ResolutionCollection
from app.schemas.settlement import (
    LeaseSettlementSummaryOut,
    SettlementPeriodCreate,
    SettlementPeriodOut,
    SettlementPeriodStatusUpdate,
    SettlementPositionCreate,
    SettlementPositionOut,
    SettlementPositionUpdate,
    UnitSettlementShareOut,
    UnitSettlementSummaryOut,
    UnitSettlementTaxShareOut,
    UnitSettlementTenantShareOut,
)
from app.models.zuordnungen import Lease, UnitOwnerHistory
from app.services.settlement_pdf import (
    ReserveFundPdfData,
    ReserveFundPdfPosition,
    TaxCertificatePdfPosition,
    TenantLetterInput,
    UnitLetterInput,
    build_settlement_pdf,
    build_settlement_pdf_batch,
    build_tenant_settlement_pdf,
    build_tenant_settlement_pdf_batch,
)

router = APIRouter(prefix="/settlement-periods", tags=["settlement-periods"])

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "Entwurf": {"Beschlossen", "Inaktiv"},
    "Beschlossen": {"Inaktiv"},
    "Inaktiv": set(),
}

HAUSGELD_FORDERUNG_NUMBERS = ("1220", "1225")
ADDITIONAL_COSTS_ACCOUNT_NUMBER = "1210"


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Abrechnungen pflegen.",
        )


def _require_read_access(current_user: User) -> None:
    """Nebenkostenabrechnung ist - wie die Beschluss-Sammlung und die
    Bankkonten - Eigentümern/Verwaltern/Admins vorbehalten. Mieter haben
    noch kein eigenes Portal (siehe PROJECTPLAN.md, 'bewusst zurück-
    gestellt') und dürfen daher nicht über die bestehenden Endpunkte auf die
    Kostenaufstellung des gesamten Gebäudes zugreifen - vor dieser Prüfung
    war das möglich (Sicherheitslücke, Chat vom 24.09.2026): ein Mieter
    konnte Ist-Kosten und Ergebnisse ALLER Einheiten/Eigentümer der eigenen
    Liegenschaft einsehen, nicht nur die eigene."""
    if resolve_role(current_user) == "mieter":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Mieter haben keinen Zugriff auf die Nebenkostenabrechnung."
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


def _get_lease_for_settlement(db: Session, settlement: SettlementPeriod, lease_id: int) -> Lease:
    lease = db.get(Lease, lease_id)
    if lease is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mietvertrag nicht gefunden")
    unit = db.get(Unit, lease.unit_id)
    if unit is None or unit.property_id != settlement.property_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mietvertrag gehört nicht zu dieser Abrechnung")
    return lease


def _validate_resolution(db: Session, resolution_id: int, property_id: int) -> None:
    resolution = db.get(ResolutionCollection, resolution_id)
    if resolution is None or resolution.deleted_at is not None or resolution.property_id != property_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannter Beschluss für diese Liegenschaft.")


def _compute_actual_amount(
    db: Session, property_id: int, account_ids: list[int], period_start, period_end
) -> float:
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


def _load_position_tenant_shares(
    db: Session, position_ids: list[int]
) -> dict[int, list[UnitSettlementTenantShare]]:
    if not position_ids:
        return {}
    rows = list(
        db.scalars(
            select(UnitSettlementTenantShare).where(UnitSettlementTenantShare.position_id.in_(position_ids))
        )
    )
    result: dict[int, list[UnitSettlementTenantShare]] = {}
    for row in rows:
        result.setdefault(row.position_id, []).append(row)
    return result


def _load_tenant_shares_for_lease(
    db: Session, position_ids: list[int], lease_id: int
) -> dict[int, UnitSettlementTenantShare]:
    """Wie _load_position_tenant_shares, aber gefiltert auf einen einzelnen
    Mietvertrag und als position_id -> Share statt position_id -> Liste -
    genau das, was der PDF-Export je Position/Mietvertrag braucht."""
    if not position_ids:
        return {}
    rows = list(
        db.scalars(
            select(UnitSettlementTenantShare).where(
                UnitSettlementTenantShare.position_id.in_(position_ids),
                UnitSettlementTenantShare.lease_id == lease_id,
            )
        )
    )
    return {row.position_id: row for row in rows}


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


def _replace_tenant_shares(
    db: Session, settlement: SettlementPeriod, position: SettlementPosition
) -> list[UnitSettlementTenantShare]:
    db.query(UnitSettlementTenantShare).filter(
        UnitSettlementTenantShare.position_id == position.position_id
    ).delete()

    if not position.is_apportionable:
        return []

    unit_shares = list(
        db.scalars(select(UnitSettlementShare).where(UnitSettlementShare.position_id == position.position_id))
    )

    tenant_shares: list[UnitSettlementTenantShare] = []
    for unit_share in unit_shares:
        fractions = compute_lease_day_fractions(
            db, unit_share.unit_id, settlement.period_start, settlement.period_end
        )
        for lease_id, amount in distribute_amount_by_lease(
            float(unit_share.allocated_actual_amount), fractions
        ):
            if amount <= 0:
                continue
            tenant_shares.append(
                UnitSettlementTenantShare(
                    position_id=position.position_id, lease_id=lease_id, allocated_amount=amount
                )
            )
    db.add_all(tenant_shares)
    db.flush()
    for s in tenant_shares:
        db.refresh(s)
    return tenant_shares


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
                Account.account_number.in_(HAUSGELD_FORDERUNG_NUMBERS),
                or_(Account.property_id.is_(None), Account.property_id == property_id),
            )
        )
    )


def _additional_costs_account_ids(db: Session, property_id: int) -> list[int]:
    return list(
        db.scalars(
            select(Account.account_id).where(
                Account.account_number == ADDITIONAL_COSTS_ACCOUNT_NUMBER,
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


def _sum_lease_prepayments(db: Session, lease_id: int, account_ids: list[int], period_start, period_end) -> float:
    if not account_ids:
        return 0.0
    result = db.scalar(
        select(func.coalesce(func.sum(EntryLine.amount), 0))
        .select_from(EntryLine)
        .join(JournalEntry, JournalEntry.entry_id == EntryLine.entry_id)
        .where(
            EntryLine.lease_id == lease_id,
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


def _recompute_lease_summaries(db: Session, settlement: SettlementPeriod) -> None:
    positions = list(
        db.scalars(select(SettlementPosition).where(SettlementPosition.settlement_id == settlement.settlement_id))
    )
    position_ids = [p.position_id for p in positions]
    tenant_shares = (
        list(
            db.scalars(
                select(UnitSettlementTenantShare).where(UnitSettlementTenantShare.position_id.in_(position_ids))
            )
        )
        if position_ids
        else []
    )
    costs_by_lease: dict[int, float] = {}
    for s in tenant_shares:
        costs_by_lease[s.lease_id] = costs_by_lease.get(s.lease_id, 0.0) + float(s.allocated_amount)

    leases = list(
        db.scalars(
            select(Lease)
            .join(Unit, Unit.unit_id == Lease.unit_id)
            .where(
                Unit.property_id == settlement.property_id,
                Lease.deleted_at.is_(None),
                Lease.start_date <= settlement.period_end,
                (Lease.end_date.is_(None)) | (Lease.end_date >= settlement.period_start),
            )
        )
    )

    additional_costs_ids = _additional_costs_account_ids(db, settlement.property_id)

    active_lease_ids = {lease.lease_id for lease in leases}
    # Entfernt Ergebniszeilen für Verträge, die inzwischen nicht mehr im
    # Zeitraum aktiv sind (z.B. nachträglich als Fehlerfassung soft-gelöscht) -
    # ohne dieses Aufräumen blieben stale Zeilen stehen, da diese Funktion
    # sonst nur upserted, nie löscht (Chat vom 24.09.2026).
    db.query(LeaseSettlementSummary).filter(
        LeaseSettlementSummary.settlement_id == settlement.settlement_id,
        LeaseSettlementSummary.lease_id.notin_(active_lease_ids),
    ).delete(synchronize_session=False)

    for lease in leases:
        total_costs = round(costs_by_lease.get(lease.lease_id, 0.0), 2)
        total_prepayments = round(
            _sum_lease_prepayments(
                db, lease.lease_id, additional_costs_ids, settlement.period_start, settlement.period_end
            ),
            2,
        )
        balance = round(total_costs - total_prepayments, 2)

        existing = db.scalar(
            select(LeaseSettlementSummary).where(
                LeaseSettlementSummary.settlement_id == settlement.settlement_id,
                LeaseSettlementSummary.lease_id == lease.lease_id,
            )
        )
        if existing is not None:
            existing.total_actual_costs = total_costs
            existing.total_prepayments = total_prepayments
            existing.balance = balance
        else:
            db.add(
                LeaseSettlementSummary(
                    settlement_id=settlement.settlement_id,
                    lease_id=lease.lease_id,
                    unit_id=lease.unit_id,
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
    tenant_shares: list[UnitSettlementTenantShare] | None = None,
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
        tenant_shares=[UnitSettlementTenantShareOut.model_validate(s) for s in (tenant_shares or [])],
    )

def _lease_summary_to_out(
    summary: LeaseSettlementSummary, lease: Lease, tenant: Tenant | None
) -> LeaseSettlementSummaryOut:
    return LeaseSettlementSummaryOut(
        summary_id=summary.summary_id,
        settlement_id=summary.settlement_id,
        lease_id=summary.lease_id,
        unit_id=summary.unit_id,
        total_actual_costs=summary.total_actual_costs,
        total_prepayments=summary.total_prepayments,
        balance=summary.balance,
        tenant_first_name=tenant.first_name if tenant else "",
        tenant_last_name=tenant.last_name if tenant else "Unbekannt",
        lease_start_date=lease.start_date,
        lease_end_date=lease.end_date,
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
    statement = db.scalar(
        select(ReserveFundStatement).where(ReserveFundStatement.settlement_id == settlement.settlement_id)
    )
    if statement is None:
        return None

    reserve_ids = reserve_account_ids(db, settlement.property_id)
    day_before_start = settlement.period_start - timedelta(days=1)

    reserve_balance_start = cumulative_balance(db, settlement.property_id, reserve_ids, day_before_start)
    reserve_balance_end = cumulative_balance(db, settlement.property_id, reserve_ids, settlement.period_end)

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
    _require_read_access(current_user)
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
    _require_read_access(current_user)
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
    tenant_shares_by_position = _load_position_tenant_shares(db, position_ids)

    return [
        _position_to_out(
            p,
            accounts_by_position.get(p.position_id, []),
            shares_by_position.get(p.position_id, []),
            tax_shares_by_position.get(p.position_id, []),
            tenant_shares_by_position.get(p.position_id, []),
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
    db.flush()

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
    tenant_shares = _replace_tenant_shares(db, settlement, position)

    db.commit()
    db.refresh(position)
    for s in shares:
        db.refresh(s)
    for s in tax_shares:
        db.refresh(s)
    for s in tenant_shares:
        db.refresh(s)

    _recompute_summaries(db, settlement)
    _recompute_lease_summaries(db, settlement)

    return _position_to_out(position, payload.account_ids, shares, tax_shares, tenant_shares)


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

    position.actual_amount = _compute_actual_amount(
        db, settlement.property_id, effective_account_ids, settlement.period_start, settlement.period_end
    )

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
    tenant_shares = _replace_tenant_shares(db, settlement, position)

    db.commit()
    db.refresh(position)
    for s in shares:
        db.refresh(s)
    for s in tax_shares:
        db.refresh(s)
    for s in tenant_shares:
        db.refresh(s)

    _recompute_summaries(db, settlement)
    _recompute_lease_summaries(db, settlement)

    return _position_to_out(position, effective_account_ids, shares, tax_shares, tenant_shares)


@router.delete("/{settlement_id}/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_settlement_position(
    settlement_id: int,
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
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
    db.query(UnitSettlementTenantShare).filter(
        UnitSettlementTenantShare.position_id == position.position_id
    ).delete()
    db.query(SettlementPositionAccount).filter(
        SettlementPositionAccount.position_id == position.position_id
    ).delete()
    db.delete(position)
    db.commit()

    _recompute_summaries(db, settlement)
    _recompute_lease_summaries(db, settlement)

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
        tenant_shares = _replace_tenant_shares(db, settlement, position)
        result.append(_position_to_out(position, account_ids, shares, tax_shares, tenant_shares))

    db.commit()
    _recompute_summaries(db, settlement)
    _recompute_lease_summaries(db, settlement)
    return result


@router.get("/{settlement_id}/summaries", response_model=list[UnitSettlementSummaryOut])
def list_unit_summaries(
    settlement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UnitSettlementSummary]:
    _require_read_access(current_user)
    settlement = _get_readable_period(db, settlement_id, current_user)
    return list(
        db.scalars(
            select(UnitSettlementSummary).where(UnitSettlementSummary.settlement_id == settlement.settlement_id)
        )
    )


@router.get("/{settlement_id}/lease-summaries", response_model=list[LeaseSettlementSummaryOut])
def list_lease_summaries(
    settlement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LeaseSettlementSummaryOut]:
    _require_read_access(current_user)
    settlement = _get_readable_period(db, settlement_id, current_user)
    summaries = list(
        db.scalars(
            select(LeaseSettlementSummary).where(LeaseSettlementSummary.settlement_id == settlement.settlement_id)
        )
    )
    if not summaries:
        return []

    lease_ids = [s.lease_id for s in summaries]
    leases_by_id = {l.lease_id: l for l in db.scalars(select(Lease).where(Lease.lease_id.in_(lease_ids)))}

    tenant_ids = {l.tenant_id for l in leases_by_id.values()}
    tenants_by_id = (
        {t.tenant_id: t for t in db.scalars(select(Tenant).where(Tenant.tenant_id.in_(tenant_ids)))}
        if tenant_ids
        else {}
    )

    result: list[LeaseSettlementSummaryOut] = []
    for s in summaries:
        lease = leases_by_id.get(s.lease_id)
        if lease is None:
            continue
        result.append(_lease_summary_to_out(s, lease, tenants_by_id.get(lease.tenant_id)))
    return result


@router.get("/{settlement_id}/units/{unit_id}/export")
def export_unit_settlement_pdf(
    settlement_id: int,
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    _require_read_access(current_user)
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

    archive_generated_pdf(
        db,
        property_id=property_.property_id,
        category="Abrechnung",
        title=f"Jahresabrechnung {settlement.fiscal_year} – {unit.unit_number}",
        filename=filename,
        content=pdf_bytes,
        settlement_id=settlement.settlement_id,
        unit_id=unit.unit_id,
        owner_id=owner.owner_id if owner else None,
        uploaded_by=current_user.user_id,
    )
    db.commit()

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{settlement_id}/export-batch")
def export_settlement_batch_pdf(
    settlement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    _require_read_access(current_user)
    settlement = _get_readable_period(db, settlement_id, current_user)
    property_ = db.get(Property, settlement.property_id)

    units = list(
        db.scalars(
            select(Unit)
            .where(Unit.property_id == settlement.property_id, Unit.deleted_at.is_(None))
            .order_by(Unit.unit_number)
        )
    )

    positions = list(
        db.scalars(select(SettlementPosition).where(SettlementPosition.settlement_id == settlement.settlement_id))
    )
    position_ids = [p.position_id for p in positions]
    accounts_by_position = _load_position_account_ids(db, position_ids)

    all_shares = (
        list(db.scalars(select(UnitSettlementShare).where(UnitSettlementShare.position_id.in_(position_ids))))
        if position_ids
        else []
    )
    shares_by_unit: dict[int, dict[int, UnitSettlementShare]] = {}
    for s in all_shares:
        shares_by_unit.setdefault(s.unit_id, {})[s.position_id] = s

    summaries = list(
        db.scalars(
            select(UnitSettlementSummary).where(UnitSettlementSummary.settlement_id == settlement.settlement_id)
        )
    )
    summary_by_unit = {s.unit_id: s for s in summaries}

    resolution = db.get(ResolutionCollection, settlement.resolution_id) if settlement.resolution_id else None

    letters: list[UnitLetterInput] = []
    for unit in units:
        owner = _get_current_owner(db, unit.unit_id)
        if owner is None:
            continue
        reserve_fund_data = _build_reserve_fund_pdf_data(db, settlement, property_, unit.unit_id)
        tax_certificate_positions = _build_tax_certificate_pdf_data(db, unit.unit_id, positions)
        letters.append(
            UnitLetterInput(
                unit=unit,
                owner=owner,
                positions=positions,
                accounts_by_position=accounts_by_position,
                shares_by_position=shares_by_unit.get(unit.unit_id, {}),
                summary=summary_by_unit.get(unit.unit_id),
                reserve_fund=reserve_fund_data,
                tax_certificate_positions=tax_certificate_positions,
            )
        )

    if not letters:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Keine Einheit mit aktuell zugeordnetem Eigentümer gefunden - Sammelversand nicht möglich.",
        )

    pdf_bytes = build_settlement_pdf_batch(
        settlement=settlement, property_=property_, resolution=resolution, letters=letters
    )

    for item in letters:
        individual_pdf = build_settlement_pdf(
            settlement=settlement,
            property_=property_,
            unit=item.unit,
            owner=item.owner,
            positions=item.positions,
            accounts_by_position=item.accounts_by_position,
            shares_by_position=item.shares_by_position,
            summary=item.summary,
            resolution=resolution,
            reserve_fund=item.reserve_fund,
            tax_certificate_positions=item.tax_certificate_positions,
        )
        archive_generated_pdf(
            db,
            property_id=property_.property_id,
            category="Abrechnung",
            title=f"Jahresabrechnung {settlement.fiscal_year} – {item.unit.unit_number}",
            filename=f"Abrechnung_{settlement.fiscal_year}_{item.unit.unit_number.replace(' ', '_')}.pdf",
            content=individual_pdf,
            settlement_id=settlement.settlement_id,
            unit_id=item.unit.unit_id,
            owner_id=item.owner.owner_id if item.owner else None,
            uploaded_by=current_user.user_id,
        )
    db.commit()

    filename = f"Abrechnungen_{settlement.fiscal_year}_Sammelversand.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{settlement_id}/leases/{lease_id}/export")
def export_lease_settlement_pdf(
    settlement_id: int,
    lease_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Mieterseitiger PDF-Export - Betriebskostenabrechnung für einen
    einzelnen Mietvertrag (Chat vom 24.09.2026). Nur Admin/Verwalter, kein
    zusätzlicher _require_read_access nötig, da _require_write_role Mieter
    ohnehin ausschließt - der Brief wird postalisch verschickt/archiviert,
    nicht online abgerufen (kein Mieterportal)."""
    _require_write_role(current_user)
    settlement = _get_readable_period(db, settlement_id, current_user)
    lease = _get_lease_for_settlement(db, settlement, lease_id)
    unit = db.get(Unit, lease.unit_id)
    tenant = db.get(Tenant, lease.tenant_id)
    if tenant is None or tenant.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mieter für diesen Vertrag nicht gefunden")

    property_ = db.get(Property, settlement.property_id)

    positions = list(
        db.scalars(select(SettlementPosition).where(SettlementPosition.settlement_id == settlement.settlement_id))
    )
    position_ids = [p.position_id for p in positions]
    tenant_shares_by_position = _load_tenant_shares_for_lease(db, position_ids, lease_id)

    summary = db.scalar(
        select(LeaseSettlementSummary).where(
            LeaseSettlementSummary.settlement_id == settlement.settlement_id,
            LeaseSettlementSummary.lease_id == lease_id,
        )
    )

    pdf_bytes = build_tenant_settlement_pdf(
        settlement=settlement,
        property_=property_,
        unit=unit,
        tenant=tenant,
        positions=positions,
        tenant_shares_by_position=tenant_shares_by_position,
        summary=summary,
    )

    filename = (
        f"Betriebskostenabrechnung_{settlement.fiscal_year}_{unit.unit_number.replace(' ', '_')}_"
        f"{tenant.last_name}.pdf"
    )

    archive_generated_pdf(
        db,
        property_id=property_.property_id,
        category="Abrechnung",
        title=f"Betriebskostenabrechnung {settlement.fiscal_year} – {unit.unit_number} ({tenant.last_name})",
        filename=filename,
        content=pdf_bytes,
        visibility="alle",
        settlement_id=settlement.settlement_id,
        unit_id=unit.unit_id,
        lease_id=lease.lease_id,
        tenant_id=tenant.tenant_id,
        uploaded_by=current_user.user_id,
    )
    db.commit()

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{settlement_id}/export-tenant-batch")
def export_settlement_tenant_batch_pdf(
    settlement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Sammel-PDF für den Postversand an Mieter: ein adressierter Brief je
    im Zeitraum aktivem Mietvertrag. Einheiten ohne Mietvertrag (Eigen-
    nutzung oder Leerstand) werden übersprungen - wie beim Eigentümer-
    Sammelversand wird zusätzlich je Mietvertrag ein individuelles PDF
    archiviert."""
    _require_write_role(current_user)
    settlement = _get_readable_period(db, settlement_id, current_user)
    property_ = db.get(Property, settlement.property_id)

    positions = list(
        db.scalars(select(SettlementPosition).where(SettlementPosition.settlement_id == settlement.settlement_id))
    )
    position_ids = [p.position_id for p in positions]

    all_tenant_shares = (
        list(
            db.scalars(
                select(UnitSettlementTenantShare).where(UnitSettlementTenantShare.position_id.in_(position_ids))
            )
        )
        if position_ids
        else []
    )
    shares_by_lease: dict[int, dict[int, UnitSettlementTenantShare]] = {}
    for s in all_tenant_shares:
        shares_by_lease.setdefault(s.lease_id, {})[s.position_id] = s

    summaries = list(
        db.scalars(
            select(LeaseSettlementSummary).where(LeaseSettlementSummary.settlement_id == settlement.settlement_id)
        )
    )
    summary_by_lease = {s.lease_id: s for s in summaries}

    # Vereinigung statt nur shares_by_lease.keys(): ein Mietvertrag mit
    # ausschließlich nicht umlagefähigen Positionen hat 0,00 € Ist-Kosten und
    # damit keine tenant_shares-Zeile, taucht aber trotzdem in summaries auf
    # und soll seinen (dann leeren) Brief bekommen.
    lease_ids = {s.lease_id for s in summaries} | set(shares_by_lease.keys())
    if not lease_ids:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Keine Mietverträge im Abrechnungszeitraum gefunden - Sammelversand nicht möglich.",
        )

    leases = list(db.scalars(select(Lease).where(Lease.lease_id.in_(lease_ids))))
    unit_ids = {l.unit_id for l in leases}
    units_by_id = {u.unit_id: u for u in db.scalars(select(Unit).where(Unit.unit_id.in_(unit_ids)))}
    tenant_ids = {l.tenant_id for l in leases}
    tenants_by_id = (
        {
            t.tenant_id: t
            for t in db.scalars(
                select(Tenant).where(Tenant.tenant_id.in_(tenant_ids), Tenant.deleted_at.is_(None))
            )
        }
        if tenant_ids
        else {}
    )

    letters: list[TenantLetterInput] = []
    for lease in leases:
        tenant = tenants_by_id.get(lease.tenant_id)
        unit = units_by_id.get(lease.unit_id)
        if tenant is None or unit is None:
            continue
        letters.append(
            TenantLetterInput(
                lease=lease,
                tenant=tenant,
                unit=unit,
                positions=positions,
                tenant_shares_by_position=shares_by_lease.get(lease.lease_id, {}),
                summary=summary_by_lease.get(lease.lease_id),
            )
        )

    if not letters:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Kein Mieter mit vollständigen Stammdaten gefunden - Sammelversand nicht möglich.",
        )

    pdf_bytes = build_tenant_settlement_pdf_batch(settlement=settlement, property_=property_, letters=letters)

    for item in letters:
        individual_pdf = build_tenant_settlement_pdf(
            settlement=settlement,
            property_=property_,
            unit=item.unit,
            tenant=item.tenant,
            positions=item.positions,
            tenant_shares_by_position=item.tenant_shares_by_position,
            summary=item.summary,
        )
        archive_generated_pdf(
            db,
            property_id=property_.property_id,
            category="Abrechnung",
            title=f"Betriebskostenabrechnung {settlement.fiscal_year} – {item.unit.unit_number} ({item.tenant.last_name})",
            filename=(
                f"Betriebskostenabrechnung_{settlement.fiscal_year}_"
                f"{item.unit.unit_number.replace(' ', '_')}_{item.tenant.last_name}.pdf"
            ),
            content=individual_pdf,
            visibility="alle",
            settlement_id=settlement.settlement_id,
            unit_id=item.unit.unit_id,
            lease_id=item.lease.lease_id,
            tenant_id=item.tenant.tenant_id,
            uploaded_by=current_user.user_id,
        )
    db.commit()

    filename = f"Betriebskostenabrechnungen_{settlement.fiscal_year}_Sammelversand.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )