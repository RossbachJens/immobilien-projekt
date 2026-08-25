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
  created_at: string;
  property_assignments: PropertyAssignment[];
}

export interface UserCreatePayload {
  name: string;
  email: string;
  password: string;
  is_admin: boolean;
  property_assignments: PropertyAssignment[];
}

export async function listUsers(): Promise<AdminUser[]> {
  const { data } = await apiClient.get<AdminUser[]>("/users");
  return data;
}

export async function createUser(payload: UserCreatePayload): Promise<AdminUser> {
  const { data } = await apiClient.post<AdminUser>("/users", payload);
  return data;
}