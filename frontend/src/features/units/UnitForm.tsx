// frontend/src/features/units/UnitForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { Unit, UnitPayload, UnitType } from "./api";
import "./UnitForm.css";

const UNIT_TYPES: UnitType[] = ["Wohnung", "Stellplatz", "Gewerbe"];

interface UnitFormProps {
  propertyId: number;
  propertyTotalMea?: number | null;
  initialValues?: Unit;
  submitLabel: string;
  onSubmit: (payload: UnitPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function UnitForm({
  propertyId,
  propertyTotalMea,
  initialValues,
  submitLabel,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: UnitFormProps) {
  const [unitNumber, setUnitNumber] = useState(initialValues?.unit_number ?? "");
  const [floor, setFloor] = useState(initialValues?.floor ?? "");
  const [squareMeters, setSquareMeters] = useState(String(initialValues?.square_meters ?? ""));
  const [mea, setMea] = useState(initialValues?.mea != null ? String(initialValues.mea) : "");
  const [unitType, setUnitType] = useState<UnitType | "">(initialValues?.unit_type ?? "");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      property_id: propertyId,
      unit_number: unitNumber,
      floor: floor || null,
      square_meters: Number(squareMeters),
      mea: mea ? Number(mea) : null,
      unit_type: unitType || null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="unit-form">
      <label>
        Einheiten-Nr. *
        <input value={unitNumber} onChange={(e) => setUnitNumber(e.target.value)} required />
      </label>
      <label>
        Etage
        <input value={floor ?? ""} onChange={(e) => setFloor(e.target.value)} placeholder="z.B. 2. OG links" />
      </label>
      <label>
        Fläche (m²) *
        <input
          type="number"
          min="0.01"
          step="0.01"
          value={squareMeters}
          onChange={(e) => setSquareMeters(e.target.value)}
          required
        />
      </label>
      <label>
        Miteigentumsanteil (MEA){propertyTotalMea != null && ` (von ${propertyTotalMea} gesamt)`}
        <input
          type="number"
          min="0.01"
          step="0.01"
          value={mea}
          onChange={(e) => setMea(e.target.value)}
          placeholder="z.B. 168.47"
        />
      </label>
      <label>
        Typ
        <select value={unitType} onChange={(e) => setUnitType(e.target.value as UnitType | "")}>
          <option value="">– bitte wählen –</option>
          {UNIT_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>

      {error && <p className="unit-form__error">{error}</p>}

      <div className="unit-form__actions">
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