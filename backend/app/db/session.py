from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI-Dependency. Öffnet pro Request eine Session und schließt sie danach.

    Ab Phase 1 wird hier zusätzlich, sobald ein authentifizierter User vorliegt,
    'SET LOCAL app.current_user_id' / 'SET LOCAL app.current_role' gesetzt, damit
    die Row-Level-Security-Policies in Postgres greifen (Defense-in-Depth,
    zweite Ebene neben der Filterung in den Routern).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
