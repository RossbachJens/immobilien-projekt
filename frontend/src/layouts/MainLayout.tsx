import { Outlet } from "react-router-dom";

import { Footer } from "./Footer";
import { Navbar } from "./Navbar";
import "./MainLayout.css";

/**
 * Rahmen für alle "normalen" Seiten. Konkrete Seiteninhalte kommen
 * über die Router-Konfiguration in <Outlet /> - MainLayout selbst
 * kennt keine Feature-Details.
 */
export function MainLayout() {
  return (
    <div className="main-layout">
      <Navbar />
      <main className="main-layout__content">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
