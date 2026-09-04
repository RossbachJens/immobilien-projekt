// frontend/src/features/allocationKeys/api.ts
import { apiClient } from "../../api/client";

export interface AllocationKey {
  key_id: number;
  property_id: number;
  unit_id: number;
  key_type: string;
  numerator_value: number;
  denominator_value: number;
  valid_from_year: number;
  valid_to_year: number | null;
}

export interface AllocationKeyCreatePayload {
  property_id: number;
  unit_id: number;
  key_type: string;
  numerator_value: number;
  denominator_value: number;
  valid_from_year: number;
  valid_to_year?: number | null;
}

export interface AllocationKeyClosePayload {
  valid_to_year: number;
}

export async function listAllocationKeys(propertyId?: number): Promise<AllocationKey[]> {
  const { data } = await apiClient.get<AllocationKey[]>("/allocation-keys", {
    params: propertyId ? { property_id: propertyId } : undefined,
  });
  return data;
}

export async function createAllocationKey(payload: AllocationKeyCreatePayload): Promise<AllocationKey> {
  const { data } = await apiClient.post<AllocationKey>("/allocation-keys", payload);
  return data;
}

export async function closeAllocationKey(
  keyId: number,
  payload: AllocationKeyClosePayload,
): Promise<AllocationKey> {
  const { data } = await apiClient.patch<AllocationKey>(`/allocation-keys/${keyId}`, payload);
  return data;
}