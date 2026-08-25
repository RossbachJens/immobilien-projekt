import { Route, Routes } from "react-router-dom";

import { LoginPage } from "../features/auth/LoginPage";
import { HealthStatus } from "../features/health/HealthStatus";
import { MainLayout } from "../layouts/MainLayout";
import { ProtectedRoute } from "./ProtectedRoute";

export function AppRoutes() {
  return (
    <Routes>
      {/* /login bewusst außerhalb von MainLayout - keine Navbar mit
          Logout-Button, solange man noch gar nicht eingeloggt ist. */}
      <Route path="/login" element={<LoginPage />} />

      <Route element={<MainLayout />}>
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <HealthStatus />
            </ProtectedRoute>
          }
        />
        {/* Ab Phase 2: /properties, /units, ... - jeweils in ProtectedRoute */}
      </Route>
    </Routes>
  );
}
