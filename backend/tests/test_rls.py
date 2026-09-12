# backend/tests/test_rls.py
"""
Testet die Postgres Row-Level-Security-Policies aus Migration
0014_row_level_security - siehe PROJECTPLAN.md, offener Punkt aus dem
Phase-1-Meilenstein ("vier Test-User ... verifiziert durch einen negativen
RLS-Testfall").

Zwei Ebenen:
  - TestRlsPoliciesDirectly: spricht die Datenbank OHNE FastAPI/Router an
    (raw SQL über den eingeschränkten app_user, mit manuell gesetztem
    RLS-Kontext) - isoliert ausschließlich die Postgres-Policies selbst,
    unabhängig von app/core/access.py::accessible_property_ids(). Das ist
    der eigentliche "negative RLS-Testfall": beweist, dass RLS auch dann
    noch schützt, wenn die Anwendungs-Filterung fehlerhaft wäre oder fehlt.
  - TestRoleAccessViaApi: End-to-End über TestClient/HTTP, wie es die vier
    Test-User im Alltag erleben würden (Defense-in-Depth als Ganzes).

Fixtures legen Testdaten direkt über die Superuser-Verbindung
(settings.migration_database_url) an/ab - ein Insert über den regulären
app_user-Pfad würde selbst an den frisch aktivierten RLS-Policies scheitern
(z.B. verlangt die properties_insert_by_verwalter-Policy bereits einen
gesetzten RLS-Kontext), daher bewusst am RLS vorbei für reine Testdaten-
Vorbereitung.

Hinweis: Läuft seit conftest.py gegen die isolierte Test-Datenbank
(Service 'db_test', siehe docker-compose.yml), nicht mehr gegen die
Dev-DB. Ein abgebrochener Testlauf hinterlässt bestenfalls Zeilen mit
Präfix "RLS-Test" in db_test - unproblematisch, da diese DB ohnehin nur
Testzwecken dient (im Zweifel: docker compose down -v für db_test).
"""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.main import app

TEST_PASSWORD = "TestPasswort123!"

# Bewusst eigener Superuser-Engine für Setup/Teardown - die Laufzeit-Engine
# der App (app.db.session.engine) verbindet seit Migration 0014 als
# eingeschränkter app_user und würde beim Anlegen der Testdaten selbst an
# RLS scheitern (siehe Modul-Docstring).
_admin_engine = create_engine(settings.migration_database_url)
_AdminSession = sessionmaker(bind=_admin_engine)


