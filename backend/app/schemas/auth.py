from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    # Bewusst 'str' statt 'EmailStr': Letzteres braucht das Zusatzpaket
    # 'email-validator', das aktuell nicht in requirements.txt steht.
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    must_change_password: bool
