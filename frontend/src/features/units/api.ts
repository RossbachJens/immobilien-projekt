// frontend/src/features/units/api.ts
import { apiClient } from "../../api/client";

export type UnitType = "Wohnung" | "Stellplatz" | "Gewerbe";

export interface Unit {
  unit_id: number;
  property_id: number;
  unit_number: string;
  floor: string | null;
  square_meters: number;
  mea: number | null;
  unit_type: UnitType | null;
}

export interface UnitPayload {
  property_id: number;
  unit_number: string;
  floor?: string | null;
  square_meters: number;
  mea?: number | null;
  unit_type?: UnitType | null;
}

// frontend/src/features/units/api.ts — OwnerAssignment* ersetzen
export interface OwnerAssignment {
  history_id: number;
  unit_id: number;
  owner_id: number;
  ownership_share: number;
  valid_from: string;
  valid_to: string | null;
  owner_number: string | null;
}

export interface OwnerAssignmentPayload {
  owner_id: number;
  ownership_share: number;
  valid_from: string;
  valid_to?: string | null;
  owner_number?: string | null;
}

export interface OwnerAssignmentUpdatePayload {
  ownership_share?: number;
  valid_to?: string | null;
  owner_number?: string | null;
}
}

export async function listUnits(propertyId?: number): Promise<Unit[]> {
  const { data } = await apiClient.get<Unit[]>("/units", {
    params: propertyId ? { property_id: propertyId } : undefined,
  });
  return data;
}

export async function createUnit(payload: UnitPayload): Promise<Unit> {
  const { data } = await apiClient.post<Unit>("/units", payload);
  return data;
}

export async function updateUnit(unitId: number, payload: Partial<UnitPayload>): Promise<Unit> {
  const { data } = await apiClient.patch<Unit>(`/units/${unitId}`, payload);
  return data;
}

export async function deleteUnit(unitId: number): Promise<void> {
  await apiClient.delete(`/units/${unitId}`);
}

export async function listUnitOwners(unitId: number): Promise<OwnerAssignment[]> {
  const { data } = await apiClient.get<OwnerAssignment[]>(`/units/${unitId}/owners`);
  return data;
}

export async function assignOwner(unitId: number, payload: OwnerAssignmentPayload): Promise<OwnerAssignment> {
  const { data } = await apiClient.post<OwnerAssignment>(`/units/${unitId}/owners`, payload);
  return data;
}

export async function updateOwnerAssignment(
  unitId: number,
  historyId: number,
  payload: OwnerAssignmentUpdatePayload,
): Promise<OwnerAssignment> {
  const { data } = await apiClient.patch<OwnerAssignment>(`/units/${unitId}/owners/${historyId}`, payload);
  return data;
}

export async function deleteOwnerAssignment(unitId: number, historyId: number): Promise<void> {
  await apiClient.delete(`/units/${unitId}/owners/${historyId}`);
}