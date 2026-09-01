// frontend/src/features/budgetPlans/api.ts — vollständig ersetzen
import { apiClient } from "../../api/client";

export type BudgetPlanStatus = "Entwurf" | "Beschlossen" | "Inaktiv";

export interface BudgetPlan {
  budget_id: number;
  property_id: number;
  fiscal_year: number;
  title: string;
  status: BudgetPlanStatus;
  resolution_id: number | null;
  created_at: string;
}

export interface BudgetPlanPayload {
  property_id: number;
  fiscal_year: number;
  title: string;
  resolution_id?: number | null;
}

export interface BudgetPlanStatusPayload {
  status: BudgetPlanStatus;
  resolution_id?: number | null;
}

export interface UnitBudgetShare {
  share_id: number;
  position_id: number;
  unit_id: number;
  allocated_planned_amount: number;
  monthly_installment: number;
}

export interface BudgetPosition {
  position_id: number;
  budget_id: number;
  account_id: number;
  description: string | null;
  planned_amount: number;
  allocation_key_type: string;
  unit_shares: UnitBudgetShare[];
}

export interface BudgetPositionPayload {
  account_id: number;
  description?: string | null;
  planned_amount: number;
  allocation_key_type: string;
}

// Bewusst dieselben Felder wie BudgetPositionPayload, aber alle optional -
// Positionen sind nur "bis zum Beschluss" (Plan-Status "Entwurf") änderbar,
// siehe app/routers/budget_plans.py::update_budget_position.
export interface BudgetPositionUpdatePayload {
  account_id?: number;
  description?: string | null;
  planned_amount?: number;
  allocation_key_type?: string;
}

export async function listBudgetPlans(propertyId?: number): Promise<BudgetPlan[]> {
  const { data } = await apiClient.get<BudgetPlan[]>("/budget-plans", {
    params: propertyId ? { property_id: propertyId } : undefined,
  });
  return data;
}

export async function createBudgetPlan(payload: BudgetPlanPayload): Promise<BudgetPlan> {
  const { data } = await apiClient.post<BudgetPlan>("/budget-plans", payload);
  return data;
}

export async function updateBudgetPlan(budgetId: number, payload: BudgetPlanStatusPayload): Promise<BudgetPlan> {
  const { data } = await apiClient.patch<BudgetPlan>(`/budget-plans/${budgetId}`, payload);
  return data;
}

export async function listBudgetPositions(budgetId: number): Promise<BudgetPosition[]> {
  const { data } = await apiClient.get<BudgetPosition[]>(`/budget-plans/${budgetId}/positions`);
  return data;
}

export async function createBudgetPosition(
  budgetId: number,
  payload: BudgetPositionPayload,
): Promise<BudgetPosition> {
  const { data } = await apiClient.post<BudgetPosition>(`/budget-plans/${budgetId}/positions`, payload);
  return data;
}

export async function updateBudgetPosition(
  budgetId: number,
  positionId: number,
  payload: BudgetPositionUpdatePayload,
): Promise<BudgetPosition> {
  const { data } = await apiClient.patch<BudgetPosition>(
    `/budget-plans/${budgetId}/positions/${positionId}`,
    payload,
  );
  return data;
}

export async function deleteBudgetPosition(budgetId: number, positionId: number): Promise<void> {
  await apiClient.delete(`/budget-plans/${budgetId}/positions/${positionId}`);
}
