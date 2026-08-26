// frontend/src/features/users/api.ts
import { apiClient } from "../../api/client";

export type PropertyRole = "Verwalter" | "Buchhalter" | "Lesezugriff";

export interface PropertyAssignment {
  property_id: number;
  role: PropertyRole;
}

export interface AdminUser {
  user_id: number;
  name: string;
  email: string;
  is_admin: boolean;
  must_change_password: boolean;
  owner_id: number | null;
  tenant_id: number | null;
  created_at: string;
  deleted_at: string | null;
  property_assignments: PropertyAssignment[];
}

export interface CreateUserPayload {
  name: string;
  email: string;
  password: string;
  is_admin: boolean;
  owner_id?: number | null;
  tenant_id?: number | null;
  property_assignments: PropertyAssignment[];
}

export interface UpdateUserPayload {
  name?: string;
  email?: string;
  is_admin?: boolean;
  owner_id?: number | null;
  tenant_id?: number | null;
  property_assignments?: PropertyAssignment[];
}

export async function listUsers(): Promise<AdminUser[]> {
  const { data } = await apiClient.get<AdminUser[]>("/users");
  return data;
}

export async function createUser(payload: CreateUserPayload): Promise<AdminUser> {
  const { data } = await apiClient.post<AdminUser>("/users", payload);
  return data;
}

export async function updateUser(userId: number, payload: UpdateUserPayload): Promise<AdminUser> {
  const { data } = await apiClient.patch<AdminUser>(`/users/${userId}`, payload);
  return data;
}

export async function deleteUser(userId: number): Promise<void> {
  await apiClient.delete(`/users/${userId}`);
}

export async function reactivateUser(userId: number): Promise<AdminUser> {
  const { data } = await apiClient.post<AdminUser>(`/users/${userId}/reactivate`);
  return data;
}