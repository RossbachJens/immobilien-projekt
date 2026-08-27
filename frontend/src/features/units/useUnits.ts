// frontend/src/features/units/useUnits.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  assignOwner,
  createUnit,
  deleteOwnerAssignment,
  deleteUnit,
  listUnitOwners,
  listUnits,
  updateOwnerAssignment,
  updateUnit,
  type OwnerAssignmentPayload,
  type OwnerAssignmentUpdatePayload,
  type UnitPayload,
} from "./api";

const unitsKey = (propertyId?: number) => ["units", propertyId ?? "all"];
const unitOwnersKey = (unitId: number) => ["units", unitId, "owners"];

export function useUnits(propertyId?: number) {
  return useQuery({
    queryKey: unitsKey(propertyId),
    queryFn: () => listUnits(propertyId),
    enabled: propertyId !== undefined,
  });
}

export function useCreateUnit(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UnitPayload) => createUnit(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: unitsKey(propertyId) }),
  });
}

export function useUpdateUnit(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ unitId, payload }: { unitId: number; payload: Partial<UnitPayload> }) =>
      updateUnit(unitId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: unitsKey(propertyId) }),
  });
}

export function useDeleteUnit(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (unitId: number) => deleteUnit(unitId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: unitsKey(propertyId) }),
  });
}

export function useUnitOwners(unitId: number) {
  return useQuery({
    queryKey: unitOwnersKey(unitId),
    queryFn: () => listUnitOwners(unitId),
  });
}

export function useAssignOwner(unitId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OwnerAssignmentPayload) => assignOwner(unitId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: unitOwnersKey(unitId) }),
  });
}

export function useUpdateOwnerAssignment(unitId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ historyId, payload }: { historyId: number; payload: OwnerAssignmentUpdatePayload }) =>
      updateOwnerAssignment(unitId, historyId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: unitOwnersKey(unitId) }),
  });
}

export function useDeleteOwnerAssignment(unitId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (historyId: number) => deleteOwnerAssignment(unitId, historyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: unitOwnersKey(unitId) }),
  });
}