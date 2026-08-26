// frontend/src/features/tenants/TenantForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { Tenant, TenantPayload } from "./api";
import "./TenantForm.css";

interface TenantFormProps {
  initialValues?: Tenant;
  submitLabel: string;
  onSubmit: (payload: TenantPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function TenantForm({ initialValues, submitLabel, onSubmit, onCancel, isSubmitting, error }: TenantFormProps) {
  const [firstName, setFirstName] = useState(initialValues?.first_name ?? "");
  const [lastName, setLastName] = useState(initialValues?.last_name ?? "");
  const [email, setEmail] = useState(initialValues?.email ?? "");
  const [streetAndNumber, setStreetAndNumber] = useState(initialValues?.street_and_number ?? "");
  const [postalCode, setPostalCode] = useState(initialValues?.postal_code ?? "");
  const [city, setCity] = useState(initialValues?.city ?? "");
  const [bankName, setBankName] = useState(initialValues?.bank_name ?? "");
  const [iban, setIban] = useState("");
  const [bic, setBic] = useState("");
  const [clearBankDetails, setClearBankDetails] = useState(false);
  const [sepaReference, setSepaReference] = useState(initialValues?.sepa_mandate_reference ?? "");

  const isEdit = initialValues !== undefined;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();

    const payload: TenantPayload = {
      first_name: firstName,
      last_name: lastName,
      email: email || null,
      street_and_number: streetAndNumber,
      postal_code: postalCode || null,
      city: city || null,
      bank_name: bankName || null,
      sepa_mandate_reference: sepaReference || null,
    };

    if (clearBankDetails) {
      payload.iban = null;
      payload.bic = null;
    } else {
      if (iban) payload.iban = iban;
      if (bic) payload.bic = bic;
    }

    onSubmit(payload);
  }

  return (
    <form onSubmit={handleSubmit} className="tenant-form">
      <label>
        Vorname *
        <input value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
      </label>
      <label>
        Nachname *
        <input value={lastName} onChange={(e) => setLastName(e.target.value)} required />
      </label>
      <label>
        E-Mail
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label>
        Straße und Hausnummer *
        <input value={streetAndNumber} onChange={(e) => setStreetAndNumber(e.target.value)} required />
      </label>
      <label>
        PLZ
        <input value={postalCode} onChange={(e) => setPostalCode(e.target.value)} />
      </label>
      <label>
        Stadt
        <input value={city} onChange={(e) => setCity(e.target.value)} />
      </label>

      <fieldset className="tenant-form__bank">
        <legend>
          Bankverbindung {isEdit && initialValues?.iban_last4 && `(hinterlegt: …${initialValues.iban_last4})`}
        </legend>
        <label>
          Bank
          <input value={bankName} onChange={(e) => setBankName(e.target.value)} />
        </label>
        <label>
          {isEdit ? "Neue IBAN" : "IBAN"}
          <input
            value={iban}
            onChange={(e) => setIban(e.target.value)}
            placeholder={isEdit ? "leer lassen = unverändert" : "DE..."}
            disabled={clearBankDetails}
          />
        </label>
        <label>
          {isEdit ? "Neue BIC" : "BIC"}
          <input
            value={bic}
            onChange={(e) => setBic(e.target.value)}
            placeholder={isEdit ? "leer lassen = unverändert" : ""}
            disabled={clearBankDetails}
          />
        </label>
        {isEdit && (
          <label className="tenant-form__checkbox">
            <input
              type="checkbox"
              checked={clearBankDetails}
              onChange={(e) => setClearBankDetails(e.target.checked)}
            />
            Bankverbindung entfernen
          </label>
        )}
        <label>
          SEPA-Mandatsreferenz
          <input value={sepaReference} onChange={(e) => setSepaReference(e.target.value)} />
        </label>
      </fieldset>

      {error && <p className="tenant-form__error">{error}</p>}

      <div className="tenant-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird gespeichert…" : submitLabel}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}