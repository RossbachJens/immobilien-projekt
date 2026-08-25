import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchCurrentUser,
  forgotPassword,
  login,
  logout,
  resetPassword,
  type CurrentUser,
} from "./api";

const CURRENT_USER_KEY = ["auth", "me"];

/**
 * Kein eigener React-Context nötig: der React-Query-Cache übernimmt diese
 * Rolle bereits (jeder Aufruf von useCurrentUser() teilt sich denselben
 * Cache-Eintrag). retry:false, weil ein 401 hier ein normaler, erwarteter
 * Zustand ist ("nicht eingeloggt") - kein Netzwerkfehler, der
 * Wiederholungsversuche verdient.
 */
export function useCurrentUser() {
  return useQuery<CurrentUser>({
    queryKey: CURRENT_USER_KEY,
    queryFn: fetchCurrentUser,
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: login,
    onSuccess: (user) => {
      queryClient.setQueryData(CURRENT_USER_KEY, user);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.setQueryData(CURRENT_USER_KEY, null);
    },
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: forgotPassword,
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: resetPassword,
  });
}