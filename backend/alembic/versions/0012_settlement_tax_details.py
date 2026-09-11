# backend/alembic/versions/0012_settlement_tax_details.py
"""§35a EStG: Lohnanteil je Abrechnungsposition (haushaltsnahe Dienstleistungen / Handwerkerleistungen)

Revision ID: 0012_settlement_tax_details
Revises: 0011_reserve_fund_statement
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_settlement_tax_details"
down_revision = "0011_reserve_fund_statement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tax_category: 'keine' (Default - Heizung, Versicherung, Verwalter-
    # gebühr etc. sind nach §35a nicht relevant) / 'haushaltsnahe_dienst-
    # leistung' (§35a Abs. 2 EStG, z.B. Hausmeister/Reinigung, Garten-
    # pflege) / 'handwerkerleistung' (§35a Abs. 3 EStG, z.B. Reparaturen,
    # Instandhaltung). VARCHAR+CHECK statt Postgres-ENUM, konsistent mit
    # den übrigen Statusfeldern im Projekt.
    op.add_column(
        "settlement_positions",
        sa.Column("tax_category", sa.String(30), nullable=False, server_default="keine"),
    )
    op.create_check_constraint(
        "ck_settlement_positions_tax_category",
        "settlement_positions",
        "tax_category IN ('keine', 'haushaltsnahe_dienstleistung', 'handwerkerleistung')",
    )

    # Lohn-/Fahrt-/Maschinenkostenanteil von actual_amount - NUR dieser
    # Anteil ist nach §35a bescheinigungsfähig. Der Materialanteil ist bei
    # BEIDEN Kategorien ausgeschlossen (nicht nur bei Handwerkerleistungen -
    # dort fällt die Trennung praktisch nur stärker ins Gewicht, weil der
    # Materialanteil einer Reparaturrechnung i.d.R. wesentlich höher ist als
    # bei einer reinen Dienstleistungsrechnung). NULL = noch nicht erfasst.
    op.add_column(
        "settlement_positions",
        sa.Column("deductible_amount", sa.Numeric(12, 2), nullable=True),
    )
    op.create_check_constraint(
        "ck_settlement_positions_deductible_amount_non_negative",
        "settlement_positions",
        "deductible_amount IS NULL OR deductible_amount >= 0",
    )

    # Verteilung des Lohnanteils auf Einheiten - eigene Tabelle statt
    # Wiederverwendung von unit_settlement_shares, da dort bereits der
    # volle actual_amount verteilt ist (andere Bemessungsgrundlage, anderer
    # Zweck). Gleiches Verteilungsprinzip (app/core/allocation.py).
    op.create_table(
        "unit_settlement_tax_shares",
        sa.Column("share_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "position_id",
            sa.Integer(),
            sa.ForeignKey("settlement_positions.position_id"),
            nullable=False,
        ),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.unit_id"), nullable=False),
        sa.Column("allocated_deductible_amount", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint(
            "allocated_deductible_amount >= 0", name="ck_unit_settlement_tax_shares_amount"
        ),
        sa.UniqueConstraint(
            "position_id", "unit_id", name="uq_unit_settlement_tax_shares_position_unit"
        ),
    )
    op.create_index(
        "idx_unit_settlement_tax_shares_unit_id", "unit_settlement_tax_shares", ["unit_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_unit_settlement_tax_shares_unit_id", table_name="unit_settlement_tax_shares")
    op.drop_table("unit_settlement_tax_shares")
    op.drop_constraint(
        "ck_settlement_positions_deductible_amount_non_negative", "settlement_positions", type_="check"
    )
    op.drop_column("settlement_positions", "deductible_amount")
    op.drop_constraint("ck_settlement_positions_tax_category", "settlement_positions", type_="check")
    op.drop_column("settlement_positions", "tax_category")