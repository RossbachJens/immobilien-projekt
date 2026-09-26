# 🏢 Relationales Immobilien- & WEG-Buchhaltungssystem (SKR 04)

Dieses Projekt stellt eine revisionssichere, datenbankseitig validierte Software-Architektur für eine gemischte Wohnungseigentumsgemeinschaft (WEG) und Mietverwaltung bereit.

## 🚀 Key Features

*   **SKR 04 Compliance:** Volle Unterstützung des Abschlussgliederungsprinzips über 4-stellige Standardkonten (z. B. Klasse 1800 für Finanzkonten, Klasse 1200 für Forderungen). Der globale Basiskontenrahmen (`accounts.property_id IS NULL`) ist kuratiert aus dem DATEV-SKR04 übernommen (`init-scripts/05_skr04_kontenrahmen.sql`, manuell anhand der Original-Seiten-Scans geprüft statt per OCR).
*   **Revisionssicherheit (Doppelte Buchführung):** Ein PostgreSQL Constraint-Trigger prüft bei jedem `COMMIT`, ob die Summe aller Soll-Beträge (`DEBIT`) der Summe aller Haben-Beträge (`CREDIT`) entspricht. Fehlbuchungen sind datenbankseitig unmöglich. Buchungen werden nie verändert oder gelöscht - Korrekturen laufen ausschließlich über eine Gegenbuchung (`POST /journal-entries/{id}/storno`).
*   **Miteigentümer- & Mietermandantentrennung:** Integrierte Relationen trennen die Zugriffe strikt. Verwalter sehen nur zugewiesene Objekte (`user_properties`), Eigentümer nur eigene Einheiten (`unit_owner_history`) und Mieter nur ihre Verträge (`leases`).
*   **PostgreSQL Row-Level-Security:** Ergänzend zur Query-Filterung in `app/core/access.py`
  erzwingen Postgres-RLS-Policies (Migration `0014_row_level_security`) dieselbe Zugriffsregel
  zusätzlich auf DB-Ebene, über einen eingeschränkten `app_user` statt des Superusers. Verifiziert
  durch einen dedizierten negativen Testfall (`backend/tests/test_rls.py`).
