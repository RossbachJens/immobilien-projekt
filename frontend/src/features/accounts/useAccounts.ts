// frontend/src/features/accounts/useAccounts.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createAccount,
  listAccounts,
  updateAccount,
  type AccountCreatePayload,
  type AccountUpdatePayload,
  type ListAccountsParams,
} from "./api";


export function useAccounts(params?: ListAccountsParams) {
  return useQuery({
    // Konten ändern sich praktisch nie zur Laufzeit (Pflege über
    // Seed-/Migrationsdaten, siehe backend/app/routers/accounts.py) - daher
    // ein längeres staleTime als bei den übrigen Hooks. params gehen mit in
    // den Cache-Key, damit gefilterte und ungefilterte Abfragen nicht
    // kollidieren.
    queryKey: ["accounts", params ?? {}],
    queryFn: () => listAccounts(params),
    staleTime: 5 * 60_000,
  });
}


export function useCreateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AccountCreatePayload) => createAccount(payload),
    // Prefix-Match: invalidiert alle ["accounts", ...]-Queries unabhängig
    // von den jeweiligen Filter-Parametern im Cache-Key.
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