# backend/app/schemas/backups.py
from datetime import datetime

from pydantic import BaseModel


class BackupOut(BaseModel):
    filename: str
    size_bytes: int
    created_at: datetime
    # True für automatische Sicherheitsdumps vor einem Restore (Präfix
    # 'pre_restore_', siehe backup-service/app/main.py) - im Frontend
    # separat markiert.
    is_safety_backup: bool