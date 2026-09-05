# Projektplan: FastAPI-Backend & React-Frontend für die Immobilien-/WEG-Datenbank

## Grundsatzentscheidungen (festgehalten)
- **Zugriffskontrolle:** Defense-in-Depth — FastAPI filtert Queries nach Rolle/Zuordnung
  UND PostgreSQL Row-Level-Security erzwingt dieselbe Regel zusätzlich auf DB-Ebene
  (Postgres-RLS steht noch aus, siehe Phase 7).
- **Erste Vertikale:** Auth/Login (inkl. RLS-Grundgerüst), da Rollenmodell alle
  weiteren Phasen durchzieht.
- **Frontend-Sprache:** TypeScript von Anfang an (Vite, TanStack Query, React Router, Zod).
- **Frontend-Design:** Orientiert sich an den bereits vorhandenen HTML/CSS-Dateien im
  Projekt (`index.html`, `features.html`, `docs.html`, `style.css`, `utilities.css` —
  ursprünglich das statische "Loruki"-Template). Farbpalette, Typografie (Lato) und
  Formensprache (abgerundete Karten mit Schatten, Navbar-Look) werden als Design-Tokens
  (`src/styles/tokens.css`) ins React-Frontend überführt.
- **Frontend-Struktur:** Bewusst **kein Monolith** — Feature-Module (`features/<domäne>/`)
  statt einer wachsenden `App.tsx`. Details siehe `frontend/src/` (Phase 0 bereits umgesetzt:
  `api/`, `components/`, `features/`, `layouts/`, `routes/`, `styles/`).
- **Navigation (Frontend):** Mit dem wachsenden Funktionsumfang ab Phase 4 wurde die
  Modul-Navigation aus der Kopfzeile (`Navbar`) in eine eigene linke Sidebar
  (`layouts/Sidebar.tsx`) verschoben — Grund: zu viele gleichrangige Module (Liegenschaften,
  Einheiten, Eigentümer, Mieter, Buchhaltung, Beschluss-Sammlung, Wirtschaftsplan,
  Sonderumlagen, ggf. Nutzerverwaltung) passen nicht mehr überschneidungsfrei in eine
  horizontale Leiste. Die `Navbar` beschränkt sich seitdem auf Logo sowie Nutzer-/
  Logout-Bereich; `Sidebar` markiert die aktive Route über `NavLink`. Auf schmalen
  Bildschirmen (`max-width: 768px`) klappt die Sidebar zu einer horizontal scrollbaren
  Leiste unterhalb der Navbar um, statt eine Off-Canvas-Lösung einzuführen — das hält den
  Aufwand gering und bleibt konsistent mit dem bestehenden Breakpoint-Muster in `style.css`.
- **Rollenmodell:** Kein separates globales Rollen-Enum. Rolle ergibt sich aus dem
  Datenmodell: `users.is_admin` → Admin, `users.owner_id` gesetzt → Eigentümer,
  `users.tenant_id` gesetzt → Mieter, sonst Verwalter/Buchhalter (granular über
  `user_properties` je Objekt).
  - **Rollenzuweisung:** Owner-/Tenant-Verknüpfung (und damit Eigentümer-/Mieter-Rolle)
  wird über `POST /users` bzw. `PATCH /users/{id}` gesetzt - nicht beim Anlegen von
  Owner/Tenant selbst (das bleibt Aufgabe der Stammdaten-Endpunkte, Phase 2). Die
  API erzwingt Rollen-Exklusivität (nie gleichzeitig Admin, Eigentümer und Mieter)
  sowie 1:1-Eindeutigkeit (ein Owner/Tenant kann nicht an zwei aktive User
  gleichzeitig verknüpft sein). `DELETE /users/{id}` ist ein Soft-Delete; der
  letzte verbleibende Admin kann weder gelöscht noch degradiert werden.
