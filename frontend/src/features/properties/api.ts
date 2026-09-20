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
  has_logo: boolean;
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

export async function uploadPropertyLogo(propertyId: number, file: File): Promise<Property> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.put<Property>(`/properties/${propertyId}/logo`, formData);
  return data;
}

export async function deletePropertyLogo(propertyId: number): Promise<void> {
  await apiClient.delete(`/properties/${propertyId}/logo`);
}

export function propertyLogoUrl(propertyId: number): string {
  return `${apiClient.defaults.baseURL}/properties/${propertyId}/logo`;
}