-- =====================================================================
-- 01_schema.sql
-- Relationales Immobilien- & WEG-Buchhaltungssystem (SKR 04)
-- PostgreSQL 16
--
-- Änderungen gegenüber v4.1:
--   - Fehlende Tabellen ergänzt: accounts, journal_entries, leases,
--     user_properties, unit_owner_history, access_log, gdpr_deletion_log
--   - DSGVO-Maßnahmen umgesetzt (siehe Abschnitt "DSGVO" unten)
--   - Phase 1: users.is_admin ergänzt (globale Admin-Rolle, siehe Router
--     app/routers/auth.py). Bewusst hier im Basisschema statt als Alembic-
--     Migration, da die Baseline (`alembic stamp head`) noch nicht gesetzt
--     wurde und dieses Skript vor jedem Alembic-Lauf ausgeführt wird.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. EXTENSIONS
-- ---------------------------------------------------------------------
-- pgcrypto wird für die Verschlüsselung von Bankverbindungsdaten
-- (IBAN/BIC) benötigt -> Art. 32 DSGVO ("Stand der Technik").
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gist;  -- für den EXCLUDE-Constraint unten

-- ---------------------------------------------------------------------
-- 1. ENUM-TYPEN
-- ---------------------------------------------------------------------
CREATE TYPE entry_direction AS ENUM ('DEBIT', 'CREDIT');
CREATE TYPE account_type    AS ENUM ('AKTIV', 'PASSIV', 'ERTRAG', 'AUFWAND');
CREATE TYPE lease_status    AS ENUM ('aktiv', 'beendet', 'gekuendigt');
CREATE TYPE property_role   AS ENUM ('Verwalter', 'Buchhalter', 'Lesezugriff');

-- =====================================================================
-- 2. STAMMDATEN
-- =====================================================================

-- --------------------------- properties -------------------------------
-- ---------------------------------------------------------------------
-- properties
-- ---------------------------------------------------------------------
CREATE TABLE properties (
    property_id           INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                   VARCHAR(100) NOT NULL,
    address                TEXT NOT NULL,
    total_square_meters    NUMERIC(10,2) CHECK (total_square_meters > 0),
    construction_year      INT CHECK (construction_year <= EXTRACT(YEAR FROM CURRENT_DATE)),
    -- Nenner für die Verteilung nach § 16 WEG (z.B. 1000 oder 10000). Die
    -- einzelnen Einheiten tragen ihren Anteil daran in units.mea (Zähler).
    total_mea              NUMERIC(10,2) CHECK (total_mea > 0),
    description            TEXT,
    created_at             TIMESTAMP NOT NULL DEFAULT now(),
    updated_at             TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at             TIMESTAMPTZ
);

-- ----------------------------- units -----------------------------------
CREATE TABLE units (
    unit_id        INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id    INT NOT NULL REFERENCES properties(property_id),
    unit_number    VARCHAR(20) NOT NULL,
    floor          VARCHAR(20),
    square_meters  NUMERIC(6,2) NOT NULL CHECK (square_meters > 0),
    -- Miteigentumsanteil dieser Einheit (Zähler) - Anteil am total_mea der
    -- zugehörigen Liegenschaft, z.B. 168.47 von insgesamt 1000.
    mea            NUMERIC(10,2) CHECK (mea > 0),
    unit_type      VARCHAR(30) CHECK (unit_type IN ('Wohnung', 'Stellplatz', 'Gewerbe')),
    deleted_at     TIMESTAMPTZ,
    UNIQUE (property_id, unit_number)
);

