// frontend/src/features/properties/PropertyForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { Property, PropertyPayload } from "./api";
import "./PropertyForm.css";

interface PropertyFormProps {
  initialValues?: Property;
  submitLabel: string;
  onSubmit: (payload: PropertyPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function PropertyForm({
  initialValues,
  submitLabel,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: PropertyFormProps) {
  const [name, setName] = useState(initialValues?.name ?? "");
  const [address, setAddress] = useState(initialValues?.address ?? "");
  const [totalSquareMeters, setTotalSquareMeters] = useState(
    initialValues?.total_square_meters != null ? String(initialValues.total_square_meters) : "",
  );
  const [constructionYear, setConstructionYear] = useState(
    initialValues?.construction_year != null ? String(initialValues.construction_year) : "",
  );
  const [totalMea, setTotalMea] = useState(
    initialValues?.total_mea != null ? String(initialValues.total_mea) : "",
  );
  const [description, setDescription] = useState(initialValues?.description ?? "");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      name,
      address,
      total_square_meters: totalSquareMeters ? Number(totalSquareMeters) : null,
      construction_year: constructionYear ? Number(constructionYear) : null,
      total_mea: totalMea ? Number(totalMea) : null,
      description: description || null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="property-form">
      <label>
        Name
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>
      <label>
        Adresse
        <input value={address} onChange={(e) => setAddress(e.target.value)} required />
      </label>
      <label>
        Wohn-/Nutzfläche gesamt (m²)
        <input
          type="number"
          min="0"
          step="0.01"
          value={totalSquareMeters}
          onChange={(e) => setTotalSquareMeters(e.target.value)}
        />
      </label>
      <label>
        Baujahr
        <input
          type="number"
          min="1800"
          max={new Date().getFullYear()}
          value={constructionYear}
          onChange={(e) => setConstructionYear(e.target.value)}
        />
      </label>
      <label>
        Miteigentumsanteile gesamt
        <input
          type="number"
          min="0.01"
          step="0.01"
          value={totalMea}
          onChange={(e) => setTotalMea(e.target.value)}
          placeholder="z.B. 1000"
        />
      </label>
      <label>
        Beschreibung
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
      </label>
      {error && <p className="property-form__error">{error}</p>}
      <div className="property-form__actions">
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