# backend/app/routers/budget_plans.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.access import accessible_property_ids
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.buchhaltung import Account
from app.models.stammdaten import Property, Unit, User
from app.models.wirtschaftsplan import BudgetPlan, BudgetPosition, UnitBudgetShare
from app.models.zuordnungen import UnitAllocationKey
from app.schemas.budget_plans import (
    BudgetPlanCreate,
    BudgetPlanOut,
    BudgetPlanStatusUpdate,
    BudgetPositionCreate,
    BudgetPositionOut,
    UnitBudgetShareOut,
)

router = APIRouter(prefix="/budget-plans", tags=["budget-plans"])

# Erlaubte Statuswechsel - keine Rückwärtsbewegung, "Inaktiv" ist Endzustand.
ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "Entwurf": {"Beschlossen", "Inaktiv"},
    "Beschlossen": {"Inaktiv"},
    "Inaktiv": set(),
}


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Wirtschaftspläne pflegen.",
        )


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> Property:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    return property_


def _get_readable_plan(db: Session, budget_id: int, current_user: User) -> BudgetPlan:
    plan = db.get(BudgetPlan, budget_id)
    if plan is None or plan.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Wirtschaftsplan nicht gefunden")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and plan.property_id not in property_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Wirtschaftsplan nicht gefunden")
    return plan


def _compute_unit_fractions(
    db: Session, property_: Property, allocation_key_type: str, fiscal_year: int
) -> dict[int, float]:
    """
    Anteil (0..1) je Einheit an einer zu verteilenden Position:
      - 'MEA'         -> unit.mea / property.total_mea
      - 'Wohnflaeche' -> unit.square_meters / Summe aller aktiven Einheiten
      - sonst         -> Suche in unit_allocation_keys nach diesem key_type,
                         gültig für fiscal_year (Gültigkeitszeitraum statt
                         Jahres-Einzelzeile, siehe PROJECTPLAN.md); Einheiten
                         ohne passenden Eintrag bekommen 0.
    """
    units = list(
        db.scalars(
            select(Unit).where(Unit.property_id == property_.property_id, Unit.deleted_at.is_(None))
        )
    )
    if not units:
        return {}

    if allocation_key_type == "MEA":
        if not property_.total_mea:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Liegenschaft hat kein total_mea hinterlegt - Verteilung nach MEA nicht möglich.",
            )
        return {u.unit_id: float(u.mea or 0) / float(property_.total_mea) for u in units}

    if allocation_key_type == "Wohnflaeche":
        total_sqm = sum(float(u.square_meters) for u in units)
        if total_sqm == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Keine Wohnfläche hinterlegt.")
        return {u.unit_id: float(u.square_meters) / total_sqm for u in units}

    keys = list(
        db.scalars(
            select(UnitAllocationKey).where(
                UnitAllocationKey.property_id == property_.property_id,
                UnitAllocationKey.key_type == allocation_key_type,
                UnitAllocationKey.valid_from_year <= fiscal_year,
                or_(
                    UnitAllocationKey.valid_to_year.is_(None),
                    UnitAllocationKey.valid_to_year >= fiscal_year,
                ),
            )
        )
    )
    if not keys:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Kein Umlageschlüssel '{allocation_key_type}' für {fiscal_year} in dieser Liegenschaft hinterlegt.",
        )
    return {k.unit_id: float(k.numerator_value) / float(k.denominator_value) for k in keys}


def _distribute_position(
    db: Session, property_: Property, planned_amount: float, allocation_key_type: str, fiscal_year: int
) -> list[tuple[int, float]]:
    """
    Liefert je Einheit den zugewiesenen Betrag - Summe entspricht exakt
    planned_amount. Eine Rundungsdifferenz (durch die 2-Nachkommastellen-
    Rundung je Einheit) geht an die Einheit mit dem größten Anteil, analog
    zum Soll=Haben-Prinzip bei Buchungen (02_triggers.sql).
    """
    fractions = _compute_unit_fractions(db, property_, allocation_key_type, fiscal_year)
    participating = {uid: f for uid, f in fractions.items() if f > 0}
    if not participating:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Keine Einheit hat einen Anteil > 0 für diesen Verteilerschlüssel.",
        )

    allocated = {uid: round(planned_amount * f, 2) for uid, f in participating.items()}
    diff = round(planned_amount - sum(allocated.values()), 2)
    if diff != 0:
        target_uid = max(participating, key=lambda uid: participating[uid])
        allocated[target_uid] = round(allocated[target_uid] + diff, 2)

    return list(allocated.items())


