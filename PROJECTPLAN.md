# Projektplan: FastAPI-Backend & React-Frontend für die Immobilien-/WEG-Datenbank

## Grundsatzentscheidungen (festgehalten)
- **Zugriffskontrolle:** Defense-in-Depth — FastAPI filtert Queries nach Rolle/Zuordnung
  UND PostgreSQL Row-Level-Security erzwingt dieselbe Regel zusätzlich auf DB-Ebene.
- **Erste Vertikale:** Auth/Login (inkl. RLS-Grundgerüst), da Rollenmodell alle
  weiteren Phasen durchzieht.
- **Frontend-Sprache:** TypeScript von Anfang an (Vite, TanStack Query, React Router, Zod).

## Architektur
```
React + TypeScript (Vite)  →  FastAPI (SQLAlchemy 2.0, Alembic, Pydantic)  →  PostgreSQL 16 (RLS)
```

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
- **Phase 0:** `docker-compose up` startet DB + FastAPI `/health` + leeres React-Grundgerüst.
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
