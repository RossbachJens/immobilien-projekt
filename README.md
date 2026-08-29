# 🏢 Relationales Immobilien- & WEG-Buchhaltungssystem (SKR 04)

Dieses Projekt stellt eine revisionssichere, datenbankseitig validierte Software-Architektur für eine gemischte Wohnungseigentumsgemeinschaft (WEG) und Mietverwaltung bereit.

## 🚀 Key Features

*   **SKR 04 Compliance:** Volle Unterstützung des Abschlussgliederungsprinzips über 4-stellige Standardkonten (z. B. Klasse 1800 für Finanzkonten, Klasse 1200 für Forderungen).
*   **Revisionssicherheit (Doppelte Buchführung):** Ein PostgreSQL Constraint-Trigger prüft bei jedem `COMMIT`, ob die Summe aller Soll-Beträge (`DEBIT`) der Summe aller Haben-Beträge (`CREDIT`) entspricht. Fehlbuchungen sind datenbankseitig unmöglich.
*   **Miteigentümer- & Mietermandantentrennung:** Integrierte Relationen trennen die Zugriffe strikt. Verwalter sehen nur zugewiesene Objekte (`user_properties`), Eigentümer nur eigene Einheiten (`unit_owner_history`) und Mieter nur ihre Verträge (`leases`).
*   **Soft-Delete (Logisches Löschen):** Daten werden durch das Feld `deleted_at` logisch ausgeblendet. Partielle Unique-Indizes sorgen dafür, dass E-Mails oder Google IDs nach einem Soft-Delete für Neuanmeldungen wieder frei werden.
*   **SEPA & Banking Ready:** Stammdaten für Bankverbindungen und eindeutige `sepa_mandate_reference`-Nummern erlauben automatisierte Lastschriftläufe (Pain.008 XML).
*   **Dynamische Umlageschlüssel mit Gültigkeitszeitraum:** Die Tabelle `unit_allocation_keys` speichert Ablesewerte (z. B. Heizkostenverteiler) nicht mehr jahresweise, sondern mit einem Gültigkeitszeitraum (`valid_from_year`/`valid_to_year`). Ein Wechsel ist nur zum nächsten 01.01. wirksam; ein DB-seitiger `EXCLUDE`-Constraint verhindert überlappende Zeiträume je Einheit und Schlüsseltyp.
*   **Rollenzuweisung über Nutzerverwaltung:** Die Rolle eines Users (Admin/Verwalter/Eigentümer/Mieter) ergibt sich aus dem Datenmodell (`is_admin`, `owner_id`, `tenant_id`, `user_properties`). Admins verknüpfen Eigentümer/Mieter über `POST`/`PATCH /users`; die API erzwingt dabei Rollen-Exklusivität und 1:1-Eindeutigkeit je Owner/Tenant.
*   **Google OAuth2 (SSO):** Hybrid-Authentifizierung in der Tabelle `users` erlaubt traditionelle E-Mail-Anmeldungen (inkl. Erstanmeldungs-Passwortzwang `must_change_password`) sowie sichere Google Sign-Ons via `google_sub_id`.
*   **Vollständiges Stammdaten-CRUD:** Objekte, Einheiten und Eigentümer-/Mieter-Stammdaten (inkl. verschlüsselter Bankverbindung) lassen sich über die API vollständig anlegen, ändern und (soft-)löschen. Eigentümer/Mieter benötigen dafür keinen eigenen Online-Zugang - dieser wird optional und getrennt über die Nutzerverwaltung vergeben.

*   **Doppelte Buchführung mit Storno-Pflicht:** Buchungen (`journal_entries`/`entry_lines`) werden nie verändert oder gelöscht - Korrekturen laufen ausschließlich über eine Gegenbuchung (`POST /journal-entries/{id}/storno`), die Soll und Haben spiegelt und über `reversed_entry_id` rückverfolgbar bleibt.
*   **SKR 04 - global und liegenschaftseigen:** Der Standard-Kontenrahmen (`accounts.property_id IS NULL`) ist zentral gepflegt; Verwalter können zusätzlich eigene 4-stellige Konten je Liegenschaft anlegen (`accounts.property_id` gesetzt), z.B. für Sonderpositionen, die im Standardrahmen fehlen. Zwei partielle Unique-Indizes verhindern doppelte Kontonummern - getrennt für globale und liegenschaftseigene Konten.
*   **Buchungen bleiben liegenschaftsbezogen:** Eine manuelle Buchung wird nie direkt einer Einheit zugeordnet - die Aufteilung auf Einheiten erfolgt erst bei der Nebenkostenabrechnung über den Umlageschlüssel (Phase 5).

## 📁 Projektstruktur

```text
immobilien-project/
├── .gitignore               # Schützt Passwörter, Secrets und DB-Ordner vor Git
├── docker-compose.yml       # Orchestriert die PostgreSQL 16 DB und das Backend
├── README.md                # Projektdokumentation
└── init-scripts/            # SQL-Skripte (werden alphabetisch initialisiert)
    ├── 01_schema.sql        # Das vollständige relationale Datenbankschema
    ├── 02_triggers.sql      # Der doppelte Buchführungstrigger (Soll = Haben)
    ├── 03_procedures.sql    # Prozedur für automatische Miet-Sollstellungen
    └── 04_testdata.sql      # Seeding für eine gemischte WEG & den Admin-Account
```

## 🔑 Erster Admin-Account

Der allererste Admin-Account wird **nicht** über die Seed-Daten (`init-scripts/04_testdata.sql`) angelegt, sondern per CLI:

\`\`\`bash
docker compose exec backend python -m app.cli create-admin \
  --name "Admin" --email admin@example.com --password "StartPasswort123!"
\`\`\`

⚠️ **Wichtig:** `docker compose down -v` löscht das komplette Datenbank-Volume (`db_data`) inklusive aller User – auch des Admin-Accounts. Nach jedem `down -v` muss der Befehl oben erneut ausgeführt werden, sonst schlägt der Login fehl, weil schlicht kein User existiert.