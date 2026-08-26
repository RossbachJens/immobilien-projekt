// frontend/src/features/owners/api.ts
import { apiClient } from "../../api/client";

export interface OwnerOption {
  owner_id: number;
  first_name: string | null;
  last_name: string;
  company_name: string | null;
}

export async function listOwners(): Promise<OwnerOption[]> {
  const { data } = await apiClient.get<OwnerOption[]>("/owners");
  return data;
}