import type { PropsWithChildren } from "react";
import { Navigate } from "react-router-dom";

import { useCurrentUser } from "../features/auth/useAuth";

export function ProtectedRoute({ children }: PropsWithChildren) {
  const { data: user, isLoading, isError } = useCurrentUser();

  // TODO Phase 2: echter Spinner statt null, sobald es dafür einen
  // gemeinsamen Loading-Baustein in components/ gibt.
  if (isLoading) return null;
  if (isError || !user) return <Navigate to="/login" replace />;

  return <>{children}</>;
}
