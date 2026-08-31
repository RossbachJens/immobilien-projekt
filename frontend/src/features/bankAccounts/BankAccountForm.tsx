// frontend/src/features/bankAccounts/BankAccountForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { accountLabel, accountLabelShort } from "../accounts/format";
import { useAccounts } from "../accounts/useAccounts";

import type { BankAccountPayload, BankAccountPurpose } from "./api";
import "./BankAccountForm.css";

const PURPOSE_LABELS: Record<BankAccountPurpose, string> = {
  GIROKONTO: "Girokonto",
  RUECKLAGENKONTO: "Rücklagenkonto",
  SONSTIGES: "Sonstiges",
};

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

interface BankAccountFormProps {
  propertyId: number;
  submitLabel: string;
  onSubmit: (payload: BankAccountPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function BankAccountForm({
  propertyId,
  submitLabel,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: BankAccountFormProps) {
  // Nur Aktivkonten - Backend erzwingt das ohnehin (Bankkonto muss auf ein
  // Bestandskonto gebucht werden), hier schon in der Auswahl eingeschränkt.
  const { data: accounts, isLoading: accountsLoading } = useAccounts({
    property_id: propertyId,
    type: "AKTIV",
    is_active: true,
  });

  const [accountId, setAccountId] = useState<number | "">("");
  const [purpose, setPurpose] = useState<BankAccountPurpose>("GIROKONTO");
  const [purposeDetail, setPurposeDetail] = useState("");
  const [bankName, setBankName] = useState("");
  const [iban, setIban] = useState("");
  const [bic, setBic] = useState("");
  const [validFrom, setValidFrom] = useState(todayIso());
  const [hasEnd, setHasEnd] = useState(false);
  const [validTo, setValidTo] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (accountId === "") return;
    onSubmit({
      property_id: propertyId,
      account_id: accountId,
      account_purpose: purpose,
      purpose_detail: purposeDetail || null,
      bank_name: bankName,
      iban: iban || null,
      bic: bic || null,
      valid_from: validFrom,
      valid_to: hasEnd && validTo ? validTo : null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="bank-account-form">
      {accountsLoading && <p className="bank-account-form__hint">Konten werden geladen…</p>}
      <label>
        SKR04-Konto *
        <select
          value={accountId}
          onChange={(e) => setAccountId(e.target.value ? Number(e.target.value) : "")}
          required
        >
          <option value="">– Konto wählen –</option>
          {accounts?.map((a) => (
            <option key={a.account_id} value={a.account_id} title={accountLabel(a)}>
              {accountLabelShort(a)}
              {a.property_id != null ? " (eigen)" : ""}
            </option>
          ))}
        </select>
      </label>
      <label>
        Kontozweck *
        <select value={purpose} onChange={(e) => setPurpose(e.target.value as BankAccountPurpose)}>
          {(Object.keys(PURPOSE_LABELS) as BankAccountPurpose[]).map((p) => (
            <option key={p} value={p}>
              {PURPOSE_LABELS[p]}
            </option>
          ))}
        </select>
      </label>
      <label>
        Detail (optional)
        <input
          value={purposeDetail}
          onChange={(e) => setPurposeDetail(e.target.value)}
          placeholder="z.B. Tagesgeld, Kündigungsgeld"
        />
      </label>
      <label>
        Bank *
        <input value={bankName} onChange={(e) => setBankName(e.target.value)} required />
      </label>
      <label>
        IBAN
        <input value={iban} onChange={(e) => setIban(e.target.value)} placeholder="DE..." />
      </label>
      <label>
        BIC
        <input value={bic} onChange={(e) => setBic(e.target.value)} />
      </label>
      <label>
        Gültig ab *
        <input type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} required />
      </label>
      <label className="bank-account-form__checkbox">
        <input type="checkbox" checked={hasEnd} onChange={(e) => setHasEnd(e.target.checked)} />
        Gültigkeitsende bereits bekannt
      </label>
      {hasEnd && (
        <label>
          Gültig bis
          <input type="date" value={validTo} onChange={(e) => setValidTo(e.target.value)} required />
        </label>
      )}

      {error && <p className="bank-account-form__error">{error}</p>}
      <div className="bank-account-form__actions">
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