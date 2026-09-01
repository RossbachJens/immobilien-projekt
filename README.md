# 🏢 Relationales Immobilien- & WEG-Buchhaltungssystem (SKR 04)

Dieses Projekt stellt eine revisionssichere, datenbankseitig validierte Software-Architektur für eine gemischte Wohnungseigentumsgemeinschaft (WEG) und Mietverwaltung bereit.

## 🚀 Key Features

*   **SKR 04 Compliance:** Volle Unterstützung des Abschlussgliederungsprinzips über 4-stellige Standardkonten (z. B. Klasse 1800 für Finanzkonten, Klasse 1200 für Forderungen). Der globale Basiskontenrahmen (`accounts.property_id IS NULL`) ist kuratiert aus dem DATEV-SKR04 übernommen (`init-scripts/05_skr04_kontenrahmen.sql`, manuell anhand der Original-Seiten-Scans geprüft statt per OCR).
*   **Revisionssicherheit (Doppelte Buchführung):** Ein PostgreSQL Constraint-Trigger prüft bei jedem `COMMIT`, ob die Summe aller Soll-Beträge (`DEBIT`) der Summe aller Haben-Beträge (`CREDIT`) entspricht. Fehlbuchungen sind datenbankseitig unmöglich. Buchungen werden nie verändert oder gelöscht - Korrekturen laufen ausschließlich über eine Gegenbuchung (`POST /journal-entries/{id}/storno`).
*   **Miteigentümer- & Mietermandantentrennung:** Integrierte Relationen trennen die Zugriffe strikt. Verwalter sehen nur zugewiesene Objekte (`user_properties`), Eigentümer nur eigene Einheiten (`unit_owner_history`) und Mieter nur ihre Verträge (`leases`).
*   **Soft-Delete (Logisches Löschen):** Daten werden durch das Feld `deleted_at` logisch ausgeblendet. Partielle Unique-Indizes sorgen dafür, dass E-Mails oder Google IDs nach einem Soft-Delete für Neuanmeldungen wieder frei werden.
*   **SKR 04 - global und liegenschaftseigen:** Der Standard-Kontenrahmen ist zentral gepflegt; Verwalter können zusätzlich eigene 4-stellige Konten je Liegenschaft anlegen (`accounts.property_id` gesetzt), z. B. für Sonderpositionen oder Rücklagenkonten (`is_reserve_account`). Zwei partielle Unique-Indizes verhindern doppelte Kontonummern - getrennt für globale und liegenschaftseigene Konten.
*   **Wirtschaftsplan, Sonderumlagen & Beschluss-Sammlung (§ 24 WEG):** `budget_plans`/`budget_positions`/`unit_budget_shares` verteilen geplante Jahresbeträge automatisch je Einheit (MEA, Wohnfläche oder individueller Umlageschlüssel). Ein Wirtschaftsplan wird erst mit Verknüpfung zu einem Beschluss verbindlich ("Beschlossen"). Sonderumlagen (`special_assessments`/`unit_special_assessment_shares`) nutzen dieselbe Verteilungslogik (`app/core/allocation.py`) inklusive Zahlungsstatus je Einheit. Die Beschluss-Sammlung selbst ist append-only mit fortlaufender, nie wiederverwendeter `lfd_nr` (auch nicht nach Soft-Delete-Korrektur); spätere Entwicklungen (z. B. eine Gerichtsentscheidung) werden als Folgeeintrag (`refers_to_resolution_id`) erfasst statt bestehende Zeilen zu ändern - dasselbe Prinzip wie bei Storno-Buchungen.
*   **Nebenkostenabrechnung:** Vollständige Jahresabrechnung je Einheit (`settlement_periods`/`settlement_positions`/`unit_settlement_shares`/`unit_settlement_summaries`). Zahlungseingänge werden auf die Hausgeld-/Mietkonten (1220/1200) gebucht, die Kostenverteilung läuft über dieselbe gemeinsame Allokationslogik wie Wirtschaftsplan und Sonderumlagen. PDF-Export je Einheit (`reportlab`) im Format der Muster-Jahresabrechnung.
*   **Reale Bankkonten je Liegenschaft (Trennungsgebot § 27 Abs. 5 WEG):** `property_bank_accounts` verwaltet Girokonto(en) und beliebig viele Rücklagenkonten (Tagesgeld, Kündigungsgeld, Festgeld, ...) je Liegenschaft mit Gültigkeitszeitraum (`valid_from`/`valid_to`) statt einem `is_active`-Flag; ein `EXCLUDE USING gist`-Constraint verhindert überlappende Gültigkeiten - dasselbe Muster wie bei der Eigentümerhistorie.
*   **Eigentümerversammlungen & Umlaufbeschluss:** `owner_meetings`/`meeting_agenda_items` bilden Präsenzversammlungen und Umlaufbeschlüsse über dieselbe Struktur ab; die Beschluss-Sammlung wird optional mit einer Versammlung verknüpft (`meeting_id`). Einladung und Niederschrift werden serverseitig als PDF generiert (WeasyPrint).
*   **Dynamische Umlageschlüssel mit Gültigkeitszeitraum:** Die Tabelle `unit_allocation_keys` speichert Ablesewerte (z. B. Heizkostenverteiler) nicht mehr jahresweise, sondern mit einem Gültigkeitszeitraum (`valid_from_year`/`valid_to_year`). Ein Wechsel ist nur zum nächsten 01.01. wirksam; ein DB-seitiger `EXCLUDE`-Constraint verhindert überlappende Zeiträume je Einheit und Schlüsseltyp.
*   **Rollenzuweisung über Nutzerverwaltung:** Die Rolle eines Users (Admin/Verwalter/Eigentümer/Mieter) ergibt sich aus dem Datenmodell (`is_admin`, `owner_id`, `tenant_id`, `user_properties`). Admins verknüpfen Eigentümer/Mieter über `POST`/`PATCH /users`; die API erzwingt dabei Rollen-Exklusivität und 1:1-Eindeutigkeit je Owner/Tenant.
*   **Google OAuth2 (SSO) - vorbereitet:** Das Datenmodell (`users.google_sub_id`, CHECK-Constraint `password_hash IS NOT NULL OR google_sub_id IS NOT NULL`) unterstützt bereits eine hybride Anmeldung; der eigentliche OAuth2-Login-Flow ist noch nicht implementiert (siehe Offene Punkte).
*   **SEPA & Banking vorbereitet:** Stammdaten für Bankverbindungen und eindeutige `sepa_mandate_reference`-Nummern liegen bei Eigentümern/Mietern/Liegenschaften bereits vor; der automatisierte Lastschriftlauf (Pain.008-XML-Export) ist noch nicht umgesetzt.
*   **Vollständiges Stammdaten-CRUD:** Objekte, Einheiten und Eigentümer-/Mieter-Stammdaten (inkl. verschlüsselter Bankverbindung) lassen sich über die API und das Frontend vollständig anlegen, ändern und (soft-)löschen. Eigentümer/Mieter benötigen dafür keinen eigenen Online-Zugang - dieser wird optional und getrennt über die Nutzerverwaltung vergeben.
*   **Buchungen bleiben liegenschaftsbezogen:** Eine manuelle Buchung wird nie direkt einer Einheit zugeordnet - die Aufteilung auf Einheiten erfolgt automatisiert erst bei der Nebenkostenabrechnung über den Umlageschlüssel.
*   **Sidebar-Navigation:** Mit der wachsenden Zahl an Modulen sitzt die Navigation nicht mehr in der Kopfzeile, sondern als linke Sidebar (`frontend/src/layouts/Sidebar.tsx`); die Navbar zeigt nur noch Logo sowie Nutzer-/Logout-Bereich.

