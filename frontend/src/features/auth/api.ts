// frontend/src/features/auth/api.ts
import { apiClient } from "../../api/client";

export interface CurrentUser {
  user_id: number;
  name: string;
  email: string;
  must_change_password: boolean;
  is_admin: boolean;
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

export interface ForgotPasswordPayload {
  identifier: string;
}

export interface ForgotPasswordResult {
  detail: string;
  // Nur ausserhalb von production befuellt (settings.environment, s. auth.py) -
  // Ersatz fuer den noch fehlenden E-Mail-Versand (PROJECTPLAN.md, Phase 7).
  dev_reset_token: string | null;
}

export async function forgotPassword(payload: ForgotPasswordPayload): Promise<ForgotPasswordResult> {
  const { data } = await apiClient.post<ForgotPasswordResult>("/auth/forgot-password", payload);
  return data;
}

export interface ResetPasswordPayload {
  token: string;
  new_password: string;
}

export async function resetPassword(payload: ResetPasswordPayload): Promise<void> {
  await apiClient.post("/auth/reset-password", payload);
}