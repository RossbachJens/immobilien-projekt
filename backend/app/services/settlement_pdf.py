# backend/app/services/settlement_pdf.py
"""
Erzeugt die Einzelabrechnung (Jahresabrechnung je Einheit) als PDF - orientiert
am Format der Muster-Datei "Einzelabrechnung 2024 Wohnung 4". Die Rücklagen-
darstellung und Vermögensaufstellung ist seit Migration 0011 abgedeckt
(optionaler Abschnitt, nur gerendert, wenn der Router Daten übergibt - siehe
reserve_fund-Parameter). Die Bescheinigung i.S.d. § 35a EStG ist seit
Migration 0012 abgedeckt (optionaler Abschnitt, siehe
tax_certificate_positions-Parameter).
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.abrechnung import SettlementPeriod, SettlementPosition, UnitSettlementShare, UnitSettlementSummary
from app.models.stammdaten import Owner, Property, Unit
from app.models.wirtschaftsplan import ResolutionCollection


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
    optionaler Parameter von build_settlement_pdf, da nicht jede Abrechnung
    (noch) eine Rücklagendarstellung hat."""

    reserve_balance_start: float
    reserve_balance_start_unit_share: float
    reserve_balance_end: float
    reserve_balance_end_unit_share: float
    positions: list[ReserveFundPdfPosition]
    operating_balance_start: float
    operating_balance_end: float


@dataclass
class TaxCertificatePdfPosition:
    """Eine §35a-relevante Abrechnungsposition, für eine Einheit aufbereitet -
    siehe app/routers/settlement_periods.py::_build_tax_certificate_pdf_data.
    total_deductible_amount/unit_deductible_amount enthalten NUR den Lohn-/
    Fahrt-/Maschinenkostenanteil (SettlementPosition.deductible_amount),
    nicht die vollen Ist-Kosten der Position."""

    description: str
    tax_category: str  # 'haushaltsnahe_dienstleistung' | 'handwerkerleistung'
    is_apportionable: bool
    allocation_key_type: str
    total_deductible_amount: float
    unit_deductible_amount: float


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


def _owner_display_name(owner: Owner) -> str:
    if owner.company_name:
        return owner.company_name
    return f"{owner.first_name or ''} {owner.last_name}".strip()


def _allocation_key_label(key_type: str) -> str:
    if key_type == "MEA":
        return "Miteigentumsanteile"
    if key_type == "Wohnflaeche":
        return "Wohnfläche"
    return key_type


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
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Jahresabrechnung {settlement.fiscal_year} - {unit.unit_number}",
    )

    styles = getSampleStyleSheet()
    heading = ParagraphStyle("SettlementHeading", parent=styles["Heading1"], fontSize=14, spaceAfter=6)
    small = ParagraphStyle("SettlementSmall", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    body = styles["Normal"]

    def _info_table() -> Table:
        """Objekt/Einheit-Block - wird sowohl im Kopf der Einzelabrechnung als
        auch (falls vorhanden) am Anfang der Rücklagendarstellung/§35a-
        Bescheinigung gezeigt. Baut jedes Mal ein frisches Table-Flowable,
        da dasselbe Objekt nicht zweimal in einer reportlab-Story
        wiederverwendet werden sollte."""
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

    story = []

    # --- Absender/Empfänger-Block ---
    if owner is not None:
        story.append(Paragraph(_owner_display_name(owner), body))
        story.append(Paragraph(owner.street_and_number, body))
        story.append(Paragraph(f"{owner.postal_code or ''} {owner.city or ''}".strip(), body))
        story.append(Spacer(1, 8 * mm))

    story.append(
        Paragraph(
            f"Jahresabrechnung für Ihre Eigentumseinheit vom "
            f"{_german_date(settlement.period_start)} bis {_german_date(settlement.period_end)}",
            heading,
        )
    )

    story.append(_info_table())
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
                small,
            )
        )
    else:
        story.append(
            Paragraph(
                "Diese Abrechnung ist noch nicht beschlossen - die Abrechnungsspitze wird erst mit "
                "Beschlussfassung über die Jahresabrechnung fällig.",
                small,
            )
        )
    story.append(Spacer(1, 8 * mm))

    # --- Einzelabrechnung: Positionen ---
    story.append(Paragraph("Einzelabrechnung", styles["Heading2"]))

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
                heading,
            )
        )
        story.append(_info_table())
        story.append(Spacer(1, 4 * mm))

        total_mea = property_.total_mea
        unit_mea = unit.mea
        if total_mea is not None and unit_mea is not None:
            gesamt_mea_display, ihr_mea_display = _de_number(total_mea), _de_number(unit_mea)
        else:
            gesamt_mea_display, ihr_mea_display = "–", "–"

        category_marker = {"haushaltsnahe_dienstleistung": "2", "handwerkerleistung": "3"}

        def _tax_table(positions_subset: list[TaxCertificatePdfPosition]) -> Table:
            rows = [
                ["", "", "Verteilungsrelevante\nBeträge", "Verteilungs-\nschlüssel", "Gesamt-\nverteiler", "Ihr\nAnteil", "Ihr\nBetrag"]
            ]
            total_gesamt = 0.0
            total_ihr = 0.0
            for p in positions_subset:
                if p.allocation_key_type == "MEA":
                    row_gesamt, row_ihr = gesamt_mea_display, ihr_mea_display
                else:
                    row_gesamt, row_ihr = "–", "–"
                rows.append(
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
            rows.append(["", "Gesamt", _eur(total_gesamt), "", "", "", _eur(total_ihr)])

            table = Table(rows, colWidths=[7 * mm, 43 * mm, 25 * mm, 24 * mm, 18 * mm, 15 * mm, 20 * mm])
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
            story.append(Paragraph("Umlagefähige haushaltsnahe Dienstleistungen/Handwerkerleistungen", styles["Heading2"]))
            story.append(_tax_table(apportionable))
            story.append(Spacer(1, 4 * mm))

        if non_apportionable:
            story.append(
                Paragraph("Nicht umlagefähige haushaltsnahe Dienstleistungen/Handwerkerleistungen", styles["Heading2"])
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
                small,
            )
        )

    # --- Rücklagendarstellung & Vermögensaufstellung (optional) ---
    if reserve_fund is not None:
        story.append(PageBreak())
        story.append(
            Paragraph(
                "Rücklagendarstellung und Vermögensaufstellung<br/>"
                f"{_german_date(settlement.period_start)} - {_german_date(settlement.period_end)}",
                heading,
            )
        )
        story.append(_info_table())
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

        story.append(Paragraph("Vermögensaufstellung", styles["Heading2"]))
        story.append(
            Paragraph(
                "Bewirtschaftungskonto(en) - Salden nicht auf Einheiten verteilt, nur Gesamtsumme "
                "der Liegenschaft.",
                small,
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

    doc.build(story)
    return buffer.getvalue()