import { apiClient } from "../../api/client";

export type UserRole = "admin" | "verwalter" | "eigentuemer" | "mieter";

export interface CurrentUser {
  user_id: number;
  email: string;
  role: UserRole;
  must_change_password: boolean;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export async function login(payload: LoginPayload): Promise<CurrentUser> {
  const { data } = await apiClient.post<CurrentUser>("/auth/login", payload);
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const { data } = await apiClient.get<CurrentUser>("/auth/me");
  return data;
}
