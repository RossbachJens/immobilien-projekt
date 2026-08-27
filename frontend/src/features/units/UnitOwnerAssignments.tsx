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

interface UnitOwnerAssignmentsProps {
  unitId: number;
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

  function handleAssign(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (ownerId === "") return;
    assignOwnerMutation.mutate(
      {
        owner_id: ownerId,
        ownership_share: Number(ownershipShare),
        valid_from: validFrom,
      },
      {
        onSuccess: () => {
          setShowForm(false);
          setOwnerId("");
          setOwnershipShare("");
        },
        onError: () => setError("Zuordnung konnte nicht angelegt werden."),
      },
    );
  }

  function handleEndAssignment(historyId: number) {
    if (!window.confirm("Diese Eigentümerzuordnung zum heutigen Tag beenden?")) return;
    updateAssignmentMutation.mutate({ historyId, payload: { valid_to: todayIso() } });
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

  const current = history?.filter((h) => h.valid_to === null) ?? [];
  const past = history?.filter((h) => h.valid_to !== null) ?? [];

  return (
    <div className="unit-owner-assignments">
      {isLoading && <p>Lädt…</p>}

      <h4>Aktuelle Eigentümer</h4>
      {current.length === 0 && <p className="unit-owner-assignments__empty">Kein Eigentümer zugeordnet.</p>}
      {current.length > 0 && (
        <ul className="unit-owner-assignments__list">
          {current.map((h) => (
            <li key={h.history_id}>
              {ownerLabel(h.owner_id)} · Anteil {h.ownership_share} · seit {h.valid_from}
              <button type="button" onClick={() => handleEndAssignment(h.history_id)}>
                Beenden
              </button>
              <button type="button" onClick={() => handleDeleteAssignment(h.history_id)}>
                Löschen
              </button>
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