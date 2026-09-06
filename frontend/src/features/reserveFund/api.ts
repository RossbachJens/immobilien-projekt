// frontend/src/features/reserveFund/api.ts
import { apiClient } from "../../api/client";

export type MovementType =
  | "Zufuehrung"
  | "Entnahme"
  | "Zinsen"
  | "Kapitalertragsteuer"
  | "Solidaritaetszuschlag"
  | "Sonstiges";

export interface ReserveFundUnitShare {
  share_id: number;
  position_id: number;
  unit_id: number;
  allocated_amount: number;
}

export interface ReserveFundPosition {
  position_id: number;
  statement_id: number;
  movement_type: MovementType;
  description: string | null;
  allocation_key_type: string;
  actual_amount: number;
  account_ids: number[];
  unit_shares: ReserveFundUnitShare[];
}

export interface ReserveFundStatement {
  statement_id: number;
  settlement_id: number;
  created_at: string;
  operating_account_ids: number[];
  reserve_balance_start: number;
  reserve_balance_end: number;
  positions_sum: number;
  control_difference: number;
  operating_balance_start: number;
  operating_balance_end: number;
  positions: ReserveFundPosition[];
}

export interface ReserveFundPositionPayload {
  movement_type: MovementType;
  description?: string | null;
  allocation_key_type: string;
  account_ids: number[];
}

export interface ReserveFundPositionUpdatePayload {
  movement_type?: MovementType;
  description?: string | null;
  allocation_key_type?: string;
  account_ids?: number[];
}

export interface OperatingAccountsPayload {
  account_ids: number[];
}

export async function getReserveFundStatement(settlementId: number): Promise<ReserveFundStatement> {
  const { data } = await apiClient.get<ReserveFundStatement>(
    `/settlement-periods/${settlementId}/reserve-fund`,
  );
  return data;
}

export async function createReserveFundStatement(settlementId: number): Promise<ReserveFundStatement> {
  const { data } = await apiClient.post<ReserveFundStatement>(
    `/settlement-periods/${settlementId}/reserve-fund`,
  );
  return data;
}

export async function setOperatingAccounts(
  settlementId: number,
  payload: OperatingAccountsPayload,
): Promise<ReserveFundStatement> {
  const { data } = await apiClient.put<ReserveFundStatement>(
    `/settlement-periods/${settlementId}/reserve-fund/operating-accounts`,
    payload,
  );
  return data;
}

export async function createReserveFundPosition(
  settlementId: number,
  payload: ReserveFundPositionPayload,
): Promise<ReserveFundPosition> {
  const { data } = await apiClient.post<ReserveFundPosition>(
    `/settlement-periods/${settlementId}/reserve-fund/positions`,
    payload,
  );
  return data;
}

export async function updateReserveFundPosition(
  settlementId: number,
  positionId: number,
  payload: ReserveFundPositionUpdatePayload,
): Promise<ReserveFundPosition> {
  const { data } = await apiClient.patch<ReserveFundPosition>(
    `/settlement-periods/${settlementId}/reserve-fund/positions/${positionId}`,
    payload,
  );
  return data;
}

export async function deleteReserveFundPosition(settlementId: number, positionId: number): Promise<void> {
  await apiClient.delete(`/settlement-periods/${settlementId}/reserve-fund/positions/${positionId}`);
}

export async function recalculateReserveFund(settlementId: number): Promise<ReserveFundPosition[]> {
  const { data } = await apiClient.post<ReserveFundPosition[]>(
    `/settlement-periods/${settlementId}/reserve-fund/recalculate`,
  );
  return data;
}