# backend/app/schemas/tenants.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str | None = Field(default=None, max_length=100)
    street_and_number: str = Field(min_length=1, max_length=150)
    postal_code: str | None = Field(default=None, max_length=10)
    city: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=100)
    iban: str | None = Field(default=None, min_length=15, max_length=34)
    bic: str | None = Field(default=None, min_length=8, max_length=11)
    sepa_mandate_reference: str | None = Field(default=None, max_length=35)


class TenantUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = Field(default=None, max_length=100)
    street_and_number: str | None = Field(default=None, min_length=1, max_length=150)
    postal_code: str | None = Field(default=None, max_length=10)
    city: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=100)
    iban: str | None = Field(default=None, min_length=15, max_length=34)
    bic: str | None = Field(default=None, min_length=8, max_length=11)
    sepa_mandate_reference: str | None = Field(default=None, max_length=35)


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: int
    first_name: str
    last_name: str
    email: str | None
    street_and_number: str
    postal_code: str | None
    city: str | None
    bank_name: str | None
    iban_last4: str | None
    sepa_mandate_reference: str | None
    created_at: datetime
    has_online_access: bool = False