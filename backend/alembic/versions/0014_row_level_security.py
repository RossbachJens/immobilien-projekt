"""Row-Level-Security (Postgres) als zweite Verteidigungslinie neben der
Query-Filterung in app/core/access.py::accessible_property_ids()

Revision ID: 0014_row_level_security
Revises: 0013_documents
Create Date: 2026-09-10
"""
import os

from alembic import op

revision = "0014_row_level_security"
down_revision = "0013_documents"  # ggf. anpassen, siehe Hinweis im Chat
branch_labels = None
depends_on = None

# NUR für lokale Entwicklung/Docker Compose. In Produktion per Secret-
# Manager setzen (APP_DB_PASSWORD) - gleiches Prinzip wie JWT_SECRET/
# PII_ENCRYPTION_KEY in app/core/config.py. MUSS mit der DATABASE_URL in
# backend/.env bzw. docker-compose.yml übereinstimmen.
APP_USER_PASSWORD = os.environ.get("APP_DB_PASSWORD", "app_user_dev_password")

# Tabellen mit direkter property_id-Spalte, deren Policy schlicht prüft, ob
# property_id in der für die aktuelle Rolle zugreifbaren Menge liegt.
# 'properties' und 'accounts' bewusst NICHT in dieser Liste - beide brauchen
# eine abweichende Policy (siehe unten).
DIRECT_PROPERTY_TABLES = [
    "units",
    "user_properties",
    "unit_allocation_keys",
    "journal_entries",
    "entry_lines",
    "resolution_collection",
    "budget_plans",
    "special_assessments",
    "settlement_periods",
    "property_bank_accounts",
    "owner_meetings",
    "documents",
]

