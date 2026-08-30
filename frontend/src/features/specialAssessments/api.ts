// frontend/src/features/specialAssessments/api.ts
import { apiClient } from "../../api/client";

export type SpecialAssessmentStatus = "Geplant" | "Eingefordert" | "Storniert";

export interface UnitSpecialAssessmentShare {
  unit_assessment_id: number;
  assessment_id: number;
  unit_id: number;
  allocated_assessment_amount: number;
  is_paid: boolean;
}

export interface SpecialAssessment {
  assessment_id: number;
  property_id: number;
  resolution_id: number | null;
  title: string;
  total_required_amount: number;
  due_date: string;
  status: SpecialAssessmentStatus;
  created_at: string;
  unit_shares: UnitSpecialAssessmentShare[];
}

export interface SpecialAssessmentPayload {
  property_id: number;
  title: string;
  total_required_amount: number;
  due_date: string;
  allocation_key_type: string;
  reference_year: number;
  resolution_id?: number | null;
}

export async function listSpecialAssessments(propertyId?: number): Promise<SpecialAssessment[]> {
  const { data } = await apiClient.get<SpecialAssessment[]>("/special-assessments", {
    params: propertyId ? { property_id: propertyId } : undefined,
  });
  return data;
}

export async function createSpecialAssessment(payload: SpecialAssessmentPayload): Promise<SpecialAssessment> {
  const { data } = await apiClient.post<SpecialAssessment>("/special-assessments", payload);
  return data;
}

export async function updateSpecialAssessmentStatus(
  assessmentId: number,
  status: SpecialAssessmentStatus,
): Promise<SpecialAssessment> {
  const { data } = await apiClient.patch<SpecialAssessment>(`/special-assessments/${assessmentId}`, { status });
  return data;
}

export async function updateSharePaymentStatus(
  assessmentId: number,
  unitAssessmentId: number,
  isPaid: boolean,
): Promise<UnitSpecialAssessmentShare> {
  const { data } = await apiClient.patch<UnitSpecialAssessmentShare>(
    `/special-assessments/${assessmentId}/shares/${unitAssessmentId}`,
    { is_paid: isPaid },
  );
  return data;
}