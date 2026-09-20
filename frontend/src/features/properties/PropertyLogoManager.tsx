// frontend/src/features/properties/PropertyLogoManager.tsx
import { useState } from "react";
import type { ChangeEvent } from "react";

import { propertyLogoUrl } from "./api";
import { useDeletePropertyLogo, useUploadPropertyLogo } from "./useProperties";
import "./PropertyLogoManager.css";

interface PropertyLogoManagerProps {
  propertyId: number;
  hasLogo: boolean;
}

export function PropertyLogoManager({ propertyId, hasLogo }: PropertyLogoManagerProps) {
  const uploadMutation = useUploadPropertyLogo();
  const deleteMutation = useDeletePropertyLogo();
  const [error, setError] = useState<string | null>(null);
  // Erzwingt ein frisches <img>, nachdem ein Logo ersetzt wurde - die URL
  // selbst bleibt gleich (/properties/{id}/logo), der Browser würde sonst
  // das gecachte alte Bild weiter anzeigen.
  const [cacheBust, setCacheBust] = useState(0);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    uploadMutation.mutate(
      { propertyId, file },
      {
        onSuccess: () => setCacheBust((n) => n + 1),
        onError: () => setError("Logo konnte nicht hochgeladen werden - nur PNG/JPEG, max. 2 MB."),
      },
    );
    event.target.value = "";
  }

  function handleDelete() {
    if (!window.confirm("Logo wirklich entfernen?")) return;
    setError(null);
    deleteMutation.mutate(propertyId, {
      onError: () => setError("Logo konnte nicht entfernt werden."),
    });
  }

  return (
    <div className="property-logo-manager">
      <span className="property-logo-manager__label">Logo für PDF-Seitenkopf</span>
      {hasLogo ? (
        <img
          className="property-logo-manager__preview"
          src={`${propertyLogoUrl(propertyId)}?v=${cacheBust}`}
          alt="Aktuelles Logo"
        />
      ) : (
        <span className="property-logo-manager__empty">Kein Logo hinterlegt</span>
      )}
      <div className="property-logo-manager__actions">
        <label className="property-logo-manager__upload">
          {hasLogo ? "Logo ersetzen" : "Logo hochladen"}
          <input type="file" accept="image/png,image/jpeg" onChange={handleFileChange} hidden />
        </label>
        {hasLogo && (
          <button type="button" onClick={handleDelete} disabled={deleteMutation.isPending}>
            Entfernen
          </button>
        )}
      </div>
      {error && <p className="property-logo-manager__error">{error}</p>}
    </div>
  );
}