# (Tabelle, FK-Spalte, Elterntabelle, Elternspalte) - die Policy prüft nur,
# ob die referenzierte Zeile der Elterntabelle für die Rolle sichtbar ist.
# Das kaskadiert automatisch durch beliebig viele Ebenen, weil Postgres die
# Policy der Elterntabelle auch innerhalb dieser Subquery anwendet - die
# Zugriffslogik muss also nur EINMAL an der Wurzel (direkte
# property_id-Spalte) stehen, nicht an jeder abgeleiteten Tabelle erneut.
CASCADING_TABLES = [
    ("unit_owner_history", "unit_id", "units", "unit_id"),
    ("leases", "unit_id", "units", "unit_id"),
    ("budget_positions", "budget_id", "budget_plans", "budget_id"),
    ("unit_budget_shares", "position_id", "budget_positions", "position_id"),
    ("unit_special_assessment_shares", "assessment_id", "special_assessments", "assessment_id"),
    ("settlement_positions", "settlement_id", "settlement_periods", "settlement_id"),
    ("settlement_position_accounts", "position_id", "settlement_positions", "position_id"),
    ("unit_settlement_shares", "position_id", "settlement_positions", "position_id"),
    ("unit_settlement_tax_shares", "position_id", "settlement_positions", "position_id"),
    ("unit_settlement_summaries", "settlement_id", "settlement_periods", "settlement_id"),
    ("reserve_fund_statements", "settlement_id", "settlement_periods", "settlement_id"),
    ("reserve_fund_statement_operating_accounts", "statement_id", "reserve_fund_statements", "statement_id"),
    ("reserve_fund_positions", "statement_id", "reserve_fund_statements", "statement_id"),
    ("reserve_fund_position_accounts", "position_id", "reserve_fund_positions", "position_id"),
    ("reserve_fund_unit_shares", "position_id", "reserve_fund_positions", "position_id"),
    ("meeting_agenda_items", "meeting_id", "owner_meetings", "meeting_id"),
]


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Hilfsfunktionen
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_current_user_id() RETURNS INT
        LANGUAGE sql STABLE AS $$
            SELECT NULLIF(current_setting('app.current_user_id', true), '')::int;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_current_role() RETURNS TEXT
        LANGUAGE sql STABLE AS $$
            SELECT NULLIF(current_setting('app.current_role', true), '');
        $$;
        """
    )
    # SECURITY DEFINER: läuft mit den Rechten des Funktions-Eigentümers
    # (postgres - diese Migration läuft über MIGRATION_DATABASE_URL als
    # Superuser), NICHT mit denen des aufrufenden app_user. Nötig, weil die
    # Funktion selbst user_properties/unit_owner_history/leases abfragt -
    # Tabellen, die weiter unten SELBST RLS-geschützt werden. Ohne
    # SECURITY DEFINER würde z.B. die Policy von 'properties' für einen
    # Eigentümer eine RLS-gefilterte Abfrage auf unit_owner_history
    # auslösen, die zur Beantwortung wiederum denselben Mechanismus
    # bräuchte - Henne-Ei-Problem. SECURITY DEFINER durchbricht das, indem
    # die Funktion intern wie der Tabelleneigentümer (RLS-Bypass) liest.
    # Spiegelt exakt app/core/access.py::accessible_property_ids().
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_accessible_property_ids() RETURNS SETOF INT
        LANGUAGE sql STABLE SECURITY DEFINER AS $$
            SELECT property_id FROM user_properties
             WHERE fn_current_role() = 'verwalter'
               AND user_id = fn_current_user_id()
            UNION
            SELECT DISTINCT u.property_id
              FROM units u
              JOIN unit_owner_history uoh ON uoh.unit_id = u.unit_id
              JOIN users usr ON usr.owner_id = uoh.owner_id
             WHERE fn_current_role() = 'eigentuemer'
               AND usr.user_id = fn_current_user_id()
               AND uoh.valid_to IS NULL
            UNION
            SELECT DISTINCT u.property_id
              FROM units u
              JOIN leases l ON l.unit_id = u.unit_id
              JOIN users usr ON usr.tenant_id = l.tenant_id
             WHERE fn_current_role() = 'mieter'
               AND usr.user_id = fn_current_user_id()
               AND l.deleted_at IS NULL
               AND l.status = 'aktiv';
        $$;
        """
    )

    # ------------------------------------------------------------------
    # 2. Eingeschränkter App-User (postgres ist Superuser und würde JEDE
    #    RLS-Policy ignorieren, unabhängig davon wie sie definiert ist)
    # ------------------------------------------------------------------
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
                CREATE ROLE app_user LOGIN PASSWORD '{APP_USER_PASSWORD}';
            ELSE
                ALTER ROLE app_user WITH PASSWORD '{APP_USER_PASSWORD}';
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO app_user', current_database());
        END
        $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO app_user;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;")
    op.execute("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_user;")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;"
    )
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO app_user;")

    # ------------------------------------------------------------------
    # 3. properties - Sonderfall: Policy für SELECT/UPDATE/DELETE prüft
    #    property_id wie überall, ABER beim INSERT existiert die neue
    #    property_id per Definition noch in KEINER user_properties-Zeile
    #    (die Zuordnung kann ja erst NACH Anlage erfolgen) - ohne separate
    #    INSERT-Policy könnte ein Verwalter (app-seitig laut
    #    _require_write_role() in properties.py ausdrücklich erlaubt) nie
    #    eine neue Liegenschaft anlegen. Mehrere PERMISSIVE Policies für
    #    denselben Befehl werden von Postgres mit OR verknüpft - die
    #    zusätzliche INSERT-Policy lockert daher NUR das Anlegen, nicht
    #    das Lesen/Ändern/Löschen bestehender Liegenschaften.
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE properties ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY properties_property_isolation ON properties
        FOR ALL
        USING (
            fn_current_role() = 'admin'
            OR property_id IN (SELECT fn_accessible_property_ids())
        );
        """
    )
    op.execute(
        """
        CREATE POLICY properties_insert_by_verwalter ON properties
        FOR INSERT
        WITH CHECK (fn_current_role() IN ('admin', 'verwalter'));
        """
    )

    # ------------------------------------------------------------------
    # 4. accounts - Sonderfall: property_id IS NULL bedeutet globales
    #    SKR04-Basiskonto (für ALLE Rollen sichtbar), property_id gesetzt
    #    bedeutet liegenschaftseigenes Konto (wie überall eingeschränkt).
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY accounts_property_isolation ON accounts
        FOR ALL
        USING (
            property_id IS NULL
            OR fn_current_role() = 'admin'
            OR property_id IN (SELECT fn_accessible_property_ids())
        );
        """
    )

    # ------------------------------------------------------------------
    # 5. Tabellen mit direkter property_id-Spalte
    # ------------------------------------------------------------------
    for table in DIRECT_PROPERTY_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY {table}_property_isolation ON {table}
            FOR ALL
            USING (
                fn_current_role() = 'admin'
                OR property_id IN (SELECT fn_accessible_property_ids())
            );
            """
        )

    # ------------------------------------------------------------------
    # 6. Kaskadierende Tabellen (kein eigenes property_id, Zugriff über
    #    die bereits RLS-geschützte Elterntabelle)
    # ------------------------------------------------------------------
    for table, fk_column, parent_table, parent_pk in CASCADING_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY {table}_property_isolation ON {table}
            FOR ALL
            USING (
                {fk_column} IN (SELECT {parent_pk} FROM {parent_table})
            );
            """
        )


def downgrade() -> None:
    for table, *_ in CASCADING_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_property_isolation ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    for table in DIRECT_PROPERTY_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_property_isolation ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS accounts_property_isolation ON accounts;")
    op.execute("ALTER TABLE accounts DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS properties_insert_by_verwalter ON properties;")
    op.execute("DROP POLICY IF EXISTS properties_property_isolation ON properties;")
    op.execute("ALTER TABLE properties DISABLE ROW LEVEL SECURITY;")

    # Hinweis: DROP ROLE schlägt fehl, solange der Backend-Container noch
    # als app_user verbunden ist - vor einem echten Downgrade den Container
    # stoppen (docker compose stop backend).
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM app_user;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM app_user;")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM app_user;"
    )
    op.execute("REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM app_user;")
    op.execute("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM app_user;")
    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM app_user;")
    op.execute("REVOKE USAGE ON SCHEMA public FROM app_user;")
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM app_user', current_database());
        END
        $$;
        """
    )
    op.execute("DROP ROLE IF EXISTS app_user;")

    op.execute("DROP FUNCTION IF EXISTS fn_accessible_property_ids();")
    op.execute("DROP FUNCTION IF EXISTS fn_current_role();")
    op.execute("DROP FUNCTION IF EXISTS fn_current_user_id();")