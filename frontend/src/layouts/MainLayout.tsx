// frontend/src/layouts/MainLayout.tsx
import { Outlet } from "react-router-dom";

import { Footer } from "./Footer";
import { Navbar } from "./Navbar";
import { Sidebar } from "./Sidebar";
import "./MainLayout.css";

/**
 * Rahmen für alle "normalen" Seiten. Konkrete Seiteninhalte kommen
 * über die Router-Konfiguration in <Outlet /> - MainLayout selbst
 * kennt keine Feature-Details. Seit Phase 4: Navbar (Kopfzeile) +
 * Sidebar (Modul-Navigation) + Content nebeneinander statt Navbar
 * mit eingebetteter Link-Leiste.
 */
export function MainLayout() {
  return (
    <div className="main-layout">
      <Navbar />
      <div className="main-layout__body">
        <Sidebar />
        <main className="main-layout__content">
          <Outlet />
        </main>
      </div>
      <Footer />
    </div>
  );
}
