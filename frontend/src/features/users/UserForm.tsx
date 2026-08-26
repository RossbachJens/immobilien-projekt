// frontend/src/features/users/UserForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { useOwners } from "../owners/useOwners";
import { useProperties } from "../properties/useProperties";
import { useTenants } from "../tenants/useTenants";
import type { PropertyAssignment, PropertyRole } from "./api";
import "./UserForm.css";

type Role = "verwalter" | "admin" | "eigentuemer" | "mieter";

const PROPERTY_ROLES: PropertyRole[] = ["Verwalter", "Buchhalter", "Lesezugriff"];

export interface UserFormValues {
  name: string;
  email: string;
  password?: string;
  is_admin: boolean;
  owner_id: number | null;
  tenant_id: number | null;
  property_assignments: PropertyAssignment[];
}

interface UserFormProps {
  initialValues?: Partial<UserFormValues>;
  requirePassword: boolean;
  submitLabel: string;
  onSubmit: (values: UserFormValues) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

function deriveRole(is_admin: boolean, owner_id: number | null, tenant_id: number | null): Role {
  if (is_admin) return "admin";
  if (owner_id != null) return "eigentuemer";
  if (tenant_id != null) return "mieter";
  return "verwalter";
}

export function UserForm({
  initialValues,
  requirePassword,
  submitLabel,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: UserFormProps) {
  const { data: owners } = useOwners();
  const { data: tenants } = useTenants();
  const { data: properties } = useProperties();

  const [name, setName] = useState(initialValues?.name ?? "");
  const [email, setEmail] = useState(initialValues?.email ?? "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>(
    deriveRole(initialValues?.is_admin ?? false, initialValues?.owner_id ?? null, initialValues?.tenant_id ?? null),
  );
  const [ownerId, setOwnerId] = useState<number | null>(initialValues?.owner_id ?? null);
  const [tenantId, setTenantId] = useState<number | null>(initialValues?.tenant_id ?? null);
  const [assignments, setAssignments] = useState<PropertyAssignment[]>(
    initialValues?.property_assignments ?? [],
  );

  function toggleAssignment(propertyId: number, checked: boolean) {
    setAssignments((prev) =>
      checked
        ? [...prev, { property_id: propertyId, role: "Verwalter" as PropertyRole }]
        : prev.filter((a) => a.property_id !== propertyId),
    );
  }

  function setAssignmentRole(propertyId: number, propertyRole: PropertyRole) {
    setAssignments((prev) =>
      prev.map((a) => (a.property_id === propertyId ? { ...a, role: propertyRole } : a)),
    );
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      name,
      email,
      password: requirePassword ? password : undefined,
      is_admin: role === "admin",
      owner_id: role === "eigentuemer" ? ownerId : null,
      tenant_id: role === "mieter" ? tenantId : null,
      property_assignments: role === "admin" ? [] : assignments,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="user-form">
      <label>
        Name
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>
      <label>
        E-Mail
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      </label>
      {requirePassword && (
        <label>
          Erstpasswort
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>
      )}

      <fieldset className="user-form__role">
        <legend>Rolle</legend>
        <label>
          <input type="radio" name="role" checked={role === "verwalter"} onChange={() => setRole("verwalter")} />
          Verwalter / Buchhalter
        </label>
        <label>
          <input type="radio" name="role" checked={role === "admin"} onChange={() => setRole("admin")} />
          Administrator
        </label>
        <label>
          <input type="radio" name="role" checked={role === "eigentuemer"} onChange={() => setRole("eigentuemer")} />
          Eigentümer
        </label>
        <label>
          <input type="radio" name="role" checked={role === "mieter"} onChange={() => setRole("mieter")} />
          Mieter
        </label>
      </fieldset>

      {role === "eigentuemer" && (
        <label>
          Verknüpfter Eigentümer
          <select
            value={ownerId ?? ""}
            onChange={(e) => setOwnerId(e.target.value ? Number(e.target.value) : null)}
            required
          >
            <option value="">– bitte wählen –</option>
            {owners?.map((o) => (
              <option key={o.owner_id} value={o.owner_id}>
                {o.company_name ?? `${o.first_name ?? ""} ${o.last_name}`.trim()}
              </option>
            ))}
          </select>
        </label>
      )}

      {role === "mieter" && (
        <label>
          Verknüpfter Mieter
          <select
            value={tenantId ?? ""}
            onChange={(e) => setTenantId(e.target.value ? Number(e.target.value) : null)}
            required
          >
            <option value="">– bitte wählen –</option>
            {tenants?.map((t) => (
              <option key={t.tenant_id} value={t.tenant_id}>
                {t.first_name} {t.last_name}
              </option>
            ))}
          </select>
        </label>
      )}

      {role !== "admin" && (
        <fieldset className="user-form__properties">
          <legend>Zugewiesene Liegenschaften</legend>
          {properties?.length === 0 && <p>Keine Liegenschaften vorhanden.</p>}
          {properties?.map((property) => {
            const assignment = assignments.find((a) => a.property_id === property.property_id);
            return (
              <div key={property.property_id} className="user-form__property-row">
                <label>
                  <input
                    type="checkbox"
                    checked={assignment !== undefined}
                    onChange={(e) => toggleAssignment(property.property_id, e.target.checked)}
                  />
                  {property.name}
                </label>
                {assignment && (
                  <select
                    value={assignment.role}
                    onChange={(e) => setAssignmentRole(property.property_id, e.target.value as PropertyRole)}
                  >
                    {PROPERTY_ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            );
          })}
        </fieldset>
      )}

      {error && <p className="user-form__error">{error}</p>}

      <div className="user-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird gespeichert…" : submitLabel}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}