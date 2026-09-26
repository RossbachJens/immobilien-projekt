# backend/alembic/versions/0018_tenant_reserve_accounts.py
"""Getrennte Forderungskonten für Nebenkostenvorauszahlung (Miete) und Instandhaltungsrücklage (Hausgeld)

Revision ID: 0018_tenant_reserve_accounts
Revises: 0017_document_categories
Create Date: 2026-09-24
"""
from alembic import op

revision = "0018_tenant_reserve_accounts"
down_revision = "0017_document_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Trennt die bisher gebündelten Forderungskonten, damit Zahlungseingänge
    # (app/routers/payments.py::create_payment) Kaltmiete/Nebenkosten-
    # vorauszahlung bzw. Bewirtschaftung/Instandhaltungsrücklage getrennt
    # buchen können - Grundlage für ein separates Soll/Ist der
    # Nebenkostenvorauszahlung (Mieterabrechnung, taggenaue Verteilung) und
    # der Rücklagenzuführung je Eigentümer (Rücklagendarstellung).
    op.execute(
        """
        INSERT INTO accounts (account_number, account_name, account_class, type, is_active)
        VALUES
            ('1210', 'Forderungen gegen Mieter (Nebenkostenvorauszahlung)', '1', 'AKTIV', TRUE),
            ('1225', 'Forderungen gegen Eigentümer (Instandhaltungsrücklage)', '1', 'AKTIV', TRUE)
        ON CONFLICT (account_number) WHERE property_id IS NULL DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM accounts WHERE account_number IN ('1210', '1225') AND property_id IS NULL"
    )