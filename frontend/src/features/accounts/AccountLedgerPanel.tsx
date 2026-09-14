// frontend/src/features/accounts/AccountLedgerPanel.tsx
import { useEffect, useState } from "react";

import { accountLabel, accountLabelShort } from "./format";
import { useAccountLedger, useAccounts } from "./useAccounts";
import "./AccountLedgerPanel.css";

interface AccountLedgerPanelProps {
  propertyId: number;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function firstOfYearIso(): string {
  return `${new Date().getFullYear()}-01-01`;
}

function formatEur(value: number): string {
  return `${value.toFixed(2)} €`;
}

export function AccountLedgerPanel({ propertyId }: AccountLedgerPanelProps) {
  const { data: accounts, isLoading: accountsLoading } = useAccounts({ property_id: propertyId });

  const [accountId, setAccountId] = useState<number | "">("");
  const [dateFrom, setDateFrom] = useState(firstOfYearIso());
  const [dateTo, setDateTo] = useState(todayIso());
  const [useDateFilter, setUseDateFilter] = useState(true);

  // Bei Wechsel der Liegenschaft (zentrale Auswahl in der Sidebar) gehört
  // das bisher gewählte Konto eventuell nicht mehr dazu - Auswahl zurücksetzen
  // statt eine Fehlermeldung für ein "verschwundenes" Konto zu zeigen.
  useEffect(() => {
    setAccountId("");
  }, [propertyId]);

  const {
    data: ledger,
    isLoading: ledgerLoading,
    isError,
  } = useAccountLedger(
    accountId !== ""
      ? {
          property_id: propertyId,
          account_id: accountId,
          date_from: useDateFilter ? dateFrom : undefined,
          date_to: useDateFilter ? dateTo : undefined,
        }
      : undefined,
  );

  const globalAccounts = (accounts ?? []).filter((a) => a.property_id == null);
  const ownAccounts = (accounts ?? []).filter((a) => a.property_id === propertyId);

  return (
    <div className="account-ledger-panel">
      <div className="account-ledger-panel__filters">
        <label>
          Konto
          <select value={accountId} onChange={(e) => setAccountId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">– Konto wählen –</option>
            {globalAccounts.length > 0 && (
              <optgroup label="Globaler Kontenrahmen">
                {globalAccounts.map((a) => (
                  <option key={a.account_id} value={a.account_id} title={accountLabel(a)}>
                    {accountLabelShort(a)}
                  </option>
                ))}
              </optgroup>
            )}
            {ownAccounts.length > 0 && (
              <optgroup label="Eigene Konten">
                {ownAccounts.map((a) => (
                  <option key={a.account_id} value={a.account_id} title={accountLabel(a)}>
                    {accountLabelShort(a)}
                  </option>
                ))}
              </optgroup>
            )}
          </select>
        </label>

        <label className="account-ledger-panel__checkbox">
          <input type="checkbox" checked={useDateFilter} onChange={(e) => setUseDateFilter(e.target.checked)} />
          Zeitraum eingrenzen
        </label>

        {useDateFilter && (
          <>
            <label>
              Von
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </label>
            <label>
              Bis
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </label>
          </>
        )}
      </div>

      {accountsLoading && <p>Konten werden geladen…</p>}
      {accountId === "" && !accountsLoading && (
        <p className="account-ledger-panel__hint">Bitte ein Konto wählen.</p>
      )}
      {ledgerLoading && <p>Kontenblatt wird geladen…</p>}
      {isError && <p className="account-ledger-panel__error">Kontenblatt konnte nicht geladen werden.</p>}

      {ledger && (
        <table className="account-ledger-panel__table">
          <thead>
            <tr>
              <th>Datum</th>
              <th>Beleg</th>
              <th>Text</th>
              <th>Soll</th>
              <th>Haben</th>
              <th>Saldo</th>
            </tr>
          </thead>
          <tbody>
            {ledger.date_from && (
              <tr className="account-ledger-panel__opening-row">
                <td>{ledger.date_from}</td>
                <td colSpan={3}>Saldovortrag</td>
                <td colSpan={2}>{formatEur(ledger.opening_balance)}</td>
              </tr>
            )}
            {ledger.lines.map((line) => (
              <tr key={line.line_id}>
                <td>{line.entry_date}</td>
                <td>{line.document_reference ?? "–"}</td>
                <td className="account-ledger-panel__description" title={line.description}>
                  {line.description}
                </td>
                <td>{line.direction === "DEBIT" ? formatEur(line.amount) : ""}</td>
                <td>{line.direction === "CREDIT" ? formatEur(line.amount) : ""}</td>
                <td>{formatEur(line.balance)}</td>
              </tr>
            ))}
            {ledger.lines.length === 0 && (
              <tr>
                <td colSpan={6}>Keine Buchungen im gewählten Zeitraum.</td>
              </tr>
            )}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={5}>Endsaldo</td>
              <td>{formatEur(ledger.closing_balance)}</td>
            </tr>
          </tfoot>
        </table>
      )}
    </div>
  );
}