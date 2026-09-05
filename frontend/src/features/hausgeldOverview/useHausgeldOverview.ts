// frontend/src/features/hausgeldOverview/useHausgeldOverview.ts
import { useQuery } from "@tanstack/react-query";

import { listHausgeldOverview, listHausgeldPayments } from "./api";

export function useHausgeldOverview(propertyId?: number, fiscalYear?: number) {
  return useQuery({
    queryKey: ["hausgeld-overview", propertyId ?? "none", fiscalYear ?? "none"],
    queryFn: () => listHausgeldOverview(propertyId as number, fiscalYear as number),
    enabled: propertyId !== undefined && fiscalYear !== undefined,
  });
}

export function useHausgeldPayments(propertyId?: number, unitId?: number, fiscalYear?: number) {
  return useQuery({
    queryKey: ["hausgeld-payments", propertyId ?? "none", unitId ?? "none", fiscalYear ?? "none"],
    queryFn: () => listHausgeldPayments(propertyId as number, unitId as number, fiscalYear as number),
    enabled: propertyId !== undefined && unitId !== undefined && fiscalYear !== undefined,
  });
}