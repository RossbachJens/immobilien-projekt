# backend/app/routers/meetings.py
import io
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from weasyprint import HTML

from app.core.access import accessible_property_ids
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.meetings import MeetingAgendaItem, OwnerMeeting
from app.models.stammdaten import Property, User
from app.schemas.meetings import (
    AgendaItemCreate,
    AgendaItemOut,
    AgendaItemUpdate,
    MeetingCreate,
    MeetingOut,
    MeetingUpdate,
)
from app.models.wirtschaftsplan import ResolutionCollection

router = APIRouter(prefix="/meetings", tags=["meetings"])


def _require_write_role(current_user: User) -> None:
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Versammlungen pflegen.",
        )


def _require_read_access(current_user: User) -> None:
    if resolve_role(current_user) == "mieter":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Mieter haben keinen Zugriff auf Eigentümerversammlungen."
        )


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> Property:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    return property_


def _get_readable_meeting(db: Session, meeting_id: int, current_user: User) -> OwnerMeeting:
    meeting = db.get(OwnerMeeting, meeting_id)
    if meeting is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versammlung nicht gefunden")
    _check_property_accessible(db, meeting.property_id, current_user)
    return meeting


def _load_agenda_items(db: Session, meeting_id: int) -> list[MeetingAgendaItem]:
    return list(
        db.scalars(
            select(MeetingAgendaItem)
            .where(MeetingAgendaItem.meeting_id == meeting_id)
            .order_by(MeetingAgendaItem.position)
        )
    )


@router.get("", response_model=list[MeetingOut])
def list_meetings(
    property_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OwnerMeeting]:
    _require_read_access(current_user)
    query = select(OwnerMeeting)

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None:
        query = query.where(OwnerMeeting.property_id.in_(property_ids))
    if property_id is not None:
        _check_property_accessible(db, property_id, current_user)
        query = query.where(OwnerMeeting.property_id == property_id)

    query = query.order_by(OwnerMeeting.meeting_date.desc())
    return list(db.scalars(query))


