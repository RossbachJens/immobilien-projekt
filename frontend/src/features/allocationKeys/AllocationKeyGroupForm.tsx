// frontend/src/features/allocationKeys/AllocationKeyGroupForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { Unit } from "../units/api";
import type { AllocationKeyCreatePayload } from "./api";
import "./AllocationKeyGroupForm.css";

interface AllocationKeyGroupFormProps {
  propertyId: number;
  units: Unit[];
  existingKeyTypes: string[];
  onSubmit: (payloads: AllocationKeyCreatePayload[]) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

function nextYear(): number {
  return new Date().getFullYear() + 1;
}

export function AllocationKeyGroupForm({
  propertyId,
  units,
  existingKeyTypes,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: AllocationKeyGroupFormProps) {
  const sortedUnits = [...units].sort((a, b) =>
    a.unit_number.localeCompare(b.unit_number, undefined, { numeric: true, sensitivity: "base" }),
  );

  const [keyType, setKeyType] = useState("");
  const [denominator, setDenominator] = useState("");
  const [validFromYear, setValidFromYear] = useState(String(nextYear()));
  const [hasEnd, setHasEnd] = useState(false);
  const [validToYear, setValidToYear] = useState("");
  const [numerators, setNumerators] = useState<Record<number, string>>({});
  const [validationError, setValidationError] = useState<string | null>(null);

  function setNumerator(unitId: number, value: string) {
    setNumerators((prev) => ({ ...prev, [unitId]: value }));
  }

  const sum = sortedUnits.reduce((acc, u) => acc + (Number(numerators[u.unit_id]) || 0), 0);
  const denominatorValue = Number(denominator) || 0;
  const difference = Math.round((denominatorValue - sum) * 10000) / 10000;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setValidationError(null);

    const payloads: AllocationKeyCreatePayload[] = [];
    for (const unit of sortedUnits) {
      const raw = numerators[unit.unit_id];
      const numerator = Number(raw);
      if (raw && numerator > 0) {
        payloads.push({
          property_id: propertyId,
          unit_id: unit.unit_id,
          key_type: keyType,
          numerator_value: numerator,
          denominator_value: denominatorValue,
          valid_from_year: Number(validFromYear),
          valid_to_year: hasEnd && validToYear ? Number(validToYear) : null,
        });
      }
    }

    if (payloads.length === 0) {
      setValidationError("Bitte für mindestens eine Einheit einen Anteil (Zähler) angeben.");
      return;
    }
    if (difference !== 0) {
      setValidationError(
        `Summe der Zähler (${sum.toFixed(4)}) entspricht nicht dem Nenner (${denominatorValue.toFixed(4)}) ` +
          `- Differenz: ${difference.toFixed(4)}.`,
      );
      return;
    }

    onSubmit(payloads);
  }

  return (
    <form onSubmit={handleSubmit} className="allocation-key-group-form">
      <label>
        Schlüsseltyp / Schlüsselname *
        <input
          value={keyType}
          onChange={(e) => setKeyType(e.target.value)}
          placeholder="z.B. Heizkosten_Verbrauch"
          list="allocation-key-type-suggestions"
          required
        />
      </label>
      <datalist id="allocation-key-type-suggestions">
        {existingKeyTypes.map((t) => (
          <option key={t} value={t} />
        ))}
      </datalist>

      <label>
        Gesamt / Nenner *
        <input
          type="number"
          min="0.0001"
          step="0.0001"
          value={denominator}
          onChange={(e) => setDenominator(e.target.value)}
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
      <p className="allocation-key-group-form__hint">
        Ein Wechsel wird laut Grundsatzentscheidung erst zum 01.01. des angegebenen Jahres wirksam.
      </p>

      <label className="allocation-key-group-form__checkbox">
        <input type="checkbox" checked={hasEnd} onChange={(e) => setHasEnd(e.target.checked)} />
        Gültigkeitsende bereits bekannt
      </label>
      {hasEnd && (
        <label>
          Gültig bis (letztes gültiges Jahr)
          <input
            type="number"
            min="2000"
            max="2100"
            value={validToYear}
            onChange={(e) => setValidToYear(e.target.value)}
            required
          />
        </label>
      )}

      <fieldset className="allocation-key-group-form__units">
        <legend>Anteile je Einheit (Zähler)</legend>
        {sortedUnits.length === 0 && <p>Keine Einheiten in dieser Liegenschaft.</p>}
        {sortedUnits.map((unit) => (
          <label key={unit.unit_id} className="allocation-key-group-form__unit-row">
            {unit.unit_number}
            <input
              type="number"
              min="0"
              step="0.0001"
              value={numerators[unit.unit_id] ?? ""}
              onChange={(e) => setNumerator(unit.unit_id, e.target.value)}
              placeholder="0"
            />
          </label>
        ))}
      </fieldset>

      <div
        className={
          "allocation-key-group-form__balance" +
          (difference !== 0
            ? " allocation-key-group-form__balance--off"
            : " allocation-key-group-form__balance--ok")
        }
      >
        Summe Zähler: {sum.toFixed(4)} · Nenner: {denominatorValue.toFixed(4)}
        {difference !== 0 && <> · Differenz: {difference.toFixed(4)}</>}
      </div>

      {(validationError || error) && (
        <p className="allocation-key-group-form__error">{validationError ?? error}</p>
      )}

      <div className="allocation-key-group-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird angelegt…" : "Umlageschlüssel anlegen"}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}