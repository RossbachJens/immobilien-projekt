// frontend/src/features/accounts/api.ts
import { apiClient } from "../../api/client";

export type AccountType = "AKTIV" | "PASSIV" | "ERTRAG" | "AUFWAND";

export interface Account {
  account_id: number;
  account_number: string;
  account_name: string;
  account_class: string;
  type: AccountType;
  is_active: boolean;
  property_id: number | null;
}

export interface ListAccountsParams {
  property_id?: number;
  type?: AccountType;
  is_active?: boolean;
}

export async function listAccounts(params?: ListAccountsParams): Promise<Account[]> {
  const { data } = await apiClient.get<Account[]>("/accounts", { params });
  return data;
}

export interface AccountCreatePayload {
  property_id: number;
  account_number: string;
  account_name: string;
  type: AccountType;
}

export interface AccountUpdatePayload {
  account_name?: string;
  type?: AccountType;
  is_active?: boolean;
}

export async function createAccount(payload: AccountCreatePayload): Promise<Account> {
  const { data } = await apiClient.post<Account>("/accounts", payload);
  return data;
}

export async function updateAccount(accountId: number, payload: AccountUpdatePayload): Promise<Account> {
  const { data } = await apiClient.patch<Account>(`/accounts/${accountId}`, payload);
  return data;
}