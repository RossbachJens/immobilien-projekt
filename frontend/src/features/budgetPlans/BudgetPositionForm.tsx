// frontend/src/features/budgetPlans/BudgetPositionForm.tsx — vollständig ersetzen
import { useState } from "react";
import type { FormEvent } from "react";

import { AllocationKeyField } from "../../components/AllocationKeyField";
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

export function BudgetPositionForm({
  propertyId,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: BudgetPositionFormProps) {
  // Ohne type-Filter laden, da Positionen sowohl Aufwandskonten als auch
  // (Liegenschaftseigene) Rücklagenkonten referenzieren dürfen - Trennung
  // erfolgt unten über optgroups.
  const { data: accounts, isLoading: accountsLoading } = useAccounts({
    property_id: propertyId,
    is_active: true,
  });
  const expenseAccounts = (accounts ?? []).filter((a) => a.type === "AUFWAND");
  const reserveAccounts = (accounts ?? []).filter((a) => a.is_reserve_account && a.type !== "AUFWAND");

  const [accountId, setAccountId] = useState<number | "">("");
  const [description, setDescription] = useState("");
  const [plannedAmount, setPlannedAmount] = useState("");
  const [keyMode, setKeyMode] = useState<"standard" | "custom">("standard");
  const [standardKey, setStandardKey] = useState("MEA");
  const [customKey, setCustomKey] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (accountId === "") return;
    onSubmit({
      account_id: accountId,
      description: description || null,
      planned_amount: Number(plannedAmount),
      allocation_key_type: keyMode === "standard" ? standardKey : customKey,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="budget-position-form">
      {accountsLoading && <p className="budget-position-form__hint">Konten werden geladen…</p>}
      <label>
        Konto *
        <select
          value={accountId}
          onChange={(e) => setAccountId(e.target.value ? Number(e.target.value) : "")}
          required
        >
          <option value="">– Konto wählen –</option>
          {expenseAccounts.length > 0 && (
            <optgroup label="Aufwandskonten">
              {expenseAccounts.map((a) => (
                <option key={a.account_id} value={a.account_id} title={accountLabel(a)}>
                  {accountLabelShort(a)}
                </option>
              ))}
            </optgroup>
          )}
          {reserveAccounts.length > 0 && (
            <optgroup label="Rücklagenkonten">
              {reserveAccounts.map((a) => (
                <option key={a.account_id} value={a.account_id} title={accountLabel(a)}>
                  {accountLabelShort(a)}
                </option>
              ))}
            </optgroup>
          )}
        </select>
      </label>
      <label>
        Bezeichnung
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="z.B. Hausmeister, Haftpflichtversicherung, Gebäudeversicherung"
        />
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

      <AllocationKeyField
        mode={keyMode}
        onModeChange={setKeyMode}
        standardKey={standardKey}
        onStandardKeyChange={setStandardKey}
        customKey={customKey}
        onCustomKeyChange={setCustomKey}
      />

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