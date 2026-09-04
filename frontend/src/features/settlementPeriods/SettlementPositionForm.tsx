// frontend/src/features/settlementPeriods/SettlementPositionForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { AllocationKeyField } from "../../components/AllocationKeyField";
import { accountLabel, accountLabelShort } from "../accounts/format";
import { useAccounts } from "../accounts/useAccounts";

import type { SettlementPosition, SettlementPositionPayload } from "./api";
import "./SettlementPositionForm.css";

const STANDARD_KEYS = ["MEA", "Wohnflaeche"];

interface SettlementPositionFormProps {
  propertyId: number;
  // Gesetzt = Bearbeiten einer bestehenden Position statt Neuanlage - nur
  // möglich, solange die Abrechnung im Entwurf ist (siehe SettlementPeriodsPage).
  initialValues?: SettlementPosition;
  submitLabel?: string;
  onSubmit: (payload: SettlementPositionPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function SettlementPositionForm({
  propertyId,
  initialValues,
  submitLabel,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: SettlementPositionFormProps) {
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
  const [isApportionable, setIsApportionable] = useState(initialValues?.is_apportionable ?? true);
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
      allocation_key_type: keyMode === "standard" ? standardKey : customKey,
      is_apportionable: isApportionable,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="settlement-position-form">
      {accountsLoading && <p className="settlement-position-form__hint">Konten werden geladen…</p>}
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
          placeholder="z.B. Hausmeister, Heizung/Wasser/Abwasser"
        />
      </label>
      <label className="settlement-position-form__checkbox">
        <input type="checkbox" checked={isApportionable} onChange={(e) => setIsApportionable(e.target.checked)} />
        Umlagefähig (§ 35a EStG / Betriebskosten)
      </label>

      <AllocationKeyField
        mode={keyMode}
        onModeChange={setKeyMode}
        standardKey={standardKey}
        onStandardKeyChange={setStandardKey}
        customKey={customKey}
        onCustomKeyChange={setCustomKey}
      />

      {!isEdit && (
        <p className="settlement-position-form__hint">
          Der Ist-Betrag wird automatisch aus den Buchungen im Abrechnungszeitraum ermittelt - keine manuelle
          Eingabe nötig.
        </p>
      )}
      {isEdit && initialValues && (
        <p className="settlement-position-form__hint">
          Aktueller Ist-Betrag: {initialValues.actual_amount.toFixed(2)} € - wird beim Speichern automatisch
          neu aus den Buchungen ermittelt.
        </p>
      )}

      {error && <p className="settlement-position-form__error">{error}</p>}
      <div className="settlement-position-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird ermittelt…" : (submitLabel ?? "Position anlegen & verteilen")}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}