// frontend/src/features/settlementPeriods/api.ts
import { apiClient } from "../../api/client";

export type SettlementStatus = "Entwurf" | "Beschlossen" | "Inaktiv";

export type TaxCategory = "keine" | "haushaltsnahe_dienstleistung" | "handwerkerleistung";

export interface UnitSettlementTaxShare {
  share_id: number;
  position_id: number;
  unit_id: number;
  allocated_deductible_amount: number;
}

export interface UnitSettlementTenantShare {
  share_id: number;
  position_id: number;
  lease_id: number;
  allocated_amount: number;
}

export interface SettlementPeriod {
  settlement_id: number;
  property_id: number;
  fiscal_year: number;
  period_start: string;
  period_end: string;
  title: string;
  status: SettlementStatus;
  resolution_id: number | null;
  created_at: string;
}

export interface SettlementPeriodPayload {
  property_id: number;
  fiscal_year: number;
  period_start: string;
  period_end: string;
  title: string;
  resolution_id?: number | null;
}

export interface SettlementStatusPayload {
  status: SettlementStatus;
  resolution_id?: number | null;
}

export interface UnitSettlementShare {
  share_id: number;
  position_id: number;
  unit_id: number;
  allocated_actual_amount: number;
}

export interface SettlementPosition {
  position_id: number;
  settlement_id: number;
  account_ids: number[];
  description: string | null;
  actual_amount: number;
  allocation_key_type: string;
  is_apportionable: boolean;
  tax_category: TaxCategory;
  deductible_amount: number | null;
  unit_shares: UnitSettlementShare[];
  tax_shares: UnitSettlementTaxShare[];
  tenant_shares: UnitSettlementTenantShare[];
}

export interface SettlementPositionPayload {
  account_ids: number[];
  description?: string | null;
  allocation_key_type: string;
  is_apportionable: boolean;
  tax_category: TaxCategory;
  deductible_amount?: number | null;
}

export interface SettlementPositionUpdatePayload {
  account_ids?: number[];
  description?: string | null;
  allocation_key_type?: string;
  is_apportionable?: boolean;
  tax_category?: TaxCategory;
  deductible_amount?: number | null;
}

export interface UnitSettlementSummary {
  summary_id: number;
  settlement_id: number;
  unit_id: number;
  total_actual_costs: number;
  total_prepayments: number;
  balance: number;
}

// Ergebnis je Mietvertrag - taggenaue Verteilung (Chat vom 24.09.2026).
// Einheiten ohne aktiven Vertrag im Zeitraum (Eigennutzung oder Leerstand)
// tauchen hier bewusst NICHT auf - siehe SettlementPeriodsPage.tsx.
export interface LeaseSettlementSummary {
  summary_id: number;
  settlement_id: number;
  lease_id: number;
  unit_id: number;
  total_actual_costs: number;
  total_prepayments: number;
  balance: number;
  tenant_first_name: string;
  tenant_last_name: string;
  lease_start_date: string;
  lease_end_date: string | null;
}

export async function listSettlementPeriods(propertyId?: number): Promise<SettlementPeriod[]> {
  const { data } = await apiClient.get<SettlementPeriod[]>("/settlement-periods", {
    params: propertyId ? { property_id: propertyId } : undefined,
  });
  return data;
}

export async function createSettlementPeriod(payload: SettlementPeriodPayload): Promise<SettlementPeriod> {
  const { data } = await apiClient.post<SettlementPeriod>("/settlement-periods", payload);
  return data;
}

export async function updateSettlementPeriod(
  settlementId: number,
  payload: SettlementStatusPayload,
): Promise<SettlementPeriod> {
  const { data } = await apiClient.patch<SettlementPeriod>(`/settlement-periods/${settlementId}`, payload);
  return data;
}

export async function listSettlementPositions(settlementId: number): Promise<SettlementPosition[]> {
  const { data } = await apiClient.get<SettlementPosition[]>(`/settlement-periods/${settlementId}/positions`);
  return data;
}

export async function createSettlementPosition(
  settlementId: number,
  payload: SettlementPositionPayload,
): Promise<SettlementPosition> {
  const { data } = await apiClient.post<SettlementPosition>(
    `/settlement-periods/${settlementId}/positions`,
    payload,
  );
  return data;
}

export async function updateSettlementPosition(
  settlementId: number,
  positionId: number,
  payload: SettlementPositionUpdatePayload,
): Promise<SettlementPosition> {
  const { data } = await apiClient.patch<SettlementPosition>(
    `/settlement-periods/${settlementId}/positions/${positionId}`,
    payload,
  );
  return data;
}

export async function deleteSettlementPosition(settlementId: number, positionId: number): Promise<void> {
  await apiClient.delete(`/settlement-periods/${settlementId}/positions/${positionId}`);
}

export async function recalculateSettlement(settlementId: number): Promise<SettlementPosition[]> {
  const { data } = await apiClient.post<SettlementPosition[]>(`/settlement-periods/${settlementId}/recalculate`);
  return data;
}

export async function listUnitSummaries(settlementId: number): Promise<UnitSettlementSummary[]> {
  const { data } = await apiClient.get<UnitSettlementSummary[]>(`/settlement-periods/${settlementId}/summaries`);
  return data;
}

export async function listLeaseSummaries(settlementId: number): Promise<LeaseSettlementSummary[]> {
  const { data } = await apiClient.get<LeaseSettlementSummary[]>(
    `/settlement-periods/${settlementId}/lease-summaries`,
  );
  return data;
}

export async function exportUnitSettlementPdf(settlementId: number, unitId: number): Promise<Blob> {
  const { data } = await apiClient.get(`/settlement-periods/${settlementId}/units/${unitId}/export`, {
    responseType: "blob",
  });
  return data;
}

export async function exportSettlementBatchPdf(settlementId: number): Promise<Blob> {
  const { data } = await apiClient.get(`/settlement-periods/${settlementId}/export-batch`, {
    responseType: "blob",
  });
  return data;
}

// frontend/src/features/settlementPeriods/api.ts — ergänzen
export async function exportLeaseSettlementPdf(settlementId: number, leaseId: number): Promise<Blob> {
  const { data } = await apiClient.get(`/settlement-periods/${settlementId}/leases/${leaseId}/export`, {
    responseType: "blob",
  });
  return data;
}

export async function exportSettlementTenantBatchPdf(settlementId: number): Promise<Blob> {
  const { data } = await apiClient.get(`/settlement-periods/${settlementId}/export-tenant-batch`, {
    responseType: "blob",
  });
  return data;
}