// frontend/src/features/hausgeldOverview/api.ts
import { apiClient } from "../../api/client";

export interface UnitHausgeldOverview {
  unit_id: number;
  unit_number: string;
  owner_id: number | null;
  monthly_target: number;
  monthly_target_reserve: number;
  target_amount: number;
  target_reserve_amount: number;
  paid_amount: number;
  paid_reserve_amount: number;
  balance: number;
  balance_reserve: number;
  has_budget_plan: boolean;
}

export interface HausgeldPayment {
  entry_id: number;
  entry_date: string;
  amount: number;
  document_reference: string | null;
  purpose: string;
}

export async function listHausgeldOverview(propertyId: number, fiscalYear: number): Promise<UnitHausgeldOverview[]> {
  const { data } = await apiClient.get<UnitHausgeldOverview[]>("/payments/hausgeld-overview", {
    params: { property_id: propertyId, fiscal_year: fiscalYear },
  });
  return data;
}

export async function listHausgeldPayments(
  propertyId: number,
  unitId: number,
  fiscalYear: number,
): Promise<HausgeldPayment[]> {
  const { data } = await apiClient.get<HausgeldPayment[]>("/payments/hausgeld-payments", {
    params: { property_id: propertyId, unit_id: unitId, fiscal_year: fiscalYear },
  });
  return data;
}