-- ---------------------------- owners ------------------------------------
-- DSGVO: IBAN/BIC werden verschlüsselt (pgcrypto) statt im Klartext
-- gespeichert. iban_last4 dient als Anzeige-Feld ("...1234") gemäß dem
-- Grundsatz der Datenminimierung (Art. 5 Abs. 1 lit. c DSGVO), sodass die
-- Anwendung nicht bei jeder Anzeige entschlüsseln muss.
CREATE TABLE owners (
    owner_id                INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name               VARCHAR(50),
    last_name                VARCHAR(50) NOT NULL,
    company_name              VARCHAR(100),
    email                     VARCHAR(100),
    phone                     VARCHAR(50),
    street_and_number        VARCHAR(150) NOT NULL,
    postal_code               VARCHAR(10),
    city                      VARCHAR(100),
    bank_name                 VARCHAR(100),
    iban_encrypted             BYTEA,              -- pgp_sym_encrypt(iban, key)
    bic_encrypted              BYTEA,              -- pgp_sym_encrypt(bic, key)
    iban_last4                VARCHAR(4),
    sepa_mandate_reference    VARCHAR(35),
    sepa_granted_at           DATE,
    created_at                TIMESTAMP NOT NULL DEFAULT now(),
    updated_at                TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at                TIMESTAMPTZ,
    anonymized_at             TIMESTAMPTZ         -- s. Abschnitt DSGVO / Loeschkonzept
);

-- ---------------------------- tenants -----------------------------------
CREATE TABLE tenants (
    tenant_id               INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name               VARCHAR(50) NOT NULL,
    last_name                VARCHAR(50) NOT NULL,
    email                     VARCHAR(100),
    street_and_number        VARCHAR(150) NOT NULL,
    postal_code               VARCHAR(10),
    city                      VARCHAR(100),
    bank_name                 VARCHAR(100),
    iban_encrypted             BYTEA,
    bic_encrypted              BYTEA,
    iban_last4                VARCHAR(4),
    sepa_mandate_reference    VARCHAR(35),
    created_at                TIMESTAMP NOT NULL DEFAULT now(),
    updated_at                TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at                TIMESTAMPTZ,
    anonymized_at             TIMESTAMPTZ
);

-- ----------------------------- users ------------------------------------
CREATE TABLE users (
    user_id                INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                    VARCHAR(100) NOT NULL,
    email                   VARCHAR(100) NOT NULL,
    password_hash            VARCHAR(255),
    google_sub_id            VARCHAR(255),
    must_change_password    BOOLEAN NOT NULL DEFAULT FALSE,
    is_admin                BOOLEAN NOT NULL DEFAULT FALSE, -- Phase 1: globale Admin-Rolle
    owner_id                 INT REFERENCES owners(owner_id),
    tenant_id                INT REFERENCES tenants(tenant_id),
    created_at               TIMESTAMP NOT NULL DEFAULT now(),
    last_login_at            TIMESTAMP,
    deleted_at                TIMESTAMPTZ,
    CONSTRAINT chk_users_auth_method
        CHECK (password_hash IS NOT NULL OR google_sub_id IS NOT NULL)
);

-- ------------------- password_reset_tokens --------------------------------
-- Fuer den "Passwort vergessen"-Flow (app/routers/auth.py). Es wird nur der
-- Hash des Tokens gespeichert (SHA-256, siehe app/core/security.py), nicht
-- der Token selbst - ein DB-Leak gibt so keine gueltigen Reset-Links preis.
-- E-Mail-Versand ist bewusst noch nicht angebunden (PROJECTPLAN.md, Phase 7)
-- - der Rohtoken wird uebergangsweise nur im Development-Modus direkt in der
-- API-Antwort zurueckgegeben (settings.environment).
CREATE TABLE password_reset_tokens (
    token_id      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id        INT NOT NULL REFERENCES users(user_id),
    token_hash      VARCHAR(64) NOT NULL, -- hex-SHA-256, immer 64 Zeichen
    expires_at      TIMESTAMP NOT NULL,
    used_at         TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_password_reset_tokens_hash ON password_reset_tokens(token_hash);
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
-- =====================================================================
-- 3. ZUORDNUNGEN / MANDANTENTRENNUNG
-- =====================================================================

-- --------------------- unit_owner_history --------------------------------
-- Historisierte Eigentümerzuordnung (wichtig bei Eigentümerwechsel
-- unterjährig, z.B. für korrekte Kostenverteilung).
CREATE TABLE unit_owner_history (
    history_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unit_id             INT NOT NULL REFERENCES units(unit_id),
    owner_id            INT NOT NULL REFERENCES owners(owner_id),
    ownership_share      NUMERIC(7,4) NOT NULL CHECK (ownership_share > 0), -- MEA, z.B. Anteil / 10000stel
    valid_from           DATE NOT NULL,
    valid_to             DATE,
    CHECK (valid_to IS NULL OR valid_to > valid_from)
);

-- ------------------------ user_properties --------------------------------
-- Verwalter/Buchhalter sehen nur ihnen zugewiesene Objekte.
CREATE TABLE user_properties (
    user_id         INT NOT NULL REFERENCES users(user_id),
    property_id     INT NOT NULL REFERENCES properties(property_id),
    role             property_role NOT NULL DEFAULT 'Verwalter',
    granted_at        TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, property_id)
);

