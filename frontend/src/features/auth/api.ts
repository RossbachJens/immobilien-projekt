import { apiClient } from "../../api/client";

export interface CurrentUser {
  user_id: number;
  name: string;
  email: string;
  must_change_password: boolean;
}

export interface LoginPayload {
  identifier: string;
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