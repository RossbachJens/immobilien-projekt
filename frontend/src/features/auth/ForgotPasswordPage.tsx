import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { Card } from "../../components/Card";
import { useForgotPassword } from "./useAuth";
import "./ForgotPasswordPage.css";

export function ForgotPasswordPage() {
  const [identifier, setIdentifier] = useState("");
  const forgotPasswordMutation = useForgotPassword();

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    forgotPasswordMutation.mutate({ identifier });
  }

  const result = forgotPasswordMutation.data;

  return (
    <div className="forgot-password-page">
      <Card>
        <h1>Passwort vergessen</h1>

        {!result && (
          <form onSubmit={handleSubmit} className="forgot-password-form">
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
            {forgotPasswordMutation.isError && (
              <p className="forgot-password-form__error">
                Anfrage konnte nicht gesendet werden. Bitte später erneut versuchen.
              </p>
            )}
            <button type="submit" disabled={forgotPasswordMutation.isPending}>
              {forgotPasswordMutation.isPending ? "Wird gesendet…" : "Link anfordern"}
            </button>
          </form>
        )}

        {result && (
          <div className="forgot-password-result">
            <p>{result.detail}</p>
            {/* Nur im Development-Modus vom Backend befüllt - Ersatz für den
                noch fehlenden E-Mail-Versand (PROJECTPLAN.md, Phase 7). */}
            {result.dev_reset_token && (
              <div className="forgot-password-result__dev">
                <p>
                  <strong>Entwicklungsmodus:</strong> Kein E-Mail-Versand aktiv.
                </p>
                <Link to={`/reset-password?token=${result.dev_reset_token}`}>
                  Passwort jetzt zurücksetzen
                </Link>
              </div>
            )}
          </div>
        )}

        <p className="forgot-password-page__back">
          <Link to="/login">Zurück zur Anmeldung</Link>
        </p>
      </Card>
    </div>
  );
}