-- --------------------- unit_allocation_keys -------------------------------
CREATE TABLE unit_allocation_keys (
    key_id                INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id            INT NOT NULL REFERENCES properties(property_id),
    unit_id                 INT NOT NULL REFERENCES units(unit_id),
    key_type                VARCHAR(50) NOT NULL,
    numerator_value          NUMERIC(10,4) NOT NULL CHECK (numerator_value >= 0),
    denominator_value        NUMERIC(10,4) NOT NULL CHECK (denominator_value > 0),
    -- Gültigkeitszeitraum statt einzelnem billing_year (s. PROJECTPLAN.md,
    -- Grundsatzentscheidung "Umlageschlüssel-Gültigkeit"). valid_to_year = NULL
    -- bedeutet "aktuell gültig / bis auf Weiteres". Ein Wechsel ist fachlich nur
    -- zum naechsten 01.01. zulaessig - diese Regel wird NICHT hier als starres
    -- CHECK erzwungen (siehe Kommentar oben), sondern erst in der Service-
    -- Schicht (Phase 5).
    valid_from_year          INT NOT NULL,
    valid_to_year             INT,
    CHECK (valid_to_year IS NULL OR valid_to_year >= valid_from_year)
);

-- Verhindert überlappende Gültigkeitszeiträume je Einheit+Schlüsseltyp
-- (ersetzt das alte UNIQUE(unit_id, key_type, billing_year)). NULL wird als
-- "unendlich" über einen Sentinel-Wert abgebildet, da int4range keine
-- echten unbegrenzten Ganzzahl-Grenzen kennt.
ALTER TABLE unit_allocation_keys
    ADD CONSTRAINT excl_unit_allocation_keys_no_overlap
    EXCLUDE USING gist (
        unit_id WITH =,
        key_type WITH =,
        int4range(valid_from_year, COALESCE(valid_to_year, 999999) + 1) WITH &&
    );
-- ------------------------------ leases -------------------------------------
CREATE TABLE leases (
    lease_id                    INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unit_id                      INT NOT NULL REFERENCES units(unit_id),
    tenant_id                    INT NOT NULL REFERENCES tenants(tenant_id),
    start_date                   DATE NOT NULL,
    end_date                     DATE,
    cold_rent                    NUMERIC(10,2) NOT NULL CHECK (cold_rent > 0),
    additional_costs_prepayment    NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (additional_costs_prepayment >= 0),
    deposit_amount                NUMERIC(10,2) CHECK (deposit_amount >= 0),
    deposit_received_at            DATE,
    status                        lease_status NOT NULL DEFAULT 'aktiv',
    created_at                    TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at                    TIMESTAMPTZ,
    CHECK (end_date IS NULL OR end_date > start_date)
);

-- =====================================================================
-- 4. BUCHHALTUNG (SKR 04)
-- =====================================================================

-- ----------------------------- accounts -------------------------------------
CREATE TABLE accounts (
    account_id       INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_number    VARCHAR(4) NOT NULL UNIQUE CHECK (account_number ~ '^[0-8][0-9]{3}$'),
    account_name       VARCHAR(100) NOT NULL,
    account_class      CHAR(1) NOT NULL, -- SKR04-Kontenklasse 0-8
    type                account_type NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE
);

