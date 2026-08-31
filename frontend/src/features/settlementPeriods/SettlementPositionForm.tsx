// frontend/src/features/settlementPeriods/SettlementPositionForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { AllocationKeyField } from "../../components/AllocationKeyField";
import { accountLabel, accountLabelShort } from "../accounts/format";
import { useAccounts } from "../accounts/useAccounts";

import type { SettlementPositionPayload } from "./api";
import "./SettlementPositionForm.css";

interface SettlementPositionFormProps {
  propertyId: number;
  onSubmit: (payload: SettlementPositionPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function SettlementPositionForm({
  propertyId,
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

  const [accountId, setAccountId] = useState<number | "">("");
  const [description, setDescription] = useState("");
  const [isApportionable, setIsApportionable] = useState(true);
  const [keyMode, setKeyMode] = useState<"standard" | "custom">("standard");
  const [standardKey, setStandardKey] = useState("MEA");
  const [customKey, setCustomKey] = useState("");

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

      <p className="settlement-position-form__hint">
        Der Ist-Betrag wird automatisch aus den Buchungen im Abrechnungszeitraum ermittelt - keine manuelle
        Eingabe nötig.
      </p>

      {error && <p className="settlement-position-form__error">{error}</p>}
      <div className="settlement-position-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird ermittelt…" : "Position anlegen & verteilen"}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}