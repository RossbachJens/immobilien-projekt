// frontend/src/features/resolutions/ResolutionForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { ResolutionPayload } from "./api";
import "./ResolutionForm.css";

interface ResolutionFormProps {
  propertyId: number;
  submitLabel: string;
  onSubmit: (payload: ResolutionPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function ResolutionForm({
  propertyId,
  submitLabel,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: ResolutionFormProps) {
  const [resolutionDate, setResolutionDate] = useState(todayIso());
  const [title, setTitle] = useState("");
  const [resolutionType, setResolutionType] = useState("");
  const [description, setDescription] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      property_id: propertyId,
      resolution_date: resolutionDate,
      title,
      resolution_type: resolutionType || null,
      description: description || null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="resolution-form">
      <label>
        Datum *
        <input type="date" value={resolutionDate} onChange={(e) => setResolutionDate(e.target.value)} required />
      </label>
      <label>
        Titel *
        <input value={title} onChange={(e) => setTitle(e.target.value)} required />
      </label>
      <label>
        Art
        <select value={resolutionType} onChange={(e) => setResolutionType(e.target.value)}>
          <option value="">– keine Angabe –</option>
          <option value="Eigentuemerversammlung">Eigentümerversammlung</option>
          <option value="Umlaufbeschluss">Umlaufbeschluss</option>
        </select>
      </label>
      <label>
        Beschreibung
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} />
      </label>

      {error && <p className="resolution-form__error">{error}</p>}

      <div className="resolution-form__actions">
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