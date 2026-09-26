# backend/app/services/settlement_pdf.py
"""
Erzeugt die Einzelabrechnung (Jahresabrechnung je Einheit) als PDF - orientiert
am Format der Muster-Datei "Einzelabrechnung 2024 Wohnung 4". Seit dem
Postversand-Feature trägt jeder Brief ein DIN-5008-Anschriftfeld an fester
Position (siehe app/core/postal.py) statt der Empfängerdaten im normalen
Textfluss - Technik: BaseDocTemplate mit einem onPage-Callback, der bei
jedem Seitenbeginn die 'scharf geschaltete' Adresse zeichnet
(Canvas-Koordinaten sind pro Seite neu, daher funktioniert das identisch für
Einzelbrief und Sammel-PDF). Ein unsichtbares Flowable (_ArmAddress) setzt
die jeweils nächste Adresse, bevor ein PageBreak() zum nächsten Empfänger
führt.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.core.postal import (
    DIN5008_CONTENT_TOP_MM,
    DIN5008_LEFT_MM,
    DIN5008_LINE_HEIGHT_MM,
    DIN5008_RECIPIENT_OFFSET_MM,
    DIN5008_SENDER_OFFSET_MM,
    DIN5008_TOP_MM,
    PostalAddress,
    build_owner_postal_address,
)
from app.models.abrechnung import (
    LeaseSettlementSummary,
    SettlementPeriod,
    SettlementPosition,
    UnitSettlementShare,
    UnitSettlementSummary,
    UnitSettlementTenantShare,
)
from app.models.stammdaten import Owner, Property, Tenant, Unit
from app.models.zuordnungen import Lease
from app.core.postal import build_tenant_postal_address
from app.models.wirtschaftsplan import ResolutionCollection

LEFT_MARGIN_MM = 20.0
RIGHT_MARGIN_MM = 20.0
BOTTOM_MARGIN_MM = 18.0
# Groß genug, um das DIN-5008-Anschriftfeld auf jeder Seite freizuhalten -
# bewusst einheitlich für alle Seiten eines Briefs (auch Folgeseiten wie
# §35a/Rücklagendarstellung), statt zwei unterschiedliche Seitenvorlagen zu
# pflegen. Kostet etwas Weißraum auf Folgeseiten, hält den Code aber
# deutlich einfacher.
TOP_MARGIN_MM = DIN5008_CONTENT_TOP_MM

_STYLES = getSampleStyleSheet()
_HEADING_STYLE = ParagraphStyle("SettlementHeading", parent=_STYLES["Heading1"], fontSize=14, spaceAfter=6)
_HEADING2_STYLE = _STYLES["Heading2"]
_SMALL_STYLE = ParagraphStyle("SettlementSmall", parent=_STYLES["Normal"], fontSize=9, textColor=colors.grey)
_BODY_STYLE = _STYLES["Normal"]
# backend/app/services/settlement_pdf.py — Imports ergänzen
from reportlab.lib.utils import ImageReader

from app.core.postal import (
    DIN5008_CONTENT_TOP_MM,
    DIN5008_LEFT_MM,
    DIN5008_LINE_HEIGHT_MM,
    DIN5008_RECIPIENT_OFFSET_MM,
    DIN5008_SENDER_OFFSET_MM,
    DIN5008_TOP_MM,
    LOGO_MAX_HEIGHT_MM,
    LOGO_MAX_WIDTH_MM,
    LOGO_RIGHT_MM,
    LOGO_TOP_MM,
    PostalAddress,
    build_owner_postal_address,
)

@dataclass
class ReserveFundPdfPosition:
    """Eine Bewegungszeile der Rücklagendarstellung, bereits für diese eine
    Einheit aufbereitet (unit_share) - siehe
    app/routers/settlement_periods.py::_build_reserve_fund_pdf_data."""

    movement_type_label: str
    description: str | None
    allocation_key_type: str
    actual_amount: float
    unit_share: float


@dataclass
class ReserveFundPdfData:
    """Bündelt Rücklagendarstellung + Vermögensaufstellung für eine Einheit -
    optionaler Parameter, da nicht jede Abrechnung (noch) eine
    Rücklagendarstellung hat."""

    reserve_balance_start: float
    reserve_balance_start_unit_share: float
    reserve_balance_end: float
    reserve_balance_end_unit_share: float
    positions: list[ReserveFundPdfPosition]
    operating_balance_start: float
    operating_balance_end: float


@dataclass
class TaxCertificatePdfPosition:
    """Eine §35a-relevante Abrechnungsposition, für eine Einheit aufbereitet."""

    description: str
    tax_category: str  # 'haushaltsnahe_dienstleistung' | 'handwerkerleistung'
    is_apportionable: bool
    allocation_key_type: str
    total_deductible_amount: float
    unit_deductible_amount: float


@dataclass
class UnitLetterInput:
    """Eingabedaten für EINEN Brief im Sammel-PDF (siehe
    build_settlement_pdf_batch) - identisch zu den Einzelparametern von
    build_settlement_pdf, nur gebündelt für die Schleife über alle Einheiten."""

    unit: Unit
    owner: Owner | None
    positions: list[SettlementPosition]
    accounts_by_position: dict[int, list[int]]
    shares_by_position: dict[int, UnitSettlementShare]
    summary: UnitSettlementSummary | None
    reserve_fund: ReserveFundPdfData | None
    tax_certificate_positions: list[TaxCertificatePdfPosition]


def _de_number(value: float | Decimal) -> str:
    """Deutsches Zahlenformat ohne Einheit: 1.234,56."""
    formatted = f"{float(value):,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def _eur(value: float | Decimal) -> str:
    """Deutsches Zahlenformat: 1.234,56 €."""
    return f"{_de_number(value)} €"


def _german_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _allocation_key_label(key_type: str) -> str:
    if key_type == "MEA":
        return "Miteigentumsanteile"
    if key_type == "Wohnflaeche":
        return "Wohnfläche"
    return key_type


# --------------------------------------------------------------------
# DIN-5008-Anschriftfeld: Zeichenlogik + Seiten-Callback
# --------------------------------------------------------------------

def _draw_din5008_address(canv, page_height: float, address: PostalAddress) -> None:
    canv.saveState()
    left = DIN5008_LEFT_MM * mm
    field_top = page_height - DIN5008_TOP_MM * mm

    canv.setFont("Helvetica", 7)
    sender_y = field_top - DIN5008_SENDER_OFFSET_MM * mm
    canv.drawString(left, sender_y, address.sender_line)
    canv.setLineWidth(0.3)
    canv.line(left, sender_y - 1, left + 70 * mm, sender_y - 1)

    canv.setFont("Helvetica", 10)
    y = field_top - DIN5008_RECIPIENT_OFFSET_MM * mm
    for line in address.recipient_lines:
        if line:
            canv.drawString(left, y, line)
        y -= DIN5008_LINE_HEIGHT_MM * mm
    canv.restoreState()

def _draw_logo(canv, page_width: float, page_height: float, property_: Property) -> None:
    if not property_.logo_content:
        return
    reader = ImageReader(BytesIO(property_.logo_content))
    iw, ih = reader.getSize()
    if not iw or not ih:
        return
    max_w, max_h = LOGO_MAX_WIDTH_MM * mm, LOGO_MAX_HEIGHT_MM * mm
    scale = min(max_w / iw, max_h / ih, 1.0)  # nie über Originalgröße hinaus vergrößern
    draw_w, draw_h = iw * scale, ih * scale
    x = page_width - LOGO_RIGHT_MM * mm - draw_w
    y = page_height - LOGO_TOP_MM * mm - draw_h
    canv.drawImage(reader, x, y, width=draw_w, height=draw_h, mask="auto")
    
def _on_page(canv, doc_) -> None:
    """Wird von reportlab bei JEDEM Seitenbeginn aufgerufen. Zeichnet Logo
    und/oder Adresse nur, wenn sie über _ArmLetterStart für genau diese
    Seite 'scharf geschaltet' wurden - Folgeseiten desselben Briefs (z.B.
    §35a-Abschnitt) bleiben dadurch ohne Briefkopf."""
    if getattr(doc_, "_pending_logo", False):
        _draw_logo(canv, doc_.pagesize[0], doc_.pagesize[1], doc_._property)
        doc_._pending_logo = False

    address = getattr(doc_, "_pending_address", None)
    if address is not None:
        _draw_din5008_address(canv, doc_.pagesize[1], address)
        doc_._pending_address = None


class _ArmLetterStart(Flowable):
    """Reines Seiteneffekt-Flowable ohne eigene Darstellung/Platzbedarf:
    setzt auf dem Dokument-Objekt, dass beim NÄCHSTEN Seitenbeginn
    (onPage-Callback, s.o.) Logo und - falls vorhanden - Adresse gezeichnet
    werden sollen. So lässt sich im selben BaseDocTemplate pro Empfänger
    ein neuer Briefkopf einsteuern, ohne mehrere Seitenvorlagen zu
    brauchen."""

    def __init__(self, doc_, address: PostalAddress | None) -> None:
        super().__init__()
        self._doc = doc_
        self._address = address
        self.width = 0
        self.height = 0

    def wrap(self, availWidth, availHeight):  # noqa: N803 - reportlab-Signatur
        return (0, 0)

    def draw(self) -> None:
        self._doc._pending_address = self._address
        self._doc._pending_logo = True


def _render_letters(
    pdf_title: str, entries: list[tuple[PostalAddress | None, list]], property_: Property
) -> bytes:
    """Baut EIN PDF aus mehreren Brief-Abschnitten (entries: Adresse +
    Flowables je Empfänger). Ein Eintrag => Einzelbrief, mehrere => Sammel-
    PDF für den Kuvertierlauf. 'property_' liefert das Logo (gleich für
    alle Briefe dieses Exports)."""
    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=LEFT_MARGIN_MM * mm,
        rightMargin=RIGHT_MARGIN_MM * mm,
        topMargin=TOP_MARGIN_MM * mm,
        bottomMargin=BOTTOM_MARGIN_MM * mm,
        title=pdf_title,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="letter")
    doc.addPageTemplates([PageTemplate(id="Letter", frames=[frame], onPage=_on_page)])

    doc._property = property_
    # Seite 1 startet, BEVOR das erste Flowable verarbeitet wird - Logo und
    # Adresse des ersten Empfängers daher direkt am doc setzen statt über
    # ein Flowable.
    doc._pending_address = entries[0][0]
    doc._pending_logo = True

    story: list = []
    for index, (address, flowables) in enumerate(entries):
        if index > 0:
            story.append(_ArmLetterStart(doc, address))
            story.append(PageBreak())
        story.extend(flowables)

    doc.build(story)
    return buffer.getvalue()


def _info_table(property_: Property, unit: Unit) -> Table:
    """Objekt/Einheit-Block - wird sowohl im Kopf der Einzelabrechnung als
    auch (falls vorhanden) am Anfang der Rücklagendarstellung/§35a-
    Bescheinigung gezeigt. Baut jedes Mal ein frisches Table-Flowable, da
    dasselbe Objekt nicht zweimal in einer reportlab-Story wiederverwendet
    werden sollte."""
    info_data = [
        ["Objekt:", property_.name],
        ["", property_.address],
        ["Einheit:", unit.unit_number + (f" – {unit.floor}" if unit.floor else "")],
    ]
    table = Table(info_data, colWidths=[30 * mm, 120 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def _letter_flowables(
    *,
    settlement: SettlementPeriod,
    property_: Property,
    unit: Unit,
    positions: list[SettlementPosition],
    accounts_by_position: dict[int, list[int]],
    shares_by_position: dict[int, UnitSettlementShare],
    summary: UnitSettlementSummary | None,
    resolution: ResolutionCollection | None,
    reserve_fund: ReserveFundPdfData | None,
    tax_certificate_positions: list[TaxCertificatePdfPosition] | None,
) -> list:
    """Baut die Flowables EINES Briefs (ohne Dokument-Setup/Adresse - die
    Anschrift wird separat über das DIN-5008-Anschriftfeld gezeichnet, s.o.)."""
    story: list = []

    story.append(
        Paragraph(
            f"Jahresabrechnung für Ihre Eigentumseinheit vom "
            f"{_german_date(settlement.period_start)} bis {_german_date(settlement.period_end)}",
            _HEADING_STYLE,
        )
    )

    story.append(_info_table(property_, unit))
    story.append(Spacer(1, 6 * mm))

    # --- Zusammenfassung ---
    total_costs = float(summary.total_actual_costs) if summary else 0.0
    total_prepayments = float(summary.total_prepayments) if summary else 0.0
    balance = float(summary.balance) if summary else 0.0
    balance_label = "Nachzahlung" if balance > 0 else "Erstattung"

    summary_data = [
        ["Bewirtschaftungskosten gem. Einzelabrechnung", _eur(total_costs)],
        ["Abzüglich geleistetes Hausgeld", _eur(total_prepayments)],
        [f"Abrechnungsspitze ({balance_label})", _eur(abs(balance))],
    ]
    summary_table = Table(summary_data, colWidths=[110 * mm, 40 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("LINEABOVE", (0, 2), (-1, 2), 0.5, colors.black),
                ("TOPPADDING", (0, 2), (-1, 2), 4),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 4 * mm))

    if resolution is not None:
        story.append(
            Paragraph(
                f"Die Abrechnungsspitze wurde durch Beschluss vom {_german_date(resolution.resolution_date)} "
                f"(Lfd. Nr. {resolution.lfd_nr}) fällig gestellt.",
                _SMALL_STYLE,
            )
        )
    else:
        story.append(
            Paragraph(
                "Diese Abrechnung ist noch nicht beschlossen - die Abrechnungsspitze wird erst mit "
                "Beschlussfassung über die Jahresabrechnung fällig.",
                _SMALL_STYLE,
            )
        )
    story.append(Spacer(1, 8 * mm))

    # --- Einzelabrechnung: Positionen ---
    story.append(Paragraph("Einzelabrechnung", _HEADING2_STYLE))

    rows = [["Kostenart", "Verteilerschlüssel", "Gesamtbetrag", "Ihr Anteil"]]
    for position in positions:
        share = shares_by_position.get(position.position_id)
        allocated = float(share.allocated_actual_amount) if share else 0.0
        account_ids = accounts_by_position.get(position.position_id, [])
        fallback_label = f"Konten {', '.join(str(a) for a in account_ids)}" if account_ids else "Position"
        label = position.description or fallback_label
        apportion_note = "" if position.is_apportionable else " (nicht umlagefähig)"
        rows.append(
            [label + apportion_note, position.allocation_key_type, _eur(position.actual_amount), _eur(allocated)]
        )
    rows.append(["Summe", "", "", _eur(total_costs)])

    position_table = Table(rows, colWidths=[65 * mm, 35 * mm, 30 * mm, 30 * mm])
    position_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
                ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(position_table)

    # --- Bescheinigung § 35a EStG (optional) ---
    if tax_certificate_positions:
        story.append(PageBreak())
        story.append(
            Paragraph(
                f"Bescheinigung i.S.d. § 35a EStG für die Abrechnung<br/>"
                f"{_german_date(settlement.period_start)} - {_german_date(settlement.period_end)}",
                _HEADING_STYLE,
            )
        )
        story.append(_info_table(property_, unit))
        story.append(Spacer(1, 4 * mm))

        total_mea = property_.total_mea
        unit_mea = unit.mea
        if total_mea is not None and unit_mea is not None:
            gesamt_mea_display, ihr_mea_display = _de_number(total_mea), _de_number(unit_mea)
        else:
            gesamt_mea_display, ihr_mea_display = "–", "–"

        category_marker = {"haushaltsnahe_dienstleistung": "2", "handwerkerleistung": "3"}

        def _tax_table(positions_subset: list[TaxCertificatePdfPosition]) -> Table:
            rows_ = [
                ["", "", "Verteilungsrelevante\nBeträge", "Verteilungs-\nschlüssel", "Gesamt-\nverteiler", "Ihr\nAnteil", "Ihr\nBetrag"]
            ]
            total_gesamt = 0.0
            total_ihr = 0.0
            for p in positions_subset:
                if p.allocation_key_type == "MEA":
                    row_gesamt, row_ihr = gesamt_mea_display, ihr_mea_display
                else:
                    row_gesamt, row_ihr = "–", "–"
                rows_.append(
                    [
                        category_marker.get(p.tax_category, ""),
                        p.description,
                        _eur(p.total_deductible_amount),
                        _allocation_key_label(p.allocation_key_type),
                        row_gesamt,
                        row_ihr,
                        _eur(p.unit_deductible_amount),
                    ]
                )
                total_gesamt += p.total_deductible_amount
                total_ihr += p.unit_deductible_amount
            rows_.append(["", "Gesamt", _eur(total_gesamt), "", "", "", _eur(total_ihr)])

            table = Table(rows_, colWidths=[7 * mm, 43 * mm, 25 * mm, 24 * mm, 18 * mm, 15 * mm, 20 * mm])
            table.setStyle(
                TableStyle(
                    [
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
                        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                        ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            return table

        apportionable = [p for p in tax_certificate_positions if p.is_apportionable]
        non_apportionable = [p for p in tax_certificate_positions if not p.is_apportionable]

        if apportionable:
            story.append(Paragraph("Umlagefähige haushaltsnahe Dienstleistungen/Handwerkerleistungen", _HEADING2_STYLE))
            story.append(_tax_table(apportionable))
            story.append(Spacer(1, 4 * mm))

        if non_apportionable:
            story.append(
                Paragraph("Nicht umlagefähige haushaltsnahe Dienstleistungen/Handwerkerleistungen", _HEADING2_STYLE)
            )
            story.append(_tax_table(non_apportionable))
            story.append(Spacer(1, 4 * mm))

        story.append(
            Paragraph(
                "2 § 35a Absatz 2 EStG Haushaltsnahe Dienstleistungen<br/>"
                "3 § 35a Absatz 3 EStG Handwerkerleistungen<br/><br/>"
                "Bescheinigt wird ausschließlich der Lohn-, Fahrt- und Maschinenkostenanteil - "
                "Materialkosten sind nach § 35a EStG nicht begünstigt und in den ausgewiesenen "
                "Beträgen nicht enthalten.",
                _SMALL_STYLE,
            )
        )

    # --- Rücklagendarstellung & Vermögensaufstellung (optional) ---
    if reserve_fund is not None:
        story.append(PageBreak())
        story.append(
            Paragraph(
                "Rücklagendarstellung und Vermögensaufstellung<br/>"
                f"{_german_date(settlement.period_start)} - {_german_date(settlement.period_end)}",
                _HEADING_STYLE,
            )
        )
        story.append(_info_table(property_, unit))
        story.append(Spacer(1, 6 * mm))

        total_mea = property_.total_mea
        unit_mea = unit.mea
        if total_mea is not None and unit_mea is not None:
            gesamt_mea_display, ihr_mea_display = _de_number(total_mea), _de_number(unit_mea)
        else:
            gesamt_mea_display, ihr_mea_display = "–", "–"

        reserve_rows = [
            ["Beschreibung", "Beträge", "Gesamtverteiler", "Ihr Anteil", "Verteilerschlüssel", "Ihr Betrag"]
        ]
        reserve_rows.append(
            [
                "Rücklagenbestand zum 01.01.",
                _eur(reserve_fund.reserve_balance_start),
                gesamt_mea_display,
                ihr_mea_display,
                "Miteigentumsanteile",
                _eur(reserve_fund.reserve_balance_start_unit_share),
            ]
        )
        for position in reserve_fund.positions:
            label = position.movement_type_label + (
                f" ({position.description})" if position.description else ""
            )
            if position.allocation_key_type == "MEA":
                row_gesamt, row_ihr = gesamt_mea_display, ihr_mea_display
            else:
                row_gesamt, row_ihr = "–", "–"
            reserve_rows.append(
                [
                    label,
                    _eur(position.actual_amount),
                    row_gesamt,
                    row_ihr,
                    _allocation_key_label(position.allocation_key_type),
                    _eur(position.unit_share),
                ]
            )
        reserve_rows.append(
            [
                "Rücklagenbestand zum 31.12.",
                _eur(reserve_fund.reserve_balance_end),
                gesamt_mea_display,
                ihr_mea_display,
                "Miteigentumsanteile",
                _eur(reserve_fund.reserve_balance_end_unit_share),
            ]
        )

        reserve_table = Table(
            reserve_rows, colWidths=[45 * mm, 22 * mm, 22 * mm, 18 * mm, 30 * mm, 22 * mm]
        )
        reserve_table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
                    ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(reserve_table)
        story.append(Spacer(1, 8 * mm))

        story.append(Paragraph("Vermögensaufstellung", _HEADING2_STYLE))
        story.append(
            Paragraph(
                "Bewirtschaftungskonto(en) - Salden nicht auf Einheiten verteilt, nur Gesamtsumme "
                "der Liegenschaft.",
                _SMALL_STYLE,
            )
        )
        story.append(Spacer(1, 2 * mm))

        asset_rows = [
            ["Bewirtschaftungskonto 01.01.", _eur(reserve_fund.operating_balance_start)],
            ["Bewirtschaftungskonto 31.12.", _eur(reserve_fund.operating_balance_end)],
        ]
        asset_table = Table(asset_rows, colWidths=[80 * mm, 40 * mm])
        asset_table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(asset_table)

    return story


def build_settlement_pdf(
    *,
    settlement: SettlementPeriod,
    property_: Property,
    unit: Unit,
    owner: Owner | None,
    positions: list[SettlementPosition],
    accounts_by_position: dict[int, list[int]],
    shares_by_position: dict[int, UnitSettlementShare],
    summary: UnitSettlementSummary | None,
    resolution: ResolutionCollection | None,
    reserve_fund: ReserveFundPdfData | None = None,
    tax_certificate_positions: list[TaxCertificatePdfPosition] | None = None,
) -> bytes:
    """Einzelexport - ein adressierter Brief für eine Einheit/einen
    Eigentümer. Gleiche Signatur wie vor dem DIN-5008-Umbau - Aufrufer
    (app/routers/settlement_periods.py) bleiben unverändert."""
    postal_address = build_owner_postal_address(property_, owner) if owner is not None else None
    flowables = _letter_flowables(
        settlement=settlement,
        property_=property_,
        unit=unit,
        positions=positions,
        accounts_by_position=accounts_by_position,
        shares_by_position=shares_by_position,
        summary=summary,
        resolution=resolution,
        reserve_fund=reserve_fund,
        tax_certificate_positions=tax_certificate_positions,
    )
    return _render_letters(
        f"Jahresabrechnung {settlement.fiscal_year} - {unit.unit_number}", [(postal_address, flowables)], property_
    )


def build_settlement_pdf_batch(
    *,
    settlement: SettlementPeriod,
    property_: Property,
    resolution: ResolutionCollection | None,
    letters: list[UnitLetterInput],
) -> bytes:
    """Sammelexport - ein PDF mit einem adressierten Brief je Einheit
    (eigene Seite(n), eigenes DIN-5008-Anschriftfeld), für den Druck-/
    Kuvertierlauf. Einheiten ohne aktuell zugeordneten Eigentümer werden
    stillschweigend übersprungen - ein Postversand ohne Empfänger ist nicht
    sinnvoll."""
    entries = []
    for item in letters:
        if item.owner is None:
            continue
        postal_address = build_owner_postal_address(property_, item.owner)
        flowables = _letter_flowables(
            settlement=settlement,
            property_=property_,
            unit=item.unit,
            positions=item.positions,
            accounts_by_position=item.accounts_by_position,
            shares_by_position=item.shares_by_position,
            summary=item.summary,
            resolution=resolution,
            reserve_fund=item.reserve_fund,
            tax_certificate_positions=item.tax_certificate_positions,
        )
        entries.append((postal_address, flowables))

    if not entries:
        raise ValueError("Keine Einheit mit zugeordnetem Eigentümer für den Sammelversand gefunden.")

    return _render_letters(f"Jahresabrechnungen {settlement.fiscal_year} - Sammelversand", entries, property_)

# backend/app/services/settlement_pdf.py — am Dateiende anfügen
@dataclass
class TenantLetterInput:
    """Eingabedaten für EINEN Brief im mieterseitigen Sammel-PDF - analog
    UnitLetterInput, aber je Mietvertrag statt je Einheit/Eigentümer (Chat
    vom 24.09.2026)."""

    lease: Lease
    tenant: Tenant
    unit: Unit
    positions: list[SettlementPosition]
    tenant_shares_by_position: dict[int, UnitSettlementTenantShare]
    summary: LeaseSettlementSummary | None


def _tenant_letter_flowables(
    *,
    settlement: SettlementPeriod,
    property_: Property,
    unit: Unit,
    positions: list[SettlementPosition],
    tenant_shares_by_position: dict[int, UnitSettlementTenantShare],
    summary: LeaseSettlementSummary | None,
) -> list:
    """Baut die Flowables EINES mieterseitigen Briefs. Enthält bewusst nur
    umlagefähige Positionen (Materialisierung von 'Bei Mietern sind die
    umlagefähigen Kosten mit dem gleichen Schlüssel wie beim Eigentümer
    abzurechnen', Chat vom 24.09.2026) - kein §35a-Abschnitt (steuerlicher
    Vorteil ausschließlich für Eigentümer) und keine Rücklagendarstellung
    (Instandhaltungsrücklage betrifft nur das Eigentumsverhältnis). Anders
    als beim Eigentümer-Brief fehlt der Hinweis auf die Fälligkeit "mit
    Beschlussfassung über die Jahresabrechnung" - das ist WEG-Innenrecht
    und für das Mietverhältnis (§ 556 BGB) ohne Bedeutung."""
    story: list = []

    story.append(
        Paragraph(
            f"Betriebskostenabrechnung für Ihre Mietwohnung vom "
            f"{_german_date(settlement.period_start)} bis {_german_date(settlement.period_end)}",
            _HEADING_STYLE,
        )
    )

    story.append(_info_table(property_, unit))
    story.append(Spacer(1, 6 * mm))

    total_costs = float(summary.total_actual_costs) if summary else 0.0
    total_prepayments = float(summary.total_prepayments) if summary else 0.0
    balance = float(summary.balance) if summary else 0.0
    balance_label = "Nachzahlung" if balance > 0 else "Erstattung"

    summary_data = [
        ["Umlagefähige Betriebskosten gem. Abrechnung", _eur(total_costs)],
        ["Abzüglich geleistete Nebenkostenvorauszahlung", _eur(total_prepayments)],
        [f"Abrechnungsergebnis ({balance_label})", _eur(abs(balance))],
    ]
    summary_table = Table(summary_data, colWidths=[110 * mm, 40 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("LINEABOVE", (0, 2), (-1, 2), 0.5, colors.black),
                ("TOPPADDING", (0, 2), (-1, 2), 4),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            "Die Fälligkeit richtet sich nach den Regelungen Ihres Mietvertrags.",
            _SMALL_STYLE,
        )
    )
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Kostenaufstellung", _HEADING2_STYLE))

    apportionable_positions = [p for p in positions if p.is_apportionable]
    rows = [["Kostenart", "Verteilerschlüssel", "Gesamtbetrag", "Ihr Anteil"]]
    for position in apportionable_positions:
        share = tenant_shares_by_position.get(position.position_id)
        allocated = float(share.allocated_amount) if share else 0.0
        label = position.description or "Position"
        rows.append([label, position.allocation_key_type, _eur(position.actual_amount), _eur(allocated)])
    rows.append(["Summe", "", "", _eur(total_costs)])

    position_table = Table(rows, colWidths=[65 * mm, 35 * mm, 30 * mm, 30 * mm])
    position_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
                ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(position_table)

    return story


def build_tenant_settlement_pdf(
    *,
    settlement: SettlementPeriod,
    property_: Property,
    unit: Unit,
    tenant: Tenant,
    positions: list[SettlementPosition],
    tenant_shares_by_position: dict[int, UnitSettlementTenantShare],
    summary: LeaseSettlementSummary | None,
) -> bytes:
    """Einzelexport für einen Mietvertrag - ein adressierter Brief."""
    postal_address = build_tenant_postal_address(property_, tenant)
    flowables = _tenant_letter_flowables(
        settlement=settlement,
        property_=property_,
        unit=unit,
        positions=positions,
        tenant_shares_by_position=tenant_shares_by_position,
        summary=summary,
    )
    return _render_letters(
        f"Betriebskostenabrechnung {settlement.fiscal_year} - {unit.unit_number}",
        [(postal_address, flowables)],
        property_,
    )


def build_tenant_settlement_pdf_batch(
    *,
    settlement: SettlementPeriod,
    property_: Property,
    letters: list[TenantLetterInput],
) -> bytes:
    """Sammelexport - ein Brief je im Zeitraum aktivem Mietvertrag."""
    entries = []
    for item in letters:
        postal_address = build_tenant_postal_address(property_, item.tenant)
        flowables = _tenant_letter_flowables(
            settlement=settlement,
            property_=property_,
            unit=item.unit,
            positions=item.positions,
            tenant_shares_by_position=item.tenant_shares_by_position,
            summary=item.summary,
        )
        entries.append((postal_address, flowables))

    if not entries:
        raise ValueError("Keine Mietverträge für den Sammelversand gefunden.")

    return _render_letters(
        f"Betriebskostenabrechnungen {settlement.fiscal_year} - Sammelversand", entries, property_
    )