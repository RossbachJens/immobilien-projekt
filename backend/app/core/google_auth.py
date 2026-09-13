# backend/app/core/google_oauth.py
"""
Minimaler Google-OAuth2-Client für den SSO-Login-Flow (siehe
app/routers/auth.py, /auth/google/login und /auth/google/callback).

WARUM userinfo-Endpunkt statt lokaler ID-Token-Verifikation:
Der "korrekte" Weg wäre, das von Google zurückgegebene ID-Token selbst
kryptografisch zu prüfen (JWKS von Google laden/cachen, Signatur/aud/iss/exp
verifizieren) - das würde aber eine neue Abhängigkeit (google-auth) und
JWKS-Cache-Verwaltung bedeuten. Stattdessen wird das Access-Token direkt
gegen Googles userinfo-Endpunkt getauscht: Google validiert dabei implizit,
die Antwort enthält dieselben Felder (sub/email/email_verified/name). Ein
Netzwerk-Hop mehr pro Login, keine Offline-Verifikation möglich - für den
aktuellen Rahmen (selbstgehostete WEG-Verwaltung) als bewusste Vereinfachung
akzeptiert. Nutzt httpx, das schon als Abhängigkeit vorhanden ist.
"""
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

STATE_COOKIE_NAME = "google_oauth_state"
# Kurzlebig - reicht für den Consent-Screen, hält aber das CSRF-Zeitfenster
# (state-Cookie) klein.
STATE_COOKIE_MAX_AGE_SECONDS = 600


def require_google_configured() -> None:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Google-SSO ist auf diesem Server nicht konfiguriert.",
        )


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def build_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        # 'select_account' statt 'consent': wir brauchen kein Offline-
        # Refresh-Token (nur ein einmaliger Login, kein dauerhafter
        # Google-API-Zugriff) - erzwingt lediglich die Kontoauswahl, falls
        # mehrere Google-Konten im Browser eingeloggt sind.
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"


class GoogleUserInfo:
    def __init__(self, sub: str, email: str, email_verified: bool, name: str | None) -> None:
        self.sub = sub
        self.email = email
        self.email_verified = email_verified
        self.name = name


def exchange_code_for_userinfo(code: str) -> GoogleUserInfo:
    """Tauscht den Authorization-Code gegen ein Access-Token und ruft damit
    Googles userinfo-Endpunkt ab. Wirft HTTPException bei jedem Fehlschlag -
    der aufrufende Router fängt das ab und wandelt es in einen Redirect mit
    Fehlercode um (kein sinnvoller Recovery-Pfad außer erneut zu
    versuchen)."""
    with httpx.Client(timeout=10.0) as client:
        token_response = client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_response.status_code != 200:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Google-Anmeldung fehlgeschlagen (Token-Tausch)."
            )
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Google-Anmeldung fehlgeschlagen (kein Access-Token erhalten).",
            )

        userinfo_response = client.get(
            GOOGLE_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_response.status_code != 200:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Google-Anmeldung fehlgeschlagen (Profildaten nicht abrufbar).",
            )
        payload = userinfo_response.json()

    sub = payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Google-Antwort unvollständig (sub/email fehlen)."
        )

    return GoogleUserInfo(
        sub=sub,
        email=email,
        email_verified=bool(payload.get("email_verified", False)),
        name=payload.get("name"),
    )