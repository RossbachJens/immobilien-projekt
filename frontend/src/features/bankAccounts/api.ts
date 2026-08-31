// frontend/src/features/bankAccounts/api.ts
import { apiClient } from "../../api/client";

export type BankAccountPurpose = "GIROKONTO" | "RUECKLAGENKONTO" | "SONSTIGES";

export interface BankAccount {
  bank_account_id: number;
  property_id: number;
  account_id: number;
  account_purpose: BankAccountPurpose;
  purpose_detail: string | null;
  bank_name: string;
  iban_last4: string | null;
  valid_from: string;
  valid_to: string | null;
  created_at: string;
}

export interface BankAccountPayload {
  property_id: number;
  account_id: number;
  account_purpose: BankAccountPurpose;
  purpose_detail?: string | null;
  bank_name: string;
  iban?: string | null;
  bic?: string | null;
  valid_from: string;
  valid_to?: string | null;
}

export interface BankAccountUpdatePayload {
  purpose_detail?: string | null;
  bank_name?: string;
  iban?: string | null;
  bic?: string | null;
  valid_to?: string | null;
}

export async function listBankAccounts(propertyId?: number): Promise<BankAccount[]> {
  const { data } = await apiClient.get<BankAccount[]>("/bank-accounts", {
    params: propertyId ? { property_id: propertyId } : undefined,
  });
  return data;
}

export async function createBankAccount(payload: BankAccountPayload): Promise<BankAccount> {
  const { data } = await apiClient.post<BankAccount>("/bank-accounts", payload);
  return data;
}

export async function updateBankAccount(
  bankAccountId: number,
  payload: BankAccountUpdatePayload,
): Promise<BankAccount> {
  const { data } = await apiClient.patch<BankAccount>(`/bank-accounts/${bankAccountId}`, payload);
  return data;
}