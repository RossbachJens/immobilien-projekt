from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.stammdaten import Property, User
from app.models.zuordnungen import UserProperty
from app.schemas.users import (
    PropertyAssignmentOut,
    UserAdminOut,
    UserCreateRequest,
)

router = APIRouter(prefix="/users", tags=["users"])


def _to_admin_out(user: User, assignments: list[UserProperty]) -> UserAdminOut:
    return UserAdminOut(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        is_admin=user.is_admin,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
        property_assignments=[
            PropertyAssignmentOut.model_validate(a) for a in assignments
        ],
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
            User.deleted_at.is_(None)
        )
    )
    if existing is not None:
         conflict_field = "E-Mail" if existing.email == payload.email else "Name"
         raise HTTPException(status.HTTP_409_CONFLICT, f"{conflict_field} wird bereits verwendet")

    if payload.property_assignments:
        requested_ids = {a.property_id for a in payload.property_assignments}
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

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        # Admin vergibt ein Erstpasswort -> User muss es beim ersten Login
        # aendern. Erzwingung selbst folgt spaeter (noch kein Check in
        # app/routers/auth.py bzw. im Frontend-Login-Flow).
        must_change_password=True,
        is_admin=payload.is_admin,
    )
    db.add(user)
    db.flush()  # vergibt user.user_id, wird fuer user_properties gebraucht

    assignments = [
        UserProperty(
            user_id=user.user_id,
            property_id=a.property_id,
            role=a.role,
        )
        for a in payload.property_assignments
    ]
    db.add_all(assignments)

    db.commit()
    db.refresh(user)
    for a in assignments:
        db.refresh(a)

    return _to_admin_out(user, assignments)