// frontend/src/features/tenants/api.ts
import { apiClient } from "../../api/client";

export interface TenantOption {
  tenant_id: number;
  first_name: string;
  last_name: string;
}

export async function listTenants(): Promise<TenantOption[]> {
  const { data } = await apiClient.get<TenantOption[]>("/tenants");
  return data;
}