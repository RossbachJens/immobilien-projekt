# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    accounts, allocation_keys, auth, bank_accounts, budget_plans, health,
    journal_entries, meetings, owners, payments, properties, resolutions,
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
app.include_router(payments.router)
app.include_router(bank_accounts.router)
app.include_router(allocation_keys.router)
app.include_router(meetings.router)

# Noch offen:
#   - access_log-Middleware (protokolliert Zugriffe auf personenbezogene Daten)
#   - rollenbasierte Filterung + Postgres RLS-Policies (Defense-in-Depth)