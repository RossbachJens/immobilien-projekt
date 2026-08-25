import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createUser, listUsers, type UserCreatePayload } from "./api";

const USERS_KEY = ["users"];

export function useUsers() {
  return useQuery({
    queryKey: USERS_KEY,
    queryFn: listUsers,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UserCreatePayload) => createUser(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}