// frontend/src/features/leases/api.ts
import { apiClient } from "../../api/client";

export type LeaseStatus = "aktiv" | "beendet" | "gekuendigt";

export interface Lease {
  lease_id: number;
  unit_id: number;
  tenant_id: number;
  start_date: string;
  end_date: string | null;
  cold_rent: number;
  additional_costs_prepayment: number;
  status: LeaseStatus;
  created_at: string;
}

export async function listUnitLeases(unitId: number): Promise<Lease[]> {
  const { data } = await apiClient.get<Lease[]>(`/units/${unitId}/leases`);
  return data;
}