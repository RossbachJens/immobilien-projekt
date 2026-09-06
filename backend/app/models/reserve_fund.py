# backend/app/models/reserve_fund.py
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReserveFundStatement(Base):
    """
    Rücklagendarstellung + Vermögensaufstellung (Muster-Einzelabrechnung,
    Abschnitt "Rücklagendarstellung und Vermögensaufstellung") - 1:1 an eine
    Nebenkostenabrechnung gekoppelt (gleicher Zeitraum/Beschluss, erscheint
    im Muster als Teil desselben Dokuments wie Einzelabrechnung und
    Einzelwirtschaftsplan).
    """

    __tablename__ = "reserve_fund_statements"

    statement_id: Mapped[int] = mapped_column(primary_key=True)
    settlement_id: Mapped[int] = mapped_column(
        ForeignKey("settlement_periods.settlement_id"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ReserveFundStatementOperatingAccount(Base):
    """Konto(en), die für die Vermögensaufstellung als 'Bewirtschaftungskonto'
    gelten (i.d.R. das/die Girokonto/Girokonten der Liegenschaft, ggf.
    mehrere bei unterjährigem Bankwechsel) - der Saldo zum 01.01./31.12. wird
    NICHT gespeichert, sondern beim Export kumulativ aus den Buchungen
    ermittelt (siehe Router) und NICHT je Einheit verteilt, nur als
    Gesamtsumme der Liegenschaft ausgewiesen."""

    __tablename__ = "reserve_fund_statement_operating_accounts"

    statement_id: Mapped[int] = mapped_column(
        ForeignKey("reserve_fund_statements.statement_id"), primary_key=True
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id"), primary_key=True)


class ReserveFundPosition(Base):
    """
    Eine Bewegungszeile der Rücklagendarstellung. Der Betrag wird
    automatisch aus den Buchungen ermittelt: gesucht werden Buchungssätze,
    die SOWOHL eine Zeile auf einem Rücklagenkonto der Liegenschaft
    (accounts.is_reserve_account) ALS AUCH eine Zeile auf einem der hier
    verknüpften Gegenkonten (ReserveFundPositionAccount) enthalten - die
    Rücklagenseite dieser Buchungen wird vorzeichenrichtig summiert
    (DEBIT = Zufluss, CREDIT = Abfluss). So lässt sich z.B. eine
    Zinsgutschrift (Gegenkonto: Zinsertragskonto) von einer Zuführung
    (Gegenkonto: Girokonto) trennen, obwohl beide dasselbe Rücklagenkonto
    betreffen - anders als bei SettlementPosition, wo direkt auf den
    verknüpften (Aufwands-)Konten summiert wird.
    """

    __tablename__ = "reserve_fund_positions"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('Zufuehrung', 'Entnahme', 'Zinsen', "
            "'Kapitalertragsteuer', 'Solidaritaetszuschlag', 'Sonstiges')"
        ),
    )

    position_id: Mapped[int] = mapped_column(primary_key=True)
    statement_id: Mapped[int] = mapped_column(ForeignKey("reserve_fund_statements.statement_id"))
    movement_type: Mapped[str] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(String(150))
    allocation_key_type: Mapped[str] = mapped_column(String(50), default="MEA")
    actual_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

# backend/app/models/reserve_fund.py — nach der ReserveFundPosition-Klasse ergänzen

# Deutsche Anzeigetexte für movement_type - Single Source of Truth für das
# Backend (PDF-Export, siehe app/services/settlement_pdf.py); das Frontend
# (features/reserveFund/ReserveFundPanel.tsx) pflegt denselben Text separat,
# da dort keine Backend-Konstanten importiert werden können.
MOVEMENT_TYPE_LABELS: dict[str, str] = {
    "Zufuehrung": "Zuführung",
    "Entnahme": "Entnahme",
    "Zinsen": "Zinsen",
    "Kapitalertragsteuer": "Kapitalertragsteuer",
    "Solidaritaetszuschlag": "Solidaritätszuschlag",
    "Sonstiges": "Sonstiges",
}

class ReserveFundPositionAccount(Base):
    """Gegenkonto(en) einer Position (Pooling wie SettlementPositionAccount) -
    z.B. mehrere Konten, falls Zinsen auf unterschiedlichen
    Zinsertragskonten verbucht werden."""

    __tablename__ = "reserve_fund_position_accounts"

    position_id: Mapped[int] = mapped_column(
        ForeignKey("reserve_fund_positions.position_id"), primary_key=True
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id"), primary_key=True)


class ReserveFundUnitShare(Base):
    __tablename__ = "reserve_fund_unit_shares"
    __table_args__ = (UniqueConstraint("position_id", "unit_id"),)

    share_id: Mapped[int] = mapped_column(primary_key=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("reserve_fund_positions.position_id"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.unit_id"))
    allocated_amount: Mapped[float] = mapped_column(Numeric(12, 2))