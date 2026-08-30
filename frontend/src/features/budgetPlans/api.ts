// frontend/src/features/budgetPlans/api.ts
import { apiClient } from "../../api/client";

export type BudgetPlanStatus = "Entwurf" | "Beschlossen" | "Inaktiv";

export interface BudgetPlan {
  budget_id: number;
  property_id: number;
  fiscal_year: number;
  title: string;
  status: BudgetPlanStatus;
  created_at: string;
}

export interface BudgetPlanPayload {
  property_id: number;
  fiscal_year: number;
  title: string;
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
  planned_amount: number;
  allocation_key_type: string;
  unit_shares: UnitBudgetShare[];
}

export interface BudgetPositionPayload {
  account_id: number;
  planned_amount: number;
  allocation_key_type: string;
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

export async function updateBudgetPlanStatus(budgetId: number, status: BudgetPlanStatus): Promise<BudgetPlan> {
  const { data } = await apiClient.patch<BudgetPlan>(`/budget-plans/${budgetId}`, { status });
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