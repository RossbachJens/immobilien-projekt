# backend/app/routers/journal_entries.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session
# Ergänzung der Imports oben in der Datei:
from datetime import date


from app.core.access import accessible_property_ids
from app.core.deps import get_current_user
from app.core.roles import resolve_role
from app.db.session import get_db
from app.models.buchhaltung import Account, EntryLine, JournalEntry
from app.models.stammdaten import Property, User
from app.schemas.journal_entries import EntryLineOut, JournalEntryCreate, JournalEntryOut
from app.models.buchhaltung import EntryDirection

router = APIRouter(prefix="/journal-entries", tags=["journal-entries"])


def _require_write_role(current_user: User) -> None:
    # Bewusst dieselbe lokale Kopie wie in properties.py/units.py - noch kein
    # gemeinsamer Ort dafür (könnte man später nach app/core/access.py ziehen).
    if resolve_role(current_user) not in ("admin", "verwalter"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nur Administratoren oder zugeordnete Verwalter dürfen Buchungen erfassen.",
        )


def _check_property_accessible(db: Session, property_id: int, current_user: User) -> Property:
    property_ = db.get(Property, property_id)
    if property_ is None or property_.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and property_id not in property_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekannte Liegenschaft")
    return property_


def _validate_accounts_for_property(db: Session, account_ids: set[int], property_id: int) -> None:
    accounts = list(db.scalars(select(Account).where(Account.account_id.in_(account_ids))))
    found_ids = {a.account_id for a in accounts}
    missing = account_ids - found_ids
    if missing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unbekannte Konto-ID(s): {sorted(missing)}")

    invalid = [
        a.account_id
        for a in accounts
        if not a.is_active or (a.property_id is not None and a.property_id != property_id)
    ]
    if invalid:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Konto-ID(s) für diese Liegenschaft nicht nutzbar (inaktiv oder fremdes "
            f"Individualkonto): {sorted(invalid)}",
        )


def _get_readable_entry(db: Session, entry_id: int, current_user: User) -> JournalEntry:
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Buchung nicht gefunden")

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None and entry.property_id not in property_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Buchung nicht gefunden")

    return entry


def _load_lines(db: Session, entry_id: int) -> list[EntryLine]:
    return list(db.scalars(select(EntryLine).where(EntryLine.entry_id == entry_id)))


def _to_out(entry: JournalEntry, lines: list[EntryLine]) -> JournalEntryOut:
    return JournalEntryOut(
        entry_id=entry.entry_id,
        property_id=entry.property_id,
        entry_date=entry.entry_date,
        document_reference=entry.document_reference,
        description=entry.description,
        created_by=entry.created_by,
        created_at=entry.created_at,
        locked_at=entry.locked_at,
        reversed_entry_id=entry.reversed_entry_id,
        lines=[EntryLineOut.model_validate(line) for line in lines],
    )


@router.get("", response_model=list[JournalEntryOut])
def list_journal_entries(
    property_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JournalEntryOut]:
    query = select(JournalEntry)

    property_ids = accessible_property_ids(db, current_user)
    if property_ids is not None:
        query = query.where(JournalEntry.property_id.in_(property_ids))
    if property_id is not None:
        query = query.where(JournalEntry.property_id == property_id)

    query = query.order_by(JournalEntry.entry_date.desc(), JournalEntry.entry_id.desc())
    entries = list(db.scalars(query))
    if not entries:
        return []

    entry_ids = [e.entry_id for e in entries]
    all_lines = list(db.scalars(select(EntryLine).where(EntryLine.entry_id.in_(entry_ids))))
    lines_by_entry: dict[int, list[EntryLine]] = {}
    for line in all_lines:
        lines_by_entry.setdefault(line.entry_id, []).append(line)

    return [_to_out(e, lines_by_entry.get(e.entry_id, [])) for e in entries]


@router.get("/{entry_id}", response_model=JournalEntryOut)
def get_journal_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JournalEntryOut:
    entry = _get_readable_entry(db, entry_id, current_user)
    return _to_out(entry, _load_lines(db, entry_id))


