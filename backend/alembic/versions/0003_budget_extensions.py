# backend/alembic/versions/0003_budget_extensions.py
"""Wirtschaftsplan-Erweiterungen: Positionsbezeichnung, Rücklagenkonten-Kennzeichnung, Beschluss-Kopplung

Revision ID: 0003_budget_extensions
Revises: 0002_resolution_details
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_budget_extensions"
down_revision = "0002_resolution_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Freitext-Bezeichnung je Position (z.B. "Hausmeister",
    #    "Haftpflichtversicherung", "Gebäudeversicherung") - unterscheidet
    #    Positionen, die auf dasselbe generische Konto gebucht werden.
    op.add_column("budget_positions", sa.Column("description", sa.String(150), nullable=True))

    # 2. Rücklagenkonten-Kennzeichnung - erweitert die "nur Aufwandskonten"-
    #    Regel für Wirtschaftsplan-Positionen: die Zuführung zur
    #    Instandhaltungsrücklage ist kein Aufwandskonto (SKR04), erscheint
    #    aber im Wirtschaftsplan als eigene Position (siehe Muster-
    #    Einzelabrechnung, Zeile "Instandhaltungsrücklage").
    op.add_column(
        "accounts",
        sa.Column("is_reserve_account", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        "UPDATE accounts SET is_reserve_account = TRUE "
        "WHERE account_number IN ('1810', '1820', '1830')"
    )

    # 3. Kopplung Wirtschaftsplan <-> Beschluss-Sammlung (§ 24 WEG) - siehe
    #    Router-Logik: Statuswechsel zu "Beschlossen" erzwingt resolution_id.
    op.add_column("budget_plans", sa.Column("resolution_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_budget_plans_resolution_id",
        "budget_plans",
        "resolution_collection",
        ["resolution_id"],
        ["resolution_id"],
    )
    op.create_index("idx_budget_plans_resolution_id", "budget_plans", ["resolution_id"])


def downgrade() -> None:
    op.drop_index("idx_budget_plans_resolution_id", table_name="budget_plans")
    op.drop_constraint("fk_budget_plans_resolution_id", "budget_plans", type_="foreignkey")
    op.drop_column("budget_plans", "resolution_id")
    op.drop_column("accounts", "is_reserve_account")
    op.drop_column("budget_positions", "description")