@pytest.fixture()
def admin_db() -> Generator[Session, None, None]:
    db = _AdminSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def rls_fixture(admin_db: Session):
    """
    Baut zwei komplett getrennte Liegenschaften mit je eigenem Verwalter,
    Eigentümer und Mieter auf - Grundlage für alle Isolations-Checks unten.

        Liegenschaft A                  Liegenschaft B
        ---------------                 ---------------
        Verwalter A (nur A zugeordnet)  Verwalter B (nur B zugeordnet)
        Einheit A1 -> Eigentümer A      Einheit B1 -> Eigentümer B
        Einheit A1 -> Mietvertrag       Einheit B1 -> Mietvertrag
                       (Mieter A)                      (Mieter B)
    """
    password_hash = hash_password(TEST_PASSWORD)

    def _property(name: str) -> int:
        return admin_db.execute(
            text(
                "INSERT INTO properties (name, address, total_mea) "
                "VALUES (:name, 'Teststraße 1', 1000) RETURNING property_id"
            ),
            {"name": name},
        ).scalar_one()

    def _unit(property_id: int, unit_number: str) -> int:
        return admin_db.execute(
            text(
                "INSERT INTO units (property_id, unit_number, square_meters, mea) "
                "VALUES (:pid, :num, 50, 500) RETURNING unit_id"
            ),
            {"pid": property_id, "num": unit_number},
        ).scalar_one()

    def _owner(last_name: str) -> int:
        return admin_db.execute(
            text(
                "INSERT INTO owners (last_name, street_and_number) "
                "VALUES (:name, 'Teststraße 2') RETURNING owner_id"
            ),
            {"name": last_name},
        ).scalar_one()

    def _tenant(last_name: str) -> int:
        return admin_db.execute(
            text(
                "INSERT INTO tenants (first_name, last_name, street_and_number) "
                "VALUES ('Test', :name, 'Teststraße 3') RETURNING tenant_id"
            ),
            {"name": last_name},
        ).scalar_one()

    def _user(
        name: str,
        email: str,
        *,
        is_admin: bool = False,
        owner_id: int | None = None,
        tenant_id: int | None = None,
    ) -> int:
        return admin_db.execute(
            text(
                "INSERT INTO users (name, email, password_hash, must_change_password, "
                "is_admin, owner_id, tenant_id) "
                "VALUES (:name, :email, :pw, FALSE, :is_admin, :owner_id, :tenant_id) "
                "RETURNING user_id"
            ),
            {
                "name": name,
                "email": email,
                "pw": password_hash,
                "is_admin": is_admin,
                "owner_id": owner_id,
                "tenant_id": tenant_id,
            },
        ).scalar_one()

    property_a = _property("RLS-Test Liegenschaft A")
    property_b = _property("RLS-Test Liegenschaft B")
    unit_a1 = _unit(property_a, "A1")
    unit_b1 = _unit(property_b, "B1")
    owner_a = _owner("Eigentümer-A")
    owner_b = _owner("Eigentümer-B")
    tenant_a = _tenant("Mieter-A")
    tenant_b = _tenant("Mieter-B")

    admin_db.execute(
        text(
            "INSERT INTO unit_owner_history (unit_id, owner_id, ownership_share, valid_from) "
            "VALUES (:uid, :oid, 500, CURRENT_DATE)"
        ),
        {"uid": unit_a1, "oid": owner_a},
    )
    admin_db.execute(
        text(
            "INSERT INTO unit_owner_history (unit_id, owner_id, ownership_share, valid_from) "
            "VALUES (:uid, :oid, 500, CURRENT_DATE)"
        ),
        {"uid": unit_b1, "oid": owner_b},
    )
    admin_db.execute(
        text(
            "INSERT INTO leases (unit_id, tenant_id, start_date, cold_rent, status) "
            "VALUES (:uid, :tid, CURRENT_DATE, 500, 'aktiv')"
        ),
        {"uid": unit_a1, "tid": tenant_a},
    )
    admin_db.execute(
        text(
            "INSERT INTO leases (unit_id, tenant_id, start_date, cold_rent, status) "
            "VALUES (:uid, :tid, CURRENT_DATE, 500, 'aktiv')"
        ),
        {"uid": unit_b1, "tid": tenant_b},
    )

    admin_user = _user("RLS-Test Admin", "rls-test-admin@example.com", is_admin=True)
    verwalter_a = _user("RLS-Test Verwalter A", "rls-test-verwalter-a@example.com")
    verwalter_b = _user("RLS-Test Verwalter B", "rls-test-verwalter-b@example.com")
    owner_user_a = _user("RLS-Test Eigentümer A", "rls-test-owner-a@example.com", owner_id=owner_a)
    tenant_user_a = _user("RLS-Test Mieter A", "rls-test-tenant-a@example.com", tenant_id=tenant_a)

    admin_db.execute(
        text(
            "INSERT INTO user_properties (user_id, property_id, role) "
            "VALUES (:uid, :pid, 'Verwalter')"
        ),
        {"uid": verwalter_a, "pid": property_a},
    )
    admin_db.execute(
        text(
            "INSERT INTO user_properties (user_id, property_id, role) "
            "VALUES (:uid, :pid, 'Verwalter')"
        ),
        {"uid": verwalter_b, "pid": property_b},
    )
    admin_db.commit()

    data = {
        "property_a": property_a,
        "property_b": property_b,
        "unit_a1": unit_a1,
        "unit_b1": unit_b1,
        "verwalter_a_user_id": verwalter_a,
    }

    try:
        yield data
    finally:
        # Reihenfolge umgekehrt zur Anlage (Fremdschlüssel) - alles über den
        # Superuser, damit RLS die Aufräumarbeiten nicht behindert.
        admin_db.execute(text("DELETE FROM leases WHERE unit_id IN (:a, :b)"), {"a": unit_a1, "b": unit_b1})
        admin_db.execute(
            text("DELETE FROM unit_owner_history WHERE unit_id IN (:a, :b)"), {"a": unit_a1, "b": unit_b1}
        )
        admin_db.execute(
            text("DELETE FROM user_properties WHERE user_id IN (:va, :vb)"),
            {"va": verwalter_a, "vb": verwalter_b},
        )
        admin_db.execute(
            text("DELETE FROM users WHERE user_id IN (:a, :va, :vb, :oa, :ta)"),
            {"a": admin_user, "va": verwalter_a, "vb": verwalter_b, "oa": owner_user_a, "ta": tenant_user_a},
        )
        admin_db.execute(text("DELETE FROM units WHERE unit_id IN (:a, :b)"), {"a": unit_a1, "b": unit_b1})
        admin_db.execute(text("DELETE FROM tenants WHERE tenant_id IN (:a, :b)"), {"a": tenant_a, "b": tenant_b})
        admin_db.execute(text("DELETE FROM owners WHERE owner_id IN (:a, :b)"), {"a": owner_a, "b": owner_b})
        admin_db.execute(
            text("DELETE FROM properties WHERE property_id IN (:a, :b)"), {"a": property_a, "b": property_b}
        )
        admin_db.commit()


