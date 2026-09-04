"""Niederschrift: Protokolltext je TOP, Abstimmungsergebnisse, Versammlungs-Kopfdaten

Revision ID: 0007_niederschrift_details
Revises: 0006_owner_meetings
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_niederschrift_details"
down_revision = "0006_owner_meetings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Kopfdaten der Niederschrift - erst NACH der Versammlung bekannt, daher
    # alle nullable (bei Anlage der Versammlung/Einladung noch unbekannt).
    # Werden im Frontend zusammen mit minutes_text im Nachgang gepflegt.
    op.add_column("owner_meetings", sa.Column("chairperson", sa.String(length=150), nullable=True))
    op.add_column("owner_meetings", sa.Column("minute_taker", sa.String(length=150), nullable=True))
    op.add_column("owner_meetings", sa.Column("end_time", sa.Time(), nullable=True))
    op.add_column("owner_meetings", sa.Column("represented_shares", sa.Numeric(10, 2), nullable=True))
    op.add_column("owner_meetings", sa.Column("quorum_met", sa.Boolean(), nullable=True))
    op.add_column("owner_meetings", sa.Column("voting_key", sa.String(length=100), nullable=True))
    op.create_check_constraint(
        "ck_owner_meetings_represented_shares_non_negative",
        "owner_meetings",
        "represented_shares IS NULL OR represented_shares >= 0",
    )

    # Protokolltext je TOP - getrennt von 'description' (bleibt der VOR der
    # Versammlung sichtbare Ankündigungstext in der Einladung). Bei TOPs mit
    # Beschlussfassung bleibt protocol_text meist leer bzw. enthält nur den
    # Verlaufstext VOR der Formel "Die Eigentümergemeinschaft fasst folgenden
    # Beschluss" - der eigentliche Beschlusstext kommt aus
    # resolution_collection.description (siehe generate_minutes_pdf).
    op.add_column("meeting_agenda_items", sa.Column("protocol_text", sa.Text(), nullable=True))

    # Abstimmungsergebnis + präzise TOP-Verknüpfung je Beschluss. Das
    # bestehende Freitextfeld 'agenda_item' (z.B. "TOP 4") bleibt für
    # Beschlüsse ohne strukturierte Versammlung (Altdaten, reine
    # Umlaufbeschlüsse ohne Agenda) - agenda_item_id ist die maschinenlesbare
    # Ergänzung, die die automatische Niederschrift-Erzeugung auswertet.
    op.add_column("resolution_collection", sa.Column("agenda_item_id", sa.Integer(), nullable=True))
    op.add_column("resolution_collection", sa.Column("votes_yes", sa.Numeric(10, 2), nullable=True))
    op.add_column("resolution_collection", sa.Column("votes_no", sa.Numeric(10, 2), nullable=True))
    op.add_column("resolution_collection", sa.Column("votes_abstain", sa.Numeric(10, 2), nullable=True))

    op.create_foreign_key(
        "fk_resolution_collection_agenda_item_id",
        "resolution_collection",
        "meeting_agenda_items",
        ["agenda_item_id"],
        ["item_id"],
    )
    op.create_index("idx_resolution_collection_agenda_item_id", "resolution_collection", ["agenda_item_id"])
    op.create_check_constraint(
        "ck_resolution_collection_votes_non_negative",
        "resolution_collection",
        "(votes_yes IS NULL OR votes_yes >= 0) AND (votes_no IS NULL OR votes_no >= 0) "
        "AND (votes_abstain IS NULL OR votes_abstain >= 0)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_resolution_collection_votes_non_negative", "resolution_collection")
    op.drop_index("idx_resolution_collection_agenda_item_id", table_name="resolution_collection")
    op.drop_constraint("fk_resolution_collection_agenda_item_id", "resolution_collection", type_="foreignkey")
    op.drop_column("resolution_collection", "votes_abstain")
    op.drop_column("resolution_collection", "votes_no")
    op.drop_column("resolution_collection", "votes_yes")
    op.drop_column("resolution_collection", "agenda_item_id")
    op.drop_column("meeting_agenda_items", "protocol_text")
    op.drop_constraint("ck_owner_meetings_represented_shares_non_negative", "owner_meetings")
    op.drop_column("owner_meetings", "voting_key")
    op.drop_column("owner_meetings", "quorum_met")
    op.drop_column("owner_meetings", "represented_shares")
    op.drop_column("owner_meetings", "end_time")
    op.drop_column("owner_meetings", "minute_taker")
    op.drop_column("owner_meetings", "chairperson")