# backend/app/routers/budget_plans.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.access import accessible_property_ids
from app.core.allocation import distribute_amount
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.buchhaltung import Account, AccountType
from app.models.stammdaten import Property, User
from app.models.wirtschaftsplan import BudgetPlan, BudgetPosition, ResolutionCollection, UnitBudgetShare
from app.schemas.budget_plans import (
    BudgetPlanCreate,
    BudgetPlanOut,
    BudgetPlanStatusUpdate,
    BudgetPositionCreate,
    BudgetPositionOut,
    UnitBudgetShareOut,
)

router = APIRouter(prefix="/budget-plans", tags=["budget-plans"])

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


def _validate_resolution(db: Session, resolution_id: int, property_id: int) -> None:
    resolution = db.get(ResolutionCollection, resolution_id)
    if (
        resolution is None
        or resolution.deleted_at is not None
        or resolution.property_id != property_id
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannter Beschluss für diese Liegenschaft.")


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

    if payload.resolution_id is not None:
        _validate_resolution(db, payload.resolution_id, payload.property_id)

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

    if payload.resolution_id is not None:
        _validate_resolution(db, payload.resolution_id, plan.property_id)
        plan.resolution_id = payload.resolution_id

    effective_resolution_id = payload.resolution_id if payload.resolution_id is not None else plan.resolution_id
    if payload.status == "Beschlossen" and effective_resolution_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Ein Wirtschaftsplan kann erst nach Zuordnung eines Beschlusses aus der "
            "Beschluss-Sammlung beschlossen werden.",
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
            description=p.description,
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
    if account.type != AccountType.aufwand and not account.is_reserve_account:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Nur Aufwandskonten oder als Rücklage gekennzeichnete Konten sind für "
            "Wirtschaftsplan-Positionen zulässig.",
        )

    property_ = db.get(Property, plan.property_id)
    unit_amounts = distribute_amount(
        db, property_, payload.planned_amount, payload.allocation_key_type, plan.fiscal_year
    )

    position = BudgetPosition(
        budget_id=plan.budget_id,
        account_id=payload.account_id,
        description=payload.description,
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
        description=position.description,
        planned_amount=position.planned_amount,
        allocation_key_type=position.allocation_key_type,
        unit_shares=[UnitBudgetShareOut.model_validate(s) for s in shares],
    )