// frontend/src/features/users/UsersPage.tsx
import { useState } from "react";

import { Card } from "../../components/Card";
import { UserForm, type UserFormValues } from "./UserForm";
import { useCreateUser, useDeleteUser, useUpdateUser, useUsers } from "./useUsers";
import "./UsersPage.css";

function roleLabel(user: { is_admin: boolean; owner_id: number | null; tenant_id: number | null }): string {
  if (user.is_admin) return "Administrator";
  if (user.owner_id != null) return "Eigentümer";
  if (user.tenant_id != null) return "Mieter";
  return "Verwalter";
}

export function UsersPage() {
  const { data: users, isLoading } = useUsers();
  const createUserMutation = useCreateUser();
  const updateUserMutation = useUpdateUser();
  const deleteUserMutation = useDeleteUser();

  const [mode, setMode] = useState<"idle" | "creating" | number>("idle");
  const [formError, setFormError] = useState<string | null>(null);

  function handleCreate(values: UserFormValues) {
    setFormError(null);
    createUserMutation.mutate(
      { ...values, password: values.password ?? "" },
      {
        onSuccess: () => setMode("idle"),
        onError: () => setFormError("User konnte nicht angelegt werden."),
      },
    );
  }

  function handleUpdate(userId: number, values: UserFormValues) {
    setFormError(null);
    updateUserMutation.mutate(
      {
        userId,
        payload: {
          name: values.name,
          email: values.email,
          is_admin: values.is_admin,
          owner_id: values.owner_id,
          tenant_id: values.tenant_id,
          property_assignments: values.property_assignments,
        },
      },
      {
        onSuccess: () => setMode("idle"),
        onError: () => setFormError("User konnte nicht aktualisiert werden."),
      },
    );
  }

  function handleDelete(userId: number) {
    if (!window.confirm("User wirklich löschen?")) return;
    deleteUserMutation.mutate(userId);
  }

  const editingUser = typeof mode === "number" ? users?.find((u) => u.user_id === mode) ?? null : null;

  return (
    <div className="users-page">
      <Card>
        <div className="users-page__header">
          <h1>Nutzerverwaltung</h1>
          {mode === "idle" && (
            <button type="button" onClick={() => setMode("creating")}>
              Neuer User
            </button>
          )}
        </div>

        {isLoading && <p>Lädt…</p>}

        <table className="users-page__table">
          <thead>
            <tr>
              <th>Name</th>
              <th>E-Mail</th>
              <th>Rolle</th>
              <th>Liegenschaften</th>
              <th>Erstlogin ausstehend</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users?.map((user) => (
              <tr key={user.user_id}>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td>{roleLabel(user)}</td>
                <td>{user.property_assignments.length}</td>
                <td>{user.must_change_password ? "Ja" : "Nein"}</td>
                <td className="users-page__actions">
                  <button type="button" onClick={() => setMode(user.user_id)}>
                    Bearbeiten
                  </button>
                  <button type="button" onClick={() => handleDelete(user.user_id)}>
                    Löschen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {mode === "creating" && (
        <Card>
          <h2>Neuen User anlegen</h2>
          <UserForm
            requirePassword
            submitLabel="Anlegen"
            onSubmit={handleCreate}
            onCancel={() => setMode("idle")}
            isSubmitting={createUserMutation.isPending}
            error={formError}
          />
        </Card>
      )}

      {editingUser && (
        <Card>
          <h2>User bearbeiten: {editingUser.name}</h2>
          <UserForm
            requirePassword={false}
            submitLabel="Speichern"
            initialValues={{
              name: editingUser.name,
              email: editingUser.email,
              is_admin: editingUser.is_admin,
              owner_id: editingUser.owner_id,
              tenant_id: editingUser.tenant_id,
              property_assignments: editingUser.property_assignments,
            }}
            onSubmit={(values) => handleUpdate(editingUser.user_id, values)}
            onCancel={() => setMode("idle")}
            isSubmitting={updateUserMutation.isPending}
            error={formError}
          />
        </Card>
      )}
    </div>
  );
}