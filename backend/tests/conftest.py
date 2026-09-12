# backend/tests/conftest.py
"""
Pytest-Konfiguration für die gesamte Test-Suite.

WICHTIG: Biegt DATABASE_URL/MIGRATION_DATABASE_URL zwingend auf die
isolierte Test-Datenbank (Service 'db_test' in docker-compose.yml) um -
und zwar BEVOR irgendein app.*-Modul importiert wird. app/core/config.py
liest Umgebungsvariablen nur einmal beim ersten Import (Settings() wird als
Modul-Singleton instanziiert), app/db/session.py baut daraus wiederum beim
ersten Import eine Engine. Pytest importiert conftest.py grundsätzlich vor
den Testmodulen im selben Verzeichnis - die Umgebungsvariablen müssen daher
hier ganz oben, vor jedem 'from app...'-Import, gesetzt werden.

Vorher liefen test_health.py & test_rls.py schlicht gegen DATABASE_URL, wie
auch immer es gerade gesetzt war (i.d.R. die echte Dev-Datenbank, siehe
docker-compose.yml) - riskant, sobald ein Test schreibend eingreift (wie
test_rls.py::rls_fixture es tut). Die Zuweisung unten überschreibt
DATABASE_URL/MIGRATION_DATABASE_URL bewusst UNBEDINGT (nicht nur als
Default via os.environ.setdefault), damit ein Testlauf niemals aus
Versehen die Dev-DB berührt, selbst wenn docker-compose sie im
Backend-Container bereits gesetzt hat.
"""
import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://app_user:app_user_dev_password@db_test:5432/immobilien_test",
)
os.environ["MIGRATION_DATABASE_URL"] = os.environ.get(
    "TEST_MIGRATION_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@db_test:5432/immobilien_test",
)

from pathlib import Path  # noqa: E402  (muss nach den os.environ-Zeilen oben stehen)

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def _migrate_test_database() -> None:
    """
    Bringt db_test einmal pro Testlauf auf den aktuellen Migrationsstand.
    'upgrade head' ist idempotent (kein Effekt, wenn bereits aktuell) -
    unproblematisch, auch wenn die Test-DB zwischen Testläufen bestehen
    bleibt (siehe docker-compose.yml, Volume db_test_data).

    WICHTIG: 'upgrade head', NICHT 'stamp head' - stamp würde die
    Migrationen nur als erledigt markieren, ohne sie auszuführen (z.B.
    bliebe dann accounts.property_id aus Migration 0001 fehlen - siehe
    README.md, Abschnitt "Erster Admin-Account"). Die tatsächliche
    Ziel-URL kommt über settings.migration_database_url aus env.py -
    hier nur script_location explizit setzen, damit es unabhängig vom
    cwd funktioniert.

    Setzt voraus, dass 'docker compose --profile test up -d db_test'
    bereits läuft - ohne laufenden db_test-Container schlägt dieser
    Fixture-Aufruf mit einem klaren Verbindungsfehler fehl, statt dass
    einzelne Tests später mit verwirrenden Timeouts scheitern.
    """
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(alembic_cfg, "head")