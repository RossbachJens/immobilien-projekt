// frontend/src/routes/AdminRoute.tsx
import type { PropsWithChildren } from "react";
import { Navigate } from "react-router-dom";

import { useCurrentUser } from "../features/auth/useAuth";

export function AdminRoute({ children }: PropsWithChildren) {
  const { data: user, isLoading, isError } = useCurrentUser();

  if (isLoading) return null;
  if (isError || !user) return <Navigate to="/login" replace />;
  if (!user.is_admin) return <Navigate to="/" replace />;

  return <>{children}</>;
}