@router.post("", response_model=JournalEntryOut, status_code=status.HTTP_201_CREATED)
def create_journal_entry(
    payload: JournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JournalEntryOut:
    _require_write_role(current_user)
    _check_property_accessible(db, payload.property_id, current_user)
    _validate_accounts_for_property(db, {line.account_id for line in payload.lines}, payload.property_id)

    entry = JournalEntry(
        property_id=payload.property_id,
        entry_date=payload.entry_date,
        document_reference=payload.document_reference,
        description=payload.description,
        created_by=current_user.user_id,
    )
    db.add(entry)
    db.flush()  # vergibt entry.entry_id, wird für die Zeilen gebraucht

    lines = [
        EntryLine(
            entry_id=entry.entry_id,
            account_id=line.account_id,
            # Zeilen erben property_id vom Beleg-Kopf - in unserer Domäne
            # gehört ein Beleg immer zu genau einer Liegenschaft.
            property_id=payload.property_id,
            unit_id=line.unit_id,
            lease_id=line.lease_id,
            amount=line.amount,
            direction=line.direction,
        )
        for line in payload.lines
    ]
    db.add_all(lines)

    try:
        db.commit()
    except (IntegrityError, DataError) as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Buchung ungültig: Soll und Haben sind nicht ausgeglichen (oder ein "
            "verknüpfter Datensatz existiert nicht).",
        ) from exc

    db.refresh(entry)
    return _to_out(entry, _load_lines(db, entry.entry_id))

def _flip_direction(direction: EntryDirection) -> EntryDirection:
    return EntryDirection.credit if direction == EntryDirection.debit else EntryDirection.debit


def _find_reversal_entry_id(db: Session, original_entry_id: int) -> int | None:
    """Prüft, ob 'original_entry_id' bereits storniert wurde - liefert ggf.
    die entry_id des existierenden Storno-Belegs (für die Fehlermeldung)."""
    return db.scalar(
        select(JournalEntry.entry_id).where(JournalEntry.reversed_entry_id == original_entry_id)
    )


@router.post("/{entry_id}/storno", response_model=JournalEntryOut, status_code=status.HTTP_201_CREATED)
def storno_journal_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JournalEntryOut:
    """
    Bucht eine 1:1-Spiegelbuchung (Soll<->Haben vertauscht, gleiche Beträge)
    zur Original-Buchung 'entry_id'. Buchungsbelege werden in der doppelten
    Buchführung nie verändert/gelöscht (siehe fehlendes PATCH/DELETE in
    diesem Router) - Korrekturen laufen ausschließlich über Storno.

    Hinweis 'locked_at': Sperrung nach Monats-/Jahresabschluss wird hier noch
    NICHT geprüft (siehe PROJECTPLAN.md, Phase 7 "Härtung") - aktuell kann
    jede Buchung jederzeit storniert werden.
    """
    _require_write_role(current_user)
    original = _get_readable_entry(db, entry_id, current_user)

    existing_reversal_id = _find_reversal_entry_id(db, entry_id)
    if existing_reversal_id is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Beleg wurde bereits storniert (Storno-Beleg #{existing_reversal_id}).",
        )

    original_lines = _load_lines(db, entry_id)

    storno_entry = JournalEntry(
        property_id=original.property_id,
        entry_date=date.today(),
        document_reference=original.document_reference,
        description=f"Storno zu Beleg #{original.entry_id}: {original.description}",
        created_by=current_user.user_id,
        reversed_entry_id=original.entry_id,
    )
    db.add(storno_entry)
    db.flush()  # vergibt storno_entry.entry_id, wird für die Zeilen gebraucht

    storno_lines = [
        EntryLine(
            entry_id=storno_entry.entry_id,
            account_id=line.account_id,
            property_id=line.property_id,
            unit_id=line.unit_id,
            lease_id=line.lease_id,
            amount=line.amount,
            direction=_flip_direction(line.direction),
        )
        for line in original_lines
    ]
    db.add_all(storno_lines)

    try:
        db.commit()
    except (IntegrityError, DataError) as exc:
        # Sollte praktisch nie auftreten (Spiegelung eines bereits
        # balancierten Belegs ist zwangsläufig wieder balanciert) - trotzdem
        # als Sicherheitsnetz abgefangen statt einen 500er durchzureichen.
        db.rollback()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Storno konnte nicht gebucht werden."
        ) from exc

    db.refresh(storno_entry)
    return _to_out(storno_entry, _load_lines(db, storno_entry.entry_id))