-- ------------------------- journal_entries -----------------------------------
-- Belegkopf. "locked_at" markiert Buchungen, die nach Monats-/Jahres-
-- abschluss revisionssicher gesperrt sind (keine UPDATE/DELETE mehr,
-- nur Stornobuchung über reversed_entry_id).
CREATE TABLE journal_entries (
    entry_id             INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id           INT NOT NULL REFERENCES properties(property_id),
    entry_date             DATE NOT NULL,
    document_reference      VARCHAR(100),
    description            TEXT NOT NULL,
    created_by              INT REFERENCES users(user_id),
    created_at              TIMESTAMP NOT NULL DEFAULT now(),
    locked_at                TIMESTAMP,
    reversed_entry_id        INT REFERENCES journal_entries(entry_id)
);

-- -------------------------- entry_lines ---------------------------------------
CREATE TABLE entry_lines (
    line_id        INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entry_id        INT NOT NULL REFERENCES journal_entries(entry_id),
    account_id       INT NOT NULL REFERENCES accounts(account_id),
    property_id      INT REFERENCES properties(property_id),
    unit_id           INT REFERENCES units(unit_id),
    lease_id          INT REFERENCES leases(lease_id),
    amount            NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    direction         entry_direction NOT NULL,
    created_at        TIMESTAMP NOT NULL DEFAULT now()
);

-- =====================================================================
-- 5. WIRTSCHAFTSPLÄNE, SONDERUMLAGEN & BESCHLUSS-SAMMLUNG
-- =====================================================================

-- ------------------------- resolution_collection -------------------------------
-- Bildet die gesetzlich vorgeschriebene Beschluss-Sammlung ab (§ 24 WEG).
-- War im gelieferten Entwurf als Fremdschlüsselziel referenziert, aber nicht
-- definiert -- hier sinnvoll ergänzt. WICHTIG: Einträge sollten grundsätzlich
-- NICHT gelöscht werden (dauerhafte Dokumentationspflicht über die gesamte
-- Lebensdauer der WEG) -- deleted_at ist hier nur für die Korrektur
-- fehlerhaft erfasster Einträge vorgesehen, nicht für reguläre
-- Lebenszyklus-Verwaltung wie bei den übrigen Tabellen.
CREATE TABLE resolution_collection (
    resolution_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id             INT NOT NULL REFERENCES properties(property_id),
    resolution_date          DATE NOT NULL,
    title                    VARCHAR(200) NOT NULL,
    description              TEXT,
    resolution_type           VARCHAR(50), -- z.B. 'Eigentuemerversammlung', 'Umlaufbeschluss'
    proposed_by_owner_id       INT REFERENCES owners(owner_id),
    created_at                TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at                 TIMESTAMPTZ
);

-- ---------------------------- budget_plans --------------------------------------
CREATE TABLE budget_plans (
    budget_id       INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id       INT NOT NULL REFERENCES properties(property_id) ON DELETE CASCADE,
    fiscal_year        INT NOT NULL,
    title              VARCHAR(150) NOT NULL,
    status             VARCHAR(30) NOT NULL DEFAULT 'Entwurf'
                          CHECK (status IN ('Entwurf', 'Beschlossen', 'Inaktiv')),
    created_at         TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
    -- Hinweis: "UNIQUE (property_id, fiscal_year) WHERE deleted_at IS NULL" als
    -- Tabellen-CONSTRAINT ist in Postgres syntaktisch nicht zulässig (WHERE ist
    -- nur bei Indizes erlaubt). Umgesetzt stattdessen als partieller Unique-Index
    -- uq_budget_plans_property_year weiter unten im Abschnitt INDIZES.
);

