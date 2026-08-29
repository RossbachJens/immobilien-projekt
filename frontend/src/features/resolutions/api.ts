// frontend/src/features/resolutions/api.ts
import { apiClient } from "../../api/client";

export interface Resolution {
  resolution_id: number;
  property_id: number;
  resolution_date: string;
  title: string;
  description: string | null;
  resolution_type: string | null;
  proposed_by_owner_id: number | null;
  created_at: string;
}

export interface ResolutionPayload {
  property_id: number;
  resolution_date: string;
  title: string;
  description?: string | null;
  resolution_type?: string | null;
}

export async function listResolutions(propertyId?: number): Promise<Resolution[]> {
  const { data } = await apiClient.get<Resolution[]>("/resolutions", {
    params: propertyId ? { property_id: propertyId } : undefined,
  });
  return data;
}

export async function createResolution(payload: ResolutionPayload): Promise<Resolution> {
  const { data } = await apiClient.post<Resolution>("/resolutions", payload);
  return data;
}