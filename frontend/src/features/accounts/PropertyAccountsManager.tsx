// frontend/src/features/accounts/PropertyAccountsManager.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { AccountType } from "./api";
import { useAccounts, useCreateAccount, useUpdateAccount } from "./useAccounts";
// frontend/src/features/accounts/PropertyAccountsManager.tsx — Import ergänzen
import { accountLabel } from "./format";
import "./PropertyAccountsManager.css";

const ACCOUNT_TYPES: { value: AccountType; label: string }[] = [
  { value: "AKTIV", label: "Aktiv (Bestand)" },
  { value: "PASSIV", label: "Passiv (Bestand)" },
  { value: "ERTRAG", label: "Ertrag" },
  { value: "AUFWAND", label: "Aufwand" },
];

interface PropertyAccountsManagerProps {
  propertyId: number;
}

export function PropertyAccountsManager({ propertyId }: PropertyAccountsManagerProps) {
  const { data: accounts, isLoading } = useAccounts({ property_id: propertyId });
  const createMutation = useCreateAccount();
  const updateMutation = useUpdateAccount();

  const [showForm, setShowForm] = useState(false);
  const [accountNumber, setAccountNumber] = useState("");
  const [accountName, setAccountName] = useState("");
  const [type, setType] = useState<AccountType>("AUFWAND");
  const [error, setError] = useState<string | null>(null);
  const [isReserveAccount, setIsReserveAccount] = useState(false);
  // Die Abfrage liefert global + eigene zusammen (für das Buchungsformular
  // gedacht) - hier interessieren nur die eigenen Konten dieser Liegenschaft.
  const ownAccounts = (accounts ?? []).filter((a) => a.property_id === propertyId);

  function handleCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    createMutation.mutate(
      { property_id: propertyId, account_number: accountNumber, account_name: accountName, type },
      {
        onSuccess: () => {
          setShowForm(false);
          setAccountNumber("");
          setAccountName("");
          setType("AUFWAND");
        },
        onError: () =>
          setError("Konto konnte nicht angelegt werden - Nummer eventuell schon vergeben."),
      },
    );
  }

  function toggleActive(accountId: number, currentlyActive: boolean) {
    updateMutation.mutate({ accountId, payload: { is_active: !currentlyActive } });
  }

    function handleCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    createMutation.mutate(
      {
        property_id: propertyId,
        account_number: accountNumber,
        account_name: accountName,
        type,
        is_reserve_account: isReserveAccount,
      },
      {
        onSuccess: () => {
          setShowForm(false);
          setAccountNumber("");
          setAccountName("");
          setType("AUFWAND");
          setIsReserveAccount(false);
        },
        onError: () =>
          setError("Konto konnte nicht angelegt werden - Nummer eventuell schon vergeben."),
      },
    );
  }

  return (
    <div className="property-accounts-manager">
      <div className="property-accounts-manager__header">
        <h3>Eigene Konten dieser Liegenschaft</h3>
        {!showForm && (
          <button type="button" onClick={() => setShowForm(true)}>
            Neues Konto
          </button>
        )}
      </div>

      {isLoading && <p>Lädt…</p>}
      {!isLoading && ownAccounts.length === 0 && (
        <p className="property-accounts-manager__empty">
          Noch keine eigenen Konten – es steht der globale SKR04-Rahmen zur Verfügung.
        </p>
      )}

      {ownAccounts.length > 0 && (
        <ul className="property-accounts-manager__list">
          {ownAccounts.map((a) => (
              <li
                key={a.account_id}
                className={a.is_active ? undefined : "property-accounts-manager__row--inactive"}
              >
              <span className="property-accounts-manager__account-name" title={accountLabel(a)}>
                {accountLabel(a)} ({a.type})
              </span>
              <button type="button" onClick={() => toggleActive(a.account_id, a.is_active)}>
                {a.is_active ? "Deaktivieren" : "Aktivieren"}
              </button>
            </li>
          ))}
        </ul>
      )}

      {showForm && (
        <form onSubmit={handleCreate} className="property-accounts-manager__form">
          {/* im <form>, vor den form-actions ergänzen */}
          <label className="property-accounts-manager__checkbox">
            <input type="checkbox" checked={isReserveAccount} onChange={(e) => setIsReserveAccount(e.target.checked)} />
            Rücklagenkonto (z.B. Instandhaltungsrücklage)
          </label>
          <label>
            Kontonummer (4-stellig, SKR04) *
            <input
              value={accountNumber}
              onChange={(e) => setAccountNumber(e.target.value)}
              pattern="[0-8][0-9]{3}"
              maxLength={4}
              placeholder="z.B. 4420"
              required
            />
          </label>
          <label>
            Bezeichnung *
            <input value={accountName} onChange={(e) => setAccountName(e.target.value)} required />
          </label>
          <label>
            Kontoart
            <select value={type} onChange={(e) => setType(e.target.value as AccountType)}>
              {ACCOUNT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          {error && <p className="property-accounts-manager__error">{error}</p>}
          <div className="property-accounts-manager__form-actions">
            <button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Wird gespeichert…" : "Anlegen"}
            </button>
            <button type="button" onClick={() => setShowForm(false)}>
              Abbrechen
            </button>
          </div>
        </form>
      )}
    </div>
  );
}