-- -------------------------- budget_positions --------------------------------------
CREATE TABLE budget_positions (
    position_id             INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    budget_id                 INT NOT NULL REFERENCES budget_plans(budget_id) ON DELETE CASCADE,
    account_id                 INT NOT NULL REFERENCES accounts(account_id), -- SKR04-Aufwandskonto, z.B. 5200 Heizung
    planned_amount               NUMERIC(12,2) NOT NULL CHECK (planned_amount >= 0),
    allocation_key_type           VARCHAR(50) NOT NULL -- z.B. 'MEA', 'Wohnflaeche'
);

-- ------------------------- unit_budget_shares ----------------------------------------
CREATE TABLE unit_budget_shares (
    share_id                      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    position_id                     INT NOT NULL REFERENCES budget_positions(position_id) ON DELETE CASCADE,
    unit_id                          INT NOT NULL REFERENCES units(unit_id) ON DELETE CASCADE,
    allocated_planned_amount           NUMERIC(12,2) NOT NULL CHECK (allocated_planned_amount >= 0),
    monthly_installment                 NUMERIC(12,2) NOT NULL CHECK (monthly_installment >= 0),
    UNIQUE (position_id, unit_id)
);

-- ------------------------ special_assessments -----------------------------------------
CREATE TABLE special_assessments (
    assessment_id              INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id                  INT NOT NULL REFERENCES properties(property_id) ON DELETE CASCADE,
    resolution_id                  INT REFERENCES resolution_collection(resolution_id) ON DELETE SET NULL,
    title                          VARCHAR(150) NOT NULL,
    total_required_amount            NUMERIC(12,2) NOT NULL CHECK (total_required_amount > 0),
    due_date                        DATE NOT NULL,
    status                          VARCHAR(30) NOT NULL DEFAULT 'Geplant'
                                       CHECK (status IN ('Geplant', 'Eingefordert', 'Storniert')),
    created_at                      TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at                       TIMESTAMPTZ
);

-- ----------------- unit_special_assessment_shares ---------------------------------------
CREATE TABLE unit_special_assessment_shares (
    unit_assessment_id             INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    assessment_id                    INT NOT NULL REFERENCES special_assessments(assessment_id) ON DELETE CASCADE,
    unit_id                           INT NOT NULL REFERENCES units(unit_id) ON DELETE CASCADE,
    allocated_assessment_amount         NUMERIC(12,2) NOT NULL CHECK (allocated_assessment_amount > 0),
    is_paid                             BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (assessment_id, unit_id)
);

