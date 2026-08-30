// frontend/src/features/resolutions/api.ts
import { apiClient } from "../../api/client";

export interface Resolution {
  resolution_id: number;
  property_id: number;
  lfd_nr: number;
  resolution_date: string;
  title: string;
  description: string | null;
  resolution_type: string | null;
  meeting_location: string | null;
  agenda_item: string | null;
  proposed_by_owner_id: number | null;
  court_name: string | null;
  court_case_number: string | null;
  court_decision_date: string | null;
  court_ruling_text: string | null;
  court_parties: string | null;
  status_note: string | null;
  created_by: number | null;
  refers_to_resolution_id: number | null;
  created_at: string;
}

export interface ResolutionPayload {
  property_id: number;
  resolution_date: string;
  title: string;
  description?: string | null;
  resolution_type?: string | null;
  meeting_location?: string | null;
  agenda_item?: string | null;
  court_name?: string | null;
  court_case_number?: string | null;
  court_decision_date?: string | null;
  court_ruling_text?: string | null;
  court_parties?: string | null;
  status_note?: string | null;
  refers_to_resolution_id?: number | null;
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