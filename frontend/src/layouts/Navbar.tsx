// frontend/src/layouts/Navbar.tsx
import { Link } from "react-router-dom";

import { useCurrentUser, useLogout } from "../features/auth/useAuth";
import "./Navbar.css";

/**
 * Reine Kopfzeile: Logo + Nutzer-/Logout-Bereich. Die frühere
 * Modul-Navigation (`<nav>` mit den Feature-Links) sitzt seit Phase 4 in
 * der linken Sidebar (siehe Sidebar.tsx) - zu viele gleichrangige Module
 * für eine horizontale Leiste, siehe PROJECTPLAN.md.
 */
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
