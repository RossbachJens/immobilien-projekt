# backend/app/schemas/users.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.zuordnungen import PropertyRole


class PropertyAssignmentIn(BaseModel):
    property_id: int
    role: PropertyRole = PropertyRole.verwalter


class PropertyAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    property_id: int
    role: PropertyRole


def _check_role_exclusivity(is_admin: bool, owner_id: int | None, tenant_id: int | None) -> None:
    flags = [is_admin, owner_id is not None, tenant_id is not None]
    if sum(flags) > 1:
        raise ValueError(
            "Ein User kann nur eine Rolle gleichzeitig haben: Admin, Eigentümer (owner_id) "
            "oder Mieter (tenant_id)."
        )


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=72)
    is_admin: bool = False
    # Verknüpfung mit einem bestehenden Owner/Tenant-Stammdatensatz - macht den
    # User zum "Eigentümer" bzw. "Mieter" (siehe app/core/roles.py::resolve_role).
    # Owner/Tenant selbst werden nicht hier angelegt, sondern über die
    # Stammdaten-Endpunkte (Phase 2) - hier wird nur verknüpft.
    owner_id: int | None = None
    tenant_id: int | None = None
    property_assignments: list[PropertyAssignmentIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_role(self) -> "UserCreateRequest":
        _check_role_exclusivity(self.is_admin, self.owner_id, self.tenant_id)
        return self


class UserUpdateRequest(BaseModel):
    """
    Alle Felder optional (PATCH-Semantik). Nur tatsächlich im Request-Body
    mitgeschickte Felder werden geändert (siehe model_dump(exclude_unset=True)
    im Router) - so kann z.B. owner_id gezielt auf null gesetzt werden
    (Verknüpfung entfernen), ohne alle anderen Felder erneut mitzuschicken.
    Rollen-Exklusivität kann hier NICHT geprüft werden (PATCH kennt den
    bestehenden DB-Zustand nicht) - das passiert im Router nach dem Merge.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=100)
    is_admin: bool | None = None
    owner_id: int | None = None
    tenant_id: int | None = None
    property_assignments: list[PropertyAssignmentIn] | None = None


class UserAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    email: str
    is_admin: bool
    must_change_password: bool
    owner_id: int | None
    tenant_id: int | None
    created_at: datetime
    property_assignments: list[PropertyAssignmentOut] = Field(default_factory=list)