# backend/alembic/versions/0010_opening_balance_account.py
"""Eröffnungsbilanzkonto (9000) für Anfangsbestände bei Datenübernahme

Revision ID: 0010_opening_balance
Revises: 0009_owner_number
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_opening_balance"
down_revision = "0009_owner_number"
branch_labels = None
depends_on = None

# Name folgt Postgres' Default-Konvention für eine unbenannte inline-CHECK-
# Constraint ("<table>_<column>_check", siehe 01_schema.sql) - falls
# abweichend, mit \d accounts in psql den echten Namen prüfen (gleicher
# Vorbehalt wie bei accounts_account_number_key in 0001_property_accounts.py).
OLD_CHECK = "account_number ~ '^[0-8][0-9]{3}$'"
NEW_CHECK = "account_number ~ '^[0-9][0-9]{3}$'"


def upgrade() -> None:
    # Kontenklasse 9 war bisher bewusst ausgeschlossen (s. Kommentar in
    # 05_skr04_kontenrahmen.sql) - wird jetzt für genau einen Zweck gebraucht:
    # das SKR04-Eröffnungsbilanzkonto als Gegenkonto für Anfangsbestände bei
    # Übernahme einer bestehenden WEG (siehe app/routers/bank_accounts.py).
    op.drop_constraint("accounts_account_number_check", "accounts", type_="check")
    op.create_check_constraint("accounts_account_number_check", "accounts", NEW_CHECK)

    op.execute(
        """
        INSERT INTO accounts (account_number, account_name, account_class, type, is_active)
        VALUES ('9000', 'Eröffnungsbilanzkonto (Anfangsbestände bei Datenübernahme)', '9', 'PASSIV', TRUE)
        ON CONFLICT (account_number) WHERE property_id IS NULL DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM accounts WHERE account_number = '9000' AND property_id IS NULL")
    op.drop_constraint("accounts_account_number_check", "accounts", type_="check")
    op.create_check_constraint("accounts_account_number_check", "accounts", OLD_CHECK)