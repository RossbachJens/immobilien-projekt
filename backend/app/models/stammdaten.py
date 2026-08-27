# backend/app/models/stammdaten.py
from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (CheckConstraint("total_mea > 0", name="ck_properties_total_mea_positive"),)

    property_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(Text)
    total_square_meters: Mapped[float | None] = mapped_column(Numeric(10, 2))
    construction_year: Mapped[int | None]
    total_mea: Mapped[float | None] = mapped_column(Numeric(10, 2))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    deleted_at: Mapped[datetime | None]

    units: Mapped[list["Unit"]] = relationship(back_populates="property")


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (
        CheckConstraint("square_meters > 0"),
        CheckConstraint("mea > 0", name="ck_units_mea_positive"),
    )

    unit_id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.property_id"))
    unit_number: Mapped[str] = mapped_column(String(20))
    floor: Mapped[str | None] = mapped_column(String(20))
    square_meters: Mapped[float] = mapped_column(Numeric(6, 2))
    mea: Mapped[float | None] = mapped_column(Numeric(10, 2))
    unit_type: Mapped[str | None] = mapped_column(String(30))
    deleted_at: Mapped[datetime | None]

    property: Mapped["Property"] = relationship(back_populates="units")


class Owner(Base):
    __tablename__ = "owners"

    owner_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str | None] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    company_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(50))
    street_and_number: Mapped[str] = mapped_column(String(150))
    postal_code: Mapped[str | None] = mapped_column(String(10))
    city: Mapped[str | None] = mapped_column(String(100))
    bank_name: Mapped[str | None] = mapped_column(String(100))
    iban_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    bic_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    iban_last4: Mapped[str | None] = mapped_column(String(4))
    sepa_mandate_reference: Mapped[str | None] = mapped_column(String(35))
    sepa_granted_at: Mapped[date | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    deleted_at: Mapped[datetime | None]
    anonymized_at: Mapped[datetime | None]


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(100))
    street_and_number: Mapped[str] = mapped_column(String(150))
    postal_code: Mapped[str | None] = mapped_column(String(10))
    city: Mapped[str | None] = mapped_column(String(100))
    bank_name: Mapped[str | None] = mapped_column(String(100))
    iban_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    bic_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    iban_last4: Mapped[str | None] = mapped_column(String(4))
    sepa_mandate_reference: Mapped[str | None] = mapped_column(String(35))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    deleted_at: Mapped[datetime | None]
    anonymized_at: Mapped[datetime | None]


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("password_hash IS NOT NULL OR google_sub_id IS NOT NULL"),
    )

    user_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    google_sub_id: Mapped[str | None] = mapped_column(String(255))
    must_change_password: Mapped[bool]
    is_admin: Mapped[bool] = mapped_column(default=False)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("owners.owner_id"))
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.tenant_id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(server_default=func.now())
    deleted_at: Mapped[datetime | None]