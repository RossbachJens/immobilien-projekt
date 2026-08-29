// frontend/src/layouts/Navbar.tsx
import { Link } from "react-router-dom";

import { useCurrentUser, useLogout } from "../features/auth/useAuth";
import "./Navbar.css";

export function Navbar() {
  const { data: user } = useCurrentUser();
  const logoutMutation = useLogout();

  return (
    <header className="navbar">
      <div className="navbar__inner">
        <Link to="/" className="navbar__logo">
          Immobilien- &amp; WEG-Verwaltung
        </Link>
{user && (
  <nav className="navbar__links">
    <Link to="/properties">Liegenschaften</Link>
    <Link to="/units">Einheiten</Link>
    <Link to="/owners">Eigentümer</Link>
    <Link to="/tenants">Mieter</Link>
    <Link to="/journal-entries">Buchhaltung</Link>
    {user.is_admin && <Link to="/users">Nutzerverwaltung</Link>}
  </nav>
)}
        {user && (
          <div className="navbar__user">
            <span>{user.name}</span>
            <button type="button" className="navbar__logout" onClick={() => logoutMutation.mutate()}>
              Abmelden
            </button>
          </div>
        )}
      </div>
    </header>
  );
}