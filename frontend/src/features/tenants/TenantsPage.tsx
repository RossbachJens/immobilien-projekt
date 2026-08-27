// frontend/src/features/tenants/TenantsPage.tsx
import { useState } from "react";

import { Card } from "../../components/Card";
import type { TenantPayload } from "./api";
import { TenantForm } from "./TenantForm";
import { useCreateTenant, useDeleteTenant, useTenants, useUpdateTenant } from "./useTenants";
import "./TenantsPage.css";

export function TenantsPage() {
  const { data: tenants, isLoading } = useTenants();
  const createTenantMutation = useCreateTenant();
  const updateTenantMutation = useUpdateTenant();
  const deleteTenantMutation = useDeleteTenant();

  const [mode, setMode] = useState<"idle" | "creating" | number>("idle");
  const [formError, setFormError] = useState<string | null>(null);

  function handleCreate(payload: TenantPayload) {
    setFormError(null);
    createTenantMutation.mutate(payload, {
      onSuccess: () => setMode("idle"),
      onError: () => setFormError("Mieter konnte nicht angelegt werden."),
    });
  }

  function handleUpdate(tenantId: number, payload: TenantPayload) {
    setFormError(null);
    updateTenantMutation.mutate(
      { tenantId, payload },
      {
        onSuccess: () => setMode("idle"),
        onError: () => setFormError("Mieter konnte nicht aktualisiert werden."),
      },
    );
  }

  function handleDelete(tenantId: number) {
    if (!window.confirm("Mieter wirklich löschen?")) return;
    deleteTenantMutation.mutate(tenantId, {
      onError: () =>
        window.alert(
          "Mieter konnte nicht gelöscht werden - vermutlich besteht noch ein aktiver Mietvertrag oder ein Online-Zugang.",
        ),
    });
  }

  const editingTenant = typeof mode === "number" ? tenants?.find((t) => t.tenant_id === mode) ?? null : null;

  return (
    <div className="tenants-page">
      <Card>
        <div className="tenants-page__header">
          <h1>Mieter</h1>
          {mode === "idle" && (
            <button type="button" onClick={() => setMode("creating")}>
              Neuer Mieter
            </button>
          )}
        </div>

        {isLoading && <p>Lädt…</p>}

        <table className="tenants-page__table">
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
            {tenants?.map((tenant) => (
              <tr key={tenant.tenant_id}>
                <td>
                  {tenant.first_name} {tenant.last_name}
                </td>
                <td>
                  {tenant.street_and_number}
                  {tenant.postal_code || tenant.city ? `, ${tenant.postal_code ?? ""} ${tenant.city ?? ""}` : ""}
                </td>
                <td>{tenant.email ?? "–"}</td>
                <td>{tenant.iban_last4 ? `…${tenant.iban_last4}` : "–"}</td>
                <td>{tenant.has_online_access ? "Ja" : "Nein"}</td>
                <td className="tenants-page__actions">
                  <button type="button" onClick={() => setMode(tenant.tenant_id)}>
                    Bearbeiten
                  </button>
                  <button type="button" onClick={() => handleDelete(tenant.tenant_id)}>
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
          <h2>Neuen Mieter anlegen</h2>
          <TenantForm
            submitLabel="Anlegen"
            onSubmit={handleCreate}
            onCancel={() => setMode("idle")}
            isSubmitting={createTenantMutation.isPending}
            error={formError}
          />
        </Card>
      )}

      {editingTenant && (
        <Card>
          <h2>
            Mieter bearbeiten: {editingTenant.first_name} {editingTenant.last_name}
          </h2>
          <TenantForm
            key={editingTenant.tenant_id}
            initialValues={editingTenant}
            submitLabel="Speichern"
            onSubmit={(payload) => handleUpdate(editingTenant.tenant_id, payload)}
            onCancel={() => setMode("idle")}
            isSubmitting={updateTenantMutation.isPending}
            error={formError}
          />
        </Card>
      )}
    </div>
  );
}