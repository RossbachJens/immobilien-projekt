# backend/app/core/tenant_allocation.py
"""
Taggenaue Verteilung des bereits je Einheit berechneten Ist-Kosten-Anteils
(unit_settlement_shares) auf die Mietverträge, die im Abrechnungszeitraum
für diese Einheit bestanden (Chat vom 24.09.2026, "Taggenaue Aufteilung").

Nur umlagefähige Positionen (is_apportionable=True) betreffen Mieter - nicht
umlagefähige Kosten (Verwaltergebühr, Instandhaltungsrücklage etc.) bleiben
beim Eigentümer und werden hier nie aufgerufen (siehe
app/routers/settlement_periods.py::_replace_tenant_shares).

Leerstandstage (kein aktiver Vertrag) werden NICHT verteilt - dieser Anteil
verbleibt implizit beim Eigentümer, da kein Mieter dafür Nebenkosten zahlt.
Die Summe der zurückgegebenen Beträge entspricht dem übergebenen
total_amount daher nur, wenn die Einheit im gesamten Zeitraum durchgehend
vermietet war (Tage-Anteile summieren sich zu 1.0) - sonst bewusst weniger,
bewusst kein künstliches "Auffüllen" auf den vollen Betrag.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.zuordnungen import Lease


def compute_lease_day_fractions(
    db: Session, unit_id: int, period_start: date, period_end: date
) -> dict[int, float]:
    """Anteil (0..1) je Mietvertrag an den Tagen des Zeitraums, für die er
    für diese Einheit aktiv war. Ein Vertrag ohne end_date gilt bis
    period_end als aktiv. Verträge ohne Überschneidung mit dem Zeitraum
    tauchen im Ergebnis nicht auf."""
    total_days = (period_end - period_start).days + 1
    if total_days <= 0:
        return {}

    leases = list(
        db.scalars(
            select(Lease).where(
                Lease.unit_id == unit_id,
                Lease.deleted_at.is_(None),
                Lease.start_date <= period_end,
                (Lease.end_date.is_(None)) | (Lease.end_date >= period_start),
            )
        )
    )

    fractions: dict[int, float] = {}
    for lease in leases:
        overlap_start = max(lease.start_date, period_start)
        overlap_end = min(lease.end_date, period_end) if lease.end_date else period_end
        active_days = (overlap_end - overlap_start).days + 1
        if active_days > 0:
            fractions[lease.lease_id] = active_days / total_days
    return fractions


def distribute_amount_by_lease(
    total_amount: float, lease_fractions: dict[int, float]
) -> list[tuple[int, float]]:
    """Verteilt total_amount auf Verträge nach Tage-Anteil. Rundungsdifferenz
    geht - analog app/core/allocation.py::distribute_amount - an den Vertrag
    mit dem größten Anteil, aber NUR, wenn die Anteile die volle Periode
    abdecken (kein Leerstand): bei Leerstand ist die "fehlende" Differenz
    kein Rundungsfehler, sondern der bewusst unverteilte Leerstandsanteil,
    und darf nicht fälschlich einem Vertrag zugeschlagen werden."""
    participating = {lid: f for lid, f in lease_fractions.items() if f > 0}
    if not participating:
        return []

    allocated = {lid: round(total_amount * f, 2) for lid, f in participating.items()}

    fraction_sum = sum(participating.values())
    if fraction_sum >= 0.999999:
        diff = round(total_amount - sum(allocated.values()), 2)
        if diff != 0:
            target_lid = max(participating, key=lambda lid: participating[lid])
            allocated[target_lid] = round(allocated[target_lid] + diff, 2)

    return list(allocated.items())