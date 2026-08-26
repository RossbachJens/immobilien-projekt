# backend/app/core/crypto.py
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings


def encrypt_value(db: Session, plain_value: str) -> bytes:
    """
    Verschlüsselt IBAN/BIC über Postgres' pgcrypto (pgp_sym_encrypt) - läuft
    serverseitig in der DB, der Schlüssel (settings.pii_encryption_key) geht
    nur als Bind-Parameter über die DB-Verbindung, nie als Python-String, der
    z.B. in einem Traceback landen könnte. Siehe 01_schema.sql, Abschnitt 6b.
    """
    return db.execute(
        text("SELECT pgp_sym_encrypt(:plain, :key)"),
        {"plain": plain_value, "key": settings.pii_encryption_key},
    ).scalar_one()


def decrypt_value(db: Session, encrypted_value: bytes) -> str:
    """Für spätere Verwendung (z.B. Pain.008-Export in Phase 6) - aktuell von
    keinem Endpoint aufgerufen, da OwnerOut/TenantOut nur iban_last4 zeigen
    (Datenminimierung, Art. 5 Abs. 1 lit. c DSGVO)."""
    return db.execute(
        text("SELECT pgp_sym_decrypt(:enc, :key)"),
        {"enc": encrypted_value, "key": settings.pii_encryption_key},
    ).scalar_one()


def iban_last4(iban: str) -> str:
    return iban.replace(" ", "")[-4:]