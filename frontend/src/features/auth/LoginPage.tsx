// frontend/src/features/auth/LoginPage.tsx — Link ergänzen
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { apiClient } from "../../api/client";
import { Card } from "../../components/Card";
import { useLogin } from "./useAuth";
import "./LoginPage.css";

const GOOGLE_ERROR_MESSAGES: Record<string, string> = {
  denied: "Google-Anmeldung abgebrochen.",
  state_mismatch: "Sitzung abgelaufen - bitte erneut versuchen.",
  email_not_verified: "Die E-Mail-Adresse deines Google-Kontos ist nicht verifiziert.",
  no_matching_account:
    "Kein Konto mit dieser E-Mail-Adresse gefunden - bitte an einen Administrator wenden.",
  account_conflict: "Diese Google-Anmeldung konnte keinem Konto eindeutig zugeordnet werden.",
  not_configured: "Google-Anmeldung ist auf diesem Server nicht verfügbar.",
  google_error: "Google-Anmeldung fehlgeschlagen - bitte erneut versuchen.",
};

export function LoginPage() {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();
  const loginMutation = useLogin();
  const [searchParams] = useSearchParams();
  const googleError = searchParams.get("google_error");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    loginMutation.mutate(
      { identifier, password },
      { onSuccess: () => navigate("/") },
    );
  }

  function handleGoogleLogin() {
    // Volle Seitennavigation statt axios-Aufruf - der OAuth-Consent-Screen
    // von Google erfordert einen echten Browser-Redirect, keinen AJAX-Call.
    window.location.href = `${apiClient.defaults.baseURL}/auth/google/login`;
  }

  return (
    <div className="login-page">
      <Card>
        <h1>Anmelden</h1>
        {googleError && (
          <p className="login-form__error">
            {GOOGLE_ERROR_MESSAGES[googleError] ?? "Google-Anmeldung fehlgeschlagen."}
          </p>
        )}
        <form onSubmit={handleSubmit} className="login-form">
          <label>
            E-Mail oder Name
            <input
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label>
            Passwort
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {loginMutation.isError && (
            <p className="login-form__error">E-Mail oder Passwort falsch.</p>
          )}
          <button type="submit" disabled={loginMutation.isPending}>
            {loginMutation.isPending ? "Anmeldung läuft…" : "Anmelden"}
          </button>
        </form>
        <button type="button" className="login-page__google-button" onClick={handleGoogleLogin}>
          Mit Google anmelden
        </button>
        <p className="login-page__forgot">
          <Link to="/forgot-password">Passwort vergessen?</Link>
        </p>
      </Card>
    </div>
  );
}