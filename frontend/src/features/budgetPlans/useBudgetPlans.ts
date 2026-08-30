// frontend/src/features/budgetPlans/useBudgetPlans.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createBudgetPlan,
  createBudgetPosition,
  listBudgetPlans,
  listBudgetPositions,
  updateBudgetPlanStatus,
  type BudgetPlanPayload,
  type BudgetPlanStatus,
  type BudgetPositionPayload,
} from "./api";

const plansKey = (propertyId?: number) => ["budget-plans", propertyId ?? "all"];
const positionsKey = (budgetId: number) => ["budget-plans", budgetId, "positions"];

export function useBudgetPlans(propertyId?: number) {
  return useQuery({
    queryKey: plansKey(propertyId),
    queryFn: () => listBudgetPlans(propertyId),
    enabled: propertyId !== undefined,
  });
}

export function useCreateBudgetPlan(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BudgetPlanPayload) => createBudgetPlan(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: plansKey(propertyId) }),
  });
}

// frontend/src/features/budgetPlans/useBudgetPlans.ts — useUpdateBudgetPlanStatus ersetzen
export function useUpdateBudgetPlan(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ budgetId, payload }: { budgetId: number; payload: BudgetPlanStatusPayload }) =>
      updateBudgetPlan(budgetId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: plansKey(propertyId) }),
  });
}

export function useBudgetPositions(budgetId: number | undefined) {
  return useQuery({
    queryKey: positionsKey(budgetId ?? -1),
    queryFn: () => listBudgetPositions(budgetId as number),
    enabled: budgetId !== undefined,
  });
}

export function useCreateBudgetPosition(budgetId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BudgetPositionPayload) => createBudgetPosition(budgetId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: positionsKey(budgetId) }),
  });
}