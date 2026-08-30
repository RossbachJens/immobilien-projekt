# Projektplan: FastAPI-Backend & React-Frontend für die Immobilien-/WEG-Datenbank

## Grundsatzentscheidungen (festgehalten)
- **Zugriffskontrolle:** Defense-in-Depth — FastAPI filtert Queries nach Rolle/Zuordnung
  UND PostgreSQL Row-Level-Security erzwingt dieselbe Regel zusätzlich auf DB-Ebene.
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
  blockieren würde.
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
- **Manuelle Buchungen sind ausschließlich liegenschaftsbezogen:** `entry_lines.
  unit_id` wird beim manuellen Erfassen bewusst NICHT gesetzt - die Aufteilung
  auf Einheiten erfolgt erst in Phase 5 über den Umlageschlüssel im Rahmen der
  Nebenkostenabrechnung. `unit_id` bleibt im Schema für automatisierte
  Buchungen reserviert (z.B. Mietsollstellung, `03_procedures.sql`).
- **Reale Bankkonten je Liegenschaft (Phase 6):** Trennungsgebot § 27 Abs. 5 WEG -
  jede Liegenschaft braucht mindestens ein Girokonto und mindestens ein
  Rücklagenkonto, real mit eigener IBAN. Eine Liegenschaft kann mehrere
  Rücklagenkonten gleichzeitig haben (z.B. Tagesgeld, Kündigungsgeld, Sparbrief -
  vgl. Konten 1810/1820/1830 in 04_testdata.sql). Neue Tabelle
  `property_bank_accounts`: property_id (FK, Pflicht), account_id (FK zu
  accounts, SKR04-Kategorie), account_purpose, bank_name, iban_encrypted (wie
  bei owners/tenants via pgcrypto), iban_last4, ggf. creditor_id für SEPA.
  1:n-Beziehung Liegenschaft -> Bankkonten.
- **Beschluss-Sammlung (§ 24 WEG) - append-only:** `resolution_collection`
  bekommt eine gesetzlich vorgeschriebene `lfd_nr` (fortlaufend je
  Liegenschaft, nie wiederverwendet - auch nicht nach Soft-Delete-Korrektur).
  Statusänderungen und Gerichtsentscheidungen zu einem bestehenden Beschluss
  werden nie durch Bearbeiten der Zeile abgebildet, sondern als neuer
  Eintrag mit `refers_to_resolution_id` ("zu lfd. Nr. X") - konsistent mit
  dem Storno-Prinzip bei `journal_entries`.


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
  Migration bereits im Repo liegen.
- **Alembic-Revision-IDs ≤ 32 Zeichen halten — alembic_version.version_num ist standardmäßig VARCHAR(32); eine längere 
  selbstgewählte Revision-ID führt zu StringDataRightTruncation erst beim finalen Versions-Update, nachdem der DDL-Teil der
  Migration bereits gelaufen ist (wird aber dank Transaktions-Wrapper in env.py vollständig zurückgerollt).


## Arbeitsweise ab jetzt (lernorientiert)
- Änderungen werden erklärt (was/warum/Alternativen), bevor der Code kommt.
- Code wird schrittweise gezeigt, nicht als großer Sprung.
- Neue Konzepte (RLS, JWT, TanStack Query, ...) werden kurz eingeordnet.
- Rückfragen zum "Warum" werden vor dem nächsten Schritt beantwortet.

## Phasen

