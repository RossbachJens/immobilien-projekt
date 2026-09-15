# backup-service/app/main.py
"""
Kleiner interner Admin-Service für Backups - läuft im selben Container wie
der bestehende Backup-Loop (scripts/backup-loop.sh) und hat als einziger
Service echten Zugriff auf pg_dump/pg_restore mit Postgres-Superuser-Rechten.
Das Hauptbackend (app_user, RLS-eingeschränkt) spricht diesen Service NUR
über einen internen Admin-Router an (app/routers/backups.py, separater
Schritt) - nie direkt vom Browser aus erreichbar, da kein Port nach außen
published ist (siehe docker-compose.yml).

Auth: gemeinsames Secret (BACKUP_SERVICE_SECRET) im Header
'X-Backup-Service-Secret'. Dieser Service vertraut vollständig dem
Hauptbackend als Aufrufer - die eigentliche Admin-Prüfung (is_admin) passiert
dort bereits vor dem Proxy-Call.
"""
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Backup-Service (intern)")

BACKUP_DIR = Path("/backups")
SECRET = os.environ["BACKUP_SERVICE_SECRET"]
PGDATABASE = os.environ["PGDATABASE"]

# Nur echte Dump-Dateien - verhindert, dass über die API z.B. eine fremde
# Datei im selben Verzeichnis gelistet/gelöscht/wiederhergestellt wird.
FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+\.dump$")


def require_secret(x_backup_service_secret: str | None = Header(default=None)) -> None:
    if x_backup_service_secret != SECRET:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ungültiges Service-Secret")


def _safe_path(filename: str) -> Path:
    """Verhindert Path-Traversal (z.B. '../../etc/passwd') und stellt sicher,
    dass wirklich nur *.dump-Dateien in BACKUP_DIR angesprochen werden."""
    if not FILENAME_PATTERN.match(filename):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ungültiger Dateiname")
    path = BACKUP_DIR / filename
    if path.parent != BACKUP_DIR:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ungültiger Dateiname")
    return path


class BackupOut(BaseModel):
    filename: str
    size_bytes: int
    created_at: datetime
    # True für die automatischen Sicherheitsdumps, die vor einem Restore
    # angelegt werden (Präfix 'pre_restore_') - im Frontend separat markiert.
    is_safety_backup: bool


class RestoreRequest(BaseModel):
    # Der Aufrufer muss den Dateinamen im Body wiederholen - zusätzliche
    # Bestätigung neben der URL, macht ein versehentliches Auslösen (Retry,
    # verklickt) deutlich unwahrscheinlicher.
    confirm_filename: str


def _list_dumps() -> list[BackupOut]:
    results = []
    for path in BACKUP_DIR.glob("*.dump"):
        file_stat = path.stat()
        results.append(
            BackupOut(
                filename=path.name,
                size_bytes=file_stat.st_size,
                created_at=datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc),
                is_safety_backup=path.name.startswith("pre_restore_"),
            )
        )
    return sorted(results, key=lambda b: b.created_at, reverse=True)


def _run_dump(prefix: str = "") -> BackupOut:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{prefix}{PGDATABASE}_{timestamp}.dump"
    target = BACKUP_DIR / filename
    tmp = target.with_suffix(target.suffix + ".tmp")

    result = subprocess.run(
        ["pg_dump", "--format=custom", "--file", str(tmp)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"pg_dump fehlgeschlagen: {result.stderr[-2000:]}",
        )
    # Atomares Umbenennen wie im bestehenden backup-loop.sh - eine
    # abgebrochene Datei bekommt nie den "echten" Namen.
    tmp.rename(target)

    file_stat = target.stat()
    return BackupOut(
        filename=filename,
        size_bytes=file_stat.st_size,
        created_at=datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc),
        is_safety_backup=bool(prefix),
    )


@app.get("/backups", response_model=list[BackupOut])
def list_backups(_: None = Depends(require_secret)) -> list[BackupOut]:
    return _list_dumps()


@app.post("/backups/trigger", response_model=BackupOut, status_code=status.HTTP_201_CREATED)
def trigger_backup(_: None = Depends(require_secret)) -> BackupOut:
    return _run_dump()


@app.get("/backups/{filename}/download")
def download_backup(filename: str, _: None = Depends(require_secret)) -> FileResponse:
    path = _safe_path(filename)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Backup nicht gefunden")
    return FileResponse(path, media_type="application/octet-stream", filename=filename)


@app.delete("/backups/{filename}", status_code=status.HTTP_204_NO_CONTENT)
def delete_backup(filename: str, _: None = Depends(require_secret)) -> None:
    path = _safe_path(filename)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Backup nicht gefunden")
    path.unlink()


@app.post("/backups/{filename}/restore", response_model=BackupOut)
def restore_backup(
    filename: str, payload: RestoreRequest, _: None = Depends(require_secret)
) -> BackupOut:
    if payload.confirm_filename != filename:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "confirm_filename stimmt nicht mit der URL überein"
        )
    path = _safe_path(filename)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Backup nicht gefunden")

    # 1. Sicherheitsnetz: aktuellen Stand VOR dem Restore selbst sichern -
    #    ein fehlerhafter oder zu alter Restore lässt sich damit rückgängig
    #    machen.
    safety_backup = _run_dump(prefix="pre_restore_")

    # 2. Andere Verbindungen (v.a. das Hauptbackend) trennen - pg_restore
    #    --clean muss Tabellen droppen/neu anlegen können, was mit aktiven
    #    Verbindungen blockiert oder Fehler wirft.
    terminate = subprocess.run(
        ["psql", "-d", PGDATABASE, "-c",
         "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
         "WHERE datname = current_database() AND pid <> pg_backend_pid();"],
        capture_output=True, text=True,
    )
    if terminate.returncode != 0:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Verbindungen konnten nicht getrennt werden: {terminate.stderr[-2000:]}",
        )

    # 3. Eigentlicher Restore. --clean/--if-exists räumt vorhandene Objekte
    #    weg, bevor sie aus dem Dump neu angelegt werden; --no-owner, weil
    #    der Dump als 'postgres' läuft und das beim Restore konsistent
    #    bleiben soll.
    restore_result = subprocess.run(
        ["pg_restore", "--clean", "--if-exists", "--no-owner",
         "--dbname", PGDATABASE, str(path)],
        capture_output=True, text=True,
    )
    if restore_result.returncode != 0:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "pg_restore meldete Fehler (Sicherheitsbackup wurde trotzdem angelegt: "
            f"{safety_backup.filename}): {restore_result.stderr[-2000:]}",
        )

    return safety_backup