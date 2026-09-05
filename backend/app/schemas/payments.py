# backend/app/schemas/payments.py
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class PaymentType(str, Enum):
    hausgeld = "hausgeld"
    miete = "miete"


class PaymentCreate(BaseModel):
    property_id: int
    payment_type: PaymentType
    unit_id: int
    # Nur bei Miete erforderlich - bei Hausgeld unzulässig (siehe Router).
    lease_id: int | None = None
    payment_date: date
    amount: float = Field(gt=0)
    reference: str | None = Field(default=None, max_length=100)
    # Optional - ohne Angabe wird automatisch das am payment_date gültige
    # Girokonto der Liegenschaft gewählt (Regelfall).
    bank_account_id: int | None = None
    
# backend/app/schemas/payments.py — ergänzen
class UnitHausgeldOverviewOut(BaseModel):
    unit_id: int
    unit_number: str
    owner_id: int | None
    monthly_target: float       # Monatssoll (Summe monthly_installment aller Positionen)
    target_amount: float        # Soll bis heute (Monatssoll × vergangene Monate)
    paid_amount: float          # Ist
    balance: float              # Soll - Ist; positiv = Rückstand, negativ = Guthaben
    has_budget_plan: bool       # false = kein beschlossener Wirtschaftsplan -> Soll ist 0


class HausgeldPaymentOut(BaseModel):
    entry_id: int
    entry_date: date
    amount: float
    document_reference: str | None