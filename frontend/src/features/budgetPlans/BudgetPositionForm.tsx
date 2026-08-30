// frontend/src/features/budgetPlans/BudgetPositionForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { accountLabel, accountLabelShort } from "../accounts/format";
import { useAccounts } from "../accounts/useAccounts";

import type { BudgetPositionPayload } from "./api";
import "./BudgetPositionForm.css";

interface BudgetPositionFormProps {
  propertyId: number;
  onSubmit: (payload: BudgetPositionPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

const STANDARD_KEYS = ["MEA", "Wohnflaeche"] as const;

export function BudgetPositionForm({
  propertyId,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: BudgetPositionFormProps) {
  // Wirtschaftsplan-Positionen sind Kostenpositionen - bewusst auf
  // Aufwandskonten eingegrenzt (anders als bei Buchungen, wo jede Kontoart
  // vorkommen kann).
  const { data: accounts, isLoading: accountsLoading } = useAccounts({
    property_id: propertyId,
    is_active: true,
    type: "AUFWAND",
  });

  const [accountId, setAccountId] = useState<number | "">("");
  const [plannedAmount, setPlannedAmount] = useState("");
  const [keyMode, setKeyMode] = useState<"standard" | "custom">("standard");
  const [allocationKey, setAllocationKey] = useState<string>("MEA");
  const [customKey, setCustomKey] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (accountId === "") return;
    onSubmit({
      account_id: accountId,
      planned_amount: Number(plannedAmount),
      allocation_key_type: keyMode === "standard" ? allocationKey : customKey,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="budget-position-form">
      {accountsLoading && <p className="budget-position-form__hint">Konten werden geladen…</p>}
      <label>
        Aufwandskonto *
        <select
          value={accountId}
          onChange={(e) => setAccountId(e.target.value ? Number(e.target.value) : "")}
          required
        >
          <option value="">– Konto wählen –</option>
          {accounts?.map((a) => (
            <option key={a.account_id} value={a.account_id} title={accountLabel(a)}>
              {accountLabelShort(a)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Geplanter Jahresbetrag (€) *
        <input
          type="number"
          min="0"
          step="0.01"
          value={plannedAmount}
          onChange={(e) => setPlannedAmount(e.target.value)}
          required
        />
      </label>

      <fieldset className="budget-position-form__key">
        <legend>Verteilerschlüssel</legend>
        <label className="budget-position-form__radio">
          <input type="radio" checked={keyMode === "standard"} onChange={() => setKeyMode("standard")} />
          Standard
        </label>
        {keyMode === "standard" && (
          <select value={allocationKey} onChange={(e) => setAllocationKey(e.target.value)}>
            {STANDARD_KEYS.map((k) => (
              <option key={k} value={k}>
                {k === "MEA" ? "Miteigentumsanteile (MEA)" : "Wohnfläche"}
              </option>
            ))}
          </select>
        )}
        <label className="budget-position-form__radio">
          <input type="radio" checked={keyMode === "custom"} onChange={() => setKeyMode("custom")} />
          Individueller Umlageschlüssel
        </label>
        {keyMode === "custom" && (
          <input
            value={customKey}
            onChange={(e) => setCustomKey(e.target.value)}
            placeholder="genauer key_type, z.B. Heizkosten_Verbrauch"
            required
          />
        )}
      </fieldset>

      {error && <p className="budget-position-form__error">{error}</p>}
      <div className="budget-position-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird verteilt…" : "Position anlegen & verteilen"}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}