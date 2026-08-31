# backend/alembic/versions/0005_property_bank_accounts.py — komplett ersetzen
"""Reale Bankkonten je Liegenschaft mit Gültigkeitszeitraum (§ 27 Abs. 5 WEG)

Revision ID: 0005_property_bank_accounts
Revises: 0004_settlement
Create Date: 2026-08-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_property_bank_accounts"
down_revision = "0004_settlement"
branch_labels = None
depends_on = None

# WICHTIG: postgresql.ENUM statt generischem sa.Enum. Bei sa.Enum baut
# SQLAlchemy beim Dispatch von create_table() intern über dialect_impl()
# eine eigene, dialektspezifische Kopie des Typs - dabei geht das
# create_type-Flag verloren, weshalb create_table() den Typ trotzdem selbst
# nochmal anzulegen versucht ("DuplicateObject"). postgresql.ENUM ist bereits
# die dialektspezifische Klasse selbst, daher wird create_type dort korrekt
# respektiert (offizielles Alembic-Cookbook-Muster für genau diesen Fall).
account_purpose_enum = postgresql.ENUM(
    "GIROKONTO", "RUECKLAGENKONTO", "SONSTIGES",
    name="property_bank_account_purpose",
)


def upgrade() -> None:
    account_purpose_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "property_bank_accounts",
        sa.Column("bank_account_id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.property_id"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.account_id"), nullable=False),
        sa.Column(
            "account_purpose",
            postgresql.ENUM(
                "GIROKONTO", "RUECKLAGENKONTO", "SONSTIGES",
                name="property_bank_account_purpose",
                # Verhindert, dass create_table() den Typ zusätzlich selbst
                # anlegt - der ist bereits über die Zeile oben erstellt.
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("purpose_detail", sa.String(length=100), nullable=True),
        sa.Column("bank_name", sa.String(length=100), nullable=False),
        sa.Column("iban_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("bic_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("iban_last4", sa.String(length=4), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_property_bank_accounts_valid_range",
        ),
    )

    op.create_index(
        "idx_property_bank_accounts_property_id", "property_bank_accounts", ["property_id"]
    )

    op.execute(
        """
        ALTER TABLE property_bank_accounts
            ADD CONSTRAINT excl_property_bank_accounts_no_overlap
            EXCLUDE USING gist (
                account_id WITH =,
                daterange(valid_from, valid_to, '[]') WITH &&
            )
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE property_bank_accounts DROP CONSTRAINT excl_property_bank_accounts_no_overlap"
    )
    op.drop_index("idx_property_bank_accounts_property_id", table_name="property_bank_accounts")
    # op.drop_table() bekommt hier nur den Tabellennamen (kein Column-Objekt
    # mit Typinfo) - löst daher kein automatisches DROP TYPE aus. Der
    # explizite .drop() unten bleibt somit die einzige Drop-Stelle, kein
    # Duplicate-Risiko wie beim Create.
    op.drop_table("property_bank_accounts")
    account_purpose_enum.drop(op.get_bind(), checkfirst=True)