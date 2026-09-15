// frontend/src/layouts/Sidebar.tsx
import { NavLink } from "react-router-dom";

import { useCurrentProperty } from "../context/PropertyContext";
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
  { to: "/journal-entries", label: "Buchhaltung" },
  { to: "/hausgeld-overview", label: "Hausgeldübersicht" },
  { to: "/resolutions", label: "Beschluss-Sammlung" },
  { to: "/budget-plans", label: "Wirtschaftsplan" },
  { to: "/special-assessments", label: "Sonderumlagen" },
  { to: "/settlement-periods", label: "Nebenkostenabrechnung" },
  { to: "/allocation-keys", label: "Umlageschlüssel" },
  { to: "/bank-accounts", label: "Bankkonten" },
  { to: "/meetings", label: "Versammlungen" },
  { to: "/documents", label: "Dokumente" },
];

/**
 * Linke Navigations-Sidebar. Trägt seit der zentralen Liegenschaftsauswahl
 * zusätzlich das Property-Dropdown oberhalb der Modul-Links (siehe
 * PropertyContext.tsx) - Feature-Seiten lesen die Auswahl über
 * useCurrentProperty() statt sie selbst zu verwalten.
 */
export function Sidebar() {
  const { data: user } = useCurrentUser();
  const { propertyId, properties, isLoading, setPropertyId } = useCurrentProperty();

  if (!user) return null;

  return (
    <aside className="sidebar">
      <label className="sidebar__property-select">
        Liegenschaft
        <select
          value={propertyId ?? ""}
          onChange={(e) => setPropertyId(e.target.value ? Number(e.target.value) : null)}
          disabled={isLoading || properties.length === 0}
        >
          {properties.length === 0 && <option value="">– keine Liegenschaft –</option>}
          {properties.map((p) => (
            <option key={p.property_id} value={p.property_id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>

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
          <>
            <NavLink
              to="/users"
              className={({ isActive }) =>
                "sidebar__link" + (isActive ? " sidebar__link--active" : "")
              }
            >
              Nutzerverwaltung
            </NavLink>
            <NavLink
              to="/backups"
              className={({ isActive }) =>
                "sidebar__link" + (isActive ? " sidebar__link--active" : "")
              }
            >
              Backups
            </NavLink>
          </>
        )}
      </nav>
    </aside>
  );
}