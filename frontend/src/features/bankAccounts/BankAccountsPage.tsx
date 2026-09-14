// frontend/src/features/bankAccounts/BankAccountsPage.tsx
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { Card } from "../../components/Card";
import { useCurrentProperty } from "../../context/PropertyContext";
import { accountLabel } from "../accounts/format";
import { useAccounts } from "../accounts/useAccounts";
import type { BankAccountPayload, BankAccountPurpose } from "./api";
import { BankAccountForm } from "./BankAccountForm";
import { useBankAccounts, useCreateBankAccount, useUpdateBankAccount } from "./useBankAccounts";
import "./BankAccountsPage.css";

const PURPOSE_LABELS: Record<BankAccountPurpose, string> = {
  GIROKONTO: "Girokonto",
  RUECKLAGENKONTO: "Rücklagenkonto",
  SONSTIGES: "Sonstiges",
};

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function BankAccountsPage() {
  const { propertyId, property, properties, isLoading: propertiesLoading } = useCurrentProperty();

  const { data: bankAccounts, isLoading, isError, error } = useBankAccounts(propertyId ?? undefined);
  const { data: accounts } = useAccounts({ property_id: propertyId ?? undefined });

  const createMutation = useCreateBankAccount(propertyId ?? -1);
  const updateMutation = useUpdateBankAccount(propertyId ?? -1);

  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [endingId, setEndingId] = useState<number | null>(null);
  const [endDate, setEndDate] = useState(todayIso());
  const [endError, setEndError] = useState<string | null>(null);

  useEffect(() => {
    setCreating(false);
    setFormError(null);
    setEndingId(null);
  }, [propertyId]);

  const isForbidden =
    isError &&
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    (error as { response?: { status?: number } }).response?.status === 403;

  function accountLabelFor(accountId: number): string {
    const account = accounts?.find((a) => a.account_id === accountId);
    return account ? accountLabel(account) : `Konto #${accountId}`;
  }

  function handleCreate(payload: BankAccountPayload) {
    setFormError(null);
    createMutation.mutate(payload, {
      onSuccess: () => setCreating(false),
      onError: () =>
        setFormError(
          "Bankkonto konnte nicht angelegt werden - für dieses SKR04-Konto existiert eventuell " +
            "bereits ein überlappender Gültigkeitszeitraum.",
        ),
    });
  }

  function startEnding(bankAccountId: number, validFrom: string) {
    setEndingId(bankAccountId);
    setEndDate(todayIso() > validFrom ? todayIso() : validFrom);
    setEndError(null);
  }

  function confirmEnding(event: FormEvent) {
    event.preventDefault();
    if (endingId === null) return;
    setEndError(null);
    updateMutation.mutate(
      { bankAccountId: endingId, payload: { valid_to: endDate } },
      {
        onSuccess: () => setEndingId(null),
        onError: () => setEndError("Gültigkeitsende konnte nicht gespeichert werden."),
      },
    );
  }

  const current = bankAccounts?.filter((b) => b.valid_to === null) ?? [];
  const past = bankAccounts?.filter((b) => b.valid_to !== null) ?? [];

  if (propertiesLoading) {
    return (
      <div className="bank-accounts-page">
        <Card>
          <p>Lädt Liegenschaften…</p>
        </Card>
      </div>
    );
  }

  if (propertyId == null || properties.length === 0) {
    return (
      <div className="bank-accounts-page">
        <Card>
          <h1>Bankkonten</h1>
          <p>Bitte zuerst links in der Sidebar eine Liegenschaft auswählen.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="bank-accounts-page">
      <Card>
        <h1>Bankkonten – {property?.name}</h1>
      </Card>

      {isForbidden && (
        <Card>
          <p>Kein Zugriff auf die Bankkonten mit diesem Konto.</p>
        </Card>
      )}

      {!isForbidden && (
        <Card>
          <div className="bank-accounts-page__header">
            <h2>Aktuelle Bankkonten</h2>
            {!creating && (
              <button type="button" onClick={() => setCreating(true)}>
                Neues Bankkonto
              </button>
            )}
          </div>

          {isLoading && <p>Lädt…</p>}
          {!isLoading && current.length === 0 && <p>Noch keine aktuellen Bankkonten erfasst.</p>}

          <ul className="bank-accounts-page__list">
            {current.map((b) => (
              <li key={b.bank_account_id} className="bank-accounts-page__entry">
                <div className="bank-accounts-page__entry-row">
                  <div>
                    <strong>{PURPOSE_LABELS[b.account_purpose]}</strong>
                    {b.purpose_detail && <> ({b.purpose_detail})</>} · {b.bank_name}
                    {b.iban_last4 && <> · …{b.iban_last4}</>} · {accountLabelFor(b.account_id)}
                    <div className="bank-accounts-page__validity">seit {b.valid_from}</div>
                  </div>
                  <button type="button" onClick={() => startEnding(b.bank_account_id, b.valid_from)}>
                    Beenden
                  </button>
                </div>

                {endingId === b.bank_account_id && (
                  <form onSubmit={confirmEnding} className="bank-accounts-page__end-form">
                    <label>
                      Gültig bis (letzter Tag)
                      <input
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        min={b.valid_from}
                        required
                      />
                    </label>
                    {endError && <p className="bank-accounts-page__error">{endError}</p>}
                    <div className="bank-accounts-page__end-form-actions">
                      <button type="submit" disabled={updateMutation.isPending}>
                        {updateMutation.isPending ? "Wird gespeichert…" : "Bestätigen"}
                      </button>
                      <button type="button" onClick={() => setEndingId(null)}>
                        Abbrechen
                      </button>
                    </div>
                  </form>
                )}
              </li>
            ))}
          </ul>

          {past.length > 0 && (
            <details className="bank-accounts-page__history">
              <summary>Historie ({past.length})</summary>
              <ul className="bank-accounts-page__list">
                {past.map((b) => (
                  <li key={b.bank_account_id} className="bank-accounts-page__entry">
                    <strong>{PURPOSE_LABELS[b.account_purpose]}</strong>
                    {b.purpose_detail && <> ({b.purpose_detail})</>} · {b.bank_name}
                    {b.iban_last4 && <> · …{b.iban_last4}</>} · {accountLabelFor(b.account_id)}
                    <div className="bank-accounts-page__validity">
                      {b.valid_from} – {b.valid_to}
                    </div>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </Card>
      )}

      {creating && (
        <Card>
          <h2>Neues Bankkonto anlegen</h2>
          <BankAccountForm
            propertyId={propertyId}
            submitLabel="Anlegen"
            onSubmit={handleCreate}
            onCancel={() => setCreating(false)}
            isSubmitting={createMutation.isPending}
            error={formError}
          />
        </Card>
      )}
    </div>
  );
}