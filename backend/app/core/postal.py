# backend/app/core/postal.py
"""
Gemeinsame Hilfsfunktionen für den Postversand (DIN 5008 Anschriftfeld) und
das Verwalter-Logo im Seitenkopf - genutzt sowohl vom ReportLab-basierten
Abrechnungs-PDF (app/services/settlement_pdf.py) als auch vom
WeasyPrint-basierten Einladungs-/Niederschrift-PDF (app/routers/meetings.py).

DIN 5008 Anschriftfeld (Fensterbriefumschlag DIN lang/C6-5), Form A:
  - linker Rand:  20 mm vom Blattrand
  - oberer Rand:  45 mm vom Blattrand
  - Breite:       85 mm
  - Höhe:         45 mm (Zusatz-/Vermerkzone + Anschriftzone)
Die erste Zeile im Feld (Zusatz-/Vermerkzone) trägt hier die
Rücksendeangabe (Absenderzeile) - Standard bei Fensterkuverts, damit ein
unzustellbarer Brief ohne separaten Absenderaufdruck zurückgeschickt werden
kann.

Logo-Kopfzone: 0-45 mm vom oberen Blattrand, also oberhalb des
Anschriftfelds - kollidiert unabhängig von der gewählten Position (hier:
oben rechts) nicht mit dem Fensterausschnitt.
"""
import base64
from dataclasses import dataclass

from app.models.stammdaten import Owner, Property

DIN5008_LEFT_MM = 20.0
DIN5008_TOP_MM = 45.0
DIN5008_WIDTH_MM = 85.0
DIN5008_HEIGHT_MM = 45.0

DIN5008_SENDER_OFFSET_MM = 3.0
DIN5008_RECIPIENT_OFFSET_MM = 9.0
DIN5008_LINE_HEIGHT_MM = 5.0

DIN5008_CONTENT_TOP_MM = DIN5008_TOP_MM + DIN5008_HEIGHT_MM + 5.0

# Logo oben rechts, oberhalb des Anschriftfelds - dieselben Werte werden
# sowohl vom ReportLab-Zeichner (settlement_pdf.py) als auch per CSS
# (meetings.py) verwendet, damit das Logo auf allen PDF-Typen optisch
# gleich sitzt.
LOGO_TOP_MM = 10.0
LOGO_RIGHT_MM = 20.0
LOGO_MAX_WIDTH_MM = 40.0
LOGO_MAX_HEIGHT_MM = 25.0
# Reine CSS-Deklarationen ohne geschweifte Klammern - lässt sich daher
# gefahrlos in Templates einsetzen, die selbst schon str.format()/f-strings
# mit CSS-Regeln (geschweifte Klammern!) verwenden.
LOGO_CSS_BOX = (
    f"top: {LOGO_TOP_MM}mm; right: {LOGO_RIGHT_MM}mm; "
    f"max-width: {LOGO_MAX_WIDTH_MM}mm; max-height: {LOGO_MAX_HEIGHT_MM}mm;"
)


@dataclass
class PostalAddress:
    """Fertig aufbereitete Anschrift für den Postversand. 'owner' wird
    mitgeführt, damit Aufrufer (z.B. für den Dateinamen) ohne erneute
    Abfrage darauf zugreifen können."""

    sender_line: str
    recipient_lines: list[str]
    owner: Owner


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