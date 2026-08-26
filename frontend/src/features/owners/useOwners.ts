// frontend/src/features/owners/useOwners.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createOwner, deleteOwner, listOwners, updateOwner, type OwnerPayload } from "./api";

const OWNERS_KEY = ["owners"];

export function useOwners() {
  return useQuery({ queryKey: OWNERS_KEY, queryFn: listOwners });
}

export function useCreateOwner() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OwnerPayload) => createOwner(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: OWNERS_KEY }),
  });
}

export function useUpdateOwner() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ownerId, payload }: { ownerId: number; payload: Partial<OwnerPayload> }) =>
      updateOwner(ownerId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: OWNERS_KEY }),
  });
}

export function useDeleteOwner() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ownerId: number) => deleteOwner(ownerId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: OWNERS_KEY }),
  });
}