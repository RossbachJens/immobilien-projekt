# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.access_log import AccessLogMiddleware
from app.core.config import settings
from app.routers import (
    accounts, allocation_keys, auth, bank_accounts, budget_plans, documents, health,
    journal_entries, meetings, owners, payments, properties, reserve_fund, resolutions,
    settlement_periods, special_assessments, tenants, units, users,
)

app = FastAPI(
    title="Immobilien- & WEG-Verwaltung API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rechenschaftspflicht (Art. 30 DSGVO) - protokolliert Zugriffe auf
# personenbezogene Stammdaten (owners/tenants/users). Bewusst NACH
# CORSMiddleware registriert: Starlette baut den Middleware-Stack in
# umgekehrter Registrierungsreihenfolge auf, wodurch AccessLogMiddleware
# zur äußeren Schicht wird und die von CORSMiddleware bereits gesetzten
# Header sieht - unproblematisch, da AccessLogMiddleware nur den
# Response-Body liest/ersetzt, keine Header verändert.
app.add_middleware(AccessLogMiddleware)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(units.router)
app.include_router(owners.router)
app.include_router(tenants.router)
app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(journal_entries.router)
app.include_router(resolutions.router)
app.include_router(special_assessments.router)
app.include_router(budget_plans.router)
app.include_router(settlement_periods.router)
app.include_router(reserve_fund.router)
app.include_router(payments.router)
app.include_router(bank_accounts.router)
app.include_router(allocation_keys.router)
app.include_router(meetings.router)
app.include_router(documents.router)


# Noch offen:
#   - Google-SSO-Login-Flow
#   - Rate-Limiting, Logging ohne PII, Key-Rotation, produktiver E-Mail-Versand
#   - access_log-Middleware: bisher nur owners/tenants/users abgedeckt -
#     documents (inkl. Downloads) und generierte PDFs (Abrechnungen,
#     Niederschriften, Einladungen) folgen in einem späteren Durchgang
#   - rollenbasierte Filterung + Postgres RLS-Policies: erledigt
#     (Migration 0014_row_level_security)