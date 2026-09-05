# backend/app/services/settlement_pdf.py
"""
Erzeugt die Einzelabrechnung (Jahresabrechnung je Einheit) als PDF - orientiert
am Format der Muster-Datei "Einzelabrechnung 2024 Wohnung 4". Bewusst NICHT
vollständig nachgebildet: § 35a EStG-Bescheinigung und Rücklagendarstellung/
Vermögensaufstellung erfordern zusätzliche Datenmodellierung (Kategorisierung
der Positionen, Bestandsführung der Rücklagenkonten) und sind als offener
Punkt in PROJECTPLAN.md vermerkt. Dieser Export deckt den Kernteil ab:
Kostenübersicht, Einzelabrechnung mit Verteilung je Position, Abrechnungsspitze.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.abrechnung import SettlementPeriod, SettlementPosition, UnitSettlementShare, UnitSettlementSummary
from app.models.stammdaten import Owner, Property, Unit
from app.models.wirtschaftsplan import ResolutionCollection


def _eur(value: float | Decimal) -> str:
    """Deutsches Zahlenformat: 1.234,56 €."""
    formatted = f"{float(value):,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} €"


def _german_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _owner_display_name(owner: Owner) -> str:
    if owner.company_name:
        return owner.company_name
    return f"{owner.first_name or ''} {owner.last_name}".strip()


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

    info_data = [
        ["Objekt:", property_.name],
        ["", property_.address],
        ["Einheit:", unit.unit_number + (f" – {unit.floor}" if unit.floor else "")],
    ]
    info_table = Table(info_data, colWidths=[30 * mm, 120 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(info_table)
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

    doc.build(story)
    return buffer.getvalue()