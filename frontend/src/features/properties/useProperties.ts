import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createProperty, listProperties, type PropertyCreatePayload } from "./api";

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
    mutationFn: (payload: PropertyCreatePayload) => createProperty(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROPERTIES_KEY });
    },
  });
}