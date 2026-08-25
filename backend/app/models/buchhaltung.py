import enum
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Numeric, Text,func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountType(str, enum.Enum):
    aktiv = "AKTIV"
    passiv = "PASSIV"
    ertrag = "ERTRAG"
    aufwand = "AUFWAND"


class EntryDirection(str, enum.Enum):
    debit = "DEBIT"
    credit = "CREDIT"


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[int] = mapped_column(primary_key=True)
    account_number: Mapped[str] = mapped_column(unique=True)
    account_name: Mapped[str]
    account_class: Mapped[str]
    type: Mapped[AccountType] = mapped_column(Enum(AccountType, name="account_type"))
    is_active: Mapped[bool]


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    entry_id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.property_id"))
    entry_date: Mapped[date]
    document_reference: Mapped[str | None]
    description: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    locked_at: Mapped[datetime | None]
    reversed_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.entry_id")
    )


class EntryLine(Base):
    """
    Soll=Haben je entry_id wird NICHT im ORM validiert, sondern per
    Postgres-Constraint-Trigger erzwungen (02_triggers.sql, Phase 3) —
    das ist bewusst die einzige verlässliche Stelle dafür.
    """

    __tablename__ = "entry_lines"
    __table_args__ = (CheckConstraint("amount > 0"),)

    line_id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.entry_id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id"))
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.property_id"))
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.unit_id"))
    lease_id: Mapped[int | None] = mapped_column(ForeignKey("leases.lease_id"))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    direction: Mapped[EntryDirection] = mapped_column(
        Enum(EntryDirection, name="entry_direction")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