- **Umlageschlüssel-Gültigkeit:** `unit_allocation_keys` wird nicht mehr
  jahresweise neu angelegt, sondern über einen Gültigkeitszeitraum
  (`valid_from_year`, `valid_to_year IS NULL` = "bis auf Weiteres") geführt. Ein
  Wechsel schließt den bisherigen Eintrag (`valid_to_year` = Vorjahr) und legt
  einen neuen offenen Eintrag an - **wirksam ausschließlich zum nächsten 01.01.**
  Ein `EXCLUDE USING gist`-Constraint (Extension `btree_gist`) verhindert
  überlappende Zeiträume je Einheit/Schlüsseltyp auf DB-Ebene; die
  01.01.-Regel selbst wird erst in der Service-Schicht durchgesetzt (Phase 5),
  da eine starre CHECK-Constraint rückwirkende historische Datenpflege
  blockieren würde. Dasselbe Gültigkeitszeitraum-Muster (statt `is_active`-Flag)
  wurde später auch für Eigentümerhistorie und reale Bankkonten (Phase 6)
  übernommen.
- **Eigentümer/Mieter ohne Online-Zugang:** `owners`/`tenants` sind eigenständige
  Stammdaten-Entitäten ohne Pflicht-Verknüpfung zu einem `users`-Datensatz. Ob ein
  Eigentümer/Mieter online Einblick in seine Daten erhält, ist eine separate,
  jederzeit nachträglich änderbare Entscheidung (`PATCH /users/{id}` mit
  `owner_id`/`tenant_id`) - CRUD auf `/owners` bzw. `/tenants` funktioniert
  unabhängig davon vollständig.
- **PII-Verschlüsselung:** IBAN/BIC werden nie im Klartext im Python-Prozess
  gehalten - `app/core/crypto.py` verschlüsselt/entschlüsselt ausschließlich
  serverseitig über Postgres' `pgp_sym_encrypt`/`pgp_sym_decrypt` (pgcrypto), der
  Schlüssel geht nur als Bind-Parameter über die DB-Verbindung. `iban_last4`
  wird zusätzlich im Klartext gepflegt (Anzeige ohne Entschlüsselung nötig).
  Dasselbe Verfahren gilt für die realen Bankkonten je Liegenschaft (Phase 6).
- **Kontenrahmen (SKR 04) - global + liegenschaftseigen:** `accounts.property_id`
  ist nullable: `NULL` = globales SKR04-Basiskonto (nur per Alembic-Migration/
  Seed-Daten gepflegt, für alle Liegenschaften sichtbar), gesetzt =
  liegenschaftseigenes Individualkonto (per `POST`/`PATCH /accounts` von
  Admin/zugeordnetem Verwalter pflegbar, 4-stellig nach SKR04-Schema). Statt
  einer globalen `UNIQUE(account_number)` gelten zwei partielle Unique-Indizes
  (`uq_accounts_number_global`, `uq_accounts_number_per_property`) - zwei
  Liegenschaften können dieselbe Nummer unabhängig voneinander vergeben.
  Deaktivierung statt Hard-Delete (`is_active`), da Individualkonten bereits
  in `entry_lines` referenziert sein können. `GET /accounts?property_id=X`
  liefert global + eigene zusammen (Basis für das Buchungsformular).
  Ein zusätzliches Flag `is_reserve_account` kennzeichnet liegenschaftseigene
  Rücklagenkonten, damit sie trotz Kontoart AKTIV (statt AUFWAND) als
  Wirtschaftsplan-/Sonderumlage-Position zulässig sind (Migration 0003).
- **Manuelle Buchungen sind ausschließlich liegenschaftsbezogen:** `entry_lines.
  unit_id` wird beim manuellen Erfassen bewusst NICHT gesetzt - die Aufteilung
  auf Einheiten erfolgt erst über den Umlageschlüssel im Rahmen von Wirtschaftsplan,
  Sonderumlage oder Nebenkostenabrechnung. `unit_id` bleibt im Schema zusätzlich für
  automatisierte Buchungen reserviert (z.B. Mietsollstellung, `03_procedures.sql`).