-- =====================================================================
-- 6. DSGVO — Technische & organisatorische Maßnahmen (Art. 25, 32 DSGVO)
-- =====================================================================
--
-- a) DATENMINIMIERUNG & RECHTSGRUNDLAGE
--    Es werden keine Einwilligungs-/Consent-Spalten für Eigentümer/Mieter
--    geführt, da die Verarbeitung auf Vertragserfüllung (Art. 6 Abs. 1
--    lit. b DSGVO) bzw. rechtlicher Verpflichtung (lit. c, z.B. HGB/AO)
--    beruht — keine Einwilligung erforderlich.
--
-- b) VERSCHLÜSSELUNG (Art. 32 DSGVO)
--    IBAN/BIC werden nicht im Klartext gespeichert (siehe owners/tenants).
--    Verschlüsselung/Entschlüsselung erfolgt anwendungsseitig über
--    pgp_sym_encrypt()/pgp_sym_decrypt(); der Schlüssel wird NICHT in
--    dieser Datenbank abgelegt, sondern extern (z.B. Vault/Secret Manager,
--    per Umgebungsvariable zur Laufzeit übergeben). Beispiel:
--
--      INSERT INTO owners (..., iban_encrypted, iban_last4)
--      VALUES (..., pgp_sym_encrypt('DE...1234', :app_key), '1234');
--
--      SELECT pgp_sym_decrypt(iban_encrypted, :app_key) FROM owners ...;
--
-- c) AUFBEWAHRUNGSPFLICHT vs. RECHT AUF LÖSCHUNG (Art. 17 DSGVO)
--    Buchungsbelege (journal_entries/entry_lines) unterliegen der
--    handels-/steuerrechtlichen Aufbewahrungspflicht von 6-10 Jahren
--    (§ 257 HGB, § 147 AO). Ein Löschanspruch nach Art. 17 DSGVO ist in
--    diesem Zeitraum gem. Art. 17 Abs. 3 lit. b DSGVO ausgeschlossen.
--    Daher: KEIN Hard-Delete von owners/tenants, solange verknüpfte
--    Buchungen/Verträge innerhalb der Aufbewahrungsfrist liegen.
--    Stattdessen zweistufiges Konzept:
--      1. deleted_at   -> "inaktiv" (Vertragsende, Soft-Delete)
--      2. anonymized_at -> nach Ablauf der Aufbewahrungsfrist werden
--         Klardaten (Name, Anschrift, Bankverbindung) durch die
--         Funktionen unten überschrieben; owner_id/tenant_id bleiben als
--         Fremdschlüssel für die weiterhin aufbewahrungspflichtigen
--         Finanzdaten bestehen (Zahlen ohne Personenbezug).
--
-- d) RECHENSCHAFTSPFLICHT (Art. 5 Abs. 2, Art. 30 DSGVO)
--    access_log protokolliert lesende/schreibende Zugriffe auf
--    personenbezogene Daten; gdpr_deletion_log dokumentiert bearbeitete
--    Löschanfragen (Betroffenenrechte, Art. 15 & 17 DSGVO).
--
-- e) SONDERFALL resolution_collection
--    Die Beschluss-Sammlung nach § 24 WEG ist dauerhaft aufzubewahren
--    (keine Löschfrist wie bei Buchungsbelegen) und dient zugleich als
--    Nachweis der Beschlussfassung -- deleted_at ist dort daher NICHT als
--    regulärer Lebenszyklus-Mechanismus zu verwenden, sondern nur für
--    nachweisliche Fehlerfassungen.
--
-- f) ZUGRIFFSKONTROLLE / MANDANTENTRENNUNG
--    user_properties, unit_owner_history und users.owner_id/tenant_id
--    stellen sicher, dass Verwalter nur zugewiesene Objekte, Eigentümer
--    nur eigene Einheiten und Mieter nur eigene Verträge sehen — auf
--    Anwendungsebene per Row-Filtering anhand dieser Tabellen
--    durchzusetzen (ggf. zusätzlich über PostgreSQL Row-Level-Security).
-- =====================================================================

-- ------------------------------ access_log -------------------------------------
CREATE TABLE access_log (
    log_id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id            INT REFERENCES users(user_id),
    accessed_table       VARCHAR(50) NOT NULL,
    accessed_record_id    INT,
    action              VARCHAR(20) NOT NULL CHECK (action IN ('SELECT','INSERT','UPDATE','DELETE','EXPORT')),
    accessed_at          TIMESTAMP NOT NULL DEFAULT now()
);

-- --------------------------- gdpr_deletion_log ----------------------------------
CREATE TABLE gdpr_deletion_log (
    request_id            INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subject_type            VARCHAR(20) NOT NULL CHECK (subject_type IN ('owner','tenant')),
    subject_id               INT NOT NULL,
    requested_at             TIMESTAMP NOT NULL DEFAULT now(),
    legal_basis_for_retention TEXT,                 -- z.B. "§ 147 AO, Frist bis 2033"
    processed_at             TIMESTAMP,
    outcome                 VARCHAR(20) CHECK (outcome IN ('anonymisiert','geloescht','abgelehnt','aufgeschoben'))
);

-- --------------------- Anonymisierungs-Funktionen (statt Hard-Delete) -------------
CREATE OR REPLACE FUNCTION anonymize_owner(p_owner_id INT) RETURNS VOID AS $$
BEGIN
    UPDATE owners
    SET first_name = NULL,
        last_name = 'GELOESCHT',
        company_name = NULL,
        email = NULL,
        phone = NULL,
        street_and_number = 'GELOESCHT',
        postal_code = NULL,
        city = NULL,
        bank_name = NULL,
        iban_encrypted = NULL,
        bic_encrypted = NULL,
        iban_last4 = NULL,
        sepa_mandate_reference = NULL,
        anonymized_at = now()
    WHERE owner_id = p_owner_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION anonymize_tenant(p_tenant_id INT) RETURNS VOID AS $$
