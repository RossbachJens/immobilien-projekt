from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, health, properties, users

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
app.include_router(users.router)

# Noch offen (Phase 1 Fortsetzung / Phase 6):
#   - access_log-Middleware (protokolliert Zugriffe auf personenbezogene Daten)
#   - rollenbasierte Filterung + Postgres RLS-Policies (Defense-in-Depth)
