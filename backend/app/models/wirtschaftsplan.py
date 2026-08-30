from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# backend/app/models/wirtschaftsplan.py — ResolutionCollection ersetzen
class ResolutionCollection(Base):
    """
    Gesetzlich vorgeschriebene Beschluss-Sammlung (§ 24 WEG). Einträge werden
    im Regelbetrieb NICHT gelöscht (dauerhafte Dokumentationspflicht) —
    deleted_at ist nur für die Korrektur von Fehlerfassungen vorgesehen,
    nicht für reguläres Lifecycle-Management wie bei anderen Tabellen.

    Feldabgleich mit dem Muster einer Beschluss-Sammlung:
      - lfd_nr                                -> "Lfd. Nr." (nie wieder-
                                                  verwendet, auch nicht nach
                                                  Soft-Delete, s. Migration
                                                  0002 - UNIQUE ohne
                                                  deleted_at-Filter)
      - title/description                     -> "Beschlusswortlaut"
      - resolution_type/meeting_location/
        resolution_date/agenda_item             -> "Versammlung (Art/Ort/
                                                    Datum/TOP) bzw. Umlauf-
                                                    beschluss (Datum der
                                                    Verkündung)"
      - court_name/court_case_number/
        court_decision_date/court_ruling_text/
        court_parties                           -> "Gerichtsentscheidung
                                                    (Tenor/Gericht/Datum/
                                                    Az./Parteien)"
      - status_note                            -> "Vermerke" (Freitext, da
                                                    Kombinationen wie
                                                    "angenommen / angefochten
                                                    mit Klage vom ..."
                                                    vorkommen)
      - created_by/created_at                  -> "Eintragungsvermerk"

    Spätere Entwicklungen zu einem Beschluss (z.B. eine Gerichtsentscheidung)
    werden NICHT durch Bearbeiten der bestehenden Zeile abgebildet, sondern
    durch einen neuen Eintrag mit refers_to_resolution_id ("zu lfd. Nr. X")
    - exakt wie im Muster (Nr. 31 "zu lfd. Nr. 17") und konsistent mit dem
    Storno-Prinzip bei journal_entries (reversed_entry_id).
    """

    __tablename__ = "resolution_collection"

    resolution_id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.property_id"))
    lfd_nr: Mapped[int]
    resolution_date: Mapped[date]
    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text)
    resolution_type: Mapped[str | None]
    meeting_location: Mapped[str | None]
    agenda_item: Mapped[str | None]
    proposed_by_owner_id: Mapped[int | None] = mapped_column(ForeignKey("owners.owner_id"))
    court_name: Mapped[str | None]
    court_case_number: Mapped[str | None]
    court_decision_date: Mapped[date | None]
    court_ruling_text: Mapped[str | None] = mapped_column(Text)
    court_parties: Mapped[str | None]
    status_note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    refers_to_resolution_id: Mapped[int | None] = mapped_column(
        ForeignKey("resolution_collection.resolution_id")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
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
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
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
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
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
