// frontend/src/features/journalEntries/JournalEntryForm.tsx
import { useRef, useState } from "react";
import type { FormEvent } from "react";

import type { AccountType } from "../accounts/api";
import { useAccounts } from "../accounts/useAccounts";

import type { EntryDirection, JournalEntryPayload } from "./api";
import "./JournalEntryForm.css";

interface FormLine {
  key: string;
  accountId: number | "";
  direction: EntryDirection;
  amount: string;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

interface JournalEntryFormProps {
  propertyId: number;
  onSubmit: (payload: JournalEntryPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function JournalEntryForm({
  propertyId,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: JournalEntryFormProps) {
  // Nur aktive Konten zur Auswahl anbieten - inaktive Konten dürfen zwar in
  // historischen Buchungen weiter auftauchen, aber für neue Buchungen nicht
  // mehr wählbar sein.
  const [typeFilter, setTypeFilter] = useState<AccountType | "">("");
  const {
    data: accounts,
    isLoading: accountsLoading,
    isError: accountsError,
  } = useAccounts({ property_id: propertyId, is_active: true, type: typeFilter || undefined });

  // Zähler nur für stabile React-keys der dynamischen Zeilen - hat keinen
  // fachlichen Bezug zur Buchung selbst.
  const lineKeyRef = useRef(0);
  function makeLine(direction: EntryDirection = "DEBIT"): FormLine {
    lineKeyRef.current += 1;
    return { key: `line-${lineKeyRef.current}`, accountId: "", direction, amount: "" };
  }

  const [entryDate, setEntryDate] = useState(todayIso());
  const [documentReference, setDocumentReference] = useState("");
  const [description, setDescription] = useState("");
  const [lines, setLines] = useState<FormLine[]>(() => [makeLine("DEBIT"), makeLine("CREDIT")]);
  const [validationError, setValidationError] = useState<string | null>(null);

  function updateLine(key: string, patch: Partial<FormLine>) {
    setLines((prev) => prev.map((line) => (line.key === key ? { ...line, ...patch } : line)));
  }

  function addLine() {
    setLines((prev) => [...prev, makeLine()]);
  }

  function removeLine(key: string) {
    setLines((prev) => (prev.length <= 2 ? prev : prev.filter((line) => line.key !== key)));
  }

  // Nur eine Vorschau für den User - die verbindliche Prüfung übernimmt der
  // DEFERRED Constraint-Trigger in Postgres beim COMMIT (02_triggers.sql).
  const debitSum = lines
    .filter((l) => l.direction === "DEBIT")
    .reduce((sum, l) => sum + (Number(l.amount) || 0), 0);
  const creditSum = lines
    .filter((l) => l.direction === "CREDIT")
    .reduce((sum, l) => sum + (Number(l.amount) || 0), 0);
  const difference = Math.round((debitSum - creditSum) * 100) / 100;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setValidationError(null);

    if (lines.some((l) => l.accountId === "" || !l.amount || Number(l.amount) <= 0)) {
      setValidationError("Bitte bei jeder Zeile ein Konto und einen Betrag > 0 angeben.");
      return;
    }
    if (difference !== 0) {
      setValidationError(
        `Soll und Haben sind nicht ausgeglichen (Differenz: ${difference.toFixed(2)} €).`,
      );
      return;
    }

    onSubmit({
      property_id: propertyId,
      entry_date: entryDate,
      document_reference: documentReference || null,
      description,
      lines: lines.map((l) => ({
        account_id: Number(l.accountId),
        direction: l.direction,
        amount: Number(l.amount),
      })),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="journal-entry-form">
      <label>
        Datum *
        <input type="date" value={entryDate} onChange={(e) => setEntryDate(e.target.value)} required />
      </label>
      <label>
        Belegnummer
        <input
          value={documentReference}
          onChange={(e) => setDocumentReference(e.target.value)}
          placeholder="optional"
        />
      </label>
      <label>
        Beschreibung *
        <input value={description} onChange={(e) => setDescription(e.target.value)} required />
      </label>

      <fieldset className="journal-entry-form__lines">
        <legend>Buchungszeilen</legend>
                <label className="journal-entry-form__type-filter">
          Kontoart eingrenzen
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as AccountType | "")}>
            <option value="">Alle</option>
            <option value="AKTIV">Aktiv</option>
            <option value="PASSIV">Passiv</option>
            <option value="ERTRAG">Ertrag</option>
            <option value="AUFWAND">Aufwand</option>
          </select>
        </label>

               {accountsLoading && <p className="journal-entry-form__hint">Konten werden geladen…</p>}
        {accountsError && (
          <p className="journal-entry-form__error">Konten konnten nicht geladen werden.</p>
        )}
        {!accountsLoading && !accountsError && accounts?.length === 0 && (
          <p className="journal-entry-form__hint">
            Kein Konto verfügbar – bitte zuerst einen Kontenrahmen anlegen.
          </p>
        )}

         <div className="journal-entry-form__lines-header"></div>

        <div className="journal-entry-form__lines-header">
          <span>Konto</span>          
          <span>Soll/Haben</span>
          <span>Betrag (€)</span>
          <span />
        </div>

        {lines.map((line) => (
          <div key={line.key} className="journal-entry-form__line">
            <select
              value={line.accountId}
              onChange={(e) =>
                updateLine(line.key, { accountId: e.target.value ? Number(e.target.value) : "" })
              }
              required
            >
              <option value="">– Konto wählen –</option>
              {accounts?.map((a) => (
                <option key={a.account_id} value={a.account_id}>
                  {a.account_number} – {a.account_name}
                  {a.property_id != null ? " (eigen)" : ""}
                </option>
              ))}
            </select>

            

            <select
              value={line.direction}
              onChange={(e) => updateLine(line.key, { direction: e.target.value as EntryDirection })}
            >
              <option value="DEBIT">Soll</option>
              <option value="CREDIT">Haben</option>
            </select>

            <input
              type="number"
              min="0.01"
              step="0.01"
              value={line.amount}
              onChange={(e) => updateLine(line.key, { amount: e.target.value })}
              required
            />

            <button
              type="button"
              onClick={() => removeLine(line.key)}
              disabled={lines.length <= 2}
              title={lines.length <= 2 ? "Mindestens zwei Zeilen erforderlich" : "Zeile entfernen"}
            >
              ✕
            </button>
          </div>
        ))}

        <button type="button" onClick={addLine} className="journal-entry-form__add-line">
          + Zeile hinzufügen
        </button>

        <div
          className={
            "journal-entry-form__balance" +
            (difference !== 0
              ? " journal-entry-form__balance--off"
              : " journal-entry-form__balance--ok")
          }
        >
          Soll: {debitSum.toFixed(2)} € · Haben: {creditSum.toFixed(2)} €
          {difference !== 0 && <> · Differenz: {difference.toFixed(2)} €</>}
        </div>
      </fieldset>

      {(validationError || error) && (
        <p className="journal-entry-form__error">{validationError ?? error}</p>
      )}

      <div className="journal-entry-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird gebucht…" : "Buchen"}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}