- **Gemeinsame Verteilungslogik:** Wirtschaftsplan-Positionen, Sonderumlagen und die
  Nebenkostenabrechnung verteilen alle einen Gesamtbetrag auf Einheiten nach demselben
  Prinzip (MEA / Wohnfläche / individueller Umlageschlüssel aus `unit_allocation_keys`).
  Diese Logik ist zentral in `app/core/allocation.py`
  (`compute_unit_fractions`, `distribute_amount`) gebündelt statt pro Feature dupliziert;
  eine Rundungsdifferenz geht an die Einheit mit dem größten Anteil (analog zum
  Soll=Haben-Prinzip bei Buchungen).
- **Reale Bankkonten je Liegenschaft (Phase 6):** Trennungsgebot § 27 Abs. 5 WEG -
  jede Liegenschaft braucht mindestens ein Girokonto und mindestens ein
  Rücklagenkonto, real mit eigener IBAN. Eine Liegenschaft kann mehrere
  Rücklagenkonten gleichzeitig haben (z.B. Tagesgeld, Kündigungsgeld, Sparbrief -
  vgl. Konten 1810/1820/1830 in 04_testdata.sql). Tabelle
  `property_bank_accounts`: property_id (FK, Pflicht), account_id (FK zu
  accounts, SKR04-Kategorie), account_purpose, bank_name, iban_encrypted (wie
  bei owners/tenants via pgcrypto), iban_last4, `valid_from`/`valid_to` statt
  `is_active`-Flag, mit `EXCLUDE USING gist` gegen überlappende Gültigkeiten -
  dasselbe Muster wie bei `unit_owner_history`. 1:n-Beziehung Liegenschaft ->
  Bankkonten.
- **Beschluss-Sammlung (§ 24 WEG) - append-only:** `resolution_collection`
  bekommt eine gesetzlich vorgeschriebene `lfd_nr` (fortlaufend je
  Liegenschaft, nie wiederverwendet - auch nicht nach Soft-Delete-Korrektur).
  Statusänderungen und Gerichtsentscheidungen zu einem bestehenden Beschluss
  werden nie durch Bearbeiten der Zeile abgebildet, sondern als neuer
  Eintrag mit `refers_to_resolution_id` ("zu lfd. Nr. X") - konsistent mit
  dem Storno-Prinzip bei `journal_entries`. Ein Wirtschaftsplan wird erst mit
  Verknüpfung zu einem `resolution_id` bindend (Statuswechsel zu "Beschlossen").
- **Eigentümerversammlungen & Umlaufbeschluss (informell ergänzt):** `owner_meetings`
  bildet sowohl Präsenzversammlungen als auch Umlaufbeschlüsse über dieselbe
  Struktur ab (kein separates Modell für Umlaufbeschlüsse), inkl.
  `meeting_agenda_items` für die Tagesordnung. `resolution_collection.meeting_id`
  ist nullable und verknüpft optional einen Beschluss mit der Versammlung, in der
  er gefasst wurde. Einladung und Niederschrift werden serverseitig als PDF
  generiert (WeasyPrint statt reportlab, da hier textlastiges HTML/CSS-Layout statt
  tabellarischer Rechenwerke im Vordergrund steht wie bei der Jahresabrechnung).
- **Nebenkostenabrechnung:** `settlement_periods`/`settlement_positions`/
  `unit_settlement_shares`/`unit_settlement_summaries` bilden Abrechnungszeitraum,
  einzelne Kostenpositionen, deren Verteilung je Einheit sowie das
  Einheiten-Gesamtergebnis ab. Zahlungseingänge werden über einen eigenen
  Payment-Endpoint auf die Konten 1220 (Hausgeld) bzw. 1200 (Miete) gebucht.
  PDF-Export je Einheit über `reportlab` (tabellenlastig, orientiert an der
  Muster-Jahresabrechnung `Einzelabrechnung 2024 Wohnung 4.docx`).
