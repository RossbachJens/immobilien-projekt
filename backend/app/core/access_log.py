# backend/app/core/access_log.py
"""
access_log-Middleware: Rechenschaftspflicht (Art. 30 DSGVO) für Zugriffe auf
personenbezogene Stammdaten. Erste Fassung deckt bewusst nur Owners/Tenants/
Users ab (siehe Chat) - Dokumente (inkl. Downloads) und generierte PDFs
(Niederschriften, Abrechnungen, Einladungen) folgen in einem späteren
Durchgang.

WARUM Middleware statt SQLAlchemy-Event-Instrumentierung:
Eine ASGI-Middleware kennt nur HTTP-Request/-Response, keine ORM-Objekte -
das erzwingt eine explizite URL-Muster-Zuordnung (siehe _RULES unten) statt
automatischer Erkennung. Vorteil: das access_log-Schema (accessed_table,
accessed_record_id NULLABLE) passt exakt dazu - eine Listenabfrage
(GET /owners mit 20 Treffern) erzeugt genau EINEN Log-Eintrag mit
accessed_record_id=NULL, nicht 20 Einzelzeilen. Eine SQLAlchemy-Event-
Lösung (after_flush/do_orm_execute) wäre automatischer, aber deutlich
komplexer und würde bei jeder Listenabfrage entweder viele Zeilen oder eine
unscharfe Sammelzeile erzeugen.

WARUM die User-ID direkt aus dem JWT-Cookie statt über get_current_user:
Middleware läuft AUSSERHALB der FastAPI-Dependency-Injection (vor jeder
Router-Dependency) - get_current_user() steht hier nicht zur Verfügung.
decode_access_token() liefert die User-ID direkt aus dem 'sub'-Claim, ohne
DB-Zugriff - für die Middleware ausreichend, ein erneutes Nachladen des
kompletten User-Objekts wäre unnötiger Overhead. Der Cookie-Name
'access_token' MUSS mit app/routers/auth.py::COOKIE_NAME übereinstimmen.

WARUM nur Status < 400 geloggt wird:
Ein 401/403/404 hat faktisch keine personenbezogenen Daten offengelegt -
Rechenschaftspflicht bezieht sich auf tatsächliche Zugriffe, nicht auf
fehlgeschlagene Versuche.

WARUM eine eigene, vom Request entkoppelte Session:
Die reguläre Request-Session (app/db/session.py::get_db) befindet sich zu
diesem Zeitpunkt (Response bereits generiert) in einem unklaren
Lebenszyklus-Zustand. Ein Fehler beim Schreiben des Audit-Eintrags darf die
eigentliche Antwort niemals kaputt machen - daher eigene Session in
try/except, Logging-Fehler landen nur im Python-Log, nicht beim Client.

WARUM der Response-Body eingesammelt und neu zusammengesetzt wird:
Für POST-Anlagen (INSERT) steht die neu vergebene ID erst NACH dem Insert
fest und muss aus der JSON-Antwort gelesen werden. body_iterator wird dabei
konsumiert und muss für den eigentlichen Client identisch wiederhergestellt
werden - Standard-Muster bei BaseHTTPMiddleware + Body-Zugriff in FastAPI.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.dsgvo import AccessLog

logger = logging.getLogger("app.access_log")

# Muss mit app/routers/auth.py::COOKIE_NAME übereinstimmen - bewusst nicht
# importiert, um keine Abhängigkeit von einem Router-Modul in app/core/
# einzuführen (core/ sollte nicht auf routers/ verweisen müssen).
_ACCESS_TOKEN_COOKIE = "access_token"


@dataclass(frozen=True)
class _Rule:
    method: str
    pattern: re.Pattern[str]
    table: str
    action: str
    # Name des ID-Felds in der JSON-Antwort - nur für INSERT relevant, bei
    # dem die ID erst NACH der Anlage bekannt ist (siehe _extract_record_id).
    response_id_field: str | None = None


def _compile(path_pattern: str) -> re.Pattern[str]:
    return re.compile(f"^{path_pattern}$")


_RULES: list[_Rule] = [
    # --- owners -----------------------------------------------------------
    _Rule("GET", _compile(r"/owners"), "owners", "SELECT"),
    _Rule("GET", _compile(r"/owners/(?P<record_id>\d+)"), "owners", "SELECT"),
    _Rule("POST", _compile(r"/owners"), "owners", "INSERT", response_id_field="owner_id"),
    _Rule("PATCH", _compile(r"/owners/(?P<record_id>\d+)"), "owners", "UPDATE"),
    _Rule("DELETE", _compile(r"/owners/(?P<record_id>\d+)"), "owners", "DELETE"),
    # --- tenants ------------------------------------------------------------
    _Rule("GET", _compile(r"/tenants"), "tenants", "SELECT"),
    _Rule("GET", _compile(r"/tenants/(?P<record_id>\d+)"), "tenants", "SELECT"),
    _Rule("POST", _compile(r"/tenants"), "tenants", "INSERT", response_id_field="tenant_id"),
    _Rule("PATCH", _compile(r"/tenants/(?P<record_id>\d+)"), "tenants", "UPDATE"),
    _Rule("DELETE", _compile(r"/tenants/(?P<record_id>\d+)"), "tenants", "DELETE"),
    # --- users ----------------------------------------------------------------
    # Kein GET /users/{id} im Router (nur Liste) - siehe app/routers/users.py.
    _Rule("GET", _compile(r"/users"), "users", "SELECT"),
    _Rule("POST", _compile(r"/users"), "users", "INSERT", response_id_field="user_id"),
    _Rule("PATCH", _compile(r"/users/(?P<record_id>\d+)"), "users", "UPDATE"),
    _Rule("DELETE", _compile(r"/users/(?P<record_id>\d+)"), "users", "DELETE"),
    # Reactivate ist ein POST, semantisch aber eine Änderung einer
    # bestehenden Zeile - daher UPDATE statt INSERT, record_id aus dem Pfad.
    _Rule("POST", _compile(r"/users/(?P<record_id>\d+)/reactivate"), "users", "UPDATE"),
]


def _match_rule(method: str, path: str) -> tuple[_Rule, int | None] | None:
    for rule in _RULES:
        if rule.method != method:
            continue
        match = rule.pattern.match(path)
        if match is None:
            continue
        record_id = int(match.group("record_id")) if "record_id" in match.groupdict() else None
        return rule, record_id
    return None


def _extract_user_id(request: Request) -> int | None:
    token = request.cookies.get(_ACCESS_TOKEN_COOKIE)
    if token is None:
        return None
    sub = decode_access_token(token)
    if sub is None:
        return None
    try:
        return int(sub)
    except ValueError:
        return None


def _write_log_entry(*, user_id: int | None, table: str, record_id: int | None, action: str) -> None:
    db = SessionLocal()
    try:
        db.add(
            AccessLog(
                user_id=user_id,
                accessed_table=table,
                accessed_record_id=record_id,
                action=action,
            )
        )
        db.commit()
    except Exception:  # noqa: BLE001 - Logging darf die Antwort nie kippen
        db.rollback()
        logger.exception("access_log-Eintrag konnte nicht geschrieben werden (table=%s)", table)
    finally:
        db.close()


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if response.status_code >= 400:
            return response

        matched = _match_rule(request.method, request.url.path)
        if matched is None:
            return response

        rule, record_id = matched

        body_bytes = b""
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()

        async def _replay_body():
            yield body_bytes

        response.body_iterator = _replay_body()  # type: ignore[attr-defined]

        if record_id is None and rule.response_id_field is not None and body_bytes:
            try:
                payload = json.loads(body_bytes)
                record_id = payload.get(rule.response_id_field)
            except (json.JSONDecodeError, AttributeError):
                record_id = None

        user_id = _extract_user_id(request)
        _write_log_entry(user_id=user_id, table=rule.table, record_id=record_id, action=rule.action)

        return response