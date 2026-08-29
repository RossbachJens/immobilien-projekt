"""Individualkonten je Liegenschaft (SKR04-Basis bleibt global)

Revision ID: 0001_property_accounts
Revises:
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_property_accounts"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # property_id NULL = globales SKR04-Basiskonto (weiterhin nur über
    # Migrationen/Seed-Daten gepflegt). Gesetzt = liegenschaftseigenes
    # Zusatzkonto, das Verwalter/Admin über POST/PATCH /accounts pflegen.
    op.add_column("accounts", sa.Column("property_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_accounts_property_id", "accounts", "properties", ["property_id"], ["property_id"]
    )
    op.create_index("idx_accounts_property_id", "accounts", ["property_id"])

    # Die bisherige globale UNIQUE(account_number) muss weichen - sie würde
    # sonst verhindern, dass zwei verschiedene Liegenschaften unabhängig
    # voneinander dieselbe eigene Kontonummer vergeben. Name entspricht der
    # Postgres-Konvention für inline UNIQUE auf einer Spalte - falls
    # abweichend, mit \d accounts in psql den echten Namen prüfen.
    op.drop_constraint("accounts_account_number_key", "accounts", type_="unique")

    # Ersatz: zwei partielle Unique-Indizes statt einer globalen Regel.
    op.create_index(
        "uq_accounts_number_global",
        "accounts",
        ["account_number"],
        unique=True,
        postgresql_where=sa.text("property_id IS NULL"),
    )
    op.create_index(
        "uq_accounts_number_per_property",
        "accounts",
        ["property_id", "account_number"],
        unique=True,
        postgresql_where=sa.text("property_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_accounts_number_per_property", table_name="accounts")
    op.drop_index("uq_accounts_number_global", table_name="accounts")
    op.create_unique_constraint("accounts_account_number_key", "accounts", ["account_number"])
    op.drop_index("idx_accounts_property_id", table_name="accounts")
    op.drop_constraint("fk_accounts_property_id", "accounts", type_="foreignkey")
    op.drop_column("accounts", "property_id")