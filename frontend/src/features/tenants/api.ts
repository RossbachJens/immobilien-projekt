// frontend/src/features/tenants/api.ts
import { apiClient } from "../../api/client";

export interface Tenant {
  tenant_id: number;
  first_name: string;
  last_name: string;
  email: string | null;
  street_and_number: string;
  postal_code: string | null;
  city: string | null;
  bank_name: string | null;
  iban_last4: string | null;
  sepa_mandate_reference: string | null;
  created_at: string;
  has_online_access: boolean;
}

export type TenantOption = Pick<Tenant, "tenant_id" | "first_name" | "last_name">;

export interface TenantPayload {
  first_name: string;
  last_name: string;
  email?: string | null;
  street_and_number: string;
  postal_code?: string | null;
  city?: string | null;
  bank_name?: string | null;
  iban?: string | null;
  bic?: string | null;
  sepa_mandate_reference?: string | null;
}

export async function listTenants(): Promise<Tenant[]> {
  const { data } = await apiClient.get<Tenant[]>("/tenants");
  return data;
}

export async function createTenant(payload: TenantPayload): Promise<Tenant> {
  const { data } = await apiClient.post<Tenant>("/tenants", payload);
  return data;
}

export async function updateTenant(tenantId: number, payload: Partial<TenantPayload>): Promise<Tenant> {
  const { data } = await apiClient.patch<Tenant>(`/tenants/${tenantId}`, payload);
  return data;
}

export async function deleteTenant(tenantId: number): Promise<void> {
  await apiClient.delete(`/tenants/${tenantId}`);
}