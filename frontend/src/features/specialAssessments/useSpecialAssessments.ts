// frontend/src/features/specialAssessments/useSpecialAssessments.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createSpecialAssessment,
  listSpecialAssessments,
  updateSharePaymentStatus,
  updateSpecialAssessmentStatus,
  type SpecialAssessmentPayload,
  type SpecialAssessmentStatus,
} from "./api";

const key = (propertyId?: number) => ["special-assessments", propertyId ?? "all"];

export function useSpecialAssessments(propertyId?: number) {
  return useQuery({
    queryKey: key(propertyId),
    queryFn: () => listSpecialAssessments(propertyId),
    enabled: propertyId !== undefined,
  });
}

export function useCreateSpecialAssessment(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SpecialAssessmentPayload) => createSpecialAssessment(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key(propertyId) }),
  });
}

export function useUpdateSpecialAssessmentStatus(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ assessmentId, status }: { assessmentId: number; status: SpecialAssessmentStatus }) =>
      updateSpecialAssessmentStatus(assessmentId, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key(propertyId) }),
  });
}

export function useUpdateSharePaymentStatus(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      assessmentId,
      unitAssessmentId,
      isPaid,
    }: {
      assessmentId: number;
      unitAssessmentId: number;
      isPaid: boolean;
    }) => updateSharePaymentStatus(assessmentId, unitAssessmentId, isPaid),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key(propertyId) }),
  });
}