*   **Soft-Delete (Logisches Löschen):** Daten werden durch das Feld `deleted_at` logisch ausgeblendet. Partielle Unique-Indizes sorgen dafür, dass E-Mails oder Google IDs nach einem Soft-Delete für Neuanmeldungen wieder frei werden.
*   **SKR 04 - global und liegenschaftseigen:** Der Standard-Kontenrahmen ist zentral gepflegt; Verwalter können zusätzlich eigene 4-stellige Konten je Liegenschaft anlegen (`accounts.property_id` gesetzt), z. B. für Sonderpositionen oder Rücklagenkonten (`is_reserve_account`). Zwei partielle Unique-Indizes verhindern doppelte Kontonummern - getrennt für globale und liegenschaftseigene Konten.
*   **Wirtschaftsplan, Sonderumlagen & Beschluss-Sammlung (§ 24 WEG):** `budget_plans`/`budget_positions`/`unit_budget_shares` verteilen geplante Jahresbeträge automatisch je Einheit (MEA, Wohnfläche oder individueller Umlageschlüssel). Ein Wirtschaftsplan wird erst mit Verknüpfung zu einem Beschluss verbindlich ("Beschlossen"). Solange er im Entwurf ist, lassen sich einzelne Positionen weiterhin bearbeiten oder löschen - die Verteilung auf die Einheiten wird dabei automatisch neu berechnet. Sonderumlagen (`special_assessments`/`unit_special_assessment_shares`) nutzen dieselbe Verteilungslogik (`app/core/allocation.py`) inklusive Zahlungsstatus je Einheit. Die Beschluss-Sammlung selbst ist append-only mit fortlaufender, nie wiederverwendeter `lfd_nr` (auch nicht nach Soft-Delete-Korrektur); spätere Entwicklungen (z. B. eine Gerichtsentscheidung) werden als Folgeeintrag (`refers_to_resolution_id`) erfasst statt bestehende Zeilen zu ändern - dasselbe Prinzip wie bei Storno-Buchungen.
*   **Nebenkostenabrechnung:** Vollständige Jahresabrechnung je Einheit (`settlement_periods`/`settlement_positions`/`unit_settlement_shares`/`unit_settlement_summaries`), Positionen ebenfalls bis zur Beschlussfassung editierbar/löschbar mit automatischer Neuberechnung der Anteile und Einheiten-Ergebnisse. Zahlungseingänge werden auf die Hausgeld-/Mietkonten (1220/1200) gebucht, die Kostenverteilung läuft über dieselbe gemeinsame Allokationslogik wie Wirtschaftsplan und Sonderumlagen. PDF-Export je Einheit (`reportlab`) im Format der Muster-Jahresabrechnung, inklusive optionaler Rücklagendarstellung und Vermögensaufstellung (`reserve_fund_statements`/`reserve_fund_positions`, siehe `app/core/reserve_accounts.py`) sowie einer Bescheinigung i.S.d. § 35a EStG (siehe eigener Punkt unten).
*   **Bescheinigung § 35a EStG:** Abrechnungspositionen lassen sich als haushaltsnahe Dienstleistung (§ 35a Abs. 2 EStG) oder Handwerkerleistung (§ 35a Abs. 3 EStG) kennzeichnen, mit separat erfasstem Lohn-/Fahrt-/Maschinenkostenanteil (`settlement_positions.deductible_amount`) - Materialkosten sind bei beiden Kategorien von der Steuerermäßigung ausgeschlossen und fließen bewusst nicht in die Bemessungsgrundlage ein. Die Verteilung des Lohnanteils auf Einheiten läuft über eine eigene Tabelle (`unit_settlement_tax_shares`), unabhängig von der Verteilung der vollen Ist-Kosten. Die Bescheinigung erscheint als eigener, optionaler Abschnitt im PDF-Export je Einheit, getrennt nach umlagefähigen und nicht umlagefähigen Positionen.
*   **Dokumentenverwaltung (DMS):** Eigenständiges Modul (`documents`-Tabelle, Dateiinhalt als BYTEA direkt in Postgres) für Kontoauszüge, Rechnungen, Angebote, Versicherungsunterlagen, Verträge, Protokolle und Sonstiges. Optionale, gezielte Verknüpfung mit Einheit, Eigentümer, Mieter, Abrechnung, Buchung oder Versammlung (alle nullable FKs, analog `entry_lines`). Dreistufige Sichtbarkeit (`intern`/`eigentuemer`/`alle`) steuert, ob Eigentümer bzw. zusätzlich Mieter ein Dokument sehen dürfen - unabhängig davon bleiben gezielt an eine andere Einheit/Person gebundene Dokumente für Dritte verborgen. Listenabfragen laden den Dateiinhalt bewusst nicht mit (SQLAlchemy `defer()`), nur der Download-Endpunkt fragt ihn gezielt ab. Dokumente lassen sich zudem nachträglich oder direkt beim Anlegen einer Buchung als Beleg mit einem `journal_entries`-Eintrag verknüpfen (mehrere Dokumente je Buchung möglich).
*   **Umlageschlüssel-Verwaltung:** Eigenständiges Frontend-Modul (`features/allocationKeys`) für CRUD auf `unit_allocation_keys` mit eigener Sidebar-Seite - ergänzt das bisherige Auswahl-Widget (`AllocationKeyField`), das in Wirtschaftsplan-, Sonderumlage- und Abrechnungsformularen nur einen bestehenden Schlüssel referenziert, nicht aber anlegt.
*   **Zahlungseingang:** Hausgeld- und Mietzahlungen werden über einen eigenen Endpunkt (`POST /payments`) auf die Forderungskonten 1220/1200 gebucht und lösen automatisch einen ausgeglichenen Buchungssatz aus (`journal_entries`/`entry_lines`). Im Frontend bewusst in die Buchhaltungsseite integriert statt als eigener Menüpunkt, da ein Zahlungseingang fachlich eine normale Buchung ist.
*   **Reale Bankkonten je Liegenschaft (Trennungsgebot § 27 Abs. 5 WEG):** `property_bank_accounts` verwaltet Girokonto(en) und beliebig viele Rücklagenkonten (Tagesgeld, Kündigungsgeld, Festgeld, ...) je Liegenschaft mit Gültigkeitszeitraum (`valid_from`/`valid_to`) statt einem `is_active`-Flag; ein `EXCLUDE USING gist`-Constraint verhindert überlappende Gültigkeiten - dasselbe Muster wie bei der Eigentümerhistorie.
*   **Eigentümerversammlungen & Umlaufbeschluss:** `owner_meetings`/`meeting_agenda_items` bilden Präsenzversammlungen und Umlaufbeschlüsse über dieselbe Struktur ab; die Beschluss-Sammlung wird optional mit einer Versammlung verknüpft (`meeting_id`). Einladung und Niederschrift werden serverseitig als PDF generiert (WeasyPrint statt reportlab, da hier textlastiges HTML/CSS-Layout statt tabellarischer Rechenwerke im Vordergrund steht wie bei der Jahresabrechnung). Die strukturierte Niederschrift (Kopfdaten wie Versammlungsleiter, Protokollführer, Endzeit, vertretene Anteile, Beschlussfähigkeit; TOP-weiser Protokolltext; Abstimmungsergebnisse je Beschluss) ist inklusive Eingabeformular im Frontend vollständig umgesetzt.
*   **Dynamische Umlageschlüssel mit Gültigkeitszeitraum:** Die Tabelle `unit_allocation_keys` speichert Ablesewerte (z. B. Heizkostenverteiler) nicht mehr jahresweise, sondern mit einem Gültigkeitszeitraum (`valid_from_year`/`valid_to_year`). Ein Wechsel ist nur zum nächsten 01.01. wirksam; ein DB-seitiger `EXCLUDE`-Constraint verhindert überlappende Zeiträume je Einheit und Schlüsseltyp.
*   **Rollenzuweisung über Nutzerverwaltung:** Die Rolle eines Users (Admin/Verwalter/Eigentümer/Mieter) ergibt sich aus dem Datenmodell (`is_admin`, `owner_id`, `tenant_id`, `user_properties`). Admins verknüpfen Eigentümer/Mieter über `POST`/`PATCH /users`; die API erzwingt dabei Rollen-Exklusivität und 1:1-Eindeutigkeit je Owner/Tenant.
*   **Google OAuth2 (SSO):** Vollständiger Authorization-Code-Flow (`app/core/google_oauth.py`,
  `/auth/google/login`, `/auth/google/callback`) gegen Googles userinfo-Endpunkt. Ein bestehendes,
  per Passwort angelegtes Konto wird bei erster erfolgreicher Google-Anmeldung automatisch anhand
  der bei Google verifizierten E-Mail-Adresse verknüpft (`google_sub_id`).
