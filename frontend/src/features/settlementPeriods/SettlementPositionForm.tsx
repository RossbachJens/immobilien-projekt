// frontend/src/features/settlementPeriods/SettlementPositionForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { AllocationKeyField } from "../../components/AllocationKeyField";
import { accountLabel } from "../accounts/format";
import { useAccounts } from "../accounts/useAccounts";

import type { SettlementPosition, SettlementPositionPayload } from "./api";
import "./SettlementPositionForm.css";

const STANDARD_KEYS = ["MEA", "Wohnflaeche"];

interface SettlementPositionFormProps {
  propertyId: number;
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

  const [accountIds, setAccountIds] = useState<number[]>(initialValues?.account_ids ?? []);
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
  const [validationError, setValidationError] = useState<string | null>(null);

  function toggleAccount(accountId: number, checked: boolean) {
    setAccountIds((prev) => (checked ? [...prev, accountId] : prev.filter((id) => id !== accountId)));
  }

  const isEdit = initialValues !== undefined;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setValidationError(null);
    if (accountIds.length === 0) {
      setValidationError("Bitte mindestens ein Konto auswählen.");
      return;
    }
    onSubmit({
      account_ids: accountIds,
      description: description || null,
      allocation_key_type: keyMode === "standard" ? standardKey : customKey,
      is_apportionable: isApportionable,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="settlement-position-form">
      {accountsLoading && <p className="settlement-position-form__hint">Konten werden geladen…</p>}

      <fieldset className="settlement-position-form__accounts">
        <legend>
          Konten *{" "}
          <span className="settlement-position-form__hint-inline">
            (mehrere möglich – Pooling, z.B. Heizkosten aus mehreren Sachkonten)
          </span>
        </legend>
        {expenseAccounts.length === 0 && reserveAccounts.length === 0 && <p>Keine Konten verfügbar.</p>}
        {expenseAccounts.length > 0 && (
          <div className="settlement-position-form__account-group">
            <p className="settlement-position-form__account-group-label">Aufwandskonten</p>
            {expenseAccounts.map((a) => (
              <label key={a.account_id} className="settlement-position-form__account-row" title={accountLabel(a)}>
                <input
                  type="checkbox"
                  checked={accountIds.includes(a.account_id)}
                  onChange={(e) => toggleAccount(a.account_id, e.target.checked)}
                />
                {accountLabel(a)}
              </label>
            ))}
          </div>
        )}
        {reserveAccounts.length > 0 && (
          <div className="settlement-position-form__account-group">
            <p className="settlement-position-form__account-group-label">Rücklagenkonten</p>
            {reserveAccounts.map((a) => (
              <label key={a.account_id} className="settlement-position-form__account-row" title={accountLabel(a)}>
                <input
                  type="checkbox"
                  checked={accountIds.includes(a.account_id)}
                  onChange={(e) => toggleAccount(a.account_id, e.target.checked)}
                />
                {accountLabel(a)}
              </label>
            ))}
          </div>
        )}
      </fieldset>

      <label>
        Bezeichnung
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="z.B. Heizkosten, Hausmeister"
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
          Der Ist-Betrag wird automatisch als Summe aller ausgewählten Konten im Abrechnungszeitraum
          ermittelt – keine manuelle Eingabe nötig.
        </p>
      )}
      {isEdit && initialValues && (
        <p className="settlement-position-form__hint">
          Aktueller Ist-Betrag: {initialValues.actual_amount.toFixed(2)} € – wird beim Speichern automatisch
          neu aus den Buchungen ermittelt.
        </p>
      )}

      {(validationError || error) && (
        <p className="settlement-position-form__error">{validationError ?? error}</p>
      )}
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