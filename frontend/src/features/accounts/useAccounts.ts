// frontend/src/features/accounts/useAccounts.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createAccount,
  getAccountLedger,
  listAccounts,
  updateAccount,
  type AccountCreatePayload,
  type AccountLedgerParams,
  type AccountUpdatePayload,
  type ListAccountsParams,
} from "./api";

export function useAccounts(params?: ListAccountsParams) {
  return useQuery({
    // Konten ändern sich praktisch nie zur Laufzeit - daher ein längeres
    // staleTime als bei den übrigen Hooks.
    queryKey: ["accounts", params ?? {}],
    queryFn: () => listAccounts(params),
    staleTime: 5 * 60_000,
  });
}

export function useCreateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AccountCreatePayload) => createAccount(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["accounts"] }),
  });
}

export function useUpdateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, payload }: { accountId: number; payload: AccountUpdatePayload }) =>
      updateAccount(accountId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["accounts"] }),
  });
}

export function useAccountLedger(params: AccountLedgerParams | undefined) {
  return useQuery({
    queryKey: ["accounts", "ledger", params ?? {}],
    queryFn: () => getAccountLedger(params as AccountLedgerParams),
    enabled: params !== undefined,
  });
}