# backend/app/models/bank_accounts.py
import enum
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Enum, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BankAccountPurpose(str, enum.Enum):
    girokonto = "GIROKONTO"
    ruecklagenkonto = "RUECKLAGENKONTO"
    sonstiges = "SONSTIGES"


class PropertyBankAccount(Base):
    """Reales Bankkonto einer Liegenschaft (§ 27 Abs. 5 WEG). Kann unterjährig
    wechseln (z.B. Bankwechsel) - Gültigkeit über valid_from/valid_to statt
    is_active, analog UnitOwnerHistory. 'aktuell gültig' = valid_to IS NULL.

    Der EXCLUDE-Constraint gegen überlappende Zeiträume je account_id
    (excl_property_bank_accounts_no_overlap) ist im SQLAlchemy-ORM nicht
    abbildbar - siehe Migration 0005, gleiches Muster wie bei
    UnitAllocationKey."""

    __tablename__ = "property_bank_accounts"
    __table_args__ = (CheckConstraint("valid_to IS NULL OR valid_to > valid_from"),)

    bank_account_id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.property_id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id"))
    account_purpose: Mapped[BankAccountPurpose] = mapped_column(
        Enum(
            BankAccountPurpose,
            name="property_bank_account_purpose",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        )
    )
    purpose_detail: Mapped[str | None] = mapped_column(String(100))
    bank_name: Mapped[str] = mapped_column(String(100))
    iban_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    bic_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    iban_last4: Mapped[str | None] = mapped_column(String(4))
    valid_from: Mapped[date]
    valid_to: Mapped[date | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())