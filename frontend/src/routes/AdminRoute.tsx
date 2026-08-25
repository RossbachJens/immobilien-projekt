import type { PropsWithChildren } from "react";
import { Navigate } from "react-router-dom";

import { useCurrentUser } from "../features/auth/useAuth";

/**
 * Wie ProtectedRoute, verlangt zusaetzlich is_admin=true. Rein UX-seitig -
 * die eigentliche Durchsetzung passiert serverseitig ueber
 * app/core/deps.py::get_current_admin (403 bei fehlender Berechtigung).
 */
export function AdminRoute({ children }: PropsWithChildren) {
  const { data: user, isLoading, isError } = useCurrentUser();

  if (isLoading) return null;
  if (isError || !user) return <Navigate to="/login" replace />;
  if (!user.is_admin) return <Navigate to="/" replace />;

  return <>{children}</>;
}