*   **SEPA & Banking vorbereitet:** Stammdaten für Bankverbindungen und eindeutige `sepa_mandate_reference`-Nummern liegen bei Eigentümern/Mietern/Liegenschaften bereits vor; der automatisierte Lastschriftlauf (Pain.008-XML-Export) ist noch nicht umgesetzt.
*   **Vollständiges Stammdaten-CRUD:** Objekte, Einheiten und Eigentümer-/Mieter-Stammdaten (inkl. verschlüsselter Bankverbindung) lassen sich über die API und das Frontend vollständig anlegen, ändern und (soft-)löschen. Eigentümer/Mieter benötigen dafür keinen eigenen Online-Zugang - dieser wird optional und getrennt über die Nutzerverwaltung vergeben.
*   **Buchungen bleiben liegenschaftsbezogen:** Eine manuelle Buchung wird nie direkt einer Einheit zugeordnet - die Aufteilung auf Einheiten erfolgt automatisiert erst bei der Nebenkostenabrechnung über den Umlageschlüssel.
*   **Sidebar-Navigation:** Mit der wachsenden Zahl an Modulen sitzt die Navigation nicht mehr in der Kopfzeile, sondern als linke Sidebar (`frontend/src/layouts/Sidebar.tsx`); die Navbar zeigt nur noch Logo sowie Nutzer-/Logout-Bereich.
*   **Backup-Verwaltung übers Admin-Frontend:** Automatische tägliche `pg_dump`-Backups (Postgres-Superuser) liegen nicht mehr nur unsichtbar im Dateisystem, sondern sind für Admins direkt im Frontend verwaltbar (`/backups`) - Anzeigen, manuelles Auslösen, Herunterladen und Löschen bestehender Dumps sowie eine Wiederherstellung. Läuft über einen eigenständigen `backup-service`-Container mit interner, nur im Docker-Netz erreichbarer Admin-API (kein Port nach außen); das Hauptbackend (`app_user`, RLS-eingeschränkt) bekommt bewusst **keine** Superuser-DB-Credentials, sondern spricht diese API per gemeinsamem Secret an. Ein Restore legt automatisch zuerst ein Sicherheitsbackup des aktuellen Stands an, trennt aktive DB-Verbindungen und verlangt eine doppelte Bestätigung des Dateinamens (Backend und Frontend), bevor der komplette Datenbestand ersetzt wird.

## 📁 Projektstruktur

