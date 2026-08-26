// frontend/src/features/owners/OwnersPage.tsx
import { useState } from "react";

import { Card } from "../../components/Card";
import type { OwnerPayload } from "./api";
import { OwnerForm } from "./OwnerForm";
import { useCreateOwner, useDeleteOwner, useOwners, useUpdateOwner } from "./useOwners";
import "./OwnersPage.css";

export function OwnersPage() {
  const { data: owners, isLoading } = useOwners();
  const createOwnerMutation = useCreateOwner();
  const updateOwnerMutation = useUpdateOwner();
  const deleteOwnerMutation = useDeleteOwner();

  const [mode, setMode] = useState<"idle" | "creating" | number>("idle");
  const [formError, setFormError] = useState<string | null>(null);

  function handleCreate(payload: OwnerPayload) {
    setFormError(null);
    createOwnerMutation.mutate(payload, {
      onSuccess: () => setMode("idle"),
      onError: () => setFormError("Eigentümer konnte nicht angelegt werden."),
    });
  }

  function handleUpdate(ownerId: number, payload: OwnerPayload) {
    setFormError(null);
    updateOwnerMutation.mutate(
      { ownerId, payload },
      {
        onSuccess: () => setMode("idle"),
        onError: () => setFormError("Eigentümer konnte nicht aktualisiert werden."),
      },
    );
  }

  function handleDelete(ownerId: number) {
    if (!window.confirm("Eigentümer wirklich löschen?")) return;
    deleteOwnerMutation.mutate(ownerId, {
      onError: () =>
        window.alert(
          "Eigentümer konnte nicht gelöscht werden - vermutlich bestehen noch aktive Zuordnungen oder ein Online-Zugang.",
        ),
    });
  }

  const editingOwner = typeof mode === "number" ? owners?.find((o) => o.owner_id === mode) ?? null : null;

  return (
    <div className="owners-page">
      <Card>
        <div className="owners-page__header">
          <h1>Eigentümer</h1>
          {mode === "idle" && (
            <button type="button" onClick={() => setMode("creating")}>
              Neuer Eigentümer
            </button>
          )}
        </div>

        {isLoading && <p>Lädt…</p>}

        <table className="owners-page__table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Adresse</th>
              <th>E-Mail</th>
              <th>IBAN</th>
              <th>Online-Zugriff</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {owners?.map((owner) => (
              <tr key={owner.owner_id}>
                <td>{owner.company_name ?? `${owner.first_name ?? ""} ${owner.last_name}`.trim()}</td>
                <td>
                  {owner.street_and_number}
                  {owner.postal_code || owner.city ? `, ${owner.postal_code ?? ""} ${owner.city ?? ""}` : ""}
                </td>
                <td>{owner.email ?? "–"}</td>
                <td>{owner.iban_last4 ? `…${owner.iban_last4}` : "–"}</td>
                <td>{owner.has_online_access ? "Ja" : "Nein"}</td>
                <td className="owners-page__actions">
                  <button type="button" onClick={() => setMode(owner.owner_id)}>
                    Bearbeiten
                  </button>
                  <button type="button" onClick={() => handleDelete(owner.owner_id)}>
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
          <h2>Neuen Eigentümer anlegen</h2>
          <OwnerForm
            submitLabel="Anlegen"
            onSubmit={handleCreate}
            onCancel={() => setMode("idle")}
            isSubmitting={createOwnerMutation.isPending}
            error={formError}
          />
        </Card>
      )}

      {editingOwner && (
        <Card>
          <h2>
            Eigentümer bearbeiten:{" "}
            {editingOwner.company_name ?? `${editingOwner.first_name ?? ""} ${editingOwner.last_name}`.trim()}
          </h2>
          <OwnerForm
            key={editingOwner.owner_id}
            initialValues={editingOwner}
            submitLabel="Speichern"
            onSubmit={(payload) => handleUpdate(editingOwner.owner_id, payload)}
            onCancel={() => setMode("idle")}
            isSubmitting={updateOwnerMutation.isPending}
            error={formError}
          />
        </Card>
      )}
    </div>
  );
}