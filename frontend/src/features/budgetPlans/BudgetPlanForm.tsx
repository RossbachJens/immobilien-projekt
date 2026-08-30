// frontend/src/features/budgetPlans/BudgetPlanForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

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
  const [fiscalYear, setFiscalYear] = useState(String(nextYear()));
  const [title, setTitle] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({ property_id: propertyId, fiscal_year: Number(fiscalYear), title });
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