@router.get("", response_model=list[BudgetPlanOut])
def list_budget_plans(
    property_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BudgetPlan]:
    query = select(BudgetPlan).where(BudgetPlan.deleted_at.is_(None))

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None:
        query = query.where(BudgetPlan.property_id.in_(property_ids))
    if property_id is not None:
        query = query.where(BudgetPlan.property_id == property_id)

    query = query.order_by(BudgetPlan.fiscal_year.desc())
    return list(db.scalars(query))


@router.post("", response_model=BudgetPlanOut, status_code=status.HTTP_201_CREATED)
def create_budget_plan(
    payload: BudgetPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetPlan:
    _require_write_role(current_user)
    _check_property_accessible(db, payload.property_id, current_user)

    plan = BudgetPlan(**payload.model_dump())
    db.add(plan)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Für {payload.fiscal_year} existiert bereits ein Wirtschaftsplan dieser Liegenschaft.",
        ) from exc

    db.refresh(plan)
    return plan


@router.patch("/{budget_id}", response_model=BudgetPlanOut)
def update_budget_plan_status(
    budget_id: int,
    payload: BudgetPlanStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetPlan:
    _require_write_role(current_user)
    plan = _get_readable_plan(db, budget_id, current_user)

    if payload.status != plan.status and payload.status not in ALLOWED_STATUS_TRANSITIONS.get(
        plan.status, set()
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Statuswechsel von '{plan.status}' zu '{payload.status}' nicht erlaubt.",
        )

    plan.status = payload.status
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/{budget_id}/positions", response_model=list[BudgetPositionOut])
def list_budget_positions(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BudgetPositionOut]:
    plan = _get_readable_plan(db, budget_id, current_user)
    positions = list(
        db.scalars(select(BudgetPosition).where(BudgetPosition.budget_id == plan.budget_id))
    )
    if not positions:
        return []

    position_ids = [p.position_id for p in positions]
    all_shares = list(
        db.scalars(select(UnitBudgetShare).where(UnitBudgetShare.position_id.in_(position_ids)))
    )
    shares_by_position: dict[int, list[UnitBudgetShare]] = {}
    for s in all_shares:
        shares_by_position.setdefault(s.position_id, []).append(s)

    return [
        BudgetPositionOut(
            position_id=p.position_id,
            budget_id=p.budget_id,
            account_id=p.account_id,
            planned_amount=p.planned_amount,
            allocation_key_type=p.allocation_key_type,
            unit_shares=[
                UnitBudgetShareOut.model_validate(s) for s in shares_by_position.get(p.position_id, [])
            ],
        )
        for p in positions
    ]


@router.post(
    "/{budget_id}/positions", response_model=BudgetPositionOut, status_code=status.HTTP_201_CREATED
)
def create_budget_position(
    budget_id: int,
    payload: BudgetPositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetPositionOut:
    _require_write_role(current_user)
    plan = _get_readable_plan(db, budget_id, current_user)

    if plan.status != "Entwurf":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Positionen können nur bearbeitet werden, solange der Plan im Entwurf ist.",
        )

    account = db.get(Account, payload.account_id)
    if account is None or not account.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekanntes oder inaktives Konto")
    if account.property_id is not None and account.property_id != plan.property_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Konto gehört zu einer anderen Liegenschaft")

    property_ = db.get(Property, plan.property_id)
    unit_amounts = _distribute_position(
        db, property_, payload.planned_amount, payload.allocation_key_type, plan.fiscal_year
    )

    position = BudgetPosition(
        budget_id=plan.budget_id,
        account_id=payload.account_id,
        planned_amount=payload.planned_amount,
        allocation_key_type=payload.allocation_key_type,
    )
    db.add(position)
    db.flush()  # vergibt position.position_id, wird für die Shares gebraucht

    shares = [
        UnitBudgetShare(
            position_id=position.position_id,
            unit_id=unit_id,
            allocated_planned_amount=amount,
            # Monatsrate gerundet - Summe der 12 Raten kann durch die
            # Rundung um wenige Cent vom Jahresbetrag abweichen; für eine
            # Ratenplanung tolerierbar (keine Buchungsrelevanz).
            monthly_installment=round(amount / 12, 2),
        )
        for unit_id, amount in unit_amounts
    ]
    db.add_all(shares)
    db.commit()
    db.refresh(position)
    for s in shares:
        db.refresh(s)

    return BudgetPositionOut(
        position_id=position.position_id,
        budget_id=position.budget_id,
        account_id=position.account_id,
        planned_amount=position.planned_amount,
        allocation_key_type=position.allocation_key_type,
        unit_shares=[UnitBudgetShareOut.model_validate(s) for s in shares],
    )