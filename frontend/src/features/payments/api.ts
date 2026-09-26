// frontend/src/features/payments/api.ts
import { apiClient } from "../../api/client";

export type PaymentType = "hausgeld" | "miete";

export interface PaymentPayload {
  unit_id: number;
  payment_type: PaymentType;
  lease_id?: number | null;
  payment_date: string;
  document_reference?: string | null;
  // Miete: gebucht auf 1200/1210.
  cold_rent_amount?: number;
  additional_costs_amount?: number;
  // Hausgeld: gebucht auf 1220/1225.
  operating_amount?: number;
  reserve_amount?: number;
  bank_account_id?: number | null;
}

export interface PaymentResult {
  entry_id: number;
}

export async function createPayment(payload: PaymentPayload): Promise<PaymentResult> {
  const { data } = await apiClient.post<PaymentResult>("/payments", payload);
  return data;
}