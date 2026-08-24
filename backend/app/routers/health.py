from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    """Prüft, dass die API läuft UND die DB-Verbindung steht."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
