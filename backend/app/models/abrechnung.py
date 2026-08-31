# backend/app/models/abrechnung.py
from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SettlementPeriod(Base):
    """
    Abrechnungszeitraum je Liegenschaft (i.d.R. Kalenderjahr) - Klammer um
    eine Jahres-/Nebenkostenabrechnung. Analog BudgetPlan (Phase 4):
    Entwurf -> Beschlossen -> Inaktiv, optional an einen Beschluss (§ 24 WEG)
    gekoppelt - die Abrechnungsspitze wird laut Muster-Einzelabrechnung erst
    "mit Beschlussfassung über die Jahresabrechnung" fällig.
    """

    __tablename__ = "settlement_periods"
    __table_args__ = (
        CheckConstraint("status IN ('Entwurf', 'Beschlossen', 'Inaktiv')"),
        CheckConstraint("period_end > period_start"),
    )

    settlement_id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.property_id"))
    fiscal_year: Mapped[int]
    period_start: Mapped[date]
    period_end: Mapped[date]
    title: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30), default="Entwurf")
    resolution_id: Mapped[int | None] = mapped_column(ForeignKey("resolution_collection.resolution_id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    deleted_at: Mapped[datetime | None]


class SettlementPosition(Base):
    """
    Eine Kostenzeile (Ist-Kosten je Konto, z.B. 'Hausmeister'). is_apportionable
    unterscheidet umlagefähige von nicht umlagefähigen Kosten (vgl.
    Muster-Einzelabrechnung) - bewusst Eigenschaft der Position statt des
    Kontos, da dieselbe Kostenart je nach Vertrag/Satzung unterschiedlich
    eingestuft werden kann.
    """

    __tablename__ = "settlement_positions"
    __table_args__ = (CheckConstraint("actual_amount >= 0"),)

    position_id: Mapped[int] = mapped_column(primary_key=True)
    settlement_id: Mapped[int] = mapped_column(ForeignKey("settlement_periods.settlement_id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id"))
    description: Mapped[str | None] = mapped_column(String(150))
    actual_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    allocation_key_type: Mapped[str]
    is_apportionable: Mapped[bool] = mapped_column(default=False)


class UnitSettlementShare(Base):
    __tablename__ = "unit_settlement_shares"
    __table_args__ = (
        CheckConstraint("allocated_actual_amount >= 0"),
        UniqueConstraint("position_id", "unit_id"),
    )

    share_id: Mapped[int] = mapped_column(primary_key=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("settlement_positions.position_id"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.unit_id"))
    allocated_actual_amount: Mapped[float] = mapped_column(Numeric(12, 2))


class UnitSettlementSummary(Base):
    """
    Ergebnis je Einheit: Ist-Kosten (Summe aller Positionen) vs. geleistete
    Vorauszahlungen (aus Zahlungseingängen, Phase 5.2) im Zeitraum.
    balance > 0 -> Erstattung, balance < 0 -> Nachzahlung/Abrechnungsspitze.
    """

    __tablename__ = "unit_settlement_summaries"
    __table_args__ = (UniqueConstraint("settlement_id", "unit_id"),)

    summary_id: Mapped[int] = mapped_column(primary_key=True)
    settlement_id: Mapped[int] = mapped_column(ForeignKey("settlement_periods.settlement_id"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.unit_id"))
    total_actual_costs: Mapped[float] = mapped_column(Numeric(12, 2))
    total_prepayments: Mapped[float] = mapped_column(Numeric(12, 2))
    balance: Mapped[float] = mapped_column(Numeric(12, 2))