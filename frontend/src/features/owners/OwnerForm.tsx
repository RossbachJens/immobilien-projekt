// frontend/src/features/owners/OwnerForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { Owner, OwnerPayload } from "./api";
import "./OwnerForm.css";

interface OwnerFormProps {
  initialValues?: Owner;
  submitLabel: string;
  onSubmit: (payload: OwnerPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function OwnerForm({ initialValues, submitLabel, onSubmit, onCancel, isSubmitting, error }: OwnerFormProps) {
  const [firstName, setFirstName] = useState(initialValues?.first_name ?? "");
  const [lastName, setLastName] = useState(initialValues?.last_name ?? "");
  const [companyName, setCompanyName] = useState(initialValues?.company_name ?? "");
  const [email, setEmail] = useState(initialValues?.email ?? "");
  const [phone, setPhone] = useState(initialValues?.phone ?? "");
  const [streetAndNumber, setStreetAndNumber] = useState(initialValues?.street_and_number ?? "");
  const [postalCode, setPostalCode] = useState(initialValues?.postal_code ?? "");
  const [city, setCity] = useState(initialValues?.city ?? "");
  const [bankName, setBankName] = useState(initialValues?.bank_name ?? "");
  const [iban, setIban] = useState("");
  const [bic, setBic] = useState("");
  const [clearBankDetails, setClearBankDetails] = useState(false);
  const [sepaReference, setSepaReference] = useState(initialValues?.sepa_mandate_reference ?? "");
  const [sepaGrantedAt, setSepaGrantedAt] = useState(initialValues?.sepa_granted_at ?? "");

  const isEdit = initialValues !== undefined;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();

    const payload: OwnerPayload = {
      first_name: firstName || null,
      last_name: lastName,
      company_name: companyName || null,
      email: email || null,
      phone: phone || null,
      street_and_number: streetAndNumber,
      postal_code: postalCode || null,
      city: city || null,
      bank_name: bankName || null,
      sepa_mandate_reference: sepaReference || null,
      sepa_granted_at: sepaGrantedAt || null,
    };

    // IBAN/BIC nur mitschicken, wenn wirklich geändert werden soll - sonst
    // bleibt die bestehende (verschlüsselte) Bankverbindung unangetastet
    // (PATCH-Semantik, siehe app/routers/owners.py::update_owner).
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
    <form onSubmit={handleSubmit} className="owner-form">
      <label>
        Vorname
        <input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
      </label>
      <label>
        Nachname *
        <input value={lastName} onChange={(e) => setLastName(e.target.value)} required />
      </label>
      <label>
        Firma
        <input value={companyName} onChange={(e) => setCompanyName(e.target.value)} />
      </label>
      <label>
        E-Mail
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label>
        Telefon
        <input value={phone} onChange={(e) => setPhone(e.target.value)} />
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

      <fieldset className="owner-form__bank">
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
          <label className="owner-form__checkbox">
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
        <label>
          SEPA erteilt am
          <input type="date" value={sepaGrantedAt ?? ""} onChange={(e) => setSepaGrantedAt(e.target.value)} />
        </label>
      </fieldset>

      {error && <p className="owner-form__error">{error}</p>}

      <div className="owner-form__actions">
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