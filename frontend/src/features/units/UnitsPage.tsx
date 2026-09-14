// frontend/src/features/units/UnitsPage.tsx
import { useEffect, useState } from "react";

import { Card } from "../../components/Card";
import { useCurrentProperty } from "../../context/PropertyContext";
import type { UnitPayload } from "./api";
import { UnitForm } from "./UnitForm";
import { UnitOwnerAssignments } from "./UnitOwnerAssignments";
import { useCreateUnit, useDeleteUnit, useUnits, useUpdateUnit } from "./useUnits";
import "./UnitsPage.css";

export function UnitsPage() {
  const { propertyId, property, properties, isLoading: propertiesLoading } = useCurrentProperty();

  const { data: units, isLoading: unitsLoading } = useUnits(propertyId ?? undefined);

  const createUnitMutation = useCreateUnit(propertyId ?? -1);
  const updateUnitMutation = useUpdateUnit(propertyId ?? -1);
  const deleteUnitMutation = useDeleteUnit(propertyId ?? -1);

  const [mode, setMode] = useState<"idle" | "creating" | number>("idle");
  const [expandedUnitId, setExpandedUnitId] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    setMode("idle");
    setExpandedUnitId(null);
    setFormError(null);
  }, [propertyId]);

  function handleCreate(payload: UnitPayload) {
    setFormError(null);
    createUnitMutation.mutate(payload, {
      onSuccess: () => setMode("idle"),
      onError: () => setFormError("Einheit konnte nicht angelegt werden - Nummer eventuell schon vergeben."),
    });
  }

  function handleUpdate(unitId: number, payload: UnitPayload) {
    setFormError(null);
    updateUnitMutation.mutate(
      { unitId, payload },
      {
        onSuccess: () => setMode("idle"),
        onError: () => setFormError("Einheit konnte nicht aktualisiert werden."),
      },
    );
  }

  function handleDelete(unitId: number) {
    if (!window.confirm("Einheit wirklich löschen?")) return;
    deleteUnitMutation.mutate(unitId, {
      onError: () => window.alert("Einheit konnte nicht gelöscht werden."),
    });
  }

  const editingUnit = typeof mode === "number" ? units?.find((u) => u.unit_id === mode) ?? null : null;

  if (propertiesLoading) {
    return (
      <div className="units-page">
        <Card>
          <p>Lädt Liegenschaften…</p>
        </Card>
      </div>
    );
  }

  if (propertyId == null || properties.length === 0) {
    return (
      <div className="units-page">
        <Card>
          <h1>Einheiten</h1>
          <p>Bitte zuerst links in der Sidebar eine Liegenschaft auswählen.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="units-page">
      <Card>
        <div className="units-page__header">
          <h2>Einheiten – {property?.name}</h2>
          {mode === "idle" && (
            <button type="button" onClick={() => setMode("creating")}>
              Neue Einheit
            </button>
          )}
        </div>

        {unitsLoading && <p>Lädt…</p>}
        {!unitsLoading && units?.length === 0 && <p>Noch keine Einheiten angelegt.</p>}

        <ul className="units-page__list">
          {units?.map((unit) => (
            <li key={unit.unit_id} className="units-page__unit">
              <div className="units-page__unit-row">
                <div>
                  <strong>{unit.unit_number}</strong>
                  {unit.floor && <> · {unit.floor}</>}
                  {" · "}
                  {unit.square_meters} m²
                  {unit.mea != null && <> · MEA {unit.mea}</>}
                  {unit.unit_type && <> · {unit.unit_type}</>}
                </div>
                <div className="units-page__unit-actions">
                  <button
                    type="button"
                    onClick={() => setExpandedUnitId(expandedUnitId === unit.unit_id ? null : unit.unit_id)}
                  >
                    {expandedUnitId === unit.unit_id ? "Eigentümer ausblenden" : "Eigentümer"}
                  </button>
                  <button type="button" onClick={() => setMode(unit.unit_id)}>
                    Bearbeiten
                  </button>
                  <button type="button" onClick={() => handleDelete(unit.unit_id)}>
                    Löschen
                  </button>
                </div>
              </div>
              {expandedUnitId === unit.unit_id && (
                <UnitOwnerAssignments unitId={unit.unit_id} unitNumber={unit.unit_number} />
              )}
            </li>
          ))}
        </ul>
      </Card>

      {mode === "creating" && (
        <Card>
          <h2>Neue Einheit anlegen</h2>
          <UnitForm
            propertyId={propertyId}
            propertyTotalMea={property?.total_mea}
            submitLabel="Anlegen"
            onSubmit={handleCreate}
            onCancel={() => setMode("idle")}
            isSubmitting={createUnitMutation.isPending}
            error={formError}
          />
        </Card>
      )}

      {editingUnit && (
        <Card>
          <h2>Einheit bearbeiten: {editingUnit.unit_number}</h2>
          <UnitForm
            key={editingUnit.unit_id}
            propertyId={propertyId}
            propertyTotalMea={property?.total_mea}
            initialValues={editingUnit}
            submitLabel="Speichern"
            onSubmit={(payload) => handleUpdate(editingUnit.unit_id, payload)}
            onCancel={() => setMode("idle")}
            isSubmitting={updateUnitMutation.isPending}
            error={formError}
          />
        </Card>
      )}
    </div>
  );
}