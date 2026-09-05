// frontend/src/features/units/UnitOwnerAssignments.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { useOwners } from "../owners/useOwners";
import {
  useAssignOwner,
  useDeleteOwnerAssignment,
  useUnitOwners,
  useUpdateOwnerAssignment,
} from "./useUnits";
import "./UnitOwnerAssignments.css";

// frontend/src/features/units/UnitOwnerAssignments.tsx — Props + Formular ergänzen
interface UnitOwnerAssignmentsProps {
  unitId: number;
  unitNumber: string;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function UnitOwnerAssignments({ unitId }: UnitOwnerAssignmentsProps) {
  const { data: history, isLoading } = useUnitOwners(unitId);
  const { data: owners } = useOwners();
  const assignOwnerMutation = useAssignOwner(unitId);
  const updateAssignmentMutation = useUpdateOwnerAssignment(unitId);
  const deleteAssignmentMutation = useDeleteOwnerAssignment(unitId);

  const [showForm, setShowForm] = useState(false);
  const [ownerId, setOwnerId] = useState<number | "">("");
  const [ownershipShare, setOwnershipShare] = useState("");
  const [validFrom, setValidFrom] = useState(todayIso());
  const [error, setError] = useState<string | null>(null);
    // frontend/src/features/units/UnitOwnerAssignments.tsx — State ergänzen
  const [endingHistoryId, setEndingHistoryId] = useState<number | null>(null);
  const [endDate, setEndDate] = useState(todayIso());
  const [endError, setEndError] = useState<string | null>(null);

  // handleAssign: owner_number mitschicken
  function handleAssign(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (ownerId === "") return;
    assignOwnerMutation.mutate(
      {
        owner_id: ownerId,
        ownership_share: Number(ownershipShare),
        valid_from: validFrom,
        owner_number: ownerNumber || null,
      },
      {
        onSuccess: () => {
          setShowForm(false);
          setOwnerId("");
          setOwnershipShare("");
          setOwnerNumber("");
        },
        onError: () => setError("Zuordnung konnte nicht angelegt werden."),
      },
    );
  }


  // frontend/src/features/units/UnitOwnerAssignments.tsx — handleEndAssignment ersetzen
function startEnding(historyId: number, validFrom: string) {
    setEndingHistoryId(historyId);
    // Nur ein Vorschlag, kein fester Wert - ein Eigentümerwechsel wird oft
    // im Voraus (Notartermin) oder rückwirkend (Grundbucheintrag) erfasst.
    setEndDate(todayIso() > validFrom ? todayIso() : validFrom);
    setEndError(null);
  }

  function confirmEnding(event: FormEvent) {
    event.preventDefault();
    if (endingHistoryId === null) return;
    setEndError(null);
    updateAssignmentMutation.mutate(
      { historyId: endingHistoryId, payload: { valid_to: endDate } },
      {
        onSuccess: () => setEndingHistoryId(null),
        onError: () => setEndError("Gültigkeitsende konnte nicht gespeichert werden."),
      },
    );
  }

  function handleDeleteAssignment(historyId: number) {
    if (
      !window.confirm(
        "Diesen Eintrag unwiderruflich löschen? Nur für Fehlerfassungen gedacht - für einen echten Eigentümerwechsel stattdessen 'Beenden' nutzen.",
      )
    )
      return;
    deleteAssignmentMutation.mutate(historyId);
  }

  function ownerLabel(id: number): string {
    const owner = owners?.find((o) => o.owner_id === id);
    if (!owner) return `Eigentümer #${id}`;
    return owner.company_name ?? `${owner.first_name ?? ""} ${owner.last_name}`.trim();
  }

  function suggestOwnerNumber(unitNumber: string, sequence: number): string {
  // Nur ein Vorschlag nach dem Muster "Einheit + laufende Nummer" - frei
  // überschreibbar, andere Nummernsysteme funktionieren genauso.
  const unitDigits = unitNumber.replace(/\D/g, "") || "0";
  return `${unitDigits.padStart(3, "0")}${String(sequence).padStart(2, "0")}`;
}

export function UnitOwnerAssignments({ unitId, unitNumber }: UnitOwnerAssignmentsProps) {
  // ... bestehende Hooks/State ...
  const [ownerNumber, setOwnerNumber] = useState("");

  const current = history?.filter((h) => h.valid_to === null) ?? [];
  const past = history?.filter((h) => h.valid_to !== null) ?? [];

  return (
    <div className="unit-owner-assignments">
      {isLoading && <p>Lädt…</p>}

      <h4>Aktuelle Eigentümer</h4>
      {current.length === 0 && <p className="unit-owner-assignments__empty">Kein Eigentümer zugeordnet.</p>}
      {current.length > 0 && (
        <ul className="unit-owner-assignments__list">
  // in der Anzeige (current.map), Eigentümernummer mit ausgeben:
  {current.map((h) => (
    <li key={h.history_id}>
      {ownerLabel(h.owner_id)} · Anteil {h.ownership_share} · seit {h.valid_from}
      {h.owner_number && <> · Nr. {h.owner_number}</>}
              <button type="button" onClick={() => startEnding(h.history_id, h.valid_from)}>
                Beenden
              </button>
              <button type="button" onClick={() => handleDeleteAssignment(h.history_id)}>
                Löschen
              </button>

              {endingHistoryId === h.history_id && (
                <form onSubmit={confirmEnding} className="unit-owner-assignments__end-form">
                  <label>
                    Gültig bis
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      min={h.valid_from}
                      required
                    />
                  </label>
                  {endError && <p className="unit-owner-assignments__error">{endError}</p>}
                  <div className="unit-owner-assignments__end-form-actions">
                    <button type="submit" disabled={updateAssignmentMutation.isPending}>
                      {updateAssignmentMutation.isPending ? "Wird gespeichert…" : "Bestätigen"}
                    </button>
                    <button type="button" onClick={() => setEndingHistoryId(null)}>
                      Abbrechen
                    </button>
                  </div>
                </form>
              )}
            </li>
          ))}
        </ul>
      )}

      {past.length > 0 && (
        <details className="unit-owner-assignments__history">
          <summary>Historie ({past.length})</summary>
          <ul className="unit-owner-assignments__list">
            {past.map((h) => (
              <li key={h.history_id}>
                {ownerLabel(h.owner_id)} · Anteil {h.ownership_share} · {h.valid_from} – {h.valid_to}
                <button type="button" onClick={() => handleDeleteAssignment(h.history_id)}>
                  Löschen
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}

      {!showForm && (
        <button type="button" onClick={() => setShowForm(true)}>
          Eigentümer zuordnen
        </button>
      )}

      {showForm && (
        <form onSubmit={handleAssign} className="unit-owner-assignments__form">
          <label>
            Eigentümer
            <select
              value={ownerId}
              onChange={(e) => setOwnerId(e.target.value ? Number(e.target.value) : "")}
              required
            >
              <option value="">– bitte wählen –</option>
              {owners?.map((o) => (
                <option key={o.owner_id} value={o.owner_id}>
                  {o.company_name ?? `${o.first_name ?? ""} ${o.last_name}`.trim()}
                </option>
              ))}
            </select>
          </label>
          <label>
            Anteil (MEA)
            <input
              type="number"
              min="0.0001"
              step="0.0001"
              value={ownershipShare}
              onChange={(e) => setOwnershipShare(e.target.value)}
              required
            />
          </label>
          <label>
            Gültig ab
            <input type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} required />
          </label>
            // im Formular, nach dem "Gültig ab"-Feld einfügen:
          <label>
            Eigentümernummer (optional)
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <input
                value={ownerNumber}
                onChange={(e) => setOwnerNumber(e.target.value)}
                placeholder="z.B. 1000401 oder eigenes Schema"
              />
              <button
                type="button"
                onClick={() => setOwnerNumber(suggestOwnerNumber(unitNumber, (history?.length ?? 0) + 1))}
              >
                Vorschlag
              </button>
            </div>
          </label>
          {error && <p className="unit-owner-assignments__error">{error}</p>}
          <div className="unit-owner-assignments__form-actions">
            <button type="submit" disabled={assignOwnerMutation.isPending}>
              {assignOwnerMutation.isPending ? "Wird gespeichert…" : "Zuordnen"}
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