# ---------------------------------------------------------------------
# Ebene 1: RLS-Policies direkt gegen die DB (ohne FastAPI/Router)
# ---------------------------------------------------------------------


class TestRlsPoliciesDirectly:
    """
    Fährt bewusst NICHT über die App-Filterung (app/core/access.py), sondern
    setzt den RLS-Kontext per Hand und stellt eine ungefilterte Abfrage -
    exakt der Fall, den die Postgres-Policy allein abfangen muss. Nutzt die
    reguläre Laufzeit-Engine (app_user), da RLS nur für diesen
    eingeschränkten User überhaupt greift (Superuser umgehen RLS immer).
    """

    def _query_property_ids_as(self, user_id: int | None, role: str | None) -> set[int]:
        from app.db.session import engine as app_user_engine

        with app_user_engine.connect() as conn:
            with conn.begin():
                conn.execute(
                    text("SELECT set_config('app.current_user_id', :uid, true)"),
                    {"uid": str(user_id) if user_id is not None else ""},
                )
                conn.execute(
                    text("SELECT set_config('app.current_role', :role, true)"),
                    {"role": role or ""},
                )
                rows = conn.execute(text("SELECT property_id FROM properties")).scalars().all()
        return set(rows)

    def test_no_context_sees_nothing(self, rls_fixture):
        """Fail-closed: ohne gesetzten Kontext (z.B. ein Skript ohne Login)
        darf RLS nichts durchlassen, nicht etwa alles."""
        visible = self._query_property_ids_as(None, None)
        assert rls_fixture["property_a"] not in visible
        assert rls_fixture["property_b"] not in visible

    def test_admin_sees_both_properties(self, rls_fixture):
        visible = self._query_property_ids_as(999999, "admin")
        assert rls_fixture["property_a"] in visible
        assert rls_fixture["property_b"] in visible

    def test_verwalter_sees_only_own_property(self, rls_fixture):
        visible = self._query_property_ids_as(rls_fixture["verwalter_a_user_id"], "verwalter")
        assert rls_fixture["property_a"] in visible
        assert rls_fixture["property_b"] not in visible


# ---------------------------------------------------------------------
# Ebene 2: End-to-End über die API, wie die vier Rollen es im Alltag erleben
# ---------------------------------------------------------------------


class TestRoleAccessViaApi:
    def _login(self, email: str) -> TestClient:
        client = TestClient(app)
        response = client.post("/auth/login", json={"identifier": email, "password": TEST_PASSWORD})
        assert response.status_code == 200, response.text
        return client

    def test_admin_sees_all_properties(self, rls_fixture):
        client = self._login("rls-test-admin@example.com")
        response = client.get("/properties")
        ids = {p["property_id"] for p in response.json()}
        assert rls_fixture["property_a"] in ids
        assert rls_fixture["property_b"] in ids

    def test_verwalter_sees_only_assigned_property(self, rls_fixture):
        client = self._login("rls-test-verwalter-a@example.com")
        response = client.get("/properties")
        ids = {p["property_id"] for p in response.json()}
        assert ids == {rls_fixture["property_a"]}

    def test_verwalter_cannot_fetch_foreign_property_by_id(self, rls_fixture):
        client = self._login("rls-test-verwalter-a@example.com")
        response = client.get(f"/properties/{rls_fixture['property_b']}")
        assert response.status_code == 404

    def test_owner_sees_only_own_unit_property(self, rls_fixture):
        client = self._login("rls-test-owner-a@example.com")
        response = client.get("/properties")
        ids = {p["property_id"] for p in response.json()}
        assert ids == {rls_fixture["property_a"]}

    def test_tenant_sees_only_own_unit_property(self, rls_fixture):
        client = self._login("rls-test-tenant-a@example.com")
        response = client.get("/properties")
        ids = {p["property_id"] for p in response.json()}
        assert ids == {rls_fixture["property_a"]}