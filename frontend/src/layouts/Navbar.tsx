import { Link } from "react-router-dom";

import "./Navbar.css";

export function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar__inner">
        <Link to="/" className="navbar__logo">
          Immobilien- &amp; WEG-Verwaltung
        </Link>
        {/* Ab Phase 1: Login/Logout-Link, abhängig vom Auth-Status */}
      </div>
    </header>
  );
}
