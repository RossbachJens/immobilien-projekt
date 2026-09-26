// frontend/src/features/settlementPeriods/useSettlementPeriods.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createSettlementPeriod,
  createSettlementPosition,
  deleteSettlementPosition,
  exportUnitSettlementPdf,
  listLeaseSummaries,
  listSettlementPeriods,
  listSettlementPositions,
  listUnitSummaries,
  recalculateSettlement,
  updateSettlementPeriod,
  updateSettlementPosition,
  exportSettlementBatchPdf,
  exportLeaseSettlementPdf, 
  exportSettlementTenantBatchPdf,
  type SettlementPeriodPayload,
  type SettlementPositionPayload,
  type SettlementPositionUpdatePayload,
  type SettlementStatusPayload,
} from "./api";

const periodsKey = (propertyId?: number) => ["settlement-periods", propertyId ?? "all"];
const positionsKey = (settlementId: number) => ["settlement-periods", settlementId, "positions"];
const summariesKey = (settlementId: number) => ["settlement-periods", settlementId, "summaries"];
const leaseSummariesKey = (settlementId: number) => ["settlement-periods", settlementId, "lease-summaries"];

export function useSettlementPeriods(propertyId?: number) {
  return useQuery({
    queryKey: periodsKey(propertyId),
    queryFn: () => listSettlementPeriods(propertyId),
    enabled: propertyId !== undefined,
  });
}

export function useCreateSettlementPeriod(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SettlementPeriodPayload) => createSettlementPeriod(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: periodsKey(propertyId) }),
  });
}

export function useUpdateSettlementPeriod(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ settlementId, payload }: { settlementId: number; payload: SettlementStatusPayload }) =>
      updateSettlementPeriod(settlementId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: periodsKey(propertyId) }),
  });
}

export function useSettlementPositions(settlementId: number | undefined) {
  return useQuery({
    queryKey: positionsKey(settlementId ?? -1),
    queryFn: () => listSettlementPositions(settlementId as number),
    enabled: settlementId !== undefined,
  });
}

export function useCreateSettlementPosition(settlementId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SettlementPositionPayload) => createSettlementPosition(settlementId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: positionsKey(settlementId) });
      queryClient.invalidateQueries({ queryKey: summariesKey(settlementId) });
      queryClient.invalidateQueries({ queryKey: leaseSummariesKey(settlementId) });
    },
  });
}

export function useUpdateSettlementPosition(settlementId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ positionId, payload }: { positionId: number; payload: SettlementPositionUpdatePayload }) =>
      updateSettlementPosition(settlementId, positionId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: positionsKey(settlementId) });
      queryClient.invalidateQueries({ queryKey: summariesKey(settlementId) });
      queryClient.invalidateQueries({ queryKey: leaseSummariesKey(settlementId) });
    },
  });
}

export function useDeleteSettlementPosition(settlementId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (positionId: number) => deleteSettlementPosition(settlementId, positionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: positionsKey(settlementId) });
      queryClient.invalidateQueries({ queryKey: summariesKey(settlementId) });
      queryClient.invalidateQueries({ queryKey: leaseSummariesKey(settlementId) });
    },
  });
}

export function useRecalculateSettlement(settlementId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => recalculateSettlement(settlementId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: positionsKey(settlementId) });
      queryClient.invalidateQueries({ queryKey: summariesKey(settlementId) });
      queryClient.invalidateQueries({ queryKey: leaseSummariesKey(settlementId) });
    },
  });
}

export function useUnitSummaries(settlementId: number | undefined) {
  return useQuery({
    queryKey: summariesKey(settlementId ?? -1),
    queryFn: () => listUnitSummaries(settlementId as number),
    enabled: settlementId !== undefined,
  });
}

export function useLeaseSummaries(settlementId: number | undefined) {
  return useQuery({
    queryKey: leaseSummariesKey(settlementId ?? -1),
    queryFn: () => listLeaseSummaries(settlementId as number),
    enabled: settlementId !== undefined,
  });
}

export function useExportUnitSettlement() {
  return useMutation({
    mutationFn: async ({
      settlementId,
      unitId,
      filename,
    }: {
      settlementId: number;
      unitId: number;
      filename: string;
    }) => {
      const blob = await exportUnitSettlementPdf(settlementId, unitId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    },
  });
}

export function useExportSettlementBatch() {
  return useMutation({
    mutationFn: async ({ settlementId, filename }: { settlementId: number; filename: string }) => {
      const blob = await exportSettlementBatchPdf(settlementId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    },
  });
}

// frontend/src/features/settlementPeriods/useSettlementPeriods.ts — ergänzen
export function useExportLeaseSettlement() {
  return useMutation({
    mutationFn: async ({
      settlementId,
      leaseId,
      filename,
    }: {
      settlementId: number;
      leaseId: number;
      filename: string;
    }) => {
      const blob = await exportLeaseSettlementPdf(settlementId, leaseId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    },
  });
}

export function useExportSettlementTenantBatch() {
  return useMutation({
    mutationFn: async ({ settlementId, filename }: { settlementId: number; filename: string }) => {
      const blob = await exportSettlementTenantBatchPdf(settlementId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    },
  });
}