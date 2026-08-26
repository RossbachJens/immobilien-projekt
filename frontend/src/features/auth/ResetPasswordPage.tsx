// frontend/src/features/auth/ResetPasswordPage.tsx
import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { Card } from "../../components/Card";
import { useResetPassword } from "./useAuth";
import "./ResetPasswordPage.css";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const navigate = useNavigate();
  const resetPasswordMutation = useResetPassword();

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setValidationError(null);

    if (newPassword !== confirmPassword) {
      setValidationError("Die Passwörter stimmen nicht überein.");
      return;
    }

    resetPasswordMutation.mutate(
      { token, new_password: newPassword },
      { onSuccess: () => navigate("/login") },
    );
  }

  if (!token) {
    return (
      <div className="reset-password-page">
        <Card>
          <h1>Passwort zurücksetzen</h1>
          <p>Dieser Link ist unvollständig oder ungültig. Bitte fordere einen neuen Reset-Link an.</p>
          <p>
            <Link to="/forgot-password">Neuen Link anfordern</Link>
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="reset-password-page">
      <Card>
        <h1>Neues Passwort vergeben</h1>
        <form onSubmit={handleSubmit} className="reset-password-form">
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
          {validationError && <p className="reset-password-form__error">{validationError}</p>}
          {resetPasswordMutation.isError && (
            <p className="reset-password-form__error">
              Token ungültig oder abgelaufen. Bitte fordere einen neuen Reset-Link an.
            </p>
          )}
          <button type="submit" disabled={resetPasswordMutation.isPending}>
            {resetPasswordMutation.isPending ? "Wird gespeichert…" : "Passwort setzen"}
          </button>
        </form>
      </Card>
    </div>
  );
}