# backend/alembic/versions/0011_reserve_fund_statement.py
"""Rücklagendarstellung & Vermögensaufstellung je Nebenkostenabrechnung

Revision ID: 0011_reserve_fund_statement
Revises: 0010_opening_balance
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_reserve_fund_statement"
down_revision = "0010_opening_balance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reserve_fund_statements",
        sa.Column("statement_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "settlement_id",
            sa.Integer(),
            sa.ForeignKey("settlement_periods.settlement_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "reserve_fund_statement_operating_accounts",
        sa.Column(
            "statement_id",
            sa.Integer(),
            sa.ForeignKey("reserve_fund_statements.statement_id"),
            primary_key=True,
        ),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.account_id"), primary_key=True),
    )

    op.create_table(
        "reserve_fund_positions",
        sa.Column("position_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "statement_id",
            sa.Integer(),
            sa.ForeignKey("reserve_fund_statements.statement_id"),
            nullable=False,
        ),
        sa.Column("movement_type", sa.String(30), nullable=False),
        sa.Column("description", sa.String(150), nullable=True),
        sa.Column("allocation_key_type", sa.String(50), nullable=False, server_default="MEA"),
        sa.Column("actual_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "movement_type IN ('Zufuehrung', 'Entnahme', 'Zinsen', "
            "'Kapitalertragsteuer', 'Solidaritaetszuschlag', 'Sonstiges')",
            name="ck_reserve_fund_positions_movement_type",
        ),
    )
    op.create_index(
        "idx_reserve_fund_positions_statement_id", "reserve_fund_positions", ["statement_id"]
    )

    op.create_table(
        "reserve_fund_position_accounts",
        sa.Column(
            "position_id",
            sa.Integer(),
            sa.ForeignKey("reserve_fund_positions.position_id"),
            primary_key=True,
        ),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.account_id"), primary_key=True),
    )

    op.create_table(
        "reserve_fund_unit_shares",
        sa.Column("share_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "position_id",
            sa.Integer(),
            sa.ForeignKey("reserve_fund_positions.position_id"),
            nullable=False,
        ),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.unit_id"), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(12, 2), nullable=False),
        sa.UniqueConstraint(
            "position_id", "unit_id", name="uq_reserve_fund_unit_shares_position_unit"
        ),
    )
    op.create_index("idx_reserve_fund_unit_shares_unit_id", "reserve_fund_unit_shares", ["unit_id"])


def downgrade() -> None:
    op.drop_index("idx_reserve_fund_unit_shares_unit_id", table_name="reserve_fund_unit_shares")
    op.drop_table("reserve_fund_unit_shares")
    op.drop_table("reserve_fund_position_accounts")
    op.drop_index("idx_reserve_fund_positions_statement_id", table_name="reserve_fund_positions")
    op.drop_table("reserve_fund_positions")
    op.drop_table("reserve_fund_statement_operating_accounts")
    op.drop_table("reserve_fund_statements")