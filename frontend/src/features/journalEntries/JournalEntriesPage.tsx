// frontend/src/features/journalEntries/JournalEntriesPage.tsx
import { useState } from "react";

import { Card } from "../../components/Card";
import { useCurrentProperty } from "../../context/PropertyContext";
import { AccountLedgerPanel } from "../accounts/AccountLedgerPanel";
import { accountLabel } from "../accounts/format";
import { PropertyAccountsManager } from "../accounts/PropertyAccountsManager";
import { useAccounts } from "../accounts/useAccounts";
import { useUploadDocument } from "../documents/useDocuments";
import type { PaymentPayload } from "../payments/api";
import { PaymentForm } from "../payments/PaymentForm";
import { useCreatePayment } from "../payments/usePayments";
import { useUnits } from "../units/useUnits";
import type { JournalEntryPayload } from "./api";
import { JournalEntryDocuments } from "./JournalEntryDocuments";
import { JournalEntryForm, type JournalEntryBelegDraft } from "./JournalEntryForm";
import {
  useCreateJournalEntry,
  useJournalEntries,
  useStornoJournalEntry,
  useUpdateJournalEntry,
} from "./useJournalEntries";
import "./JournalEntriesPage.css";

type Tab = "buchungen" | "kontenblatt";

export function JournalEntriesPage() {
  const { propertyId, property, properties, isLoading: propertiesLoading } = useCurrentProperty();

  const { data: entries, isLoading: entriesLoading } = useJournalEntries(propertyId ?? undefined);
  const { data: accounts } = useAccounts({ property_id: propertyId ?? undefined });
  const { data: units } = useUnits(propertyId ?? undefined);

  const createMutation = useCreateJournalEntry(propertyId ?? -1);
  const updateMutation = useUpdateJournalEntry(propertyId ?? -1);
  const stornoMutation = useStornoJournalEntry(propertyId ?? -1);
  const createPaymentMutation = useCreatePayment(propertyId ?? -1);
  const uploadDocumentMutation = useUploadDocument();

  const [tab, setTab] = useState<Tab>("buchungen");
  // number = entry_id, das gerade bearbeitet wird.
  const [mode, setMode] = useState<"idle" | "creating" | "recording-payment" | number>("idle");
  const [expandedEntryId, setExpandedEntryId] = useState<number | null>(null);
  const [expandedDocumentsEntryId, setExpandedDocumentsEntryId] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  function unitLabel(unitId: number | null): string {
    if (unitId == null) return "–";
    const unit = units?.find((u) => u.unit_id === unitId);
    return unit ? unit.unit_number : `#${unitId}`;
  }

  function handleCreate(payload: JournalEntryPayload, beleg?: JournalEntryBelegDraft) {
    if (propertyId == null) return;
    setFormError(null);
    createMutation.mutate(payload, {
      onSuccess: (entry) => {
        setMode("idle");
        // Beleg-Upload läuft bewusst NACH dem Buchen als zweiter Request -
        // ein Dokument kann erst verknüpft werden, wenn die Buchung (und
        // damit entry_id) existiert. Schlägt nur dieser zweite Schritt fehl,
        // bleibt die Buchung trotzdem bestehen (kein Rollback) - deshalb ein
        // eigener, expliziter Fehlerhinweis statt formError, damit klar
        // wird, dass die Buchung sehr wohl angelegt wurde.
        if (beleg) {
          uploadDocumentMutation.mutate(
            {
              property_id: propertyId,
              category: beleg.category,
              title: beleg.title,
              visibility: "intern",
              journal_entry_id: entry.entry_id,
              file: beleg.file,
            },
            {
              onError: () =>
                window.alert(
                  "Buchung wurde angelegt, aber der Beleg konnte nicht hochgeladen werden - bitte nachträglich über „Belege\" bei der Buchung ergänzen.",
                ),
            },
          );
        }
      },
      onError: () =>
        setFormError("Buchung konnte nicht gespeichert werden - Soll und Haben eventuell nicht ausgeglichen."),
    });
  }

  function handleUpdate(entryId: number, payload: JournalEntryPayload) {
    setFormError(null);
    // property_id wird beim Korrigieren nicht mitgeschickt - die
    // Liegenschaft einer Buchung ändert sich nie (siehe
    // JournalEntryUpdatePayload/app/schemas/journal_entries.py::JournalEntryUpdate).
    const { property_id: _propertyId, ...updatePayload } = payload;
    updateMutation.mutate(
      { entryId, payload: updatePayload },
      {
        onSuccess: () => setMode("idle"),
        onError: () =>
          setFormError(
            "Buchung konnte nicht aktualisiert werden - eventuell ist die zugehörige " +
              "Nebenkostenabrechnung für diesen Zeitraum bereits abgeschlossen, die Buchung wurde " +
              "bereits storniert, oder Soll/Haben sind nicht ausgeglichen.",
          ),
      },
    );
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

  const editingEntry = typeof mode === "number" ? entries?.find((e) => e.entry_id === mode) ?? null : null;

  if (propertiesLoading) {
    return (
      <div className="journal-entries-page">
        <Card>
          <p>Lädt Liegenschaften…</p>
        </Card>
      </div>
    );
  }

  if (propertyId == null || properties.length === 0) {
    return (
      <div className="journal-entries-page">
        <Card>
          <h1>Buchhaltung</h1>
          <p>Bitte zuerst links in der Sidebar eine Liegenschaft auswählen.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="journal-entries-page">
      <Card>
        <h1>Buchhaltung – {property?.name}</h1>
        <div className="journal-entries-page__tabs">
          <button
            type="button"
            className={
              "journal-entries-page__tab" + (tab === "buchungen" ? " journal-entries-page__tab--active" : "")
            }
            onClick={() => setTab("buchungen")}
          >
            Buchungen
          </button>
          <button
            type="button"
            className={
              "journal-entries-page__tab" + (tab === "kontenblatt" ? " journal-entries-page__tab--active" : "")
            }
            onClick={() => setTab("kontenblatt")}
          >
            Kontenblatt
          </button>
        </div>
      </Card>

      {tab === "buchungen" && (
        <>
          <Card>
            <PropertyAccountsManager propertyId={propertyId} />
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
                // Nur "reine" liegenschaftsbezogene Buchungen sind über diese
                // Funktion korrigierbar - automatisiert erzeugte Zeilen mit
                // Einheiten-/Vertragsbezug (Zahlungseingänge, Mietsollstellung)
                // würden ihre unit_id/lease_id verlieren, da das Formular
                // diese Felder gar nicht erfasst. Serverseitig zusätzlich
                // abgesichert (app/routers/journal_entries.py::_require_editable).
                const isEditable =
                  !isReversed && entry.lines.every((l) => l.unit_id == null && l.lease_id == null);
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
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedDocumentsEntryId(
                              expandedDocumentsEntryId === entry.entry_id ? null : entry.entry_id,
                            )
                          }
                        >
                          {expandedDocumentsEntryId === entry.entry_id ? "Belege ausblenden" : "Belege"}
                        </button>
                        {isEditable && (
                          <button type="button" onClick={() => setMode(entry.entry_id)}>
                            Bearbeiten
                          </button>
                        )}
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

                    {expandedDocumentsEntryId === entry.entry_id && (
                      <JournalEntryDocuments propertyId={propertyId} journalEntryId={entry.entry_id} />
                    )}
                  </li>
                );
              })}
            </ul>
          </Card>
        </>
      )}

      {tab === "kontenblatt" && (
        <Card>
          <h2>Kontenblatt</h2>
          <AccountLedgerPanel propertyId={propertyId} />
        </Card>
      )}

      {mode === "creating" && tab === "buchungen" && (
        <Card>
          <h2>Neue Buchung erfassen</h2>
          <JournalEntryForm
            propertyId={propertyId}
            onSubmit={handleCreate}
            onCancel={() => setMode("idle")}
            isSubmitting={createMutation.isPending}
            error={formError}
          />
        </Card>
      )}

      {typeof mode === "number" && tab === "buchungen" && editingEntry && (
        <Card>
          <h2>Buchung bearbeiten</h2>
          <JournalEntryForm
            propertyId={propertyId}
            initialValues={editingEntry}
            submitLabel="Änderungen speichern"
            onSubmit={(payload) => handleUpdate(editingEntry.entry_id, payload)}
            onCancel={() => setMode("idle")}
            isSubmitting={updateMutation.isPending}
            error={formError}
          />
        </Card>
      )}

      {mode === "recording-payment" && tab === "buchungen" && (
        <Card>
          <h2>Zahlungseingang erfassen</h2>
          <PaymentForm
            propertyId={propertyId}
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