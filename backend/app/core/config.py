from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Zentrale Konfiguration. Werte werden aus Umgebungsvariablen bzw. einer
    .env-Datei geladen (siehe .env.example) — niemals hier hart kodieren.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Datenbank
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/immobilien"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    password_reset_token_expire_minutes: int = 30

    # DSGVO: Schlüssel zur Verschlüsselung von IBAN/BIC (pgcrypto).
    # MUSS in Produktion aus einem Secret-Manager kommen, nicht aus .env im Repo.
    pii_encryption_key: str = "change-me-in-production"

    # Google OAuth2 (SSO)
    google_client_id: str | None = None
    google_client_secret: str | None = None

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    environment: str = "development"


settings = Settings()
