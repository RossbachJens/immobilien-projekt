# backend/alembic/versions/0002_resolution_details.py
"""Beschluss-Sammlung: fehlende Pflichtfelder nach Muster (§ 24 WEG)

Revision ID: 0002_resolution_details
Revises: 0001_property_accounts
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_resolution_details"          # ← 23 Zeichen statt 34
down_revision = "0001_property_accounts"
branch_labels = None
depends_on = None




def upgrade() -> None:
    op.add_column("resolution_collection", sa.Column("lfd_nr", sa.Integer(), nullable=True))
    op.add_column("resolution_collection", sa.Column("meeting_location", sa.String(200), nullable=True))
    op.add_column("resolution_collection", sa.Column("agenda_item", sa.String(50), nullable=True))
    op.add_column("resolution_collection", sa.Column("court_name", sa.String(200), nullable=True))
    op.add_column("resolution_collection", sa.Column("court_case_number", sa.String(100), nullable=True))
    op.add_column("resolution_collection", sa.Column("court_decision_date", sa.Date(), nullable=True))
    op.add_column("resolution_collection", sa.Column("court_ruling_text", sa.Text(), nullable=True))
    op.add_column("resolution_collection", sa.Column("court_parties", sa.String(300), nullable=True))
    op.add_column("resolution_collection", sa.Column("status_note", sa.Text(), nullable=True))
    op.add_column("resolution_collection", sa.Column("created_by", sa.Integer(), nullable=True))
    op.add_column(
        "resolution_collection", sa.Column("refers_to_resolution_id", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_resolution_collection_created_by", "resolution_collection", "users", ["created_by"], ["user_id"]
    )
    op.create_foreign_key(
        "fk_resolution_collection_refers_to",
        "resolution_collection",
        "resolution_collection",
        ["refers_to_resolution_id"],
        ["resolution_id"],
    )

    # Backfill für evtl. bereits vorhandene Zeilen - vor dieser Migration gab
    # es keine offizielle laufende Nummer, daher pro Liegenschaft aufsteigend
    # nach resolution_id (= bisherige Anlage-Reihenfolge) nachvergeben.
    op.execute(
        """
        WITH numbered AS (
            SELECT resolution_id,
                   ROW_NUMBER() OVER (PARTITION BY property_id ORDER BY resolution_id) AS rn
            FROM resolution_collection
        )
        UPDATE resolution_collection rc
        SET lfd_nr = numbered.rn
        FROM numbered
        WHERE rc.resolution_id = numbered.resolution_id
        """
    )

    op.alter_column("resolution_collection", "lfd_nr", nullable=False)
    # Bewusst OHNE "WHERE deleted_at IS NULL" (anders als die partiellen
    # Unique-Indizes bei users/owners/tenants) - die Lfd. Nr. darf laut
    # Muster nie doppelt vergeben werden, auch nicht nach einer Korrektur.
    op.create_unique_constraint(
        "uq_resolution_collection_property_lfd_nr", "resolution_collection", ["property_id", "lfd_nr"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_resolution_collection_property_lfd_nr", "resolution_collection", type_="unique")
    op.drop_constraint("fk_resolution_collection_refers_to", "resolution_collection", type_="foreignkey")
    op.drop_constraint("fk_resolution_collection_created_by", "resolution_collection", type_="foreignkey")
    for col in (
        "refers_to_resolution_id", "created_by", "status_note", "court_parties",
        "court_ruling_text", "court_decision_date", "court_case_number", "court_name",
        "agenda_item", "meeting_location", "lfd_nr",
    ):
        op.drop_column("resolution_collection", col)