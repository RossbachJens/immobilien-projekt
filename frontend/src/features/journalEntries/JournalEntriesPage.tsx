// frontend/src/features/journalEntries/JournalEntriesPage.tsx
import { useState } from "react";

import { Card } from "../../components/Card";
import { accountLabel } from "../accounts/format";
import { PropertyAccountsManager } from "../accounts/PropertyAccountsManager";
import { useAccounts } from "../accounts/useAccounts";
import { PaymentForm } from "../payments/PaymentForm";
import type { PaymentPayload } from "../payments/api";
import { useCreatePayment } from "../payments/usePayments";
import { useProperties } from "../properties/useProperties";
import { useUnits } from "../units/useUnits";
import type { JournalEntryPayload } from "./api";
import { JournalEntryForm } from "./JournalEntryForm";
import { useCreateJournalEntry, useJournalEntries, useStornoJournalEntry } from "./useJournalEntries";
import "./JournalEntriesPage.css";

export function JournalEntriesPage() {
  const { data: properties, isLoading: propertiesLoading } = useProperties();
  const [propertyId, setPropertyId] = useState<number | "">("");

  const selectedPropertyId = propertyId === "" ? undefined : propertyId;
  const { data: entries, isLoading: entriesLoading } = useJournalEntries(selectedPropertyId);
  const { data: accounts } = useAccounts({ property_id: selectedPropertyId });
  const { data: units } = useUnits(selectedPropertyId);

  const createMutation = useCreateJournalEntry(selectedPropertyId ?? -1);
  const stornoMutation = useStornoJournalEntry(selectedPropertyId ?? -1);
  const createPaymentMutation = useCreatePayment(selectedPropertyId ?? -1);

  const [mode, setMode] = useState<"idle" | "creating" | "recording-payment">("idle");
  const [expandedEntryId, setExpandedEntryId] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  function unitLabel(unitId: number | null): string {
    if (unitId == null) return "–";
    const unit = units?.find((u) => u.unit_id === unitId);
    return unit ? unit.unit_number : `#${unitId}`;
  }

  function handleCreate(payload: JournalEntryPayload) {
    setFormError(null);
    createMutation.mutate(payload, {
      onSuccess: () => setMode("idle"),
      onError: () =>
        setFormError("Buchung konnte nicht gespeichert werden - Soll und Haben eventuell nicht ausgeglichen."),
    });
  }

  function handlePayment(payload: PaymentPayload) {
    setFormError(null);
    createPaymentMutation.mutate(payload, {
      onSuccess: () => setMode("idle"),
      onError: () => setFormError("Zahlung konnte nicht gebucht werden."),
    });
  }

  function handleStorno(entryId: number) {
    if (!window.confirm("Diesen Beleg stornieren? Es wird eine Gegenbuchung erzeugt.")) return;
    stornoMutation.mutate(entryId, {
      onError: () => window.alert("Storno fehlgeschlagen - Beleg wurde eventuell bereits storniert."),
    });
  }

  const reversedEntryIds = new Set(
    entries?.filter((e) => e.reversed_entry_id != null).map((e) => e.reversed_entry_id) ?? [],
  );

  return (
    <div className="journal-entries-page">
      <Card>
        <h1>Buchhaltung</h1>
        {propertiesLoading && <p>Lädt Liegenschaften…</p>}
        <label className="journal-entries-page__property-select">
          Liegenschaft
          <select
            value={propertyId}
            onChange={(e) => {
              setPropertyId(e.target.value ? Number(e.target.value) : "");
              setMode("idle");
              setExpandedEntryId(null);
            }}
          >
            <option value="">– bitte wählen –</option>
            {properties?.map((p) => (
              <option key={p.property_id} value={p.property_id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
      </Card>

      {selectedPropertyId !== undefined && (
        <>
          <Card>
            <PropertyAccountsManager propertyId={selectedPropertyId} />
          </Card>

          <Card>
            <div className="journal-entries-page__header">
              <h2>Buchungen</h2>
              {mode === "idle" && (
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button type="button" onClick={() => setMode("creating")}>
                    Neue Buchung
                  </button>
                  <button type="button" onClick={() => setMode("recording-payment")}>
                    Zahlung erfassen
                  </button>
                </div>
              )}
            </div>

            {entriesLoading && <p>Lädt…</p>}
            {!entriesLoading && entries?.length === 0 && <p>Noch keine Buchungen erfasst.</p>}

            <ul className="journal-entries-page__list">
              {entries?.map((entry) => {
                const isStorno = entry.reversed_entry_id != null;
                const isReversed = reversedEntryIds.has(entry.entry_id);
                const total = entry.lines
                  .filter((l) => l.direction === "DEBIT")
                  .reduce((sum, l) => sum + l.amount, 0);

                return (
                  <li key={entry.entry_id} className="journal-entries-page__entry">
                    <div className="journal-entries-page__entry-row">
                      <div>
                        <strong>{entry.entry_date}</strong> · {entry.description}
                        {entry.document_reference && <> · Beleg-Nr. {entry.document_reference}</>}
                        {" · "}
                        {total.toFixed(2)} €
                        {isStorno && (
                          <span className="journal-entries-page__badge">
                            Storno zu #{entry.reversed_entry_id}
                          </span>
                        )}
                        {isReversed && (
                          <span className="journal-entries-page__badge journal-entries-page__badge--reversed">
                            Storniert
                          </span>
                        )}
                      </div>
                      <div className="journal-entries-page__entry-actions">
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedEntryId(expandedEntryId === entry.entry_id ? null : entry.entry_id)
                          }
                        >
                          {expandedEntryId === entry.entry_id ? "Zeilen ausblenden" : "Zeilen anzeigen"}
                        </button>
                        {!isStorno && !isReversed && (
                          <button type="button" onClick={() => handleStorno(entry.entry_id)}>
                            Stornieren
                          </button>
                        )}
                      </div>
                    </div>

                    {expandedEntryId === entry.entry_id && (
                      <table className="journal-entries-page__lines-table">
                        <thead>
                          <tr>
                            <th>Konto</th>
                            <th>Einheit</th>
                            <th>Soll</th>
                            <th>Haben</th>
                          </tr>
                        </thead>
                        <tbody>
                          {entry.lines.map((line) => {
                            const account = accounts?.find((a) => a.account_id === line.account_id) ?? {
                              account_number: "",
                              account_name: `Konto #${line.account_id}`,
                            };
                            return (
                              <tr key={line.line_id}>
                                <td title={accountLabel(account)}>{accountLabel(account)}</td>
                                <td>{unitLabel(line.unit_id)}</td>
                                <td>{line.direction === "DEBIT" ? `${line.amount.toFixed(2)} €` : ""}</td>
                                <td>{line.direction === "CREDIT" ? `${line.amount.toFixed(2)} €` : ""}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    )}
                  </li>
                );
              })}
            </ul>
          </Card>
        </>
      )}

      {mode === "creating" && selectedPropertyId !== undefined && (
        <Card>
          <h2>Neue Buchung erfassen</h2>
          <JournalEntryForm
            propertyId={selectedPropertyId}
            onSubmit={handleCreate}
            onCancel={() => setMode("idle")}
            isSubmitting={createMutation.isPending}
            error={formError}
          />
        </Card>
      )}

      {mode === "recording-payment" && selectedPropertyId !== undefined && (
        <Card>
          <h2>Zahlungseingang erfassen</h2>
          <PaymentForm
            units={units ?? []}
            onSubmit={handlePayment}
            onCancel={() => setMode("idle")}
            isSubmitting={createPaymentMutation.isPending}
            error={formError}
          />
        </Card>
      )}
    </div>
  );
}