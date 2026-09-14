# backend/app/schemas/accounts.py
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.buchhaltung import AccountType, EntryDirection


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: int
    account_number: str
    account_name: str
    account_class: str
    type: AccountType
    is_active: bool
    property_id: int | None
    is_reserve_account: bool


class AccountCreate(BaseModel):
    property_id: int
    account_number: str = Field(pattern=r"^[0-8][0-9]{3}$")
    account_name: str = Field(min_length=1, max_length=100)
    type: AccountType
    is_reserve_account: bool = False


class AccountUpdate(BaseModel):
    """Nur für liegenschaftseigene Konten - account_number ist bewusst nicht
    änderbar (könnte sonst bestehende Buchungszeilen fachlich verfälschen)."""

    account_name: str | None = Field(default=None, min_length=1, max_length=100)
    type: AccountType | None = None
    is_active: bool | None = None
    is_reserve_account: bool | None = None


class AccountLedgerLineOut(BaseModel):
    """Eine Buchungszeile im Kontenblatt - 'balance' ist der laufende Saldo
    NACH dieser Zeile (Soll-Betrag positiv, Haben-Betrag negativ addiert)."""

    line_id: int
    entry_id: int
    entry_date: date
    document_reference: str | None
    description: str
    unit_id: int | None
    direction: EntryDirection
    amount: float
    balance: float


class AccountLedgerOut(BaseModel):
    account_id: int
    account_number: str
    account_name: str
    property_id: int
    date_from: date | None
    date_to: date | None
    # Saldo aus allen Buchungen VOR date_from - 0, wenn kein date_from
    # gesetzt ist (dann beginnt die Anzeige bei der allerersten Buchung).
    opening_balance: float
    closing_balance: float
    lines: list[AccountLedgerLineOut] = Field(default_factory=list)