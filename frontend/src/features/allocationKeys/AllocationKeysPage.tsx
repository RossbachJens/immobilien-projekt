// frontend/src/features/allocationKeys/AllocationKeysPage.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { Card } from "../../components/Card";
import { useProperties } from "../properties/useProperties";
import { useUnits } from "../units/useUnits";
import { AllocationKeyGroupForm } from "./AllocationKeyGroupForm";
import type { AllocationKey, AllocationKeyCreatePayload } from "./api";
import {
  AllocationKeyGroupError,
  useAllocationKeys,
  useCloseAllocationKeyGroup,
  useCreateAllocationKeyGroup,
} from "./useAllocationKeys";
import "./AllocationKeysPage.css";

interface AllocationKeyGroup {
  key_type: string;
  denominator_value: number;
  valid_from_year: number;
  valid_to_year: number | null;
  entries: { key_id: number; unit_id: number; numerator_value: number }[];
}

function groupIdentifier(group: Pick<AllocationKeyGroup, "key_type" | "denominator_value" | "valid_from_year" | "valid_to_year">): string {
  return `${group.key_type}__${group.denominator_value}__${group.valid_from_year}__${group.valid_to_year ?? "open"}`;
}

function groupAllocationKeys(keys: AllocationKey[]): AllocationKeyGroup[] {
  const map = new Map<string, AllocationKeyGroup>();
  for (const k of keys) {
    const id = groupIdentifier(k);
    const existing = map.get(id);
    if (existing) {
      existing.entries.push({ key_id: k.key_id, unit_id: k.unit_id, numerator_value: k.numerator_value });
    } else {
      map.set(id, {
        key_type: k.key_type,
        denominator_value: k.denominator_value,
        valid_from_year: k.valid_from_year,
        valid_to_year: k.valid_to_year,
        entries: [{ key_id: k.key_id, unit_id: k.unit_id, numerator_value: k.numerator_value }],
      });
    }
  }
  return Array.from(map.values()).sort((a, b) => {
    if (a.key_type !== b.key_type) return a.key_type.localeCompare(b.key_type);
    return b.valid_from_year - a.valid_from_year;
  });
}

function todayYear(): number {
  return new Date().getFullYear();
}

