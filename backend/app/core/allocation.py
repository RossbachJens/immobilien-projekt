# backend/app/core/allocation.py
"""
Gemeinsame Verteilungslogik für Wirtschaftsplan-Positionen (Phase 4.2) und
Sonderumlagen (Phase 4.3) - beide verteilen einen Gesamtbetrag auf Einheiten
nach demselben Prinzip (MEA / Wohnfläche / individueller Umlageschlüssel aus
unit_allocation_keys); nur das Ziel des Ergebnisses unterscheidet sich
(unit_budget_shares vs. unit_special_assessment_shares).
"""
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.stammdaten import Property, Unit
from app.models.zuordnungen import UnitAllocationKey


def compute_unit_fractions(
    db: Session, property_: Property, allocation_key_type: str, fiscal_year: int
) -> dict[int, float]:
    """
    Anteil (0..1) je Einheit an einem zu verteilenden Betrag:
      - 'MEA'         -> unit.mea / property.total_mea
      - 'Wohnflaeche' -> unit.square_meters / Summe aller aktiven Einheiten
      - sonst         -> Suche in unit_allocation_keys nach diesem key_type,
                         gültig für fiscal_year (Gültigkeitszeitraum, siehe
                         PROJECTPLAN.md); Einheiten ohne passenden Eintrag
                         bekommen 0.
    """
    units = list(
        db.scalars(
            select(Unit).where(Unit.property_id == property_.property_id, Unit.deleted_at.is_(None))
        )
    )
    if not units:
        return {}

    if allocation_key_type == "MEA":
        if not property_.total_mea:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Liegenschaft hat kein total_mea hinterlegt - Verteilung nach MEA nicht möglich.",
            )
        return {u.unit_id: float(u.mea or 0) / float(property_.total_mea) for u in units}

    if allocation_key_type == "Wohnflaeche":
        total_sqm = sum(float(u.square_meters) for u in units)
        if total_sqm == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Keine Wohnfläche hinterlegt.")
        return {u.unit_id: float(u.square_meters) / total_sqm for u in units}

    keys = list(
        db.scalars(
            select(UnitAllocationKey).where(
                UnitAllocationKey.property_id == property_.property_id,
                UnitAllocationKey.key_type == allocation_key_type,
                UnitAllocationKey.valid_from_year <= fiscal_year,
                or_(
                    UnitAllocationKey.valid_to_year.is_(None),
                    UnitAllocationKey.valid_to_year >= fiscal_year,
                ),
            )
        )
    )
    if not keys:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Kein Umlageschlüssel '{allocation_key_type}' für {fiscal_year} in dieser Liegenschaft hinterlegt.",
        )
    return {k.unit_id: float(k.numerator_value) / float(k.denominator_value) for k in keys}


def distribute_amount(
    db: Session, property_: Property, total_amount: float, allocation_key_type: str, fiscal_year: int
) -> list[tuple[int, float]]:
    """
    Liefert je Einheit den zugewiesenen Betrag - Summe entspricht exakt
    total_amount. Eine Rundungsdifferenz (durch 2-Nachkommastellen-Rundung je
    Einheit) geht an die Einheit mit dem größten Anteil - analog zum
    Soll=Haben-Prinzip bei Buchungen (02_triggers.sql).
    """
    fractions = compute_unit_fractions(db, property_, allocation_key_type, fiscal_year)
    participating = {uid: f for uid, f in fractions.items() if f > 0}
    if not participating:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Keine Einheit hat einen Anteil > 0 für diesen Verteilerschlüssel.",
        )

    allocated = {uid: round(total_amount * f, 2) for uid, f in participating.items()}
    diff = round(total_amount - sum(allocated.values()), 2)
    if diff != 0:
        target_uid = max(participating, key=lambda uid: participating[uid])
        allocated[target_uid] = round(allocated[target_uid] + diff, 2)

    return list(allocated.items())