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
  is_reserve_account: boolean;
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
  is_reserve_account?: boolean;
}

export interface AccountUpdatePayload {
  account_name?: string;
  type?: AccountType;
  is_active?: boolean;
  is_reserve_account?: boolean;
}

export async function createAccount(payload: AccountCreatePayload): Promise<Account> {
  const { data } = await apiClient.post<Account>("/accounts", payload);
  return data;
}

export async function updateAccount(accountId: number, payload: AccountUpdatePayload): Promise<Account> {
  const { data } = await apiClient.patch<Account>(`/accounts/${accountId}`, payload);
  return data;
}

// --- Kontenblatt -----------------------------------------------------------

export type LedgerEntryDirection = "DEBIT" | "CREDIT";

export interface AccountLedgerLine {
  line_id: number;
  entry_id: number;
  entry_date: string;
  document_reference: string | null;
  description: string;
  unit_id: number | null;
  direction: LedgerEntryDirection;
  amount: number;
  balance: number;
}

export interface AccountLedger {
  account_id: number;
  account_number: string;
  account_name: string;
  property_id: number;
  date_from: string | null;
  date_to: string | null;
  opening_balance: number;
  closing_balance: number;
  lines: AccountLedgerLine[];
}

export interface AccountLedgerParams {
  property_id: number;
  account_id: number;
  date_from?: string;
  date_to?: string;
}

export async function getAccountLedger(params: AccountLedgerParams): Promise<AccountLedger> {
  const { account_id, ...query } = params;
  const { data } = await apiClient.get<AccountLedger>(`/accounts/${account_id}/ledger`, { params: query });
  return data;
}