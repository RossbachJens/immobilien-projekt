# backend/app/core/access.py
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.roles import resolve_role
from app.models.stammdaten import Unit, User
from app.models.zuordnungen import Lease, LeaseStatus, UnitOwnerHistory, UserProperty


def accessible_property_ids(db: Session, user: User) -> set[int] | None:
    """
    Liefert die Menge der Liegenschafts-IDs, auf die 'user' zugreifen darf.
    None bedeutet "kein Filter" (Admin - sieht alles). Das ist die erste
    Verteidigungslinie (FastAPI-Query-Filterung) von Defense-in-Depth; die
    zweite Ebene (Postgres RLS via SET LOCAL app.current_user_id) ist noch
    offen (siehe PROJECTPLAN.md, Phase 1).
    """
    role = resolve_role(user)

    if role == "admin":
        return None

    if role == "verwalter":
        return set(
            db.scalars(
                select(UserProperty.property_id).where(UserProperty.user_id == user.user_id)
            )
        )

    if role == "eigentuemer":
        return set(
            db.scalars(
                select(Unit.property_id)
                .join(UnitOwnerHistory, UnitOwnerHistory.unit_id == Unit.unit_id)
                .where(
                    UnitOwnerHistory.owner_id == user.owner_id,
                    UnitOwnerHistory.valid_to.is_(None),
                )
            )
        )

    if role == "mieter":
        return set(
            db.scalars(
                select(Unit.property_id)
                .join(Lease, Lease.unit_id == Unit.unit_id)
                .where(
                    Lease.tenant_id == user.tenant_id,
                    Lease.deleted_at.is_(None),
                    Lease.status == LeaseStatus.aktiv,
                )
            )
        )

    return set()