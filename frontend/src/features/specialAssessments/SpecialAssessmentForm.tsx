// frontend/src/features/specialAssessments/SpecialAssessmentForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { AllocationKeyField } from "../../components/AllocationKeyField";
import { useResolutions } from "../resolutions/useResolutions";

import type { SpecialAssessmentPayload } from "./api";
import "./SpecialAssessmentForm.css";

interface SpecialAssessmentFormProps {
  propertyId: number;
  onSubmit: (payload: SpecialAssessmentPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function SpecialAssessmentForm({
  propertyId,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: SpecialAssessmentFormProps) {
  const { data: resolutions } = useResolutions(propertyId);

  const [title, setTitle] = useState("");
  const [totalAmount, setTotalAmount] = useState("");
  const [dueDate, setDueDate] = useState(todayIso());
  const [referenceYear, setReferenceYear] = useState(String(new Date().getFullYear()));
  const [keyMode, setKeyMode] = useState<"standard" | "custom">("standard");
  const [standardKey, setStandardKey] = useState("MEA");
  const [customKey, setCustomKey] = useState("");
  const [resolutionId, setResolutionId] = useState<number | "">("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      property_id: propertyId,
      title,
      total_required_amount: Number(totalAmount),
      due_date: dueDate,
      allocation_key_type: keyMode === "standard" ? standardKey : customKey,
      reference_year: Number(referenceYear),
      resolution_id: resolutionId === "" ? null : resolutionId,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="special-assessment-form">
      <label>
        Titel *
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="z.B. Fassadensanierung" required />
      </label>
      <label>
        Gesamtbetrag (€) *
        <input
          type="number"
          min="0.01"
          step="0.01"
          value={totalAmount}
          onChange={(e) => setTotalAmount(e.target.value)}
          required
        />
      </label>
      <label>
        Fälligkeitsdatum *
        <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
      </label>
      <label>
        Bezugsjahr (für individuellen Umlageschlüssel)
        <input type="number" value={referenceYear} onChange={(e) => setReferenceYear(e.target.value)} />
      </label>

      <AllocationKeyField
        mode={keyMode}
        onModeChange={setKeyMode}
        standardKey={standardKey}
        onStandardKeyChange={setStandardKey}
        customKey={customKey}
        onCustomKeyChange={setCustomKey}
      />

      <label>
        Zugehöriger Beschluss (optional)
        <select value={resolutionId} onChange={(e) => setResolutionId(e.target.value ? Number(e.target.value) : "")}>
          <option value="">– kein Beschluss –</option>
          {resolutions?.map((r) => (
            <option key={r.resolution_id} value={r.resolution_id}>
              Lfd. Nr. {r.lfd_nr} – {r.title}
            </option>
          ))}
        </select>
      </label>

      {error && <p className="special-assessment-form__error">{error}</p>}
      <div className="special-assessment-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird verteilt…" : "Sonderumlage anlegen & verteilen"}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}