| # | Phase | Inhalt | Abhängig von |
|---|-------|--------|---------------|
| 0 | Setup | Backend-/Frontend-Grundgerüst, Docker Compose, modulare Frontend-Struktur, CI-Basis | — |
| 1 | Auth & Access Control | Login (E-Mail + Google SSO) für Admin/Verwalter/Eigentümer/Mieter, JWT via httpOnly-Cookie, RLS-Policies, `access_log`-Middleware, Nutzerverwaltung (Anlegen/Bearbeiten/Löschen inkl. Rollenzuweisung) | 0 |
| 2 | Stammdaten | CRUD für properties/units/owners/tenants, Soft-Delete | 1 |
| 3 | Buchhaltung | Journal/Entry-Lines, Soll=Haben-Trigger (`02_triggers.sql`), Storno-Flow | 2 |
| 4 | Wirtschaftsplan, Sonderumlagen & Beschluss-Sammlung | Wirtschaftspläne je Objekt/Jahr (`budget_plans`, `budget_positions`), Verteilung je Einheit nach MEA/Umlageschlüssel (`unit_budget_shares`), Sonderumlagen (`special_assessments`, `unit_special_assessment_shares`), Beschluss-Sammlung § 24 WEG (`resolution_collection`, dauerhaft aufbewahrt, kein regulärer Soft-Delete-Lifecycle) | 2, 3 |
| 5 | Nebenkostenabrechnung | Umlageschlüssel-Berechnung (`unit_allocation_keys` mit Gültigkeitszeitraum, Wechsel nur zum 01.01. wirksam), PDF-Export je Einheit (siehe Beispiel „Einzelabrechnung 2024 Wohnung 4") | 3, 4 |
| 6 | Mietsollstellung & SEPA | `03_procedures.sql`, Pain.008-XML-Export | 3 |
| 7 | Härtung & Betrieb | Rate-Limiting, Logging ohne PII, Backups, Key-Rotation, E2E-Tests | laufend |

## Meilensteine je Phase
- **Phase 0:** `docker-compose up` startet DB + FastAPI `/health` + React-Grundgerüst mit
  modularer Ordnerstruktur und übernommenem Design. ✅ erledigt
- **Phase 1:** Vier Test-User (Admin/Verwalter/Eigentümer/Mieter) können sich einloggen
  und erhalten nachweislich unterschiedliche Ergebnismengen auf `/properties` —
  verifiziert durch einen negativen RLS-Testfall.
- **Phase 2:** Admin/Verwalter legt Objekt + Einheiten an, ordnet Eigentümer zu —
  vollständig im Frontend.
- **Phase 3:** Buchung mit Soll≠Haben wird serverseitig zuverlässig abgelehnt (Testfall).
- **Phase 4:** Verwalter legt für ein Objekt einen Wirtschaftsplan mit Positionen an; das
  System verteilt die Beträge automatisch je Einheit nach Umlageschlüssel
  (`unit_budget_shares`). Eine Sonderumlage kann einem Beschluss aus der Beschluss-Sammlung
  zugeordnet und ebenfalls je Einheit verteilt werden.
- **Phase 5:** Vollständige Betriebskostenabrechnung für ein Testobjekt als PDF (Format
  orientiert an der Beispiel-Jahresabrechnung im Projekt).
- **Phase 6:** Gültige Pain.008-Datei für einen Lastschriftlauf.
- **Phase 7:** Vor Produktivbetrieb abgeschlossen.


## Status
- [x] Datenbankschema (`01_schema.sql`) inkl. DSGVO-Maßnahmen
- [x] Phase 0 — Setup
- [ ] Phase 1 — Auth & Access Control *(Login, JWT, Nutzerverwaltung inkl. Rollenzuweisung ✅; RLS-Policies & `access_log`-Middleware offen)*
- [ ] Phase 2 — Stammdaten *(Backend-CRUD für properties/units/owners/tenants inkl. Soft-Delete und Eigentümerzuordnung ✅; Frontend für Units/Owners/Tenants offen)*
- [x] Phase 3 — Buchhaltung *(Kontenrahmen global + liegenschaftseigen, Journal-Erfassung mit Soll=Haben-Trigger, Storno-Flow, Frontend inkl. Kontenverwaltung je Liegenschaft ✅)*
- [ ] Phase 4 — Wirtschaftsplan, Sonderumlagen & Beschluss-Sammlung
- [ ] Phase 5 — Nebenkostenabrechnung
- [ ] Phase 6 — Mietsollstellung & SEPA
- [ ] Phase 7 — Härtung & Betrieb
