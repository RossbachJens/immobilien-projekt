import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { Card } from "../../components/Card";
import { useLogin } from "./useAuth";
import "./LoginPage.css";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();
  const loginMutation = useLogin();

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    loginMutation.mutate(
      { email, password },
      { onSuccess: () => navigate("/") },
    );
  }

  return (
    <div className="login-page">
      <Card>
        <h1>Anmelden</h1>
        <form onSubmit={handleSubmit} className="login-form">
          <label>
            E-Mail
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
      </Card>
    </div>
  );
}
