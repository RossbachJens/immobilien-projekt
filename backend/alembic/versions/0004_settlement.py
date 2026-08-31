# backend/alembic/versions/0004_settlement.py
"""Nebenkostenabrechnung: Abrechnungszeiträume, Positionen, Einheiten-Anteile

Revision ID: 0004_settlement
Revises: 0003_budget_extensions
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_settlement"
down_revision = "0003_budget_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "settlement_periods",
        sa.Column("settlement_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.property_id"), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="Entwurf"),
        sa.Column("resolution_id", sa.Integer(), sa.ForeignKey("resolution_collection.resolution_id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('Entwurf', 'Beschlossen', 'Inaktiv')", name="ck_settlement_periods_status"),
        sa.CheckConstraint("period_end > period_start", name="ck_settlement_periods_period"),
    )
    op.create_index(
        "uq_settlement_periods_property_year",
        "settlement_periods",
        ["property_id", "fiscal_year"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("idx_settlement_periods_property_id", "settlement_periods", ["property_id"])
    op.create_index("idx_settlement_periods_resolution_id", "settlement_periods", ["resolution_id"])

    op.create_table(
        "settlement_positions",
        sa.Column("position_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("settlement_id", sa.Integer(), sa.ForeignKey("settlement_periods.settlement_id"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.account_id"), nullable=False),
        sa.Column("description", sa.String(150), nullable=True),
        sa.Column("actual_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("allocation_key_type", sa.String(50), nullable=False),
        sa.Column("is_apportionable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("actual_amount >= 0", name="ck_settlement_positions_amount"),
    )
    op.create_index("idx_settlement_positions_settlement_id", "settlement_positions", ["settlement_id"])
    op.create_index("idx_settlement_positions_account_id", "settlement_positions", ["account_id"])

    op.create_table(
        "unit_settlement_shares",
        sa.Column("share_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("position_id", sa.Integer(), sa.ForeignKey("settlement_positions.position_id"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.unit_id"), nullable=False),
        sa.Column("allocated_actual_amount", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("allocated_actual_amount >= 0", name="ck_unit_settlement_shares_amount"),
        sa.UniqueConstraint("position_id", "unit_id", name="uq_unit_settlement_shares_position_unit"),
    )
    op.create_index("idx_unit_settlement_shares_unit_id", "unit_settlement_shares", ["unit_id"])

    op.create_table(
        "unit_settlement_summaries",
        sa.Column("summary_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("settlement_id", sa.Integer(), sa.ForeignKey("settlement_periods.settlement_id"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.unit_id"), nullable=False),
        sa.Column("total_actual_costs", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_prepayments", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False),
        sa.UniqueConstraint("settlement_id", "unit_id", name="uq_unit_settlement_summaries_settlement_unit"),
    )
    op.create_index("idx_unit_settlement_summaries_unit_id", "unit_settlement_summaries", ["unit_id"])


def downgrade() -> None:
    op.drop_table("unit_settlement_summaries")
    op.drop_table("unit_settlement_shares")
    op.drop_table("settlement_positions")
    op.drop_index("uq_settlement_periods_property_year", table_name="settlement_periods")
    op.drop_table("settlement_periods")