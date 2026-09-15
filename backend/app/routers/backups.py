# backend/app/routers/backups.py
"""
Admin-Backup-Verwaltung - proxyt zum internen Backup-Service (siehe
backup-service/app/main.py). Alle eigentlichen DB-Operationen (pg_dump/
pg_restore als Superuser) laufen ausschließlich dort; dieser Router prüft
nur is_admin und reicht die Anfrage weiter (app/core/backup_client.py).

Restore ist absichtlich destruktiv und mit Downtime verbunden - der
Backup-Service verlangt zusätzlich eine confirm_filename-Bestätigung
(app/core/backup_client.py::restore_backup schickt sie automatisch mit),
das Frontend verlangt zusätzlich eine manuelle Eingabe des Dateinamens
(siehe BackupsPage.tsx).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.backup_client import (
    delete_backup as _delete_backup,
    list_backups as _list_backups,
    restore_backup as _restore_backup,
    stream_download,
    trigger_backup as _trigger_backup,
)
from app.core.deps import get_current_admin
from app.models.stammdaten import User
from app.schemas.backups import BackupOut

router = APIRouter(prefix="/backups", tags=["backups"])


@router.get("", response_model=list[BackupOut])
def list_backups(_admin: User = Depends(get_current_admin)) -> list[BackupOut]:
    return [BackupOut.model_validate(b) for b in _list_backups()]


@router.post("/trigger", response_model=BackupOut, status_code=status.HTTP_201_CREATED)
def trigger_backup(_admin: User = Depends(get_current_admin)) -> BackupOut:
    return BackupOut.model_validate(_trigger_backup())


@router.get("/{filename}/download")
def download_backup(filename: str, _admin: User = Depends(get_current_admin)) -> StreamingResponse:
    # Existenzprüfung vorab - eine bereits begonnene StreamingResponse kann
    # einen Fehler mittendrin nicht mehr sauber in einen 404 verwandeln.
    existing = {b["filename"] for b in _list_backups()}
    if filename not in existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Backup nicht gefunden")

    return StreamingResponse(
        stream_download(filename),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
def delete_backup(filename: str, _admin: User = Depends(get_current_admin)) -> None:
    _delete_backup(filename)


@router.post("/{filename}/restore", response_model=BackupOut)
def restore_backup(filename: str, _admin: User = Depends(get_current_admin)) -> BackupOut:
    return BackupOut.model_validate(_restore_backup(filename))