// frontend/src/features/leases/useLeases.ts
import { useQuery } from "@tanstack/react-query";

import { listUnitLeases } from "./api";

export function useUnitLeases(unitId: number | undefined) {
  return useQuery({
    queryKey: ["units", unitId ?? -1, "leases"],
    queryFn: () => listUnitLeases(unitId as number),
    enabled: unitId !== undefined,
  });
}