// frontend/src/features/properties/PropertiesPage.tsx
import { useState } from "react";

import { Card } from "../../components/Card";
import type { PropertyPayload } from "./api";
import { PropertyForm } from "./PropertyForm";
import { useCreateProperty, useProperties, useUpdateProperty } from "./useProperties";
import "./PropertiesPage.css";

export function PropertiesPage() {
  const { data: properties, isLoading } = useProperties();
  const createPropertyMutation = useCreateProperty();
  const updatePropertyMutation = useUpdateProperty();

  const [mode, setMode] = useState<"idle" | "creating" | number>("idle");
  const [formError, setFormError] = useState<string | null>(null);

  function handleCreate(payload: PropertyPayload) {
    setFormError(null);
    createPropertyMutation.mutate(payload, {
      onSuccess: () => setMode("idle"),
      onError: () => setFormError("Liegenschaft konnte nicht angelegt werden."),
    });
  }

  function handleUpdate(propertyId: number, payload: PropertyPayload) {
    setFormError(null);
    updatePropertyMutation.mutate(
      { propertyId, payload },
      {
        onSuccess: () => setMode("idle"),
        onError: () => setFormError("Liegenschaft konnte nicht aktualisiert werden."),
      },
    );
  }

  const editingProperty =
    typeof mode === "number" ? properties?.find((p) => p.property_id === mode) ?? null : null;

  return (
    <div className="properties-page">
      <Card>
        <div className="properties-page__header">
          <h1>Liegenschaften</h1>
          {mode === "idle" && (
            <button type="button" onClick={() => setMode("creating")}>
              Neue Liegenschaft
            </button>
          )}
        </div>
        {isLoading && <p>Lädt…</p>}
        <ul className="properties-page__list">
          {properties?.map((property) => (
            <li key={property.property_id}>
              <div>
                <strong>{property.name}</strong> — {property.address}
                {property.total_square_meters != null && <> · {property.total_square_meters} m²</>}
                {property.construction_year != null && <> · Baujahr {property.construction_year}</>}
                {property.total_mea != null && <> · MEA gesamt {property.total_mea}</>}
              </div>
              <button type="button" onClick={() => setMode(property.property_id)}>
                Bearbeiten
              </button>
            </li>
          ))}
        </ul>
      </Card>

      {mode === "creating" && (
        <Card>
          <h2>Neue Liegenschaft anlegen</h2>
          <PropertyForm
            submitLabel="Anlegen"
            onSubmit={handleCreate}
            onCancel={() => setMode("idle")}
            isSubmitting={createPropertyMutation.isPending}
            error={formError}
          />
        </Card>
      )}

      {editingProperty && (
        <Card>
          <h2>Liegenschaft bearbeiten: {editingProperty.name}</h2>
          <PropertyForm
            key={editingProperty.property_id}
            initialValues={editingProperty}
            submitLabel="Speichern"
            onSubmit={(payload) => handleUpdate(editingProperty.property_id, payload)}
            onCancel={() => setMode("idle")}
            isSubmitting={updatePropertyMutation.isPending}
            error={formError}
          />
        </Card>
      )}
    </div>
  );
}