// frontend/src/features/owners/api.ts
import { apiClient } from "../../api/client";

export interface Owner {
  owner_id: number;
  first_name: string | null;
  last_name: string;
  company_name: string | null;
  email: string | null;
  phone: string | null;
  street_and_number: string;
  postal_code: string | null;
  city: string | null;
  bank_name: string | null;
  iban_last4: string | null;
  sepa_mandate_reference: string | null;
  sepa_granted_at: string | null;
  created_at: string;
  has_online_access: boolean;
}

// Für Dropdowns (z.B. UserForm) - Owner ist strukturell kompatibel.
export type OwnerOption = Pick<Owner, "owner_id" | "first_name" | "last_name" | "company_name">;

export interface OwnerPayload {
  first_name?: string | null;
  last_name: string;
  company_name?: string | null;
  email?: string | null;
  phone?: string | null;
  street_and_number: string;
  postal_code?: string | null;
  city?: string | null;
  bank_name?: string | null;
  iban?: string | null;
  bic?: string | null;
  sepa_mandate_reference?: string | null;
  sepa_granted_at?: string | null;
}

export async function listOwners(): Promise<Owner[]> {
  const { data } = await apiClient.get<Owner[]>("/owners");
  return data;
}

export async function createOwner(payload: OwnerPayload): Promise<Owner> {
  const { data } = await apiClient.post<Owner>("/owners", payload);
  return data;
}

export async function updateOwner(ownerId: number, payload: Partial<OwnerPayload>): Promise<Owner> {
  const { data } = await apiClient.patch<Owner>(`/owners/${ownerId}`, payload);
  return data;
}

export async function deleteOwner(ownerId: number): Promise<void> {
  await apiClient.delete(`/owners/${ownerId}`);
}