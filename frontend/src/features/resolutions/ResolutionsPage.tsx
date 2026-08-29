// frontend/src/features/resolutions/ResolutionsPage.tsx
import { useState } from "react";

import { Card } from "../../components/Card";
import { useProperties } from "../properties/useProperties";
import type { ResolutionPayload } from "./api";
import { ResolutionForm } from "./ResolutionForm";
import { useCreateResolution, useResolutions } from "./useResolutions";
import "./ResolutionsPage.css";

const RESOLUTION_TYPE_LABELS: Record<string, string> = {
  Eigentuemerversammlung: "Eigentümerversammlung",
  Umlaufbeschluss: "Umlaufbeschluss",
};

export function ResolutionsPage() {
  const { data: properties, isLoading: propertiesLoading } = useProperties();
  const [propertyId, setPropertyId] = useState<number | "">("");

  const selectedPropertyId = propertyId === "" ? undefined : propertyId;
  const { data: resolutions, isLoading, isError, error } = useResolutions(selectedPropertyId);
  const createMutation = useCreateResolution(selectedPropertyId ?? -1);

  const [mode, setMode] = useState<"idle" | "creating">("idle");
  const [formError, setFormError] = useState<string | null>(null);

  // 403 (Mieter) von "noch keine Beschlüsse" unterscheiden - sonst wirkt es
  // wie ein leeres Objekt statt einer fehlenden Berechtigung.
  const isForbidden =
    isError && typeof error === "object" && error !== null && "response" in error &&
    (error as { response?: { status?: number } }).response?.status === 403;

  function handleCreate(payload: ResolutionPayload) {
    setFormError(null);
    createMutation.mutate(payload, {
      onSuccess: () => setMode("idle"),
      onError: () => setFormError("Beschluss konnte nicht angelegt werden."),
    });
  }

  return (
    <div className="resolutions-page">
      <Card>
        <h1>Beschluss-Sammlung</h1>
        <p className="resolutions-page__hint">
          Gesetzlich vorgeschriebene Dokumentation nach § 24 WEG. Einträge werden nicht bearbeitet
          oder gelöscht.
        </p>
        {propertiesLoading && <p>Lädt Liegenschaften…</p>}
        <label className="resolutions-page__property-select">
          Liegenschaft
          <select
            value={propertyId}
            onChange={(e) => {
              setPropertyId(e.target.value ? Number(e.target.value) : "");
              setMode("idle");
            }}
          >
            <option value="">– bitte wählen –</option>
            {properties?.map((p) => (
              <option key={p.property_id} value={p.property_id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
      </Card>

      {selectedPropertyId !== undefined && isForbidden && (
        <Card>
          <p>Kein Zugriff auf die Beschluss-Sammlung mit diesem Konto.</p>
        </Card>
      )}

      {selectedPropertyId !== undefined && !isForbidden && (
        <Card>
          <div className="resolutions-page__header">
            <h2>Beschlüsse</h2>
            {mode === "idle" && (
              <button type="button" onClick={() => setMode("creating")}>
                Neuer Beschluss
              </button>
            )}
          </div>

          {isLoading && <p>Lädt…</p>}
          {!isLoading && resolutions?.length === 0 && <p>Noch keine Beschlüsse erfasst.</p>}

          <ul className="resolutions-page__list">
            {resolutions?.map((r) => (
              <li key={r.resolution_id}>
                <div>
                  <strong>{r.resolution_date}</strong> · {r.title}
                  {r.resolution_type && (
                    <> · {RESOLUTION_TYPE_LABELS[r.resolution_type] ?? r.resolution_type}</>
                  )}
                </div>
                {r.description && <p className="resolutions-page__description">{r.description}</p>}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {mode === "creating" && selectedPropertyId !== undefined && (
        <Card>
          <h2>Neuen Beschluss erfassen</h2>
          <ResolutionForm
            propertyId={selectedPropertyId}
            submitLabel="Anlegen"
            onSubmit={handleCreate}
            onCancel={() => setMode("idle")}
            isSubmitting={createMutation.isPending}
            error={formError}
          />
        </Card>
      )}
    </div>
  );
}