# Projektplan: FastAPI-Backend & React-Frontend für die Immobilien-/WEG-Datenbank

## Grundsatzentscheidungen (festgehalten)
- **Zugriffskontrolle:** Defense-in-Depth — FastAPI filtert Queries nach Rolle/Zuordnung
  UND PostgreSQL Row-Level-Security erzwingt dieselbe Regel zusätzlich auf DB-Ebene.
- **Erste Vertikale:** Auth/Login (inkl. RLS-Grundgerüst), da Rollenmodell alle
  weiteren Phasen durchzieht.
- **Frontend-Sprache:** TypeScript von Anfang an (Vite, TanStack Query, React Router, Zod).
- **Frontend-Design:** Orientiert sich an den bereits vorhandenen HTML/CSS-Dateien im
  Projekt (`index.html`, `features.html`, `docs.html`, `style.css`, `utilities.css` —
  ursprünglich das statische "Loruki"-Template). Farbpalette (CSS-Variablen wie
  `--primary-color`, `--secondary-color`, `--dark-color`, `--light-color`), Typografie
  (Lato), Utility-Klassen (`.container`, `.card`, `.btn`, `.grid`, Spacing-Klassen) und
  die generelle Formensprache (abgerundete Karten mit Schatten, Navbar-Look) dienen als
  Design-Grundlage für die React-Komponenten. Diese Werte werden nicht 1:1 kopiert,
  sondern als Design-Tokens (z. B. in einer zentralen `theme.css` / CSS-Variablen-Datei)
  ins React-Frontend überführt, damit die Anwendung konsistent aussieht, ohne die
  statischen Utility-Klassen direkt weiterzuschleppen.
- **Frontend-Struktur:** Bewusst **kein Monolith**. Klare Trennung nach Feature-Modulen
  statt einer einzigen wachsenden `App.tsx`. Grobe Zielstruktur:
  ```
  frontend/src/
  ├── api/              # zentraler HTTP-Client + typisierte API-Funktionen je Domäne
  ├── components/        # wiederverwendbare, "dumme" UI-Bausteine (Button, Card, Input, …)
  ├── features/           # ein Ordner je fachlicher Domäne, z. B.:
  │   ├── auth/            #   Login, Session-Handling
  │   ├── properties/       #   Objekte/Einheiten
  │   ├── accounting/        #   Buchhaltung
  │   └── ...                 #   je Feature: components/, hooks/, api.ts, types.ts
  ├── layouts/            # Seitenrahmen (Navbar, Footer, geschützte Layouts)
  ├── routes/             # Routing-Konfiguration (React Router)
  ├── styles/             # zentrale Design-Tokens, abgeleitet aus style.css/utilities.css
  └── lib/                # generische Helfer (Formatierung, Validierung, …)
  ```
  Jedes Feature bleibt für sich testbar und austauschbar; geteilte UI-Bausteine wandern
  erst dann nach `components/`, wenn sie tatsächlich von mehreren Features genutzt werden
  (kein verfrühtes Abstrahieren).

## Architektur
```
React + TypeScript (Vite)  →  FastAPI (SQLAlchemy 2.0, Alembic, Pydantic)  →  PostgreSQL 16 (RLS)
```

## Arbeitsweise ab jetzt (lernorientiert)
Für alle kommenden Schritte gilt zusätzlich:
- Änderungen werden nicht nur ausgeführt, sondern **nachvollziehbar erklärt**: was wird
  geändert, warum, und welche Alternativen es gäbe.
- Code-Diffs/neue Dateien werden Schritt für Schritt gezeigt statt als großer Sprung,
  damit der Aufbau (z. B. Auth-Flow, RLS-Policy, React-Query-Hook) mitverfolgt werden kann.
- Bei neuen Konzepten (z. B. Row-Level-Security, JWT-Handling, TanStack Query) gibt es
  jeweils eine kurze Einordnung, bevor der Code kommt.
- Rückfragen zum "Warum" sind ausdrücklich erwünscht und werden vor dem nächsten Schritt
  beantwortet.

## Phasen

| # | Phase | Inhalt | Abhängig von |
|---|-------|--------|---------------|
| 0 | Setup | Backend-/Frontend-Grundgerüst, Docker Compose, CI-Basis | — |
| 1 | Auth & Access Control | Login (E-Mail + Google SSO), JWT, RLS-Policies, `access_log`-Middleware | 0 |
| 2 | Stammdaten | CRUD für properties/units/owners/tenants, Soft-Delete | 1 |
| 3 | Buchhaltung | Journal/Entry-Lines, Soll=Haben-Trigger (`02_triggers.sql`), Storno-Flow | 2 |
| 4 | Nebenkostenabrechnung | Umlageschlüssel-Berechnung, PDF-Export je Einheit | 3 |
| 5 | Mietsollstellung & SEPA | `03_procedures.sql`, Pain.008-XML-Export | 3 |
| 6 | Härtung & Betrieb | Rate-Limiting, Logging ohne PII, Backups, Key-Rotation, E2E-Tests | laufend |

## Meilensteine je Phase
- **Phase 0:** `docker-compose up` startet DB + FastAPI `/health` + React-Grundgerüst mit
  modularer Ordnerstruktur (siehe oben) und übernommenem Design (Farben/Typo aus
  `style.css`/`utilities.css`).
- **Phase 1:** Drei Test-User (Admin/Owner/Tenant) erhalten nachweislich unterschiedliche
  Ergebnismengen auf `/properties` — verifiziert durch einen negativen RLS-Testfall.
- **Phase 2:** Admin legt Objekt + Einheiten an, ordnet Eigentümer zu — vollständig im Frontend.
- **Phase 3:** Buchung mit Soll≠Haben wird serverseitig zuverlässig abgelehnt (Testfall).
- **Phase 4:** Vollständige Betriebskostenabrechnung für ein Testobjekt als PDF.
- **Phase 5:** Gültige Pain.008-Datei für einen Lastschriftlauf.
- **Phase 6:** Vor Produktivbetrieb abgeschlossen.

## Status
- [x] Datenbankschema (`01_schema.sql`) inkl. DSGVO-Maßnahmen
- [ ] Phase 0 — Setup *(in Arbeit)*
- [ ] Phase 1 — Auth & Access Control
- [ ] Phase 2 — Stammdaten
- [ ] Phase 3 — Buchhaltung
- [ ] Phase 4 — Nebenkostenabrechnung
- [ ] Phase 5 — Mietsollstellung & SEPA
- [ ] Phase 6 — Härtung & Betrieb
