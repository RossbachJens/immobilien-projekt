// frontend/src/features/reserveFund/useReserveFund.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createReserveFundPosition,
  createReserveFundStatement,
  deleteReserveFundPosition,
  getReserveFundStatement,
  recalculateReserveFund,
  setOperatingAccounts,
  updateReserveFundPosition,
  type OperatingAccountsPayload,
  type ReserveFundPositionPayload,
  type ReserveFundPositionUpdatePayload,
} from "./api";

const statementKey = (settlementId: number) => ["reserve-fund", settlementId];

export function useReserveFundStatement(settlementId: number | undefined) {
  return useQuery({
    queryKey: statementKey(settlementId ?? -1),
    queryFn: () => getReserveFundStatement(settlementId as number),
    enabled: settlementId !== undefined,
    // 404 heißt hier "noch nicht angelegt" - kein Retry, siehe
    // ReserveFundPanel.tsx (bietet stattdessen einen Anlegen-Button an).
    retry: false,
  });
}

export function useCreateReserveFundStatement(settlementId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => createReserveFundStatement(settlementId),
    onSuccess: (data) => queryClient.setQueryData(statementKey(settlementId), data),
  });
}

export function useSetOperatingAccounts(settlementId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OperatingAccountsPayload) => setOperatingAccounts(settlementId, payload),
    onSuccess: (data) => queryClient.setQueryData(statementKey(settlementId), data),
  });
}

export function useCreateReserveFundPosition(settlementId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ReserveFundPositionPayload) => createReserveFundPosition(settlementId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: statementKey(settlementId) }),
  });
}

export function useUpdateReserveFundPosition(settlementId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      positionId,
      payload,
    }: {
      positionId: number;
      payload: ReserveFundPositionUpdatePayload;
    }) => updateReserveFundPosition(settlementId, positionId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: statementKey(settlementId) }),
  });
}

export function useDeleteReserveFundPosition(settlementId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (positionId: number) => deleteReserveFundPosition(settlementId, positionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: statementKey(settlementId) }),
  });
}

export function useRecalculateReserveFund(settlementId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => recalculateReserveFund(settlementId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: statementKey(settlementId) }),
  });
}