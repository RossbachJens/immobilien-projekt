# backend/app/routers/tenants.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_value, iban_last4
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.stammdaten import Tenant, User
from app.models.zuordnungen import Lease, LeaseStatus
from app.schemas.tenants import TenantCreate, TenantOut, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _get_active_tenant(db: Session, tenant_id: int) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None or tenant.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mieter nicht gefunden")
    return tenant


def _to_tenant_out(db: Session, tenant: Tenant) -> TenantOut:
    has_user = (
        db.scalar(select(User.user_id).where(User.tenant_id == tenant.tenant_id, User.deleted_at.is_(None)))
        is not None
    )
    return TenantOut(
        tenant_id=tenant.tenant_id,
        first_name=tenant.first_name,
        last_name=tenant.last_name,
        email=tenant.email,
        street_and_number=tenant.street_and_number,
        postal_code=tenant.postal_code,
        city=tenant.city,
        bank_name=tenant.bank_name,
        iban_last4=tenant.iban_last4,
        sepa_mandate_reference=tenant.sepa_mandate_reference,
        created_at=tenant.created_at,
        has_online_access=has_user,
    )


@router.get("", response_model=list[TenantOut])
def list_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> list[TenantOut]:
    tenants = list(db.scalars(select(Tenant).where(Tenant.deleted_at.is_(None))))
    return [_to_tenant_out(db, t) for t in tenants]


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> TenantOut:
    return _to_tenant_out(db, _get_active_tenant(db, tenant_id))


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> TenantOut:
    tenant = Tenant(**payload.model_dump(exclude={"iban", "bic"}))

    if payload.iban:
        tenant.iban_encrypted = encrypt_value(db, payload.iban)
        tenant.iban_last4 = iban_last4(payload.iban)
    if payload.bic:
        tenant.bic_encrypted = encrypt_value(db, payload.bic)

    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return _to_tenant_out(db, tenant)


@router.patch("/{tenant_id}", response_model=TenantOut)
def update_tenant(
    tenant_id: int,
    payload: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> TenantOut:
    tenant = _get_active_tenant(db, tenant_id)
    for field, value in payload.model_dump(exclude_unset=True, exclude={"iban", "bic"}).items():
        setattr(tenant, field, value)

    unset = payload.model_fields_set
    if "iban" in unset:
        if payload.iban:
            tenant.iban_encrypted = encrypt_value(db, payload.iban)
            tenant.iban_last4 = iban_last4(payload.iban)
        else:
            tenant.iban_encrypted = None
            tenant.iban_last4 = None
    if "bic" in unset:
        tenant.bic_encrypted = encrypt_value(db, payload.bic) if payload.bic else None

    tenant.updated_at = func.now()
    db.commit()
    db.refresh(tenant)
    return _to_tenant_out(db, tenant)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> None:
    tenant = _get_active_tenant(db, tenant_id)

    if db.scalar(
        select(Lease.lease_id).where(
            Lease.tenant_id == tenant_id, Lease.status == LeaseStatus.aktiv, Lease.deleted_at.is_(None)
        )
    ) is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mieter hat noch einen aktiven Mietvertrag.")

    if db.scalar(
        select(User.user_id).where(User.tenant_id == tenant_id, User.deleted_at.is_(None))
    ) is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Mieter ist noch mit einem aktiven User-Login verknüpft - diese "
            "Verknüpfung zuerst über PATCH /users/{user_id} entfernen.",
        )

    tenant.deleted_at = func.now()
    db.commit()