import { useState, type FormEvent } from "react";
import { isAxiosError } from "axios";

import { Card } from "../../components/Card";
import { useProperties } from "../properties/useProperties";
import type { PropertyAssignment, PropertyRole } from "./api";
import { useCreateUser, useUsers } from "./useUsers";
import "./UsersPage.css";

const PROPERTY_ROLES: PropertyRole[] = ["Verwalter", "Buchhalter", "Lesezugriff"];

function extractErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail;
  }
  return fallback;
}

export function UsersPage() {
  const { data: users, isLoading: usersLoading } = useUsers();
  const { data: properties } = useProperties();
  const createUserMutation = useCreateUser();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [assignments, setAssignments] = useState<PropertyAssignment[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<number | "">("");
  const [selectedRole, setSelectedRole] = useState<PropertyRole>("Verwalter");
  const [error, setError] = useState<string | null>(null);

  function handleAddAssignment() {
    if (selectedPropertyId === "") return;
    if (assignments.some((a) => a.property_id === selectedPropertyId)) return;
    setAssignments([...assignments, { property_id: selectedPropertyId, role: selectedRole }]);
    setSelectedPropertyId("");
  }

  function handleRemoveAssignment(propertyId: number) {
    setAssignments(assignments.filter((a) => a.property_id !== propertyId));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    createUserMutation.mutate(
      {
        name,
        email,
        password,
        is_admin: isAdmin,
        property_assignments: isAdmin ? [] : assignments,
      },
      {
        onSuccess: () => {
          setName("");
          setEmail("");
          setPassword("");
          setIsAdmin(false);
          setAssignments([]);
        },
        onError: (err) =>
          setError(extractErrorMessage(err, "Benutzer konnte nicht angelegt werden.")),
      },
    );
  }

  function propertyName(propertyId: number): string {
    return properties?.find((p) => p.property_id === propertyId)?.name ?? `#${propertyId}`;
  }

  return (
    <div className="users-page">
      <Card>
        <h1>Benutzer</h1>
        {usersLoading && <p>Lädt…</p>}
        <table className="users-page__table">
          <thead>
            <tr>
              <th>Name</th>
              <th>E-Mail</th>
              <th>Rolle</th>
              <th>Passwortänderung ausstehend</th>
            </tr>
          </thead>
          <tbody>
            {users?.map((user) => (
              <tr key={user.user_id}>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td>
                  {user.is_admin ? (
                    <span className="users-page__badge users-page__badge--admin">Admin</span>
                  ) : user.property_assignments.length > 0 ? (
                    <ul className="users-page__assignment-list">
                      {user.property_assignments.map((a) => (
                        <li key={a.property_id}>
                          {propertyName(a.property_id)} ({a.role})
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className="users-page__badge">ohne Zuordnung</span>
                  )}
                </td>
                <td>{user.must_change_password ? "Ja" : "Nein"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card>
        <h2>Neuen Benutzer anlegen</h2>
        <form onSubmit={handleSubmit} className="users-page__form">
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            E-Mail
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Initiales Passwort
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </label>
          <label className="users-page__checkbox">
            <input type="checkbox" checked={isAdmin} onChange={(e) => setIsAdmin(e.target.checked)} />
            Administrator (globaler Zugriff, keine Objektzuordnung nötig)
          </label>

          {!isAdmin && (
            <fieldset className="users-page__assignments">
              <legend>Liegenschaften zuordnen</legend>
              <div className="users-page__assignment-picker">
                <select
                  value={selectedPropertyId}
                  onChange={(e) =>
                    setSelectedPropertyId(e.target.value ? Number(e.target.value) : "")
                  }
                >
                  <option value="">Liegenschaft wählen…</option>
                  {properties
                    ?.filter((p) => !assignments.some((a) => a.property_id === p.property_id))
                    .map((p) => (
                      <option key={p.property_id} value={p.property_id}>
                        {p.name}
                      </option>
                    ))}
                </select>
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value as PropertyRole)}
                >
                  {PROPERTY_ROLES.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </select>
                <button type="button" onClick={handleAddAssignment} disabled={!selectedPropertyId}>
                  Hinzufügen
                </button>
              </div>

              {assignments.length > 0 && (
                <ul className="users-page__assignment-list">
                  {assignments.map((a) => (
                    <li key={a.property_id}>
                      {propertyName(a.property_id)} ({a.role})
                      <button
                        type="button"
                        className="users-page__remove-btn"
                        onClick={() => handleRemoveAssignment(a.property_id)}
                      >
                        Entfernen
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </fieldset>
          )}

          {error && <p className="users-page__error">{error}</p>}
          <button type="submit" disabled={createUserMutation.isPending}>
            {createUserMutation.isPending ? "Wird gespeichert…" : "Anlegen"}
          </button>
        </form>
      </Card>
    </div>
  );
}