# backend/app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.stammdaten import Owner, Property, Tenant, User
from app.models.zuordnungen import UserProperty
from app.schemas.users import (
    PropertyAssignmentOut,
    UserAdminOut,
    UserCreateRequest,
    UserUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["users"])


def _to_admin_out(user: User, assignments: list[UserProperty]) -> UserAdminOut:
    return UserAdminOut(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        is_admin=user.is_admin,
        must_change_password=user.must_change_password,
        owner_id=user.owner_id,
        tenant_id=user.tenant_id,
        created_at=user.created_at,
        property_assignments=[
            PropertyAssignmentOut.model_validate(a) for a in assignments
        ],
    )


def _load_assignments(db: Session, user_id: int) -> list[UserProperty]:
    return list(db.scalars(select(UserProperty).where(UserProperty.user_id == user_id)))


def _check_role_exclusivity(is_admin: bool, owner_id: int | None, tenant_id: int | None) -> None:
    flags = [is_admin, owner_id is not None, tenant_id is not None]
    if sum(flags) > 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Ein User kann nur eine Rolle gleichzeitig haben: Admin, Eigentümer oder Mieter.",
        )


def _validate_owner_link(db: Session, owner_id: int, exclude_user_id: int | None = None) -> None:
    owner = db.get(Owner, owner_id)
    if owner is None or owner.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unbekannter Eigentümer: {owner_id}")

    conflict_query = select(User).where(User.owner_id == owner_id, User.deleted_at.is_(None))
    if exclude_user_id is not None:
        conflict_query = conflict_query.where(User.user_id != exclude_user_id)
    if db.scalar(conflict_query) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Eigentümer {owner_id} ist bereits mit einem anderen User verknüpft.",
        )


def _validate_tenant_link(db: Session, tenant_id: int, exclude_user_id: int | None = None) -> None:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None or tenant.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unbekannter Mieter: {tenant_id}")

    conflict_query = select(User).where(User.tenant_id == tenant_id, User.deleted_at.is_(None))
    if exclude_user_id is not None:
        conflict_query = conflict_query.where(User.user_id != exclude_user_id)
    if db.scalar(conflict_query) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Mieter {tenant_id} ist bereits mit einem anderen User verknüpft.",
        )


def _validate_property_assignments(db: Session, assignments: list) -> None:
    if not assignments:
        return
    requested_ids = {a.property_id for a in assignments}
    found_ids = set(
        db.scalars(
            select(Property.property_id).where(
                Property.property_id.in_(requested_ids),
                Property.deleted_at.is_(None),
            )
        )
    )
    missing = requested_ids - found_ids
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unbekannte oder gelöschte Liegenschaft(en): {sorted(missing)}",
        )


@router.get("", response_model=list[UserAdminOut])
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> list[UserAdminOut]:
    users = list(db.scalars(select(User).where(User.deleted_at.is_(None))))
    if not users:
        return []

    user_ids = [u.user_id for u in users]
    assignments = list(
        db.scalars(select(UserProperty).where(UserProperty.user_id.in_(user_ids)))
    )
    by_user: dict[int, list[UserProperty]] = {}
    for a in assignments:
        by_user.setdefault(a.user_id, []).append(a)

    return [_to_admin_out(u, by_user.get(u.user_id, [])) for u in users]


@router.post("", response_model=UserAdminOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> UserAdminOut:
    existing = db.scalar(
        select(User).where(
            or_(User.email == payload.email, User.name == payload.name),
            User.deleted_at.is_(None),
        )
    )
    if existing is not None:
        conflict_field = "E-Mail" if existing.email == payload.email else "Name"
        raise HTTPException(status.HTTP_409_CONFLICT, f"{conflict_field} wird bereits verwendet")

    if payload.owner_id is not None:
        _validate_owner_link(db, payload.owner_id)
    if payload.tenant_id is not None:
        _validate_tenant_link(db, payload.tenant_id)
    _validate_property_assignments(db, payload.property_assignments)

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        must_change_password=True,
        is_admin=payload.is_admin,
        owner_id=payload.owner_id,
        tenant_id=payload.tenant_id,
    )
    db.add(user)
    db.flush()  # vergibt user.user_id, wird fuer user_properties gebraucht

    assignments = [
        UserProperty(user_id=user.user_id, property_id=a.property_id, role=a.role)
        for a in payload.property_assignments
    ]
    db.add_all(assignments)

    db.commit()
    db.refresh(user)
    for a in assignments:
        db.refresh(a)

    return _to_admin_out(user, assignments)


@router.patch("/{user_id}", response_model=UserAdminOut)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> UserAdminOut:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User nicht gefunden")

    update_data = payload.model_dump(exclude_unset=True, exclude={"property_assignments"})

    if "email" in update_data or "name" in update_data:
        new_email = update_data.get("email", user.email)
        new_name = update_data.get("name", user.name)
        conflict = db.scalar(
            select(User).where(
                or_(User.email == new_email, User.name == new_name),
                User.deleted_at.is_(None),
                User.user_id != user_id,
            )
        )
        if conflict is not None:
            conflict_field = "E-Mail" if conflict.email == new_email else "Name"
            raise HTTPException(status.HTTP_409_CONFLICT, f"{conflict_field} wird bereits verwendet")

    new_is_admin = update_data.get("is_admin", user.is_admin)
    new_owner_id = update_data.get("owner_id", user.owner_id)
    new_tenant_id = update_data.get("tenant_id", user.tenant_id)
    _check_role_exclusivity(new_is_admin, new_owner_id, new_tenant_id)

    if "owner_id" in update_data and update_data["owner_id"] is not None:
        _validate_owner_link(db, update_data["owner_id"], exclude_user_id=user_id)
    if "tenant_id" in update_data and update_data["tenant_id"] is not None:
        _validate_tenant_link(db, update_data["tenant_id"], exclude_user_id=user_id)

    if user.is_admin and update_data.get("is_admin") is False:
        other_admins = db.scalar(
            select(func.count()).select_from(User).where(
                User.is_admin.is_(True), User.deleted_at.is_(None), User.user_id != user_id
            )
        )
        if not other_admins:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Letzter Admin kann nicht degradiert werden")

    for field, value in update_data.items():
        setattr(user, field, value)

    if payload.property_assignments is not None:
        _validate_property_assignments(db, payload.property_assignments)
        db.query(UserProperty).filter(UserProperty.user_id == user_id).delete()
        db.add_all(
            UserProperty(user_id=user_id, property_id=a.property_id, role=a.role)
            for a in payload.property_assignments
        )

    db.commit()
    db.refresh(user)
    assignments = _load_assignments(db, user_id)
    return _to_admin_out(user, assignments)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> None:
    if user_id == current_admin.user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Eigenes Konto kann nicht gelöscht werden")

    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User nicht gefunden")

    if user.is_admin:
        other_admins = db.scalar(
            select(func.count()).select_from(User).where(
                User.is_admin.is_(True), User.deleted_at.is_(None), User.user_id != user_id
            )
        )
        if not other_admins:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Letzter Admin kann nicht gelöscht werden")

    user.deleted_at = func.now()
    db.commit()