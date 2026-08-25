import { Navigate, Route, Routes } from "react-router-dom";

import { ForgotPasswordPage } from "../features/auth/ForgotPasswordPage";
import { LoginPage } from "../features/auth/LoginPage";
import { ResetPasswordPage } from "../features/auth/ResetPasswordPage";
import { HealthStatus } from "../features/health/HealthStatus";
import { PropertiesPage } from "../features/properties/PropertiesPage";
import { UsersPage } from "../features/users/UsersPage";
import { MainLayout } from "../layouts/MainLayout";
import { AdminRoute } from "./AdminRoute";
import { ProtectedRoute } from "./ProtectedRoute";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
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
         <Route
          path="/users"
          element={
            <AdminRoute>
              <UsersPage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}