// frontend/src/features/resolutions/useResolutions.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createResolution, listResolutions, type ResolutionPayload } from "./api";

const resolutionsKey = (propertyId?: number) => ["resolutions", propertyId ?? "all"];

export function useResolutions(propertyId?: number) {
  return useQuery({
    queryKey: resolutionsKey(propertyId),
    queryFn: () => listResolutions(propertyId),
    enabled: propertyId !== undefined,
    // Mieter bekommen 403 - kein Retry, sonst dreht React Query sinnlos weiter.
    retry: false,
  });
}

export function useCreateResolution(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ResolutionPayload) => createResolution(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: resolutionsKey(propertyId) }),
  });
}