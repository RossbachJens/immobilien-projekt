// frontend/src/features/payments/api.ts
import { apiClient } from "../../api/client";

export type PaymentType = "hausgeld" | "miete";

export interface PaymentPayload {
  unit_id: number;
  payment_type: PaymentType;
  lease_id?: number | null;
  amount: number;
  payment_date: string;
  document_reference?: string | null;
}

// Rückgabe ist ein vollständiger Buchungsbeleg (siehe JournalEntryOut) -
// hier reicht die entry_id für die Erfolgsmeldung.
export interface PaymentResult {
  entry_id: number;
}

export async function createPayment(payload: PaymentPayload): Promise<PaymentResult> {
  const { data } = await apiClient.post<PaymentResult>("/payments", payload);
  return data;
}