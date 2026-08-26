// frontend/src/features/users/useUsers.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createUser,
  deleteUser,
  listUsers,
  updateUser,
  type CreateUserPayload,
  type UpdateUserPayload,
} from "./api";

const USERS_KEY = ["users"];

export function useUsers() {
  return useQuery({ queryKey: USERS_KEY, queryFn: listUsers });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateUserPayload) => createUser(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, payload }: { userId: number; payload: UpdateUserPayload }) =>
      updateUser(userId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => deleteUser(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}

// frontend/src/features/users/useUsers.ts — ergänzen
export function useReactivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => reactivateUser(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}