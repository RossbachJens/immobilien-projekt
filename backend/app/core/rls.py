# backend/app/core/rls.py
"""
RLS-Kontext: zweite Verteidigungslinie neben der Query-Filterung in
app/core/access.py::accessible_property_ids() (siehe PROJECTPLAN.md,
Grundsatzentscheidung "Zugriffskontrolle"). Die Postgres-Policies (Migration
0014_row_level_security) lesen 'app.current_user_id'/'app.current_role' über
current_setting() - dieses Modul ist dafür zuständig, diese beiden Werte pro
Request korrekt zu setzen.

WARUM ein ContextVar + Session-Event statt einmaligem SET LOCAL am
Request-Anfang:
SET LOCAL (bzw. set_config(..., true)) gilt nur bis zum nächsten COMMIT.
Viele Router committen mehrfach pro Request (z.B. flush -> mehrere INSERTs
-> commit -> anschließende refresh()/SELECTs, siehe
app/routers/journal_entries.py). Ein einmalig gesetzter Kontext wäre nach
dem ersten Commit still wirkungslos - current_setting() liefert dann NULL,
RLS-Policies liefern 0 Zeilen statt eines Fehlers (schwer zu debuggen).

Das 'after_begin'-Event feuert bei JEDER neuen Transaktion einer Session
(also auch nach jedem Commit) und setzt den Kontext daher zuverlässig neu -
solange die ContextVar für die Dauer des Requests gesetzt bleibt.

is_local=true (dritter Parameter von set_config) entspricht SET LOCAL -
bewusst NICHT is_local=false (Session-/Verbindungsebene): bei SQLAlchemys
Connection-Pooling würde ein verbindungsweiter Wert sonst über das Ende des
Requests hinaus auf der gepoolten Verbindung "kleben bleiben" und beim
nächsten Checkout an einen ANDEREN User durchgereicht werden können. SET
LOCAL wird von Postgres garantiert am Transaktionsende zurückgesetzt -
fail-safe statt auf diszipliniertes manuelles Zurücksetzen beim
Connection-Checkin angewiesen.

Requests ohne authentifizierten User (z.B. /health, /auth/login vor Login,
app/cli.py-Skripte) lassen die ContextVar auf None - RLS-geschützte Tabellen
liefern dann serverseitig 0 Zeilen (fail closed), nicht etwa alles
(fail open).
"""
from contextvars import ContextVar

from sqlalchemy import event, text
from sqlalchemy.orm import Session

current_rls_context: ContextVar[tuple[int, str] | None] = ContextVar(
    "current_rls_context", default=None
)


def apply_rls_context(db: Session, user_id: int, role: str) -> None:
    """Einmal pro Request aus app/core/deps.py::get_current_user aufgerufen,
    sobald User und Rolle feststehen. Setzt den Kontext sowohl für die
    bereits laufende Transaktion (die User-Abfrage in get_current_user hat
    schon eine geöffnet, bevor die Rolle bekannt war) als auch - über die
    ContextVar - für alle künftigen Transaktionen dieses Requests (siehe
    Docstring oben)."""
    current_rls_context.set((user_id, role))
    db.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(user_id)})
    db.execute(text("SELECT set_config('app.current_role', :role, true)"), {"role": role})


@event.listens_for(Session, "after_begin")
def _reapply_rls_context_on_new_transaction(session: Session, transaction, connection) -> None:
    ctx = current_rls_context.get()
    if ctx is None:
        return
    user_id, role = ctx
    connection.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(user_id)})
    connection.execute(text("SELECT set_config('app.current_role', :role, true)"), {"role": role})