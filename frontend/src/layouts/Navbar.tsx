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
          <div className="navbar__user">
            <span>{user.email}</span>
            <button
              type="button"
              className="navbar__logout"
              onClick={() => logoutMutation.mutate()}
            >
              Abmelden
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
