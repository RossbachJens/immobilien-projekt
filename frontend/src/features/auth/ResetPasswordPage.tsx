import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { Card } from "../../components/Card";
import { useResetPassword } from "./useAuth";
import "./ResetPasswordPage.css";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  // Token kommt normalerweise per Query-Param aus dem (noch simulierten)
  // E-Mail-Link - manuelles Einfügen bleibt trotzdem möglich.
  const [token, setToken] = useState(searchParams.get("token") ?? "");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [mismatchError, setMismatchError] = useState(false);
  const resetPasswordMutation = useResetPassword();

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      setMismatchError(true);
      return;
    }
    setMismatchError(false);
    resetPasswordMutation.mutate(
      { token, new_password: newPassword },
      { onSuccess: () => navigate("/login") },
    );
  }

  return (
    <div className="reset-password-page">
      <Card>
        <h1>Neues Passwort festlegen</h1>
        <form onSubmit={handleSubmit} className="reset-password-form">
          <label>
            Reset-Token
            <input type="text" value={token} onChange={(e) => setToken(e.target.value)} required />
          </label>
          <label>
            Neues Passwort
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>
          <label>
            Neues Passwort bestätigen
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>
          {mismatchError && (
            <p className="reset-password-form__error">Die Passwörter stimmen nicht überein.</p>
          )}
          {resetPasswordMutation.isError && (
            <p className="reset-password-form__error">
              Token ungültig oder abgelaufen. Bitte fordern Sie einen neuen Link an.
            </p>
          )}
          <button type="submit" disabled={resetPasswordMutation.isPending}>
            {resetPasswordMutation.isPending ? "Wird gespeichert…" : "Passwort speichern"}
          </button>
        </form>
        <p className="reset-password-page__back">
          <Link to="/login">Zurück zur Anmeldung</Link>
        </p>
      </Card>
    </div>
  );
}