BEGIN
    UPDATE tenants
    SET first_name = 'GELOESCHT',
        last_name = 'GELOESCHT',
        street_and_number = 'GELOESCHT',
        postal_code = NULL,
        city = NULL,
        bank_name = NULL,
        iban_encrypted = NULL,
        bic_encrypted = NULL,
        iban_last4 = NULL,
        sepa_mandate_reference = NULL,
        anonymized_at = now()
    WHERE tenant_id = p_tenant_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 7. INDIZES
-- =====================================================================

-- Partielle Unique-Indizes: Werte werden nach Soft-Delete wieder frei
-- (siehe README) — aktiv nur für Datensätze mit deleted_at IS NULL.
CREATE UNIQUE INDEX idx_users_email_active
    ON users (email) WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX idx_users_name_active
    ON users (name) WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX idx_users_google_sub_active
    ON users (google_sub_id) WHERE deleted_at IS NULL AND google_sub_id IS NOT NULL;

CREATE UNIQUE INDEX idx_owners_sepa_active
    ON owners (sepa_mandate_reference) WHERE deleted_at IS NULL AND sepa_mandate_reference IS NOT NULL;

CREATE UNIQUE INDEX idx_tenants_sepa_active
    ON tenants (sepa_mandate_reference) WHERE deleted_at IS NULL AND sepa_mandate_reference IS NOT NULL;

-- Fremdschlüssel-Indizes für Performance
CREATE INDEX idx_units_property_id ON units(property_id);
CREATE INDEX idx_allocation_keys_unit_id ON unit_allocation_keys(unit_id);
CREATE INDEX idx_allocation_keys_property_id ON unit_allocation_keys(property_id);
CREATE INDEX idx_users_owner_id ON users(owner_id);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_unit_owner_history_unit_id ON unit_owner_history(unit_id);
CREATE INDEX idx_unit_owner_history_owner_id ON unit_owner_history(owner_id);
CREATE INDEX idx_leases_unit_id ON leases(unit_id);
CREATE INDEX idx_leases_tenant_id ON leases(tenant_id);
CREATE INDEX idx_journal_entries_property_id ON journal_entries(property_id);
CREATE INDEX idx_entry_lines_entry_id ON entry_lines(entry_id);
CREATE INDEX idx_entry_lines_account_id ON entry_lines(account_id);
CREATE INDEX idx_entry_lines_property_id ON entry_lines(property_id);
CREATE INDEX idx_entry_lines_unit_id ON entry_lines(unit_id);
CREATE INDEX idx_entry_lines_lease_id ON entry_lines(lease_id);
CREATE INDEX idx_access_log_user_id ON access_log(user_id);
CREATE INDEX idx_access_log_accessed_at ON access_log(accessed_at);

-- Wirtschaftspläne, Sonderumlagen & Beschluss-Sammlung
CREATE UNIQUE INDEX uq_budget_plans_property_year
    ON budget_plans (property_id, fiscal_year) WHERE deleted_at IS NULL;

CREATE INDEX idx_resolution_collection_property_id ON resolution_collection(property_id);
CREATE INDEX idx_budget_plans_property_id ON budget_plans(property_id);
CREATE INDEX idx_budget_positions_lookup ON budget_positions(budget_id);
CREATE INDEX idx_budget_positions_account_id ON budget_positions(account_id);
CREATE INDEX idx_unit_budget_shares_lookup ON unit_budget_shares(unit_id);
CREATE INDEX idx_special_assessments_property ON special_assessments(property_id);
CREATE INDEX idx_special_assessments_resolution_id ON special_assessments(resolution_id);
CREATE INDEX idx_unit_assessment_shares_lookup ON unit_special_assessment_shares(unit_id);
