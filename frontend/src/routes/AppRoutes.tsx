import { Route, Routes } from "react-router-dom";

import { HealthStatus } from "../features/health/HealthStatus";
import { MainLayout } from "../layouts/MainLayout";

/**
 * Ab Phase 1 kommen hier weitere <Route>-Einträge dazu (z.B. /login),
 * Phase 2 dann /properties etc. - jedes Feature bringt seine eigene
 * Seiten-Komponente mit, AppRoutes verweist nur darauf.
 */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<HealthStatus />} />
      </Route>
    </Routes>
  );
}
