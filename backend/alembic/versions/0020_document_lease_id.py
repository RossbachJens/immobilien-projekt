# backend/alembic/versions/0020_document_lease_id.py
"""Mietvertrags-Verknüpfung für Dokumente (mieterseitige Betriebskostenabrechnung, Unterscheidung bei Mieterwechsel)

Revision ID: 0020_document_lease_id
Revises: 0019_tenant_shares
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_document_lease_id"
down_revision = "0019_tenant_shares"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents", sa.Column("lease_id", sa.Integer(), sa.ForeignKey("leases.lease_id"), nullable=True)
    )
    op.create_index("idx_documents_lease_id", "documents", ["lease_id"])


def downgrade() -> None:
    op.drop_index("idx_documents_lease_id", table_name="documents")
    op.drop_column("documents", "lease_id")