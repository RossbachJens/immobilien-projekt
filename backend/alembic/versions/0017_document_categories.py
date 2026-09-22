# backend/alembic/versions/0017_document_categories.py
"""Neue Dokumentkategorien für automatisch archivierte PDFs (Einladung, Niederschrift, Abrechnung)

Revision ID: 0017_document_categories
Revises: 0016_property_logo
Create Date: 2026-09-21
"""
from alembic import op

revision = "0017_document_categories"
down_revision = "0016_property_logo"
branch_labels = None
depends_on = None

OLD_CATEGORIES = (
    "'Kontoauszug', 'Rechnung', 'Angebot', 'Versicherung', 'Vertrag', "
    "'Protokoll', 'Sonstiges'"
)
NEW_CATEGORIES = (
    "'Kontoauszug', 'Rechnung', 'Angebot', 'Versicherung', 'Vertrag', "
    "'Protokoll', 'Sonstiges', 'Einladung', 'Niederschrift', 'Abrechnung'"
)


def upgrade() -> None:
    op.drop_constraint("ck_documents_category", "documents", type_="check")
    op.create_check_constraint(
        "ck_documents_category", "documents", f"category IN ({NEW_CATEGORIES})"
    )


def downgrade() -> None:
    # Zeilen mit den neuen, automatisch archivierten Kategorien würden den
    # alten CHECK sonst verletzen - vor dem Downgrade auf 'Sonstiges' umstellen.
    op.execute(
        "UPDATE documents SET category = 'Sonstiges' "
        "WHERE category IN ('Einladung', 'Niederschrift', 'Abrechnung')"
    )
    op.drop_constraint("ck_documents_category", "documents", type_="check")
    op.create_check_constraint(
        "ck_documents_category", "documents", f"category IN ({OLD_CATEGORIES})"
    )