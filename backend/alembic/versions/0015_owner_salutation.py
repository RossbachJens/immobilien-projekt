# backend/alembic/versions/0015_owner_salutation.py
"""Anrede (Herr/Frau) je Eigentümer - für DIN-5008-Anschriftfeld beim Postversand

Revision ID: 0015_owner_salutation
Revises: 0014_row_level_security
Create Date: 2026-09-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_owner_salutation"
down_revision = "0014_row_level_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NULL = keine Anrede (z.B. Firmenadressat oder schlicht nicht gepflegt) -
    # dann entfällt beim Postversand einfach die Anredezeile im
    # DIN-5008-Anschriftfeld (siehe app/core/postal.py).
    op.add_column("owners", sa.Column("salutation", sa.String(length=10), nullable=True))
    op.create_check_constraint(
        "ck_owners_salutation",
        "owners",
        "salutation IS NULL OR salutation IN ('Herr', 'Frau')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_owners_salutation", "owners", type_="check")
    op.drop_column("owners", "salutation")