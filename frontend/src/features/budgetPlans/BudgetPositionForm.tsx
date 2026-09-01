// frontend/src/features/budgetPlans/BudgetPositionForm.tsx — vollständig ersetzen
import { useState } from "react";
import type { FormEvent } from "react";

import { AllocationKeyField } from "../../components/AllocationKeyField";
import { accountLabel, accountLabelShort } from "../accounts/format";
import { useAccounts } from "../accounts/useAccounts";

import type { BudgetPosition, BudgetPositionPayload } from "./api";
import "./BudgetPositionForm.css";

const STANDARD_KEYS = ["MEA", "Wohnflaeche"];

interface BudgetPositionFormProps {
  propertyId: number;
  // Gesetzt = Bearbeiten einer bestehenden Position statt Neuanlage - nur
  // möglich, solange der Plan im Entwurf ist (siehe BudgetPlansPage).
  initialValues?: BudgetPosition;
  submitLabel?: string;
  onSubmit: (payload: BudgetPositionPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function BudgetPositionForm({
  propertyId,
  initialValues,
  submitLabel,
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

  const initialIsStandardKey = initialValues
    ? STANDARD_KEYS.includes(initialValues.allocation_key_type)
    : true;

  const [accountId, setAccountId] = useState<number | "">(initialValues?.account_id ?? "");
  const [description, setDescription] = useState(initialValues?.description ?? "");
  const [plannedAmount, setPlannedAmount] = useState(
    initialValues != null ? String(initialValues.planned_amount) : "",
  );
  const [keyMode, setKeyMode] = useState<"standard" | "custom">(
    initialIsStandardKey ? "standard" : "custom",
  );
  const [standardKey, setStandardKey] = useState(
    initialIsStandardKey ? initialValues?.allocation_key_type ?? "MEA" : "MEA",
  );
  const [customKey, setCustomKey] = useState(
    !initialIsStandardKey ? initialValues?.allocation_key_type ?? "" : "",
  );

  const isEdit = initialValues !== undefined;

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
          {isSubmitting
            ? "Wird gespeichert…"
            : (submitLabel ?? (isEdit ? "Speichern" : "Position anlegen & verteilen"))}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}
