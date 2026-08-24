from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ResolutionCollection(Base):
    """
    Gesetzlich vorgeschriebene Beschluss-Sammlung (§ 24 WEG). Einträge werden
    im Regelbetrieb NICHT gelöscht (dauerhafte Dokumentationspflicht) —
    deleted_at ist nur für die Korrektur von Fehlerfassungen vorgesehen,
    nicht für reguläres Lifecycle-Management wie bei anderen Tabellen.
    """

    __tablename__ = "resolution_collection"

    resolution_id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.property_id"))
    resolution_date: Mapped[date]
    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text)
    resolution_type: Mapped[str | None]
    proposed_by_owner_id: Mapped[int | None] = mapped_column(ForeignKey("owners.owner_id"))
    created_at: Mapped[datetime]
    deleted_at: Mapped[datetime | None]


class BudgetPlan(Base):
    __tablename__ = "budget_plans"
    __table_args__ = (
        # Entspricht dem partiellen Unique-Index uq_budget_plans_property_year
        # in 01_schema.sql (WHERE deleted_at IS NULL) — die Bedingung selbst
        # kann im ORM-Constraint nicht abgebildet werden, siehe SQL-Datei.
        UniqueConstraint("property_id", "fiscal_year", name="uq_budget_plans_property_year_orm"),
    )

    budget_id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.property_id"))
    fiscal_year: Mapped[int]
    title: Mapped[str]
    status: Mapped[str] = mapped_column(default="Entwurf")
    created_at: Mapped[datetime]
    deleted_at: Mapped[datetime | None]


class BudgetPosition(Base):
    __tablename__ = "budget_positions"
    __table_args__ = (CheckConstraint("planned_amount >= 0"),)

    position_id: Mapped[int] = mapped_column(primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budget_plans.budget_id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id"))
    planned_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    allocation_key_type: Mapped[str]


class UnitBudgetShare(Base):
    __tablename__ = "unit_budget_shares"
    __table_args__ = (
        CheckConstraint("allocated_planned_amount >= 0"),
        CheckConstraint("monthly_installment >= 0"),
        UniqueConstraint("position_id", "unit_id"),
    )

    share_id: Mapped[int] = mapped_column(primary_key=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("budget_positions.position_id"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.unit_id"))
    allocated_planned_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    monthly_installment: Mapped[float] = mapped_column(Numeric(12, 2))


class SpecialAssessment(Base):
    __tablename__ = "special_assessments"
    __table_args__ = (CheckConstraint("total_required_amount > 0"),)

    assessment_id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.property_id"))
    resolution_id: Mapped[int | None] = mapped_column(
        ForeignKey("resolution_collection.resolution_id")
    )
    title: Mapped[str]
    total_required_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    due_date: Mapped[date]
    status: Mapped[str] = mapped_column(default="Geplant")
    created_at: Mapped[datetime]
    deleted_at: Mapped[datetime | None]


class UnitSpecialAssessmentShare(Base):
    __tablename__ = "unit_special_assessment_shares"
    __table_args__ = (
        CheckConstraint("allocated_assessment_amount > 0"),
        UniqueConstraint("assessment_id", "unit_id"),
    )

    unit_assessment_id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("special_assessments.assessment_id"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.unit_id"))
    allocated_assessment_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    is_paid: Mapped[bool] = mapped_column(default=False)