export function AllocationKeysPage() {
  const { data: properties, isLoading: propertiesLoading } = useProperties();
  const [propertyId, setPropertyId] = useState<number | "">("");
  const selectedPropertyId = propertyId === "" ? undefined : propertyId;

  const { data: units } = useUnits(selectedPropertyId);
  const { data: keys, isLoading: keysLoading } = useAllocationKeys(selectedPropertyId);

  const createGroupMutation = useCreateAllocationKeyGroup(selectedPropertyId ?? -1);
  const closeGroupMutation = useCloseAllocationKeyGroup(selectedPropertyId ?? -1);

  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Gruppen-Identifier, für den gerade ein Gültigkeitsende eingegeben wird.
  const [closingGroupKey, setClosingGroupKey] = useState<string | null>(null);
  const [closeYear, setCloseYear] = useState(String(todayYear() - 1));
  const [closeError, setCloseError] = useState<string | null>(null);

  function unitLabel(unitId: number): string {
    const unit = units?.find((u) => u.unit_id === unitId);
    return unit ? unit.unit_number : `#${unitId}`;
  }

  const groups = groupAllocationKeys(keys ?? []);
  const existingKeyTypes = Array.from(new Set((keys ?? []).map((k) => k.key_type)));

  function handleCreate(payloads: AllocationKeyCreatePayload[]) {
    setFormError(null);
    createGroupMutation.mutate(payloads, {
      onSuccess: () => setCreating(false),
      onError: (err) => {
        if (err instanceof AllocationKeyGroupError) {
          setFormError(
            "Für folgende Einheiten konnte kein Umlageschlüssel angelegt werden (eventuell " +
              `überlappender Gültigkeitszeitraum): ${err.failedUnitIds.map(unitLabel).join(", ")}.`,
          );
        } else {
          setFormError("Umlageschlüssel konnte nicht angelegt werden.");
        }
      },
    });
  }

  function startClosing(group: AllocationKeyGroup) {
    setClosingGroupKey(groupIdentifier(group));
    setCloseYear(String(Math.max(group.valid_from_year, todayYear() - 1)));
    setCloseError(null);
  }

  function confirmClose(event: FormEvent, group: AllocationKeyGroup) {
    event.preventDefault();
    setCloseError(null);
    closeGroupMutation.mutate(
      { keyIds: group.entries.map((e) => e.key_id), validToYear: Number(closeYear) },
      {
        onSuccess: () => setClosingGroupKey(null),
        onError: () => setCloseError("Gültigkeitsende konnte nicht für alle Einheiten gespeichert werden."),
      },
    );
  }

  return (
    <div className="allocation-keys-page">
      <Card>
        <h1>Umlageschlüssel</h1>
        <p className="allocation-keys-page__hint">
          Individuelle Verteilerschlüssel (z.B. Heizkostenverteiler) je Einheit - ergänzend zu den
          Standard-Schlüsseln MEA und Wohnfläche. Ein Wechsel wird laut Grundsatzentscheidung erst zum
          nächsten 01.01. wirksam.
        </p>
        {propertiesLoading && <p>Lädt Liegenschaften…</p>}
        <label className="allocation-keys-page__property-select">
          Liegenschaft
          <select
            value={propertyId}
            onChange={(e) => {
              setPropertyId(e.target.value ? Number(e.target.value) : "");
              setCreating(false);
              setClosingGroupKey(null);
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
        <Card>
          <div className="allocation-keys-page__header">
            <h2>Bestehende Umlageschlüssel</h2>
            {!creating && (
              <button type="button" onClick={() => setCreating(true)}>
                Neuer Umlageschlüssel
              </button>
            )}
          </div>

          {keysLoading && <p>Lädt…</p>}
          {!keysLoading && groups.length === 0 && <p>Noch keine individuellen Umlageschlüssel erfasst.</p>}

          <ul className="allocation-keys-page__list">
            {groups.map((group) => {
              const isOpen = group.valid_to_year === null;
              const id = groupIdentifier(group);
              const sortedEntries = [...group.entries].sort((a, b) =>
                unitLabel(a.unit_id).localeCompare(unitLabel(b.unit_id), undefined, { numeric: true }),
              );

              return (
                <li key={id} className="allocation-keys-page__group">
                  <div className="allocation-keys-page__group-row">
                    <div>
                      <strong>{group.key_type}</strong> · Nenner {group.denominator_value} · gültig ab{" "}
                      {group.valid_from_year}
                      {group.valid_to_year != null && <> bis {group.valid_to_year}</>}
                    </div>
                    {isOpen && (
                      <button type="button" onClick={() => startClosing(group)}>
                        Schließen
                      </button>
                    )}
                  </div>

                  <table className="allocation-keys-page__entries-table">
                    <thead>
                      <tr>
                        <th>Einheit</th>
                        <th>Zähler</th>
                        <th>Anteil</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedEntries.map((entry) => (
                        <tr key={entry.key_id}>
                          <td>{unitLabel(entry.unit_id)}</td>
                          <td>{entry.numerator_value}</td>
                          <td>{((entry.numerator_value / group.denominator_value) * 100).toFixed(2)} %</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {closingGroupKey === id && (
                    <form onSubmit={(e) => confirmClose(e, group)} className="allocation-keys-page__close-form">
                      <label>
                        Letztes gültiges Jahr
                        <input
                          type="number"
                          value={closeYear}
                          onChange={(e) => setCloseYear(e.target.value)}
                          min={group.valid_from_year}
                          required
                        />
                      </label>
                      {closeError && <p className="allocation-keys-page__error">{closeError}</p>}
                      <div className="allocation-keys-page__close-form-actions">
                        <button type="submit" disabled={closeGroupMutation.isPending}>
                          {closeGroupMutation.isPending ? "Wird gespeichert…" : "Bestätigen"}
                        </button>
                        <button type="button" onClick={() => setClosingGroupKey(null)}>
                          Abbrechen
                        </button>
                      </div>
                    </form>
                  )}
                </li>
              );
            })}
          </ul>
        </Card>
      )}

      {creating && selectedPropertyId !== undefined && (
        <Card>
          <h2>Neuen Umlageschlüssel anlegen</h2>
          <AllocationKeyGroupForm
            propertyId={selectedPropertyId}
            units={units ?? []}
            existingKeyTypes={existingKeyTypes}
            onSubmit={handleCreate}
            onCancel={() => setCreating(false)}
            isSubmitting={createGroupMutation.isPending}
            error={formError}
          />
        </Card>
      )}
    </div>
  );
}