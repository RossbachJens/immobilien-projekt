// frontend/src/features/properties/useProperties.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createProperty,
  deletePropertyLogo,
  listProperties,
  updateProperty,
  uploadPropertyLogo,
  type PropertyPayload,
} from "./api";

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

export function useUploadPropertyLogo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ propertyId, file }: { propertyId: number; file: File }) => uploadPropertyLogo(propertyId, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROPERTIES_KEY }),
  });
}

export function useDeletePropertyLogo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (propertyId: number) => deletePropertyLogo(propertyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROPERTIES_KEY }),
  });
}