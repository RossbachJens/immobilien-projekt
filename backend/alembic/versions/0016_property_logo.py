# backend/alembic/versions/0016_property_logo.py
"""Verwalter-Logo je Liegenschaft für den PDF-Seitenkopf (Abrechnung, Einladung, Niederschrift)

Revision ID: 0016_property_logo
Revises: 0015_owner_salutation
Create Date: 2026-09-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_property_logo"
down_revision = "0015_owner_salutation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # BYTEA direkt in Postgres, wie schon bei documents.content - kein
    # zusätzliches Dateisystem-/Objektspeicher-Handling für eine einzelne,
    # kleine Datei je Liegenschaft. logo_mime_type steuert Content-Type
    # beim Ausliefern (app/routers/properties.py::get_property_logo) sowie
    # das Data-URI-Präfix beim WeasyPrint-Embedding (app/core/postal.py).
    # Kein DB-CHECK auf mime_type - die Beschränkung auf PNG/JPEG erzwingt
    # ausschließlich der Upload-Endpunkt (analog documents, dort ebenfalls
    # ohne CHECK auf mime_type).
    op.add_column("properties", sa.Column("logo_content", sa.LargeBinary(), nullable=True))
    op.add_column("properties", sa.Column("logo_mime_type", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("properties", "logo_mime_type")
    op.drop_column("properties", "logo_content")