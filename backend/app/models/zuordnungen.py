import enum
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Numeric, UniqueConstraint,func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PropertyRole(str, enum.Enum):
    verwalter = "Verwalter"
    buchhalter = "Buchhalter"
    lesezugriff = "Lesezugriff"


class LeaseStatus(str, enum.Enum):
    aktiv = "aktiv"
    beendet = "beendet"
    gekuendigt = "gekuendigt"


class UnitOwnerHistory(Base):
    __tablename__ = "unit_owner_history"
    __table_args__ = (CheckConstraint("ownership_share > 0"),)

    history_id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.unit_id"))
    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.owner_id"))
    ownership_share: Mapped[float] = mapped_column(Numeric(7, 4))
    valid_from: Mapped[date]
    valid_to: Mapped[date | None]


class UserProperty(Base):
    __tablename__ = "user_properties"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.property_id"), primary_key=True
    )
    role: Mapped[PropertyRole] = mapped_column(Enum(PropertyRole, name="property_role"))
    granted_at: Mapped[datetime] = mapped_column(server_default=func.now())


class UnitAllocationKey(Base):
    __tablename__ = "unit_allocation_keys"
    __table_args__ = (UniqueConstraint("unit_id", "key_type", "billing_year"),)

    key_id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.property_id"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.unit_id"))
    key_type: Mapped[str]
    billing_year: Mapped[int]
    numerator_value: Mapped[float] = mapped_column(Numeric(10, 4))
    denominator_value: Mapped[float] = mapped_column(Numeric(10, 4))


class Lease(Base):
    __tablename__ = "leases"
    __table_args__ = (CheckConstraint("cold_rent > 0"),)

    lease_id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.unit_id"))
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.tenant_id"))
    start_date: Mapped[date]
    end_date: Mapped[date | None]
    cold_rent: Mapped[float] = mapped_column(Numeric(10, 2))
    additional_costs_prepayment: Mapped[float] = mapped_column(Numeric(10, 2))
    deposit_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    deposit_received_at: Mapped[date | None]
    status: Mapped[LeaseStatus] = mapped_column(Enum(LeaseStatus, name="lease_status"))
    created_at: Mapped[datetime]
    deleted_at: Mapped[datetime | None]