## 📁 Projektstruktur

```text
immobilien-project/
├── .gitignore                     # Schützt Passwörter, Secrets und DB-Ordner vor Git
├── docker-compose.yml              # Orchestriert PostgreSQL 16, Backend und Frontend
├── README.md                      # Projektdokumentation
├── PROJECTPLAN.md                 # Lebendes Dokument: Phasenplan, Grundsatzentscheidungen, Status
├── init-scripts/                  # SQL-Skripte (werden alphabetisch initialisiert)
│   ├── 01_schema.sql              # Das vollständige relationale Datenbankschema
│   ├── 02_triggers.sql            # Der doppelte Buchführungstrigger (Soll = Haben)
│   ├── 03_procedures.sql          # Prozedur für automatische Miet-Sollstellungen
│   ├── 04_testdata.sql            # Seeding für eine gemischte WEG (kein Admin mehr, siehe unten)
│   └── 05_skr04_kontenrahmen.sql  # Kuratierter globaler SKR04-Basisrahmen (Klassen 0-6)
├── backend/
│   ├── alembic/versions/          # Schema-Änderungen NACH der 01_schema.sql-Baseline
│   │   ├── 0001_property_accounts.py
│   │   ├── 0002_resolution_details.py
│   │   └── 0003_budget_extensions.py
│   └── app/
│       ├── models/ · schemas/ · routers/ · core/   # FastAPI-Anwendung (SQLAlchemy 2.0, Pydantic)
│       └── cli.py                 # CLI zum Anlegen des ersten Admin-Accounts
└── frontend/
    └── src/
        ├── api/ · components/ · layouts/ · routes/ · styles/
        └── features/<domäne>/     # api.ts / useHook.ts / Page.tsx je Fachdomäne
```

