// frontend/src/features/owners/useOwners.ts
import { useQuery } from "@tanstack/react-query";

import { listOwners } from "./api";

export function useOwners() {
  return useQuery({ queryKey: ["owners"], queryFn: listOwners });
}