```text
immobilien-project/
├── .gitignore                     # Schützt Passwörter, Secrets und DB-Ordner vor Git
├── docker-compose.yml              # Orchestriert PostgreSQL 16, Backend, Frontend und Backup-Service
├── README.md                      # Projektdokumentation
├── PROJECTPLAN.md                 # Lebendes Dokument: Phasenplan, Grundsatzentscheidungen, Status
├── init-scripts/                  # SQL-Skripte (werden alphabetisch initialisiert)
│   ├── 01_schema.sql              # Das vollständige relationale Datenbankschema
│   ├── 02_triggers.sql            # Der doppelte Buchführungstrigger (Soll = Haben)
│   ├── 03_procedures.sql          # Prozedur für automatische Miet-Sollstellungen
│   ├── 04_testdata.sql            # Seeding für eine gemischte WEG (kein Admin mehr, siehe unten)
│   └── 05_skr04_kontenrahmen.sql  # Kuratierter globaler SKR04-Basisrahmen (Klassen 0-6)
├── scripts/
│   └── backup-loop.sh             # Periodischer pg_dump-Loop (läuft im backup-service-Container)
├── backup-service/                # Interne Admin-API für Backup-Verwaltung (Liste/Trigger/Download/Löschen/Restore)
│   ├── Dockerfile                 # Basis postgres:16 (garantiert pg_dump/pg_restore-Kompatibilität) + Python
│   ├── entrypoint.sh              # Startet backup-loop.sh im Hintergrund + Admin-API im Vordergrund
│   ├── requirements.txt
│   └── app/
│       └── main.py                # FastAPI-Mini-Service, Secret-Auth über X-Backup-Service-Secret
├── backend/
│   ├── alembic/versions/          # Schema-Änderungen NACH der 01_schema.sql-Baseline
│   │   ├── 0001_property_accounts.py
│   │   ├── 0002_resolution_details.py
│   │   ├── 0003_budget_extensions.py
│   │   ├── 0004_settlement.py               # Nebenkostenabrechnung
│   │   ├── 0005_property_bank_accounts.py   # Reale Bankkonten je Liegenschaft
│   │   ├── 0006_owner_meetings.py           # Eigentümerversammlungen & Umlaufbeschluss
│   │   ├── 0007_niederschrift_details.py    # Strukturierte Niederschrift (Kopfdaten, Abstimmungen)
│   │   ├── 0008_settlement_multi_account.py # Mehrere Konten je Abrechnungsposition (Pooling)
│   │   ├── 0009_owner_number.py             # Optionale Eigentümernummer je Einheiten-Zuordnung
│   │   ├── 0010_opening_balance_account.py  # Eröffnungsbilanzkonto (9000) für Anfangsbestände
│   │   ├── 0011_reserve_fund_statement.py   # Rücklagendarstellung & Vermögensaufstellung
│   │   ├── 0012_settlement_tax_details.py   # § 35a EStG: Lohnanteil je Abrechnungsposition
│   │   └── 0013_documents.py                # Dokumentenverwaltung (DMS)
│   │   ├── 0014_row_level_security.py       # PostgreSQL-RLS als zweite Verteidigungslinie
│   │   ├── 0015_owner_salutation.py         # Anrede je Eigentümer (DIN-5008-Anschriftfeld)
│   │   ├── 0016_property_logo.py            # Verwalter-Logo für PDF-Seitenkopf
│   │   └── 0017_document_categories.py      # Neue Kategorien für automatisch archivierte PDFs
│   └── app/
│       ├── models/ · schemas/ · routers/ · core/ · services/   # FastAPI-Anwendung (SQLAlchemy 2.0, Pydantic)
│       │                                                        # inkl. app/core/backup_client.py + app/routers/backups.py
│       └── cli.py                 # CLI zum Anlegen des ersten Admin-Accounts
└── frontend/
    └── src/
        ├── api/ · components/ · layouts/ · routes/ · styles/
        └── features/<domäne>/     # api.ts / useHook.ts / Page.tsx je Fachdomäne, u.a.
                                    # properties, units, owners, tenants, users, accounts,
                                    # journalEntries, payments, resolutions, budgetPlans,
                                    # specialAssessments, settlementPeriods, reserveFund,
                                    # bankAccounts, allocationKeys, meetings, documents,
                                    # backups, auth, health
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

Abgeschlossen sind die Phasen 0–6 sowie [...] sowie eine erste Dokumentenverwaltung inkl.
 Beleg-Verknüpfung zu Buchungen und automatischer Archivierung generierter PDFs. Aus Phase 7
 sind die Backup-Verwaltung übers Admin-Frontend,
  PostgreSQL-Row-Level-Security als zweite Verteidigungslinie, der Google-SSO-Login-Flow sowie
  eine erste `access_log`-Middleware bereits umgesetzt. Details und der vollständige Phasenplan stehen in `PROJECTPLAN.md`.

Noch offen:
- **Bewusst zurückgestellt:** mieterseitige Betriebskostenabrechnung (aktuell nur eigentümerseitige Nebenkostenabrechnung).
- Phase 7 (Härtung & Betrieb): [...] `access_log`-Middleware deckt bisher nur
   owners/tenants/users ab, nicht Dokumente (inkl. Downloads), Backups und die
   PDF-Generierungs-Endpunkte.
   (`generate_monthly_lease_demands`, `03_procedures.sql`) existiert bereits, ist aber noch
- Mietsollstellung & SEPA-Export (Pain.008): [...]