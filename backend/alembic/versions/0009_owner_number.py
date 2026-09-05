# backend/alembic/versions/0009_owner_number.py
"""Optionale Eigentümernummer je Einheiten-Zuordnung (frei wählbares Nummernsystem)

Revision ID: 0009_owner_number
Revises: 0008_settlement_multi_account
Create Date: 2026-09-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_owner_number"
down_revision = "0008_settlement_multi_account"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "unit_owner_history",
        sa.Column("owner_number", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("unit_owner_history", "owner_number")