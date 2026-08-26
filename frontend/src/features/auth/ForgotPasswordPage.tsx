// frontend/src/features/auth/ForgotPasswordPage.tsx
import { useState } from "react";
import type { FormEvent } from "react";
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
          <button type="submit" disabled={forgotPasswordMutation.isPending}>
            {forgotPasswordMutation.isPending ? "Wird gesendet…" : "Reset-Link anfordern"}
          </button>
        </form>

        {result && (
          <div className="forgot-password-page__result">
            <p>{result.detail}</p>
            {result.dev_reset_token && (
              <p>
                Entwicklungsmodus – kein E-Mail-Versand konfiguriert:{" "}
                <Link to={`/reset-password?token=${result.dev_reset_token}`}>
                  Passwort jetzt zurücksetzen
                </Link>
              </p>
            )}
          </div>
        )}

        <p className="forgot-password-page__back">
          <Link to="/login">Zurück zum Login</Link>
        </p>
      </Card>
    </div>
  );
}