# backend/alembic/versions/0006_owner_meetings.py
"""Eigentümerversammlungen: Einladung, Tagesordnung, Niederschrift

Revision ID: 0006_owner_meetings
Revises: 0005_property_bank_accounts
Create Date: 2026-08-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_owner_meetings"
down_revision = "0005_property_bank_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "owner_meetings",
        sa.Column("meeting_id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.property_id"), nullable=False),
        # Gleiche drei Werte wie bisher schon in resolution_collection.resolution_type
        # (siehe ResolutionForm.tsx MEETING_TYPES) - Freitext statt DB-ENUM,
        # konsistent mit dem bestehenden Feld.
        sa.Column("meeting_type", sa.String(length=50), nullable=False),
        # Versammlung: Termin der Versammlung. Umlaufbeschluss: Frist zur
        # Stimmabgabe.
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("meeting_time", sa.Time(), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("invitation_date", sa.Date(), nullable=True),
        sa.Column("agenda_intro", sa.Text(), nullable=True),
        sa.Column("minutes_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Geplant"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('Geplant', 'Eingeladen', 'Durchgeführt', 'Protokolliert')",
            name="ck_owner_meetings_status",
        ),
    )
    op.create_index("idx_owner_meetings_property_id", "owner_meetings", ["property_id"])

    op.create_table(
        "meeting_agenda_items",
        sa.Column("item_id", sa.Integer(), primary_key=True),
        sa.Column("meeting_id", sa.Integer(), sa.ForeignKey("owner_meetings.meeting_id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("meeting_id", "position", name="uq_meeting_agenda_items_position"),
    )
    op.create_index("idx_meeting_agenda_items_meeting_id", "meeting_agenda_items", ["meeting_id"])

    # Optionale Rückverknüpfung Beschluss -> Versammlung (NICHT TOP ->
    # Beschluss, siehe Erklärung im Chat) - ermöglicht der Niederschrift,
    # die tatsächlich gefassten Beschlüsse dieser Versammlung abzufragen.
    op.add_column("resolution_collection", sa.Column("meeting_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_resolution_collection_meeting_id",
        "resolution_collection",
        "owner_meetings",
        ["meeting_id"],
        ["meeting_id"],
    )
    op.create_index("idx_resolution_collection_meeting_id", "resolution_collection", ["meeting_id"])


def downgrade() -> None:
    op.drop_index("idx_resolution_collection_meeting_id", table_name="resolution_collection")
    op.drop_constraint("fk_resolution_collection_meeting_id", "resolution_collection", type_="foreignkey")
    op.drop_column("resolution_collection", "meeting_id")
    op.drop_index("idx_meeting_agenda_items_meeting_id", table_name="meeting_agenda_items")
    op.drop_table("meeting_agenda_items")
    op.drop_index("idx_owner_meetings_property_id", table_name="owner_meetings")
    op.drop_table("owner_meetings")