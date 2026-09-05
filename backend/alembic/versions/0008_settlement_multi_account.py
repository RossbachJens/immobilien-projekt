# backend/alembic/versions/0008_settlement_multi_account.py
"""Nebenkostenabrechnung: mehrere Konten je Position (Pooling, z.B. Heizkosten)

Revision ID: 0008_settlement_multi_account
Revises: 0007_niederschrift_details
Create Date: 2026-09-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_settlement_multi_account"
down_revision = "0007_niederschrift_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Neue Zuordnungstabelle: eine Position kann jetzt mehrere Konten bündeln
    # (z.B. Heizkosten aus Brennstoff + Wartung + Messdienst-Gebühr zu einer
    # Position zusammenfassen, bevor nach HeizkostenV verteilt wird).
    # Komposit-Primärschlüssel statt Surrogatschlüssel - analog user_properties.
    op.create_table(
        "settlement_position_accounts",
        sa.Column(
            "position_id",
            sa.Integer(),
            sa.ForeignKey("settlement_positions.position_id"),
            primary_key=True,
        ),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.account_id"),
            primary_key=True,
        ),
    )
    op.create_index(
        "idx_settlement_position_accounts_account_id",
        "settlement_position_accounts",
        ["account_id"],
    )

    # Bestehende 1:1-Zuordnungen in die neue Tabelle übernehmen, bevor die
    # alte Spalte verschwindet.
    op.execute(
        """
        INSERT INTO settlement_position_accounts (position_id, account_id)
        SELECT position_id, account_id FROM settlement_positions
        """
    )

    # Der zugehörige FK-Constraint auf der alten Spalte wird von Postgres
    # automatisch mit abgelegt, da er ausschließlich auf dieser Spalte
    # dieser Tabelle liegt - der Index davor explizit, da er ein eigenes
    # Objekt ist.
    op.drop_index("idx_settlement_positions_account_id", table_name="settlement_positions")
    op.drop_column("settlement_positions", "account_id")


def downgrade() -> None:
    # Verlustbehaftet, falls eine Position inzwischen mehr als ein Konto
    # gebündelt hat: es wird deterministisch das kleinste account_id je
    # Position zurückübernommen.
    op.add_column("settlement_positions", sa.Column("account_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE settlement_positions sp
        SET account_id = sub.account_id
        FROM (
            SELECT DISTINCT ON (position_id) position_id, account_id
            FROM settlement_position_accounts
            ORDER BY position_id, account_id
        ) sub
        WHERE sp.position_id = sub.position_id
        """
    )
    op.alter_column("settlement_positions", "account_id", nullable=False)
    op.create_foreign_key(
        "settlement_positions_account_id_fkey",
        "settlement_positions",
        "accounts",
        ["account_id"],
        ["account_id"],
    )
    op.create_index("idx_settlement_positions_account_id", "settlement_positions", ["account_id"])
    op.drop_index(
        "idx_settlement_position_accounts_account_id", table_name="settlement_position_accounts"
    )
    op.drop_table("settlement_position_accounts")