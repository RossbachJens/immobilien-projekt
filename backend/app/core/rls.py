# backend/app/core/rls.py
"""
RLS-Kontext: zweite Verteidigungslinie neben der Query-Filterung in
app/core/access.py::accessible_property_ids() (siehe PROJECTPLAN.md,
Grundsatzentscheidung "Zugriffskontrolle"). Die Postgres-Policies (Migration
0014_row_level_security) lesen 'app.current_user_id'/'app.current_role' über
current_setting() - dieses Modul ist dafür zuständig, diese beiden Werte pro
Request korrekt zu setzen.

WARUM session.info statt ContextVar (Korrektur nach Produktionsfehler):
Ein erster Anlauf hat den Kontext über eine contextvars.ContextVar
weitergereicht. Das schlägt in DIESEM Projekt fehl, weil FastAPI jede
SYNCHRONE Dependency-Funktion (get_db, get_current_user) UND den Endpoint
selbst jeweils über anyio.to_thread.run_sync() ausführt - und das läuft
intern über eine KOPIE des aktuellen contextvars.Context
(copy_context().run(...)). Eine ContextVar.set()-Änderung innerhalb von
get_current_user() ist daher nur innerhalb dieses einen Threadpool-Aufrufs
sichtbar und geht beim Rücksprung verloren - sie erreicht weder den
Endpoint-Aufruf noch später feuernde after_begin-Events.

session.info ist dagegen ein normales dict-Attribut auf dem Session-Objekt
selbst - und dieses Objekt IST über alle Threadpool-Aufrufe eines Requests
hinweg identisch (FastAPI cached die get_db-Dependency und reicht dieselbe
Instanz durch, s. app/core/deps.py). Dadurch funktioniert die Weitergabe
unabhängig davon, auf welchem OS-Thread der jeweilige Code gerade läuft.

WARUM überhaupt ein nachträgliches Neu-Setzen nötig ist (after_begin-Event):
SET LOCAL (bzw. set_config(..., true)) gilt nur bis zum nächsten COMMIT.
Viele Router committen mehrfach pro Request (z.B. flush -> mehrere INSERTs
-> commit -> anschließende refresh()/SELECTs, siehe
app/routers/journal_entries.py oder budget_plans.py::update_budget_plan_status).
Ein einmalig gesetzter Kontext wäre nach dem ersten Commit still
wirkungslos - current_setting() liefert dann NULL, RLS-Policies liefern
0 Zeilen statt eines Fehlers (führte exakt zum "Could not refresh
instance"-Fehler). Das 'after_begin'-Event feuert bei JEDER neuen
Transaktion der Session (auch nach jedem Commit) und setzt den Kontext
daher zuverlässig neu.

is_local=true (dritter Parameter von set_config) entspricht SET LOCAL -
bewusst NICHT is_local=false (Session-/Verbindungsebene): bei SQLAlchemys
Connection-Pooling würde ein verbindungsweiter Wert sonst über das Ende des
Requests hinaus auf der gepoolten Verbindung "kleben bleiben" und beim
nächsten Checkout an einen ANDEREN User durchgereicht werden können. SET
LOCAL wird von Postgres garantiert am Transaktionsende zurückgesetzt -
fail-safe statt auf diszipliniertes manuelles Zurücksetzen beim
Connection-Checkin angewiesen.

Requests ohne authentifizierten User (z.B. /health, /auth/login vor Login,
app/cli.py-Skripte) lassen session.info leer - RLS-geschützte Tabellen
liefern dann serverseitig 0 Zeilen (fail closed), nicht etwa alles
(fail open).
"""
from sqlalchemy import event, text
from sqlalchemy.orm import Session

_INFO_KEY_USER_ID = "rls_user_id"
_INFO_KEY_ROLE = "rls_role"


def apply_rls_context(db: Session, user_id: int, role: str) -> None:
    """Einmal pro Request aus app/core/deps.py::get_current_user aufgerufen,
    sobald User und Rolle feststehen. Setzt den Kontext sowohl für die
    bereits laufende Transaktion (die User-Abfrage in get_current_user hat
    schon eine geöffnet, bevor die Rolle bekannt war) als auch - über
    session.info - für alle künftigen Transaktionen dieses Requests (siehe
    Docstring oben)."""
    db.info[_INFO_KEY_USER_ID] = user_id
    db.info[_INFO_KEY_ROLE] = role
    db.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(user_id)})
    db.execute(text("SELECT set_config('app.current_role', :role, true)"), {"role": role})


@event.listens_for(Session, "after_begin")
def _reapply_rls_context_on_new_transaction(session: Session, transaction, connection) -> None:
    user_id = session.info.get(_INFO_KEY_USER_ID)
    role = session.info.get(_INFO_KEY_ROLE)
    if user_id is None or role is None:
        return
    connection.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(user_id)})
    connection.execute(text("SELECT set_config('app.current_role', :role, true)"), {"role": role})
    