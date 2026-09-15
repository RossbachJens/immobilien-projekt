# backend/app/core/backup_client.py
"""
HTTP-Client zum internen Backup-Service (siehe backup-service/app/main.py).
Das Hauptbackend hat bewusst KEINE Superuser-DB-Credentials für
pg_dump/pg_restore (RLS-Trennung aus Phase 7 bleibt unangetastet) -
stattdessen spricht es nur diese eng begrenzte interne API an, die nur über
das Docker-Netz erreichbar ist (kein Port nach außen, siehe
docker-compose.yml). Nutzt httpx wie bereits app/core/google_oauth.py.
"""
from collections.abc import Generator

import httpx
from fastapi import HTTPException

from app.core.config import settings

_HEADERS = {"X-Backup-Service-Secret": settings.backup_service_secret}
# pg_dump/pg_restore eines größeren Datenbestands kann dauern - deutlich
# großzügiger als der Default-Timeout von httpx.
_TIMEOUT = httpx.Timeout(300.0)


def _handle_error(response: httpx.Response) -> None:
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise HTTPException(response.status_code, detail)


def list_backups() -> list[dict]:
    with httpx.Client(base_url=settings.backup_service_url, headers=_HEADERS, timeout=_TIMEOUT) as client:
        response = client.get("/backups")
    _handle_error(response)
    return response.json()


def trigger_backup() -> dict:
    with httpx.Client(base_url=settings.backup_service_url, headers=_HEADERS, timeout=_TIMEOUT) as client:
        response = client.post("/backups/trigger")
    _handle_error(response)
    return response.json()


def delete_backup(filename: str) -> None:
    with httpx.Client(base_url=settings.backup_service_url, headers=_HEADERS, timeout=_TIMEOUT) as client:
        response = client.delete(f"/backups/{filename}")
    _handle_error(response)


def restore_backup(filename: str) -> dict:
    """Liefert die Metadaten des automatisch angelegten Sicherheitsbackups
    (nicht der wiederhergestellten Datei selbst) - siehe
    backup-service/app/main.py::restore_backup."""
    with httpx.Client(base_url=settings.backup_service_url, headers=_HEADERS, timeout=_TIMEOUT) as client:
        response = client.post(f"/backups/{filename}/restore", json={"confirm_filename": filename})
    _handle_error(response)
    return response.json()


def stream_download(filename: str) -> Generator[bytes, None, None]:
    """Streamt die Dump-Datei vom Backup-Service durch, statt sie komplett
    im Hauptbackend-Prozess zu puffern (Dumps können mehrere hundert MB
    groß sein). Erwartet, dass die Existenz der Datei vom Aufrufer bereits
    geprüft wurde (siehe app/routers/backups.py::download_backup) - ein
    Fehler mitten im Stream ließe sich nicht mehr sauber in einen
    HTTP-Fehlercode umwandeln, da die Response-Header dann schon raus sind."""
    with httpx.Client(base_url=settings.backup_service_url, headers=_HEADERS, timeout=_TIMEOUT) as client:
        with client.stream("GET", f"/backups/{filename}/download") as response:
            yield from response.iter_bytes()