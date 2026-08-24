from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Gemeinsame Basisklasse aller ORM-Models. Wird von Alembic für
    Autogenerate-Vergleiche importiert (siehe alembic/env.py)."""

    pass
