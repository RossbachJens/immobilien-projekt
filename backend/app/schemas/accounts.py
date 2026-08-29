# backend/app/schemas/accounts.py
from pydantic import BaseModel, ConfigDict, Field

from app.models.buchhaltung import AccountType


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: int
    account_number: str
    account_name: str
    account_class: str
    type: AccountType
    is_active: bool
    property_id: int | None


class AccountCreate(BaseModel):
    property_id: int
    account_number: str = Field(pattern=r"^[0-8][0-9]{3}$")
    account_name: str = Field(min_length=1, max_length=100)
    type: AccountType


class AccountUpdate(BaseModel):
    """Nur für liegenschaftseigene Konten - account_number ist bewusst nicht
    änderbar (könnte sonst bestehende Buchungszeilen fachlich verfälschen)."""

    account_name: str | None = Field(default=None, min_length=1, max_length=100)
    type: AccountType | None = None
    is_active: bool | None = None