- **Editable-until-Beschluss (Wirtschaftsplan-/Abrechnungspositionen):** Solange
  ein Wirtschaftsplan bzw. eine Abrechnungsperiode im Status "Entwurf" ist,
  lassen sich einzelne Positionen über `PATCH`/`DELETE /budget-plans/{id}/
  positions/{position_id}` bzw. `/settlement-periods/{id}/positions/{position_id}`
  weiterhin ändern oder entfernen. Jede Änderung berechnet die betroffenen
  `unit_budget_shares`/`unit_settlement_shares` (bei Abrechnungen zusätzlich die
  `unit_settlement_summaries`) automatisch neu, statt die alte Verteilung stehen
  zu lassen. Nach der Beschlussfassung ("Beschlossen") sind Positionen gesperrt -
  Korrekturen laufen dann nur noch über eine neue Abrechnungsperiode bzw. einen
  neuen Wirtschaftsplan, nicht durch nachträgliches Editieren der beschlossenen
  Zahlen (konsistent mit dem Storno-Prinzip, nur vor statt nach der
  Verbindlichkeit).
- **Umlageschlüssel-Verwaltung im Frontend:** Für CRUD auf `unit_allocation_keys`
  (siehe Grundsatzentscheidung „Umlageschlüssel-Gültigkeit" oben) existiert ein
  eigenständiges Feature-Modul (`frontend/src/features/allocationKeys/`: `api.ts`,
  `useAllocationKeys.ts`, `AllocationKeyForm.tsx`, `AllocationKeysPage.tsx`) mit
  eigener Route und Sidebar-Eintrag „Umlageschlüssel" - zuvor war ein Umlageschlüssel
  nur indirekt über `AllocationKeyField` (das Auswahl-Widget in Wirtschaftsplan-,
  Sonderumlage- und Abrechnungsformularen) referenzierbar, nicht aber eigenständig
  anlegbar/schließbar.



## Architektur
```
React + TypeScript (Vite)  →  FastAPI (SQLAlchemy 2.0, Alembic, Pydantic)  →  PostgreSQL 16 (RLS)
```
## Hinweise für die lokale Entwicklung
- **`docker compose down -v` löscht alle User:** Das DB-Volume wird komplett neu
  aufgebaut, `04_testdata.sql` legt bewusst keinen User mehr an (siehe
  `app/cli.py`). Nach jedem `down -v` muss der erste Admin-Account manuell neu
  angelegt werden:
  `docker compose exec backend python -m app.cli create-admin --name "Admin"
  --email admin@example.com --password "StartPasswort123!"`.
- **SQLAlchemy-Enum-Spalten und Postgres-ENUMs:** `Enum(PyEnum, name=...)`
  persistiert standardmäßig den Python-Member-**Namen** (z.B. `aktiv`), nicht
  den **Wert** (`AKTIV`). Weicht der Name vom Wert ab (wie bei `AccountType`,
  `EntryDirection`, `PropertyRole`), muss `values_callable=lambda e: [x.value
  for x in e]` gesetzt werden - sonst schlägt der INSERT mit
  `invalid input value for enum ...` fehl, obwohl das Postgres-ENUM selbst
  korrekt definiert ist. Betrifft nur Enums, deren Name ≠ Wert ist
  (`LeaseStatus` z.B. ist unkritisch, dort sind beide identisch).
- **Alembic-Migrationen nach `alembic stamp head` nicht vergessen
  auszuführen:** Ein neues Modellfeld im ORM (`app/models/...`) ist erst nach
  `docker compose exec backend alembic upgrade head` tatsächlich in der DB
  vorhanden - vorher wirft jeder Zugriff `UndefinedColumn`, obwohl Code und
  Migration bereits im Repo liegen. `alembic stamp head` markiert eine
  Migration nur als erledigt, OHNE sie auszuführen.
- **Alembic-Revision-IDs ≤ 32 Zeichen halten** — `alembic_version.version_num` ist standardmäßig
  VARCHAR(32); eine längere selbstgewählte Revision-ID führt zu StringDataRightTruncation
  erst beim finalen Versions-Update, nachdem der DDL-Teil der Migration bereits gelaufen ist
  (wird aber dank Transaktions-Wrapper in env.py vollständig zurückgerollt). Migrationen, die
  noch nicht ausgeführt wurden, dürfen dafür in-place überarbeitet werden.
- **OCR-Extraktion des SKR04-PDF unzuverlässig:** Für `05_skr04_kontenrahmen.sql` wurde jeder
  Eintrag manuell anhand der Original-Seiten-Scans geprüft statt per automatisierter
  Volltextextraktion übernommen (mehrspaltiges Tabellenlayout im Original).
- **WeasyPrint auf Debian „trixie": Paketname geändert** — die Bibliothek heißt dort
  `libgdk-pixbuf-2.0-0` statt der älteren `libgdk-pixbuf2.0-0`-Bezeichnung; ohne die
  Anpassung im `backend/Dockerfile` schlägt der Image-Build beim `apt-get install`
  fehl, obwohl WeasyPrint selbst korrekt in `requirements.txt` steht.
- **Doppelte Postgres-ENUM-Anlage in Migrationen vermeiden:** Wird ein `ENUM`-Typ
  innerhalb einer Migration zunächst separat per `.create(op.get_bind(),
  checkfirst=True)` angelegt (z.B. weil eine Spalte diesen Typ referenziert, bevor
  die Tabelle selbst existiert), muss die Spalte in `create_table()` mit
  `sqlalchemy.dialects.postgresql.ENUM(..., create_type=False)` referenziert
  werden - sonst versucht SQLAlchemy beim `create_table()`-Dispatch, den Typ ein
  zweites Mal anzulegen (`DuplicateObject`). Generisches `sa.Enum(...)` reicht
  dafür nicht: es baut beim Dispatch eine eigene dialektspezifische Kopie und
  verliert dabei das `create_type`-Flag - es muss direkt `postgresql.ENUM` sein
  (siehe `0005_property_bank_accounts.py`, dort auch der Downgrade-Sonderfall:
  `op.drop_table()` löst kein automatisches `DROP TYPE` aus, das ENUM muss separat
  gedroppt werden).


## Arbeitsweise ab jetzt (lernorientiert)
- Änderungen werden erklärt (was/warum/Alternativen), bevor der Code kommt.
- Code wird schrittweise gezeigt, nicht als großer Sprung.
- Neue Konzepte (RLS, JWT, TanStack Query, ...) werden kurz eingeordnet.
- Rückfragen zum "Warum" werden vor dem nächsten Schritt beantwortet.
- PROJECTPLAN.md wird von Jens gepflegt; bereits bestätigte Entscheidungen werden von
  Claude nicht erneut editiert.

## Phasen

| # | Phase | Inhalt | Abhängig von |
|---|-------|--------|---------------|
| 0 | Setup | Backend-/Frontend-Grundgerüst, Docker Compose, modulare Frontend-Struktur, CI-Basis | — |
| 1 | Auth & Access Control | Login (E-Mail + Google SSO) für Admin/Verwalter/Eigentümer/Mieter, JWT via httpOnly-Cookie, RLS-Policies, `access_log`-Middleware, Nutzerverwaltung (Anlegen/Bearbeiten/Löschen inkl. Rollenzuweisung) | 0 |
| 2 | Stammdaten | CRUD für properties/units/owners/tenants, Soft-Delete, Eigentümerzuordnung je Einheit | 1 |
| 3 | Buchhaltung | Journal/Entry-Lines, Soll=Haben-Trigger (`02_triggers.sql`), Storno-Flow, Kontenrahmen global + liegenschaftseigen | 2 |
| 4 | Wirtschaftsplan, Sonderumlagen & Beschluss-Sammlung | Wirtschaftspläne je Objekt/Jahr (`budget_plans`, `budget_positions`), Verteilung je Einheit nach MEA/Umlageschlüssel (`unit_budget_shares`), Sonderumlagen (`special_assessments`, `unit_special_assessment_shares`), Beschluss-Sammlung § 24 WEG (`resolution_collection`, dauerhaft aufbewahrt, kein regulärer Soft-Delete-Lifecycle) | 2, 3 |
| 5 | Nebenkostenabrechnung | Umlageschlüssel-Berechnung (`unit_allocation_keys` mit Gültigkeitszeitraum, Wechsel nur zum 01.01. wirksam), Zahlungseingang, PDF-Export je Einheit (siehe Beispiel „Einzelabrechnung 2024 Wohnung 4") | 3, 4 |
| 6 | Reale Bankkonten je Liegenschaft | `property_bank_accounts` (Trennungsgebot § 27 Abs. 5 WEG), Girokonto/Rücklagenkonten mit Gültigkeitszeitraum statt `is_active` | 3 |
| 7 | Härtung & Betrieb | Rate-Limiting, Logging ohne PII, Backups, Key-Rotation, E2E-Tests, PostgreSQL-RLS-Durchsetzung, Google-SSO-Login-Flow, `access_log`-Middleware, produktiver E-Mail-Versand | laufend |
| 8 | Eigentümerversammlungen & Umlaufbeschluss *(informell ergänzt, ursprünglich nicht in der Phasenliste)* | `owner_meetings`, `meeting_agenda_items`, Verknüpfung mit `resolution_collection`, Einladung/Niederschrift als PDF (WeasyPrint), Umlaufbeschluss über dieselbe Struktur | 4 |
| 9 | Mietsollstellung & SEPA *(verschoben aus der ursprünglich als Phase 6 geplanten Reihenfolge)* | `03_procedures.sql`, Pain.008-XML-Export | 3 |

> **Hinweis:** Phase 6 wurde inhaltlich von "Mietsollstellung & SEPA" auf "Reale Bankkonten je
> Liegenschaft" umgewidmet, da das Trennungsgebot (§ 27 Abs. 5 WEG) fachlich früher benötigt
> wurde. Mietsollstellung/SEPA-Export laufen dafür als eigene, spätere Phase 9. Phase 8
> (Eigentümerversammlungen) wurde zusätzlich zur ursprünglichen Planung ergänzt, weil sie in
> der Praxis vor Phase 7 (Härtung) gebraucht wurde.

## Meilensteine je Phase
- **Phase 0:** `docker-compose up` startet DB + FastAPI `/health` + React-Grundgerüst mit
  modularer Ordnerstruktur und übernommenem Design. ✅ erledigt
- **Phase 1:** Vier Test-User (Admin/Verwalter/Eigentümer/Mieter) können sich einloggen
  und erhalten nachweislich unterschiedliche Ergebnismengen auf `/properties` —
  verifiziert durch einen negativen RLS-Testfall. *(Login/JWT/Nutzerverwaltung ✅, RLS-Testfall offen)*
- **Phase 2:** Admin/Verwalter legt Objekt + Einheiten an, ordnet Eigentümer zu —
  vollständig im Frontend. ✅ erledigt
- **Phase 3:** Buchung mit Soll≠Haben wird serverseitig zuverlässig abgelehnt (Testfall). ✅ erledigt
- **Phase 4:** Verwalter legt für ein Objekt einen Wirtschaftsplan mit Positionen an; das
  System verteilt die Beträge automatisch je Einheit nach Umlageschlüssel
  (`unit_budget_shares`). Eine Sonderumlage kann einem Beschluss aus der Beschluss-Sammlung
  zugeordnet und ebenfalls je Einheit verteilt werden. ✅ erledigt — Positionen lassen sich
  zusätzlich bis zur Beschlussfassung weiter bearbeiten/löschen, mit automatischer
  Neuberechnung der Einheiten-Anteile (siehe Grundsatzentscheidung „Editable-until-Beschluss").
- **Phase 5:** Vollständige Betriebskostenabrechnung für ein Testobjekt als PDF (Format
  orientiert an der Beispiel-Jahresabrechnung im Projekt). ✅ erledigt — inkl. PDF-Export,
  Zahlungseingang (in die Buchhaltungsseite integriert, `features/payments`, kein
  eigener Menüpunkt) und eigenständigem Umlageschlüssel-CRUD-Modul (`features/allocationKeys`).
- **Phase 6:** Jede Liegenschaft verfügt über mindestens ein Giro- und ein Rücklagenkonto mit
  eigener IBAN und Gültigkeitszeitraum. ✅ erledigt
- **Phase 7:** Vor Produktivbetrieb abgeschlossen. *(offen)*
- **Phase 8:** Eine Eigentümerversammlung kann angelegt, Einladung und Niederschrift als PDF
  erzeugt und Beschlüsse daraus in die Beschluss-Sammlung übernommen werden; ein
  Umlaufbeschluss läuft über dieselbe Struktur. ✅ Kernfunktion erledigt; eine Erweiterung um
  eine strukturierte Niederschrift (Kopfdaten wie Versammlungsleiter/Protokollführer/
  Endzeit/vertretene Anteile/Beschlussfähigkeit, TOP-weiser Protokolltext, Abstimmungs-
  ergebnisse je Beschluss) ist im Backend fertig (Migration `0007`,
  `PATCH /meetings/{meeting_id}/agenda-items/{item_id}`) - das zugehörige
  Eingabeformular im Frontend steht noch aus.
- **Phase 9:** Gültige Pain.008-Datei für einen Lastschriftlauf. *(offen)*


## Status
- [x] Datenbankschema (`01_schema.sql`) inkl. DSGVO-Maßnahmen
- [x] Phase 0 — Setup
- [ ] Phase 1 — Auth & Access Control *(Login, JWT, Nutzerverwaltung inkl. Rollenzuweisung ✅; RLS-Policies, `access_log`-Middleware und Google-SSO-Login-Flow offen)*
- [x] Phase 2 — Stammdaten *(Backend-CRUD für properties/units/owners/tenants inkl. Soft-Delete und Eigentümerzuordnung sowie Frontend für Properties/Units/Owners/Tenants ✅)*
- [x] Phase 3 — Buchhaltung *(Kontenrahmen global + liegenschaftseigen, Journal-Erfassung mit Soll=Haben-Trigger, Storno-Flow, Frontend inkl. Kontenverwaltung je Liegenschaft ✅)*
- [x] Phase 4 — Wirtschaftsplan, Sonderumlagen & Beschluss-Sammlung *(Backend + Frontend ✅; Positionen bis zur Beschlussfassung editierbar/löschbar ✅)*
- [x] Phase 5 — Nebenkostenabrechnung *(Kernfunktion inkl. PDF-Export, Zahlungseingang (integriert in die Buchhaltungsseite) und eigenständiges Umlageschlüssel-CRUD-Modul ✅)*
- [x] Phase 6 — Reale Bankkonten je Liegenschaft *(`property_bank_accounts` mit Gültigkeitszeitraum ✅)*
- [ ] Phase 7 — Härtung & Betrieb *(offen: RLS-Durchsetzung, Google-SSO-Flow, `access_log`-Middleware, produktiver E-Mail-Versand, Rate-Limiting, Backups, Key-Rotation, E2E-Tests)*
- [x] Phase 8 — Eigentümerversammlungen & Umlaufbeschluss *(informell ergänzt; `owner_meetings`, Einladung/Niederschrift als PDF ✅; strukturierte Niederschrift (Kopfdaten, TOP-Protokolltext, Abstimmungsergebnisse) im Backend fertig, Frontend-Formular offen)*
- [ ] Phase 9 — Mietsollstellung & SEPA *(offen, verschoben aus der ursprünglich als Phase 6 geplanten Reihenfolge)*

### Bewusst zurückgestellt (kein eigener Phasen-Slot)
- § 35a EStG-Bescheinigung (Haushaltsnahe Dienstleistungen/Handwerkerleistungen)
- Rücklagendarstellung und Vermögensaufstellung
- Mieterseitige Betriebskostenabrechnung (aktuell nur eigentümerseitige Nebenkostenabrechnung)
- „Dokumente"-Navigationseintrag (zentrale Übersicht aller erzeugten PDFs - Einladungen,
  Niederschriften, Jahresabrechnungen - liegen bisher nur verstreut je Feature-Seite vor