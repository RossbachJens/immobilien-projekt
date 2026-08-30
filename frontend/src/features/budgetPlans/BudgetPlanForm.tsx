// frontend/src/features/budgetPlans/BudgetPlanForm.tsx — vollständig ersetzen
import { useState } from "react";
import type { FormEvent } from "react";

import { useResolutions } from "../resolutions/useResolutions";

import type { BudgetPlanPayload } from "./api";
import "./BudgetPlanForm.css";

interface BudgetPlanFormProps {
  propertyId: number;
  onSubmit: (payload: BudgetPlanPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

function nextYear(): number {
  return new Date().getFullYear() + 1;
}

export function BudgetPlanForm({ propertyId, onSubmit, onCancel, isSubmitting, error }: BudgetPlanFormProps) {
  const { data: resolutions } = useResolutions(propertyId);

  const [fiscalYear, setFiscalYear] = useState(String(nextYear()));
  const [title, setTitle] = useState("");
  const [resolutionId, setResolutionId] = useState<number | "">("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      property_id: propertyId,
      fiscal_year: Number(fiscalYear),
      title,
      resolution_id: resolutionId === "" ? null : resolutionId,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="budget-plan-form">
      <label>
        Wirtschaftsjahr *
        <input type="number" value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)} required />
      </label>
      <label>
        Titel *
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={`z.B. Wirtschaftsplan ${fiscalYear}`}
          required
        />
      </label>
      <label>
        Zugehöriger Beschluss (optional)
        <select value={resolutionId} onChange={(e) => setResolutionId(e.target.value ? Number(e.target.value) : "")}>
          <option value="">– noch kein Beschluss –</option>
          {resolutions?.map((r) => (
            <option key={r.resolution_id} value={r.resolution_id}>
              Lfd. Nr. {r.lfd_nr} – {r.title}
            </option>
          ))}
        </select>
      </label>
      {error && <p className="budget-plan-form__error">{error}</p>}
      <div className="budget-plan-form__actions">
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