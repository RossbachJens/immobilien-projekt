// frontend/src/features/settlementPeriods/api.ts
import { apiClient } from "../../api/client";

export type SettlementStatus = "Entwurf" | "Beschlossen" | "Inaktiv";

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
  account_id: number;
  description: string | null;
  actual_amount: number;
  allocation_key_type: string;
  is_apportionable: boolean;
  unit_shares: UnitSettlementShare[];
}

export interface SettlementPositionPayload {
  account_id: number;
  description?: string | null;
  allocation_key_type: string;
  is_apportionable: boolean;
}

// Bewusst dieselben Felder wie SettlementPositionPayload, aber alle optional
// - Positionen sind nur "bis zum Beschluss" (Abrechnungs-Status "Entwurf")
// änderbar, siehe app/routers/settlement_periods.py::update_settlement_position.
// actual_amount ist absichtlich nicht enthalten - der Ist-Betrag wird beim
// Speichern serverseitig automatisch neu aus den Buchungen ermittelt.
export interface SettlementPositionUpdatePayload {
  account_id?: number;
  description?: string | null;
  allocation_key_type?: string;
  is_apportionable?: boolean;
}

export interface UnitSettlementSummary {
  summary_id: number;
  settlement_id: number;
  unit_id: number;
  total_actual_costs: number;
  total_prepayments: number;
  balance: number;
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

export async function exportUnitSettlementPdf(settlementId: number, unitId: number): Promise<Blob> {
  const { data } = await apiClient.get(`/settlement-periods/${settlementId}/units/${unitId}/export`, {
    responseType: "blob",
  });
  return data;
}