// frontend/src/features/properties/useProperties.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createProperty, listProperties, updateProperty, type PropertyPayload } from "./api";

const PROPERTIES_KEY = ["properties"];

export function useProperties() {
  return useQuery({
    queryKey: PROPERTIES_KEY,
    queryFn: listProperties,
  });
}

export function useCreateProperty() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PropertyPayload) => createProperty(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROPERTIES_KEY });
    },
  });
}

export function useUpdateProperty() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ propertyId, payload }: { propertyId: number; payload: Partial<PropertyPayload> }) =>
      updateProperty(propertyId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROPERTIES_KEY });
    },
  });
}