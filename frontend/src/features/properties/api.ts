// frontend/src/features/properties/api.ts
import { apiClient } from "../../api/client";

export interface Property {
  property_id: number;
  name: string;
  address: string;
  total_square_meters: number | null;
  construction_year: number | null;
  total_mea: number | null;
  description: string | null;
  created_at: string;
}

export interface PropertyPayload {
  name: string;
  address: string;
  total_square_meters?: number | null;
  construction_year?: number | null;
  total_mea?: number | null;
  description?: string | null;
}

export async function listProperties(): Promise<Property[]> {
  const { data } = await apiClient.get<Property[]>("/properties");
  return data;
}

export async function createProperty(payload: PropertyPayload): Promise<Property> {
  const { data } = await apiClient.post<Property>("/properties", payload);
  return data;
}

export async function updateProperty(propertyId: number, payload: Partial<PropertyPayload>): Promise<Property> {
  const { data } = await apiClient.patch<Property>(`/properties/${propertyId}`, payload);
  return data;
}