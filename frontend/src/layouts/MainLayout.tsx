// frontend/src/layouts/MainLayout.tsx
import { Outlet } from "react-router-dom";

import { PropertyProvider } from "../context/PropertyContext";
import { Footer } from "./Footer";
import { Navbar } from "./Navbar";
import { Sidebar } from "./Sidebar";
import "./MainLayout.css";

/**
 * Rahmen für alle "normalen" Seiten. PropertyProvider stellt die zentrale
 * Liegenschaftsauswahl (Sidebar-Dropdown) für alle darunterliegenden Seiten
 * bereit, damit sie nicht mehr jede einzeln einen eigenen Selector pflegen.
 */
export function MainLayout() {
  return (
    <PropertyProvider>
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
    </PropertyProvider>
  );
}