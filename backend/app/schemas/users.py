from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.zuordnungen import PropertyRole


class PropertyAssignmentIn(BaseModel):
    property_id: int
    role: PropertyRole = PropertyRole.verwalter


class PropertyAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    property_id: int
    role: PropertyRole


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=100)
    # max_length=72: bcrypt truncated/verweigert laengere Passwoerter
    # (siehe backend/app/core/security.py) - hier frueh statt erst beim Hashen ablehnen.
    password: str = Field(min_length=8, max_length=72)
    is_admin: bool = False
    # Nur relevant fuer is_admin=False: Admins haben ueber is_admin globalen
    # Zugriff (app/core/roles.py::resolve_role) und brauchen keine Zuordnung.
    # Verwalter/Buchhalter/Lesezugriff ergibt sich granular je Objekt hieraus.
    property_assignments: list[PropertyAssignmentIn] = Field(default_factory=list)


class UserAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    email: str
    is_admin: bool
    must_change_password: bool
    created_at: datetime
    property_assignments: list[PropertyAssignmentOut] = Field(default_factory=list)