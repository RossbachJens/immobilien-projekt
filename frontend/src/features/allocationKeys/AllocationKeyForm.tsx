// frontend/src/features/allocationKeys/AllocationKeyForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { Unit } from "../units/api";

import type { AllocationKeyPayload } from "./api";
import "./AllocationKeyForm.css";

function currentYear(): number {
  return new Date().getFullYear();
}

interface AllocationKeyFormProps {
  propertyId: number;
  units: Unit[];
  existingKeyTypes: string[];
  onSubmit: (payload: AllocationKeyPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function AllocationKeyForm({
  propertyId,
  units,
  existingKeyTypes,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: AllocationKeyFormProps) {
  const [unitId, setUnitId] = useState<number | "">("");
  const [keyType, setKeyType] = useState("");
  const [numeratorValue, setNumeratorValue] = useState("");
  const [denominatorValue, setDenominatorValue] = useState("");
  const [validFromYear, setValidFromYear] = useState(String(currentYear() + 1));
  const [hasEnd, setHasEnd] = useState(false);
  const [validToYear, setValidToYear] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (unitId === "") return;
    onSubmit({
      property_id: propertyId,
      unit_id: unitId,
      key_type: keyType,
      numerator_value: Number(numeratorValue),
      denominator_value: Number(denominatorValue),
      valid_from_year: Number(validFromYear),
      valid_to_year: hasEnd && validToYear ? Number(validToYear) : null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="allocation-key-form">
      <label>
        Einheit *
        <select
          value={unitId}
          onChange={(e) => setUnitId(e.target.value ? Number(e.target.value) : "")}
          required
        >
          <option value="">– Einheit wählen –</option>
          {units.map((u) => (
            <option key={u.unit_id} value={u.unit_id}>
              {u.unit_number}
            </option>
          ))}
        </select>
      </label>
      <label>
        Schlüssel-Typ *
        <input
          value={keyType}
          onChange={(e) => setKeyType(e.target.value)}
          placeholder="z.B. Heizkosten_Verbrauch"
          list="allocation-key-type-suggestions"
          maxLength={50}
          required
        />
      </label>
      {existingKeyTypes.length > 0 && (
        <datalist id="allocation-key-type-suggestions">
          {existingKeyTypes.map((t) => (
            <option key={t} value={t} />
          ))}
        </datalist>
      )}
      <label>
        Zähler
        <input
          type="number"
          min="0"
          step="0.0001"
          value={numeratorValue}
          onChange={(e) => setNumeratorValue(e.target.value)}
          placeholder="z.B. 3500"
          required
        />
      </label>
      <label>
        Nenner
        <input
          type="number"
          min="0.0001"
          step="0.0001"
          value={denominatorValue}
          onChange={(e) => setDenominatorValue(e.target.value)}
          placeholder="z.B. 10000"
          required
        />
      </label>
      <label>
        Gültig ab (Jahr) *
        <input
          type="number"
          min="2000"
          max="2100"
          value={validFromYear}
          onChange={(e) => setValidFromYear(e.target.value)}
          required
        />
      </label>
      <label className="allocation-key-form__checkbox">
        <input type="checkbox" checked={hasEnd} onChange={(e) => setHasEnd(e.target.checked)} />
        Gültigkeitsende bereits bekannt
      </label>
      {hasEnd && (
        <label>
          Gültig bis (Jahr)
          <input
            type="number"
            min={validFromYear}
            max="2100"
            value={validToYear}
            onChange={(e) => setValidToYear(e.target.value)}
            required
          />
        </label>
      )}

      <p className="allocation-key-form__hint">
        Anteil = Zähler / Nenner (z.B. 3.500 / 10.000 = 35 %). Ein Wechsel der Werte wirkt erst zum
        nächsten 01.01. – dafür zunächst den bestehenden Schlüssel schließen (Gültig bis = Vorjahr).
      </p>

      {error && <p className="allocation-key-form__error">{error}</p>}
      <div className="allocation-key-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird gespeichert…" : "Anlegen"}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}