# backend/alembic/versions/0013_documents.py
"""Dokumentenverwaltung (DMS): Belege, Kontoauszüge, Angebote etc. als BYTEA in Postgres

Revision ID: 0013_documents
Revises: 0012_settlement_tax_details
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_documents"
down_revision = "0012_settlement_tax_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("document_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.property_id"), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        # Optionale, gezielte Verknüpfungen - alle nullable, analog
        # entry_lines.unit_id/lease_id.
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.unit_id"), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("owners.owner_id"), nullable=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.tenant_id"), nullable=True),
        sa.Column(
            "settlement_id", sa.Integer(), sa.ForeignKey("settlement_periods.settlement_id"), nullable=True
        ),
        sa.Column(
            "journal_entry_id", sa.Integer(), sa.ForeignKey("journal_entries.entry_id"), nullable=True
        ),
        sa.Column("meeting_id", sa.Integer(), sa.ForeignKey("owner_meetings.meeting_id"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        # Grundsatzentscheidung: Dateiinhalt direkt als BYTEA in Postgres
        # statt Dateisystem/S3 - einfacher Betrieb (ein Backup-Ziel, kein
        # Volume-Handling), auf Kosten von DB-/Backup-Größe. Upload-Größe
        # wird dafür serverseitig begrenzt (siehe app/routers/documents.py).
        sa.Column("content", sa.LargeBinary(), nullable=False),
        # intern = nur Admin/Verwalter, eigentuemer = zusätzlich zugeordnete
        # Eigentümer, alle = zusätzlich Mieter. Additiv gestaffelt, keine
        # granularere Rechtevergabe je Dokument vorgesehen.
        sa.Column("visibility", sa.String(20), nullable=False, server_default="intern"),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "category IN ('Kontoauszug', 'Rechnung', 'Angebot', 'Versicherung', 'Vertrag', "
            "'Protokoll', 'Sonstiges')",
            name="ck_documents_category",
        ),
        sa.CheckConstraint(
            "visibility IN ('intern', 'eigentuemer', 'alle')", name="ck_documents_visibility"
        ),
        sa.CheckConstraint("file_size_bytes > 0", name="ck_documents_file_size_positive"),
    )

    op.create_index("idx_documents_property_id", "documents", ["property_id"])
    op.create_index("idx_documents_unit_id", "documents", ["unit_id"])
    op.create_index("idx_documents_owner_id", "documents", ["owner_id"])
    op.create_index("idx_documents_tenant_id", "documents", ["tenant_id"])
    op.create_index("idx_documents_settlement_id", "documents", ["settlement_id"])
    op.create_index("idx_documents_journal_entry_id", "documents", ["journal_entry_id"])
    op.create_index("idx_documents_meeting_id", "documents", ["meeting_id"])


def downgrade() -> None:
    op.drop_index("idx_documents_meeting_id", table_name="documents")
    op.drop_index("idx_documents_journal_entry_id", table_name="documents")
    op.drop_index("idx_documents_settlement_id", table_name="documents")
    op.drop_index("idx_documents_tenant_id", table_name="documents")
    op.drop_index("idx_documents_owner_id", table_name="documents")
    op.drop_index("idx_documents_unit_id", table_name="documents")
    op.drop_index("idx_documents_property_id", table_name="documents")
    op.drop_table("documents")