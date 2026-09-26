# backend/alembic/versions/0019_tenant_shares.py
"""Taggenaue Verteilung umlagefähiger Abrechnungspositionen auf Mietverträge + Mieter-Ergebnis je Vertrag

Revision ID: 0019_tenant_shares
Revises: 0018_tenant_reserve_accounts
Create Date: 2026-09-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_tenant_shares"
down_revision = "0018_tenant_reserve_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "unit_settlement_tenant_shares",
        sa.Column("share_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "position_id", sa.Integer(), sa.ForeignKey("settlement_positions.position_id"), nullable=False
        ),
        sa.Column("lease_id", sa.Integer(), sa.ForeignKey("leases.lease_id"), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("allocated_amount >= 0", name="ck_unit_settlement_tenant_shares_amount"),
        sa.UniqueConstraint(
            "position_id", "lease_id", name="uq_unit_settlement_tenant_shares_position_lease"
        ),
    )
    op.create_index(
        "idx_unit_settlement_tenant_shares_lease_id", "unit_settlement_tenant_shares", ["lease_id"]
    )

    op.create_table(
        "lease_settlement_summaries",
        sa.Column("summary_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "settlement_id", sa.Integer(), sa.ForeignKey("settlement_periods.settlement_id"), nullable=False
        ),
        sa.Column("lease_id", sa.Integer(), sa.ForeignKey("leases.lease_id"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.unit_id"), nullable=False),
        sa.Column("total_actual_costs", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_prepayments", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False),
        sa.UniqueConstraint(
            "settlement_id", "lease_id", name="uq_lease_settlement_summaries_settlement_lease"
        ),
    )
    op.create_index(
        "idx_lease_settlement_summaries_lease_id", "lease_settlement_summaries", ["lease_id"]
    )

    # RLS - dieselbe kaskadierende Policy wie für die übrigen Positions-/
    # Summary-Tabellen (Migration 0014_row_level_security): Zugriff folgt der
    # bereits RLS-geschützten Elterntabelle, keine eigene property_id-Spalte
    # nötig. app_user erbt SELECT/INSERT/UPDATE/DELETE bereits über die
    # ALTER DEFAULT PRIVILEGES-Regel aus Migration 0014 (neue Tabellen
    # desselben Owners erhalten die Rechte automatisch).
    op.execute("ALTER TABLE unit_settlement_tenant_shares ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY unit_settlement_tenant_shares_property_isolation ON unit_settlement_tenant_shares
        FOR ALL
        USING (
            position_id IN (SELECT position_id FROM settlement_positions)
        );
        """
    )

    op.execute("ALTER TABLE lease_settlement_summaries ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY lease_settlement_summaries_property_isolation ON lease_settlement_summaries
        FOR ALL
        USING (
            settlement_id IN (SELECT settlement_id FROM settlement_periods)
        );
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS lease_settlement_summaries_property_isolation ON lease_settlement_summaries;"
    )
    op.execute("ALTER TABLE lease_settlement_summaries DISABLE ROW LEVEL SECURITY;")
    op.execute(
        "DROP POLICY IF EXISTS unit_settlement_tenant_shares_property_isolation ON unit_settlement_tenant_shares;"
    )
    op.execute("ALTER TABLE unit_settlement_tenant_shares DISABLE ROW LEVEL SECURITY;")

    op.drop_index("idx_lease_settlement_summaries_lease_id", table_name="lease_settlement_summaries")
    op.drop_table("lease_settlement_summaries")
    op.drop_index("idx_unit_settlement_tenant_shares_lease_id", table_name="unit_settlement_tenant_shares")
    op.drop_table("unit_settlement_tenant_shares")