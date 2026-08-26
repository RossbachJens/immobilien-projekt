# backend/app/schemas/owners.py
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class OwnerCreate(BaseModel):
    first_name: str | None = Field(default=None, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    company_name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    street_and_number: str = Field(min_length=1, max_length=150)
    postal_code: str | None = Field(default=None, max_length=10)
    city: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=100)
    # Klartext nur im Request - wird sofort serverseitig verschlüsselt
    # (app/core/crypto.py) und nie unverschlüsselt gespeichert oder
    # zurückgegeben (siehe OwnerOut: nur iban_last4).
    iban: str | None = Field(default=None, min_length=15, max_length=34)
    bic: str | None = Field(default=None, min_length=8, max_length=11)
    sepa_mandate_reference: str | None = Field(default=None, max_length=35)
    sepa_granted_at: date | None = None


class OwnerUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    company_name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    street_and_number: str | None = Field(default=None, min_length=1, max_length=150)
    postal_code: str | None = Field(default=None, max_length=10)
    city: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=100)
    iban: str | None = Field(default=None, min_length=15, max_length=34)
    bic: str | None = Field(default=None, min_length=8, max_length=11)
    sepa_mandate_reference: str | None = Field(default=None, max_length=35)
    sepa_granted_at: date | None = None


class OwnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    owner_id: int
    first_name: str | None
    last_name: str
    company_name: str | None
    email: str | None
    phone: str | None
    street_and_number: str
    postal_code: str | None
    city: str | None
    bank_name: str | None
    iban_last4: str | None
    sepa_mandate_reference: str | None
    sepa_granted_at: date | None
    created_at: datetime
    # true, wenn ein aktiver User über users.owner_id verknüpft ist - rein
    # informativ für die Verwaltung, keine eigene Owner-Spalte.
    has_online_access: bool = False