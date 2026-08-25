from app.models.stammdaten import User


def resolve_role(user: User) -> str:
    """
    Leitet die effektive Rolle aus dem Datenmodell ab (kein separates
    Rollen-Enum, da Zugriff je nach Objekt/Verknüpfung variiert):
      - is_admin=True     -> "admin"        (globaler Zugriff, umgeht RLS)
      - owner_id gesetzt   -> "eigentuemer"
      - tenant_id gesetzt  -> "mieter"
      - sonst              -> "verwalter"   (Zuordnung zu Objekten erfolgt
                               granular über user_properties, s. Phase 2/RLS)
    """
    if user.is_admin:
        return "admin"
    if user.owner_id is not None:
        return "eigentuemer"
    if user.tenant_id is not None:
        return "mieter"
    return "verwalter"
