import { Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "../features/auth/LoginPage";
import { HealthStatus } from "../features/health/HealthStatus";
import { PropertiesPage } from "../features/properties/PropertiesPage";
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
        <Route
          path="/properties"
          element={
            <ProtectedRoute>
              <PropertiesPage />
            </ProtectedRoute>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}