# 🏢 Relationales Immobilien- & WEG-Buchhaltungssystem (SKR 04)

Dieses Projekt stellt eine revisionssichere, datenbankseitig validierte Software-Architektur für eine gemischte Wohnungseigentumsgemeinschaft (WEG) und Mietverwaltung bereit.

## 🚀 Key Features

*   **SKR 04 Compliance:** Volle Unterstützung des Abschlussgliederungsprinzips über 4-stellige Standardkonten (z. B. Klasse 1800 für Finanzkonten, Klasse 1200 für Forderungen).
*   **Revisionssicherheit (Doppelte Buchführung):** Ein PostgreSQL Constraint-Trigger prüft bei jedem `COMMIT`, ob die Summe aller Soll-Beträge (`DEBIT`) der Summe aller Haben-Beträge (`CREDIT`) entspricht. Fehlbuchungen sind datenbankseitig unmöglich.
*   **Miteigentümer- & Mietermandantentrennung:** Integrierte Relationen trennen die Zugriffe strikt. Verwalter sehen nur zugewiesene Objekte (`user_properties`), Eigentümer nur eigene Einheiten (`unit_owner_history`) und Mieter nur ihre Verträge (`leases`).
*   **Soft-Delete (Logisches Löschen):** Daten werden durch das Feld `deleted_at` logisch ausgeblendet. Partielle Unique-Indizes sorgen dafür, dass E-Mails oder Google IDs nach einem Soft-Delete für Neuanmeldungen wieder frei werden.
*   **SEPA & Banking Ready:** Stammdaten für Bankverbindungen und eindeutige `sepa_mandate_reference`-Nummern erlauben automatisierte Lastschriftläufe (Pain.008 XML).
*   **Dynamische Umlageschlüssel:** Die Tabelle `unit_allocation_keys` speichert jährlich wechselnde Ablesewerte (z. B. Heizkostenverteiler), um verbrauchsabhängige Betriebskostenabrechnungen über das Backend zu fahren.
*   **Google OAuth2 (SSO):** Hybrid-Authentifizierung in der Tabelle `users` erlaubt traditionelle E-Mail-Anmeldungen (inkl. Erstanmeldungs-Passwortzwang `must_change_password`) sowie sichere Google Sign-Ons via `google_sub_id`.

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