@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
def create_meeting(
    payload: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OwnerMeeting:
    _require_write_role(current_user)
    _check_property_accessible(db, payload.property_id, current_user)

    meeting = OwnerMeeting(**payload.model_dump(), created_by=current_user.user_id)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.patch("/{meeting_id}", response_model=MeetingOut)
def update_meeting(
    meeting_id: int,
    payload: MeetingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OwnerMeeting:
    _require_write_role(current_user)
    meeting = _get_readable_meeting(db, meeting_id, current_user)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(meeting, field, value)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.get("/{meeting_id}/agenda-items", response_model=list[AgendaItemOut])
def list_agenda_items(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MeetingAgendaItem]:
    _require_read_access(current_user)
    _get_readable_meeting(db, meeting_id, current_user)
    return _load_agenda_items(db, meeting_id)


@router.post(
    "/{meeting_id}/agenda-items", response_model=AgendaItemOut, status_code=status.HTTP_201_CREATED
)
def create_agenda_item(
    meeting_id: int,
    payload: AgendaItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeetingAgendaItem:
    _require_write_role(current_user)
    _get_readable_meeting(db, meeting_id, current_user)

    item = MeetingAgendaItem(meeting_id=meeting_id, **payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"TOP-Nummer {payload.position} ist bereits vergeben."
        ) from exc

    db.refresh(item)
    return item


@router.patch("/{meeting_id}/agenda-items/{item_id}", response_model=AgendaItemOut)
def update_agenda_item(
    meeting_id: int,
    item_id: int,
    payload: AgendaItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeetingAgendaItem:
    """Für die Pflege des Protokolltexts NACH der Versammlung - Titel/
    Beschreibung/Position bleiben ebenfalls korrigierbar."""
    _require_write_role(current_user)
    _get_readable_meeting(db, meeting_id, current_user)

    item = db.get(MeetingAgendaItem, item_id)
    if item is None or item.meeting_id != meeting_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tagesordnungspunkt nicht gefunden")

    update_data = payload.model_dump(exclude_unset=True)
    if "position" in update_data:
        conflict = db.scalar(
            select(MeetingAgendaItem).where(
                MeetingAgendaItem.meeting_id == meeting_id,
                MeetingAgendaItem.position == update_data["position"],
                MeetingAgendaItem.item_id != item_id,
            )
        )
        if conflict is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"TOP-Nummer {update_data['position']} ist bereits vergeben."
            )

    for field, value in update_data.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{meeting_id}/agenda-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agenda_item(
    meeting_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Hartes Löschen - Tagesordnungspunkte sind reine Planung, keine
    aufbewahrungspflichtige Historie wie resolution_collection."""
    _require_write_role(current_user)
    _get_readable_meeting(db, meeting_id, current_user)

    item = db.get(MeetingAgendaItem, item_id)
    if item is None or item.meeting_id != meeting_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tagesordnungspunkt nicht gefunden")
    db.delete(item)
    db.commit()


INVITATION_TEMPLATE = """
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'DejaVu Sans', sans-serif; font-size: 11pt; color: #222; }}
  .header {{ margin-bottom: 2cm; }}
  h1 {{ font-size: 14pt; }}
  ol {{ padding-left: 1.2cm; }}
  li {{ margin-bottom: 0.4cm; }}
  .description {{ font-size: 10pt; color: #444; margin-top: 0.1cm; }}
</style>
</head>
<body>
  <div class="header">{property_name}<br>{property_address}</div>
  <h1>Einladung zur {meeting_type}</h1>
  <p>Sehr geehrte Damen und Herren,</p>
  <p>{intro}</p>
  <p><strong>Termin:</strong> {meeting_date_line}<br>{location_detail_line}</p>
  <h2>Tagesordnung</h2>
  <ol>{agenda_html}</ol>
</body>
</html>
"""


@router.get("/{meeting_id}/invitation.pdf")
def generate_invitation_pdf(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    _require_read_access(current_user)
    meeting = _get_readable_meeting(db, meeting_id, current_user)
    property_ = db.get(Property, meeting.property_id)
    agenda_items = _load_agenda_items(db, meeting_id)

    if not agenda_items:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Ohne Tagesordnungspunkte kann keine Einladung erzeugt werden."
        )

    is_circular = meeting.meeting_type == "Umlaufbeschluss"
    meeting_date_line = (
        f"Frist zur Stimmabgabe bis {meeting.meeting_date.strftime('%d.%m.%Y')}"
        if is_circular
        else meeting.meeting_date.strftime("%d.%m.%Y")
        + (f", {meeting.meeting_time.strftime('%H:%M')} Uhr" if meeting.meeting_time else "")
    )
    location_detail_line = "" if is_circular else f"<strong>Ort:</strong> {meeting.location or '–'}"

    agenda_html = "".join(
        f"<li>{item.title}"
        + (f'<div class="description">{item.description}</div>' if item.description else "")
        + "</li>"
        for item in agenda_items
    )

    html_content = INVITATION_TEMPLATE.format(
        property_name=property_.name,
        property_address=property_.address,
        meeting_type=meeting.meeting_type,
        intro=meeting.agenda_intro or "hiermit laden wir Sie herzlich ein.",
        meeting_date_line=meeting_date_line,
        location_detail_line=location_detail_line,
        agenda_html=agenda_html,
    )

    pdf_bytes = HTML(string=html_content).write_pdf()

    meeting.invitation_date = date_type.today()
    if meeting.status == "Geplant":
        meeting.status = "Eingeladen"
    db.commit()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Einladung_Versammlung_{meeting_id}.pdf"'},
    )


def _de_number(value: float | None) -> str:
    """Deutsches Zahlenformat ohne Einheit: 846,76 - Rückgabe '–' bei fehlendem Wert."""
    if value is None:
        return "–"
    formatted = f"{float(value):,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


MINUTES_TEMPLATE = """
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'DejaVu Sans', sans-serif; font-size: 11pt; color: #222; }}
  .header {{ margin-bottom: 1cm; }}
  h1 {{ font-size: 14pt; }}
  h2 {{ font-size: 12pt; margin-top: 1cm; }}
  .meta {{ color: #555; font-size: 10pt; margin-bottom: 0.3cm; }}
  .meta-table {{ font-size: 10pt; color: #444; margin-bottom: 1cm; border-collapse: collapse; }}
  .meta-table td {{ padding: 1px 10px 1px 0; vertical-align: top; }}
  .top {{ margin-bottom: 0.9cm; }}
  .top-title {{ font-weight: bold; margin-bottom: 0.15cm; }}
  .top-text {{ white-space: pre-line; margin-bottom: 0.2cm; }}
  .resolution {{ margin-top: 0.3cm; margin-left: 0.3cm; }}
  .resolution .intro {{ font-weight: bold; margin-bottom: 0.1cm; }}
  .resolution .text {{ white-space: pre-line; margin-bottom: 0.2cm; }}
  .votes-table {{ font-size: 10pt; margin: 0.2cm 0 0.2cm 0.3cm; border-collapse: collapse; }}
  .votes-table td {{ padding: 1px 14px 1px 0; }}
  .status {{ font-weight: bold; margin-top: 0.1cm; margin-left: 0.3cm; }}
  .other-resolutions {{ margin-top: 1cm; }}
</style>
</head>
<body>
  <div class="header">{property_name}<br>{property_address}</div>
  <h1>Niederschrift zur {meeting_type}</h1>
  <div class="meta">{meeting_date_line}{location_line}</div>
  <table class="meta-table">{meta_rows_html}</table>
  {free_text_html}
  {tops_html}
  {other_resolutions_html}
</body>
</html>
"""


@router.get("/{meeting_id}/minutes.pdf")
def generate_minutes_pdf(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Baut die Niederschrift je Tagesordnungspunkt auf: 'protocol_text' des TOPs
    (Verlaufstext) gefolgt von allen über 'agenda_item_id' verknüpften
    Beschlüssen (Formel + resolution.description als Beschlusstext +
    Abstimmungsergebnis + status_note als Beschlussstatus). Beschlüsse, die
    zwar dieser Versammlung zugeordnet sind, aber keinem TOP (Altdaten,
    Umlaufbeschluss ohne Agenda), landen gesammelt am Ende.
    """
    _require_read_access(current_user)
    meeting = _get_readable_meeting(db, meeting_id, current_user)
    property_ = db.get(Property, meeting.property_id)
    agenda_items = _load_agenda_items(db, meeting_id)

    resolutions = list(
        db.scalars(
            select(ResolutionCollection)
            .where(ResolutionCollection.meeting_id == meeting_id, ResolutionCollection.deleted_at.is_(None))
            .order_by(ResolutionCollection.lfd_nr)
        )
    )
    resolutions_by_item: dict[int, list[ResolutionCollection]] = {}
    unlinked_resolutions: list[ResolutionCollection] = []
    for r in resolutions:
        if r.agenda_item_id is not None:
            resolutions_by_item.setdefault(r.agenda_item_id, []).append(r)
        else:
            unlinked_resolutions.append(r)

    is_circular = meeting.meeting_type == "Umlaufbeschluss"
    meeting_date_line = (
        f"Frist zur Stimmabgabe bis {meeting.meeting_date.strftime('%d.%m.%Y')}"
        if is_circular
        else meeting.meeting_date.strftime("%d.%m.%Y")
        + (f", {meeting.meeting_time.strftime('%H:%M')} Uhr" if meeting.meeting_time else "")
    )
    location_line = "" if is_circular or not meeting.location else f" · {meeting.location}"

    meta_rows: list[str] = []
    if not is_circular:
        if meeting.chairperson:
            meta_rows.append(f"<tr><td>Versammlungsleiter:</td><td>{meeting.chairperson}</td></tr>")
        if meeting.minute_taker:
            meta_rows.append(f"<tr><td>Protokollführer:</td><td>{meeting.minute_taker}</td></tr>")
        if meeting.meeting_time:
            meta_rows.append(f"<tr><td>Beginn:</td><td>{meeting.meeting_time.strftime('%H:%M')} Uhr</td></tr>")
        if meeting.end_time:
            meta_rows.append(f"<tr><td>Ende:</td><td>{meeting.end_time.strftime('%H:%M')} Uhr</td></tr>")
    if meeting.represented_shares is not None:
        meta_rows.append(
            f"<tr><td>Vertretene Stimmanteile:</td><td>{_de_number(meeting.represented_shares)} "
            "Miteigentumsanteile</td></tr>"
        )
    if meeting.quorum_met is not None:
        meta_rows.append(f"<tr><td>Beschlussfähigkeit:</td><td>{'ja' if meeting.quorum_met else 'nein'}</td></tr>")
    if meeting.voting_key:
        meta_rows.append(f"<tr><td>Abstimmungsschlüssel:</td><td>{meeting.voting_key}</td></tr>")
    meta_rows_html = "".join(meta_rows)

    free_text_html = f'<div class="top-text">{meeting.minutes_text}</div>' if meeting.minutes_text else ""

    def render_resolution(r: ResolutionCollection) -> str:
        parts = ['<div class="resolution">']
        parts.append('<div class="intro">Die Eigentümergemeinschaft fasst folgenden Beschluss</div>')
        if r.description:
            parts.append(f'<div class="text">{r.description}</div>')
        if r.votes_yes is not None or r.votes_no is not None or r.votes_abstain is not None:
            parts.append(
                '<table class="votes-table">'
                f"<tr><td>Abstimmungsergebnis:</td><td>JA-Stimmen</td><td>{_de_number(r.votes_yes)}</td></tr>"
                f"<tr><td></td><td>NEIN-Stimmen</td><td>{_de_number(r.votes_no)}</td></tr>"
                f"<tr><td></td><td>Stimmenthaltungen</td><td>{_de_number(r.votes_abstain)}</td></tr>"
                "</table>"
            )
        if r.status_note:
            parts.append(f'<div class="status">Beschlussstatus: {r.status_note}</div>')
        parts.append("</div>")
        return "".join(parts)

    tops_parts: list[str] = []
    for item in agenda_items:
        tops_parts.append('<div class="top">')
        tops_parts.append(f'<div class="top-title">TOP {item.position} {item.title}</div>')
        if item.protocol_text:
            tops_parts.append(f'<div class="top-text">{item.protocol_text}</div>')
        for r in resolutions_by_item.get(item.item_id, []):
            tops_parts.append(render_resolution(r))
        tops_parts.append("</div>")
    tops_html = "".join(tops_parts) if tops_parts else "<p>Keine Tagesordnungspunkte erfasst.</p>"

    other_resolutions_html = ""
    if unlinked_resolutions:
        other_parts = ['<div class="other-resolutions"><h2>Weitere Beschlüsse dieser Versammlung</h2>']
        for r in unlinked_resolutions:
            other_parts.append(f'<div class="top-title">Lfd. Nr. {r.lfd_nr} – {r.title}</div>')
            other_parts.append(render_resolution(r))
        other_parts.append("</div>")
        other_resolutions_html = "".join(other_parts)

    html_content = MINUTES_TEMPLATE.format(
        property_name=property_.name,
        property_address=property_.address,
        meeting_type=meeting.meeting_type,
        meeting_date_line=meeting_date_line,
        location_line=location_line,
        meta_rows_html=meta_rows_html,
        free_text_html=free_text_html,
        tops_html=tops_html,
        other_resolutions_html=other_resolutions_html,
    )
    pdf_bytes = HTML(string=html_content).write_pdf()

    if meeting.status in ("Geplant", "Eingeladen", "Durchgeführt"):
        meeting.status = "Protokolliert"
    db.commit()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Niederschrift_Versammlung_{meeting_id}.pdf"'},
    )