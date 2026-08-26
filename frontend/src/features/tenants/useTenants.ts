// frontend/src/features/tenants/useTenants.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createTenant, deleteTenant, listTenants, updateTenant, type TenantPayload } from "./api";

const TENANTS_KEY = ["tenants"];

export function useTenants() {
  return useQuery({ queryKey: TENANTS_KEY, queryFn: listTenants });
}

export function useCreateTenant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TenantPayload) => createTenant(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TENANTS_KEY }),
  });
}

export function useUpdateTenant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tenantId, payload }: { tenantId: number; payload: Partial<TenantPayload> }) =>
      updateTenant(tenantId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TENANTS_KEY }),
  });
}

export function useDeleteTenant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tenantId: number) => deleteTenant(tenantId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TENANTS_KEY }),
  });
}