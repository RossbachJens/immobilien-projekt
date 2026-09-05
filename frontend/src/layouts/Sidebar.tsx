// frontend/src/layouts/Sidebar.tsx
import { NavLink } from "react-router-dom";

import { useCurrentUser } from "../features/auth/useAuth";
import "./Sidebar.css";

interface NavItem {
  to: string;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/properties", label: "Liegenschaften" },
  { to: "/units", label: "Einheiten" },
  { to: "/owners", label: "Eigentümer" },
  { to: "/tenants", label: "Mieter" },
  // frontend/src/layouts/Sidebar.tsx — NAV_ITEMS ergänzen (nach "Buchhaltung")
  { to: "/journal-entries", label: "Buchhaltung" },
  { to: "/hausgeld-overview", label: "Hausgeldübersicht" },
  { to: "/resolutions", label: "Beschluss-Sammlung" },
  { to: "/budget-plans", label: "Wirtschaftsplan" },
  { to: "/special-assessments", label: "Sonderumlagen" },
  { to: "/settlement-periods", label: "Nebenkostenabrechnung" },
  { to: "/allocation-keys", label: "Umlageschlüssel" },
  { to: "/bank-accounts", label: "Bankkonten" },
  { to: "/meetings", label: "Versammlungen" },
  
];

/**
 * Linke Navigations-Sidebar. War bis Phase 3 Teil der Navbar (horizontale
 * Link-Leiste) - ab Phase 4 sind es zu viele gleichrangige Module für eine
 * Kopfzeile geworden (siehe PROJECTPLAN.md, Grundsatzentscheidung
 * "Navigation"). Rendert nichts, solange kein User eingeloggt ist - analog
 * zum bisherigen Verhalten in Navbar.
 */
export function Sidebar() {
  const { data: user } = useCurrentUser();

  if (!user) return null;

  return (
    <aside className="sidebar">
      <nav className="sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              "sidebar__link" + (isActive ? " sidebar__link--active" : "")
            }
          >
            {item.label}
          </NavLink>
        ))}
        {user.is_admin && (
          <NavLink
            to="/users"
            className={({ isActive }) =>
              "sidebar__link" + (isActive ? " sidebar__link--active" : "")
            }
          >
            Nutzerverwaltung
          </NavLink>
        )}
      </nav>
    </aside>
  );
}
