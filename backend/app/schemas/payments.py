# backend/app/schemas/payments.py
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, model_validator


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

    # Miete: Trennung in Kaltmiete- und Nebenkostenvorauszahlungs-Anteil,
    # gebucht auf getrennte Forderungskonten (1200/1210) - Grundlage für die
    # taggenaue Mieterabrechnung (Soll/Ist der Vorauszahlung je Vertrag).
    cold_rent_amount: float | None = Field(default=None, ge=0)
    additional_costs_amount: float | None = Field(default=None, ge=0)

    # Hausgeld: Trennung in Bewirtschaftungskosten- und
    # Instandhaltungsrücklage-Anteil, gebucht auf getrennte Forderungskonten
    # (1220/1225).
    operating_amount: float | None = Field(default=None, ge=0)
    reserve_amount: float | None = Field(default=None, ge=0)

    # Umbenannt von 'reference' -> 'document_reference' (Chat vom
    # 24.09.2026): das Frontend sendet seit jeher 'document_reference' -
    # das Feld hieß hier bisher anders und wurde von Pydantic stillschweigend
    # ignoriert (unbekannte Felder werden per Default verworfen), die
    # Belegnummer kam nie in der Buchung an.
    document_reference: str | None = Field(default=None, max_length=100)
    # Optional - ohne Angabe wird automatisch das am payment_date gültige
    # Girokonto der Liegenschaft gewählt (Regelfall).
    bank_account_id: int | None = None

    @model_validator(mode="after")
    def _require_positive_split(self) -> "PaymentCreate":
        if self.payment_type == PaymentType.miete:
            total = (self.cold_rent_amount or 0) + (self.additional_costs_amount or 0)
        else:
            total = (self.operating_amount or 0) + (self.reserve_amount or 0)
        if total <= 0:
            raise ValueError("Mindestens einer der beiden Beträge muss > 0 sein.")
        return self


class UnitHausgeldOverviewOut(BaseModel):
    unit_id: int
    unit_number: str
    owner_id: int | None
    monthly_target: float           # Monatssoll gesamt (Bewirtschaftung + Rücklage)
    monthly_target_reserve: float   # davon Instandhaltungsrücklage
    target_amount: float            # Soll bis heute, gesamt
    target_reserve_amount: float    # davon Instandhaltungsrücklage
    paid_amount: float              # Ist, gesamt
    paid_reserve_amount: float      # davon auf das Rücklagenkonto (1225) gezahlt
    balance: float                  # Soll - Ist, gesamt
    balance_reserve: float          # davon Rücklagenanteil
    has_budget_plan: bool


class HausgeldPaymentOut(BaseModel):
    entry_id: int
    entry_date: date
    amount: float
    document_reference: str | None
    purpose: str  # "Bewirtschaftung" | "Instandhaltungsruecklage"