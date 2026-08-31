// frontend/src/features/bankAccounts/useBankAccounts.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createBankAccount,
  listBankAccounts,
  updateBankAccount,
  type BankAccountPayload,
  type BankAccountUpdatePayload,
} from "./api";

const bankAccountsKey = (propertyId?: number) => ["bank-accounts", propertyId ?? "all"];

export function useBankAccounts(propertyId?: number) {
  return useQuery({
    queryKey: bankAccountsKey(propertyId),
    queryFn: () => listBankAccounts(propertyId),
    enabled: propertyId !== undefined,
    // Mieter bekommen 403 (siehe Router) - kein Retry, analog useResolutions.
    retry: false,
  });
}

export function useCreateBankAccount(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BankAccountPayload) => createBankAccount(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: bankAccountsKey(propertyId) }),
  });
}

export function useUpdateBankAccount(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      bankAccountId,
      payload,
    }: {
      bankAccountId: number;
      payload: BankAccountUpdatePayload;
    }) => updateBankAccount(bankAccountId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: bankAccountsKey(propertyId) }),
  });
}