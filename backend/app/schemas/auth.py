from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    # Login funktioniert wahlweise mit E-Mail oder Name (app/routers/auth.py
    # ::login) - "identifier" statt "email", weil hier beides reinkommen kann.
    identifier: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    email: str
    must_change_password: bool


class ForgotPasswordRequest(BaseModel):
    identifier: str


class ForgotPasswordResponse(BaseModel):
    detail: str
    # Nur befuellt, wenn settings.environment != "production" UND ein Konto
    # gefunden wurde - Ersatz fuer den noch fehlenden E-Mail-Versand
    # (PROJECTPLAN.md, Phase 7). Niemals in Produktion befuellen.
    dev_reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)