## 🔑 Erster Admin-Account

Der allererste Admin-Account wird **nicht** über die Seed-Daten (`init-scripts/04_testdata.sql`) angelegt, sondern per CLI:

```bash
docker compose exec backend python -m app.cli create-admin \
  --name "Admin" --email admin@example.com --password "StartPasswort123!"
```

⚠️ **Wichtig:** `docker compose down -v` löscht das komplette Datenbank-Volume (`db_data`) inklusive aller User – auch des Admin-Accounts. Nach jedem `down -v` muss der Befehl oben erneut ausgeführt werden, sonst schlägt der Login fehl, weil schlicht kein User existiert.

⚠️ **Wichtig:** Nach `init-scripts/05_skr04_kontenrahmen.sql` (frischer DB-Container) zwingend `docker compose exec backend alembic upgrade head` ausführen (**nicht** `alembic stamp head` - das markiert Migrationen nur als erledigt, ohne sie tatsächlich auszuführen).

## 📌 Aktueller Stand & offene Punkte

Abgeschlossen sind die Phasen 0–6 sowie - zusätzlich zur ursprünglichen Phasenplanung - Eigentümerversammlungen inkl. Umlaufbeschluss. Details und der vollständige Phasenplan stehen in `PROJECTPLAN.md`.

Noch offen:
- **Frontend:** Zahlungseingang-UI (Nebenkostenabrechnung) und Umlageschlüssel-CRUD-UI fehlen noch; einzelne Berechnungs-Slices der Nebenkostenabrechnung (ab 5.3) sind möglicherweise noch lückenhaft.
- **Bewusst zurückgestellt:** § 35a EStG-Bescheinigung, Rücklagendarstellung/Vermögensaufstellung, mieterseitige Betriebskostenabrechnung.
- **Phase 7 (Härtung & Betrieb):** E-Mail-Versand (aktuell nur ein Dev-Token-Stub im Passwort-Reset-Flow), PostgreSQL-Row-Level-Security als zweite Verteidigungslinie neben der Query-Filterung, Google-SSO-Login-Flow (Datenmodell bereits vorbereitet), `access_log`-Middleware, Rate-Limiting, Backups, Key-Rotation, E2E-Tests.
- **Mietsollstellung & SEPA-Export (Pain.008):** War ursprünglich als Phase 6 geplant, wurde zugunsten der Bankkonten-Verwaltung je Liegenschaft zurückgestellt und läuft jetzt als eigene, spätere Phase.
