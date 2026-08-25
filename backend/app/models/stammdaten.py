from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Property(Base):
    __tablename__ = "properties"

    property_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(Text)
    total_square_meters: Mapped[float | None] = mapped_column(Numeric(10, 2))
    construction_year: Mapped[int | None]
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    deleted_at: Mapped[datetime | None]

    units: Mapped[list["Unit"]] = relationship(back_populates="property")


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (CheckConstraint("square_meters > 0"),)

    unit_id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.property_id"))
    unit_number: Mapped[str] = mapped_column(String(20))
    floor: Mapped[str | None] = mapped_column(String(20))
    square_meters: Mapped[float] = mapped_column(Numeric(6, 2))
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
    # DSGVO: verschlüsselt gespeichert (pgcrypto), niemals im Klartext im ORM.
    iban_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    bic_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    iban_last4: Mapped[str | None] = mapped_column(String(4))
    sepa_mandate_reference: Mapped[str | None] = mapped_column(String(35))
    sepa_granted_at: Mapped[date | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    deleted_at: Mapped[datetime | None]
    anonymized_at: Mapped[datetime | None]


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    street_and_number: Mapped[str] = mapped_column(String(150))
    postal_code: Mapped[str | None] = mapped_column(String(10))
    city: Mapped[str | None] = mapped_column(String(100))
    bank_name: Mapped[str | None] = mapped_column(String(100))
    iban_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    bic_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    iban_last4: Mapped[str | None] = mapped_column(String(4))
    sepa_mandate_reference: Mapped[str | None] = mapped_column(String(35))
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    deleted_at: Mapped[datetime | None]
    anonymized_at: Mapped[datetime | None]


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("password_hash IS NOT NULL OR google_sub_id IS NOT NULL"),
    )

    user_id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    google_sub_id: Mapped[str | None] = mapped_column(String(255))
    must_change_password: Mapped[bool]
    # Phase 1: globale Admin-Rolle. Eigentümer/Mieter ergeben sich aus
    # owner_id/tenant_id, Verwalter granular aus user_properties -
    # siehe app/core/roles.py::resolve_role.
    is_admin: Mapped[bool] = mapped_column(default=False)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("owners.owner_id"))
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.tenant_id"))
    created_at: Mapped[datetime]
    last_login_at: Mapped[datetime | None]
    deleted_at: Mapped[datetime | None]
