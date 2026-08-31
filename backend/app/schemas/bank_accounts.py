# backend/app/schemas/bank_accounts.py
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.bank_accounts import BankAccountPurpose


class BankAccountCreate(BaseModel):
    property_id: int
    account_id: int
    account_purpose: BankAccountPurpose
    purpose_detail: str | None = Field(default=None, max_length=100)
    bank_name: str = Field(min_length=1, max_length=100)
    iban: str | None = Field(default=None, min_length=15, max_length=34)
    bic: str | None = Field(default=None, min_length=8, max_length=11)
    valid_from: date
    valid_to: date | None = None


class BankAccountUpdate(BaseModel):
    """Für Korrekturen am laufenden Konto sowie zum Beenden der Gültigkeit
    (valid_to setzen). property_id/account_id/valid_from bewusst nicht
    änderbar - ein echter Kontowechsel läuft über einen neuen Eintrag
    (POST), nicht über Editieren des bestehenden - analog
    OwnerAssignmentUpdate bei unit_owner_history."""

    purpose_detail: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, min_length=1, max_length=100)
    iban: str | None = Field(default=None, min_length=15, max_length=34)
    bic: str | None = Field(default=None, min_length=8, max_length=11)
    valid_to: date | None = None


class BankAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bank_account_id: int
    property_id: int
    account_id: int
    account_purpose: BankAccountPurpose
    purpose_detail: str | None
    bank_name: str
    iban_last4: str | None
    valid_from: date
    valid_to: date | None
    created_at: datetime