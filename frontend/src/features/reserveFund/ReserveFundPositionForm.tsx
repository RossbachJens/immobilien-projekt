// frontend/src/features/reserveFund/ReserveFundPositionForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { accountLabel } from "../accounts/format";
import { useAccounts } from "../accounts/useAccounts";

import type { MovementType, ReserveFundPosition, ReserveFundPositionPayload } from "./api";
import "./ReserveFundPositionForm.css";

const MOVEMENT_TYPES: { value: MovementType; label: string }[] = [
  { value: "Zufuehrung", label: "Zuführung" },
  { value: "Entnahme", label: "Liquiditätsentnahme" },
  { value: "Zinsen", label: "Zinsen" },
  { value: "Kapitalertragsteuer", label: "Kapitalertragsteuer" },
  { value: "Solidaritaetszuschlag", label: "Solidaritätszuschlag" },
  { value: "Sonstiges", label: "Sonstiges" },
];

interface ReserveFundPositionFormProps {
  propertyId: number;
  initialValues?: ReserveFundPosition;
  submitLabel?: string;
  onSubmit: (payload: ReserveFundPositionPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function ReserveFundPositionForm({
  propertyId,
  initialValues,
  submitLabel,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: ReserveFundPositionFormProps) {
  const { data: accounts, isLoading: accountsLoading } = useAccounts({
    property_id: propertyId,
    is_active: true,
  });
  // Gegenkonten dürfen selbst keine Rücklagenkonten sein (siehe Backend-
  // Validierung in app/routers/reserve_fund.py::_validate_counter_accounts).
  const counterAccounts = (accounts ?? []).filter((a) => !a.is_reserve_account);

  const [movementType, setMovementType] = useState<MovementType>(
    initialValues?.movement_type ?? "Zufuehrung",
  );
  const [description, setDescription] = useState(initialValues?.description ?? "");
  const [allocationKeyType, setAllocationKeyType] = useState(
    initialValues?.allocation_key_type ?? "MEA",
  );
  const [accountIds, setAccountIds] = useState<number[]>(initialValues?.account_ids ?? []);
  const [validationError, setValidationError] = useState<string | null>(null);

  const isEdit = initialValues !== undefined;

  function toggleAccount(accountId: number, checked: boolean) {
    setAccountIds((prev) => (checked ? [...prev, accountId] : prev.filter((id) => id !== accountId)));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setValidationError(null);
    if (accountIds.length === 0) {
      setValidationError("Bitte mindestens ein Gegenkonto auswählen.");
      return;
    }
    onSubmit({
      movement_type: movementType,
      description: description || null,
      allocation_key_type: allocationKeyType,
      account_ids: accountIds,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="reserve-fund-position-form">
      <label>
        Bewegungsart *
        <select value={movementType} onChange={(e) => setMovementType(e.target.value as MovementType)}>
          {MOVEMENT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </label>

      <label>
        Bezeichnung
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="optional, z.B. Kontoführende Bank"
        />
      </label>

      <label>
        Verteilerschlüssel
        <select value={allocationKeyType} onChange={(e) => setAllocationKeyType(e.target.value)}>
          <option value="MEA">Miteigentumsanteile (MEA)</option>
          <option value="Wohnflaeche">Wohnfläche</option>
        </select>
      </label>

      <fieldset className="reserve-fund-position-form__accounts">
        <legend>
          Gegenkonto(en) *{" "}
          <span className="reserve-fund-position-form__hint-inline">
            (die Buchungsgegenseite auf dem Rücklagenkonto - unterscheidet z.B. eine Zinsgutschrift von
            einer Zuführung)
          </span>
        </legend>
        {accountsLoading && <p>Konten werden geladen…</p>}
        {!accountsLoading && counterAccounts.length === 0 && <p>Keine Konten verfügbar.</p>}
        {counterAccounts.map((a) => (
          <label
            key={a.account_id}
            className="reserve-fund-position-form__account-row"
            title={accountLabel(a)}
          >
            <input
              type="checkbox"
              checked={accountIds.includes(a.account_id)}
              onChange={(e) => toggleAccount(a.account_id, e.target.checked)}
            />
            {accountLabel(a)}
          </label>
        ))}
      </fieldset>

      {!isEdit && (
        <p className="reserve-fund-position-form__hint">
          Der Betrag wird automatisch als Saldo der Rücklagenkonten gegen die ausgewählten Gegenkonten im
          Abrechnungszeitraum ermittelt.
        </p>
      )}
      {isEdit && initialValues && (
        <p className="reserve-fund-position-form__hint">
          Aktueller Betrag: {initialValues.actual_amount.toFixed(2)} € – wird beim Speichern automatisch
          neu ermittelt.
        </p>
      )}

      {(validationError || error) && (
        <p className="reserve-fund-position-form__error">{validationError ?? error}</p>
      )}
      <div className="reserve-fund-position-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird ermittelt…" : (submitLabel ?? "Position anlegen")}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}