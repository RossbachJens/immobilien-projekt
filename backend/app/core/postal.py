# backend/app/core/postal.py
"""
Gemeinsame Hilfsfunktionen für den Postversand (DIN 5008 Anschriftfeld) und
das Verwalter-Logo im Seitenkopf - genutzt vom ReportLab-basierten
Abrechnungs-PDF (app/services/settlement_pdf.py, Eigentümer UND seit
24.09.2026 auch Mieter) sowie vom WeasyPrint-basierten
Einladungs-/Niederschrift-PDF (app/routers/meetings.py).
"""
import base64
from dataclasses import dataclass

from app.models.stammdaten import Owner, Property, Tenant

DIN5008_LEFT_MM = 20.0
DIN5008_TOP_MM = 45.0
DIN5008_WIDTH_MM = 85.0
DIN5008_HEIGHT_MM = 45.0

DIN5008_SENDER_OFFSET_MM = 3.0
DIN5008_RECIPIENT_OFFSET_MM = 9.0
DIN5008_LINE_HEIGHT_MM = 5.0

DIN5008_CONTENT_TOP_MM = DIN5008_TOP_MM + DIN5008_HEIGHT_MM + 5.0

LOGO_TOP_MM = 10.0
LOGO_RIGHT_MM = 20.0
LOGO_MAX_WIDTH_MM = 40.0
LOGO_MAX_HEIGHT_MM = 25.0
LOGO_CSS_BOX = (
    f"top: {LOGO_TOP_MM}mm; right: {LOGO_RIGHT_MM}mm; "
    f"max-width: {LOGO_MAX_WIDTH_MM}mm; max-height: {LOGO_MAX_HEIGHT_MM}mm;"
)


@dataclass
class PostalAddress:
    """Fertig aufbereitete Anschrift für den Postversand. 'owner'/'tenant'
    werden mitgeführt, damit Aufrufer ohne erneute Abfrage darauf zugreifen
    können - je nach Empfängertyp ist nur eines der beiden gesetzt."""

    sender_line: str
    recipient_lines: list[str]
    owner: Owner | None = None
    tenant: Tenant | None = None


def build_owner_postal_address(property_: Property, owner: Owner) -> PostalAddress:
    """
    Absenderzeile (Rücksendeangabe im Fenster) = Name/Adresse der
    Liegenschaft (aktuell keine separate Verwalter-Adresse im Datenmodell).

    Empfängerblock:
      - Firma gesetzt  -> Firmenname, optional 'z. Hd. <Person>'
      - sonst          -> Anrede (falls gepflegt) + Vor-/Nachname
      - danach immer   -> Straße, PLZ/Ort
    """
    sender_line = f"{property_.name} · {property_.address}"

    lines: list[str] = []
    if owner.company_name:
        lines.append(owner.company_name)
        person = f"{owner.first_name or ''} {owner.last_name}".strip()
        if person:
            lines.append(f"z. Hd. {person}")
    else:
        if owner.salutation:
            lines.append(owner.salutation)
        lines.append(f"{owner.first_name or ''} {owner.last_name}".strip())

    lines.append(owner.street_and_number)
    lines.append(f"{owner.postal_code or ''} {owner.city or ''}".strip())

    return PostalAddress(sender_line=sender_line, recipient_lines=lines, owner=owner)


def build_tenant_postal_address(property_: Property, tenant: Tenant) -> PostalAddress:
    """Wie build_owner_postal_address, für Mieter (Chat vom 24.09.2026,
    mieterseitige Betriebskostenabrechnung). Tenant hat weder salutation
    noch company_name - der Empfängerblock ist entsprechend einfacher."""
    sender_line = f"{property_.name} · {property_.address}"

    lines: list[str] = [f"{tenant.first_name} {tenant.last_name}".strip()]
    lines.append(tenant.street_and_number)
    lines.append(f"{tenant.postal_code or ''} {tenant.city or ''}".strip())

    return PostalAddress(sender_line=sender_line, recipient_lines=lines, tenant=tenant)


def greeting_for_owner(owner: Owner) -> str:
    """Anredezeile im Brieftext (nicht im Adressfeld)."""
    if owner.company_name and not (owner.first_name or owner.last_name):
        return "Sehr geehrte Damen und Herren,"
    if owner.salutation == "Herr":
        return f"Sehr geehrter Herr {owner.last_name},"
    if owner.salutation == "Frau":
        return f"Sehr geehrte Frau {owner.last_name},"
    name = f"{owner.first_name or ''} {owner.last_name}".strip()
    return f"Sehr geehrte/r {name}," if name else "Sehr geehrte Damen und Herren,"


def greeting_for_tenant(tenant: Tenant) -> str:
    """Wie greeting_for_owner, für Mieter - ohne Anrede-/Firmenfeld."""
    name = f"{tenant.first_name} {tenant.last_name}".strip()
    return f"Sehr geehrte/r {name}," if name else "Sehr geehrte Damen und Herren,"


def logo_data_uri(property_: Property) -> str | None:
    """Base64-Data-URI des Liegenschafts-Logos für WeasyPrint-Templates -
    eingebettet statt per <img src="/properties/{id}/logo">, damit
    WeasyPrint beim PDF-Rendern keinen zusätzlichen (authentifizierten)
    HTTP-Request gegen die eigene API braucht. None, wenn kein Logo
    hinterlegt ist."""
    if not property_.logo_content or not property_.logo_mime_type:
        return None
    encoded = base64.b64encode(property_.logo_content).decode("ascii")
    return f"data:{property_.logo_mime_type};base64,{encoded}"