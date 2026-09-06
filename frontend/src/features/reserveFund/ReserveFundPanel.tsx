// frontend/src/features/reserveFund/ReserveFundPanel.tsx
import { useState } from "react";

import { accountLabel } from "../accounts/format";
import { useAccounts } from "../accounts/useAccounts";

import type { MovementType, ReserveFundPositionPayload } from "./api";
import { ReserveFundPositionForm } from "./ReserveFundPositionForm";
import {
  useCreateReserveFundPosition,
  useCreateReserveFundStatement,
  useDeleteReserveFundPosition,
  useRecalculateReserveFund,
  useReserveFundStatement,
  useSetOperatingAccounts,
  useUpdateReserveFundPosition,
} from "./useReserveFund";
import "./ReserveFundPanel.css";

const MOVEMENT_TYPE_LABELS: Record<MovementType, string> = {
  Zufuehrung: "Zuführung",
  Entnahme: "Liquiditätsentnahme",
  Zinsen: "Zinsen",
  Kapitalertragsteuer: "Kapitalertragsteuer",
  Solidaritaetszuschlag: "Solidaritätszuschlag",
  Sonstiges: "Sonstiges",
};

interface ReserveFundPanelProps {
  settlementId: number;
  propertyId: number;
  periodStatus: "Entwurf" | "Beschlossen" | "Inaktiv";
  unitLabelFor: (unitId: number) => string;
}

export function ReserveFundPanel({
  settlementId,
  propertyId,
  periodStatus,
  unitLabelFor,
}: ReserveFundPanelProps) {
  const { data: statement, isLoading, isError, error } = useReserveFundStatement(settlementId);
  const { data: accounts } = useAccounts({ property_id: propertyId });

  const createStatementMutation = useCreateReserveFundStatement(settlementId);
  const setOperatingAccountsMutation = useSetOperatingAccounts(settlementId);
  const createPositionMutation = useCreateReserveFundPosition(settlementId);
  const updatePositionMutation = useUpdateReserveFundPosition(settlementId);
  const deletePositionMutation = useDeleteReserveFundPosition(settlementId);
  const recalculateMutation = useRecalculateReserveFund(settlementId);

  const isDraft = periodStatus === "Entwurf";

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingPositionId, setEditingPositionId] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const [editingOperatingAccounts, setEditingOperatingAccounts] = useState(false);
  const [operatingAccountDraft, setOperatingAccountDraft] = useState<number[]>([]);
  const [operatingAccountsError, setOperatingAccountsError] = useState<string | null>(null);

  const notFound =
    isError &&
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    (error as { response?: { status?: number } }).response?.status === 404;

  function accountLabelFor(accountId: number): string {
    const account = accounts?.find((a) => a.account_id === accountId);
    return account ? accountLabel(account) : `Konto #${accountId}`;
  }

  function startEditingOperatingAccounts() {
    setOperatingAccountDraft(statement?.operating_account_ids ?? []);
    setOperatingAccountsError(null);
    setEditingOperatingAccounts(true);
  }

  function toggleOperatingAccount(accountId: number, checked: boolean) {
    setOperatingAccountDraft((prev) =>
      checked ? [...prev, accountId] : prev.filter((id) => id !== accountId),
    );
  }

  function saveOperatingAccounts() {
    setOperatingAccountsError(null);
    setOperatingAccountsMutation.mutate(
      { account_ids: operatingAccountDraft },
      {
        onSuccess: () => setEditingOperatingAccounts(false),
        onError: () =>
          setOperatingAccountsError("Bewirtschaftungskonten konnten nicht gespeichert werden."),
      },
    );
  }

  function handleCreatePosition(payload: ReserveFundPositionPayload) {
    setFormError(null);
    createPositionMutation.mutate(payload, {
      onSuccess: () => setShowCreateForm(false),
      onError: () => setFormError("Position konnte nicht angelegt werden."),
    });
  }

  function handleUpdatePosition(positionId: number, payload: ReserveFundPositionPayload) {
    setFormError(null);
    updatePositionMutation.mutate(
      { positionId, payload },
      {
        onSuccess: () => setEditingPositionId(null),
        onError: () => setFormError("Position konnte nicht aktualisiert werden."),
      },
    );
  }

  function handleDeletePosition(positionId: number) {
    if (!window.confirm("Diese Position wirklich löschen?")) return;
    deletePositionMutation.mutate(positionId);
  }

  function startEditingPosition(positionId: number) {
    setFormError(null);
    setShowCreateForm(false);
    setEditingPositionId(positionId);
  }

  if (isLoading) return <p>Lädt Rücklagendarstellung…</p>;

  if (notFound) {
    return (
      <div className="reserve-fund-panel">
        <h4>Rücklagendarstellung &amp; Vermögensaufstellung</h4>
        <p className="reserve-fund-panel__empty">
          Noch keine Rücklagendarstellung für diese Abrechnung angelegt.
        </p>
        {isDraft && (
          <button
            type="button"
            onClick={() => createStatementMutation.mutate()}
            disabled={createStatementMutation.isPending}
          >
            {createStatementMutation.isPending ? "Wird angelegt…" : "Rücklagendarstellung anlegen"}
          </button>
        )}
      </div>
    );
  }

  if (isError || !statement) {
    return <p className="reserve-fund-panel__error">Rücklagendarstellung konnte nicht geladen werden.</p>;
  }

  return (
    <div className="reserve-fund-panel">
      <h4>Rücklagendarstellung</h4>
      <table className="reserve-fund-panel__balance-table">
        <tbody>
          <tr>
            <td>Rücklagenbestand zum 01.01.</td>
            <td>{statement.reserve_balance_start.toFixed(2)} €</td>
          </tr>
          <tr>
            <td>Rücklagenbestand zum 31.12.</td>
            <td>{statement.reserve_balance_end.toFixed(2)} €</td>
          </tr>
          <tr>
            <td>Summe zugeordneter Positionen</td>
            <td>{statement.positions_sum.toFixed(2)} €</td>
          </tr>
          <tr
            className={
              statement.control_difference !== 0
                ? "reserve-fund-panel__control-row--off"
                : "reserve-fund-panel__control-row--ok"
            }
          >
            <td>Kontrolldifferenz (nicht zugeordnete Bewegungen)</td>
            <td>{statement.control_difference.toFixed(2)} €</td>
          </tr>
        </tbody>
      </table>

      {statement.positions.length === 0 && <p>Noch keine Positionen erfasst.</p>}

      {statement.positions.map((position) =>
        editingPositionId === position.position_id ? (
          <ReserveFundPositionForm
            key={position.position_id}
            propertyId={propertyId}
            initialValues={position}
            submitLabel="Speichern"
            onSubmit={(payload) => handleUpdatePosition(position.position_id, payload)}
            onCancel={() => setEditingPositionId(null)}
            isSubmitting={updatePositionMutation.isPending}
            error={formError}
          />
        ) : (
          <details key={position.position_id} className="reserve-fund-panel__position">
            <summary>
              {MOVEMENT_TYPE_LABELS[position.movement_type]}
              {position.description && ` – ${position.description}`} · {position.actual_amount.toFixed(2)}{" "}
              € · {position.allocation_key_type}
            </summary>
            <p className="reserve-fund-panel__account">
              Gegenkonto(en): {position.account_ids.map(accountLabelFor).join(", ")}
            </p>
            <table className="reserve-fund-panel__shares-table">
              <thead>
                <tr>
                  <th>Einheit</th>
                  <th>Anteiliger Betrag</th>
                </tr>
              </thead>
              <tbody>
                {position.unit_shares.map((share) => (
                  <tr key={share.share_id}>
                    <td>{unitLabelFor(share.unit_id)}</td>
                    <td>{share.allocated_amount.toFixed(2)} €</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {isDraft && (
              <div className="reserve-fund-panel__position-actions">
                <button type="button" onClick={() => startEditingPosition(position.position_id)}>
                  Bearbeiten
                </button>
                <button type="button" onClick={() => handleDeletePosition(position.position_id)}>
                  Löschen
                </button>
              </div>
            )}
          </details>
        ),
      )}

      {isDraft && (
        <div className="reserve-fund-panel__actions">
          {!showCreateForm && editingPositionId === null && (
            <button type="button" onClick={() => setShowCreateForm(true)}>
              Neue Position
            </button>
          )}
          <button
            type="button"
            onClick={() => recalculateMutation.mutate()}
            disabled={recalculateMutation.isPending}
            title="Zieht Beträge aller Positionen frisch aus den Buchungen (z.B. nach nachträglichen Buchungen/Stornos)"
          >
            {recalculateMutation.isPending ? "Wird neu berechnet…" : "Neu berechnen"}
          </button>
        </div>
      )}
      {!isDraft && (
        <p className="reserve-fund-panel__locked">
          Abrechnung ist "{periodStatus}" - Positionen können nicht mehr geändert werden.
        </p>
      )}

      {showCreateForm && (
        <ReserveFundPositionForm
          propertyId={propertyId}
          onSubmit={handleCreatePosition}
          onCancel={() => setShowCreateForm(false)}
          isSubmitting={createPositionMutation.isPending}
          error={formError}
        />
      )}

      <h4 className="reserve-fund-panel__assets-heading">Vermögensaufstellung</h4>
      <p className="reserve-fund-panel__hint">
        Bewirtschaftungskonto(en) - Salden werden nicht auf Einheiten verteilt, nur als Gesamtsumme der
        Liegenschaft ausgewiesen.
      </p>

      {!editingOperatingAccounts && (
        <>
          <table className="reserve-fund-panel__balance-table">
            <tbody>
              <tr>
                <td>Bewirtschaftungskonto 01.01.</td>
                <td>{statement.operating_balance_start.toFixed(2)} €</td>
              </tr>
              <tr>
                <td>Bewirtschaftungskonto 31.12.</td>
                <td>{statement.operating_balance_end.toFixed(2)} €</td>
              </tr>
            </tbody>
          </table>
          <p className="reserve-fund-panel__account">
            {statement.operating_account_ids.length > 0
              ? `Konten: ${statement.operating_account_ids.map(accountLabelFor).join(", ")}`
              : "Noch kein Bewirtschaftungskonto ausgewählt."}
          </p>
          {isDraft && (
            <button type="button" onClick={startEditingOperatingAccounts}>
              Bewirtschaftungskonto(en) bearbeiten
            </button>
          )}
        </>
      )}

      {editingOperatingAccounts && (
        <div className="reserve-fund-panel__operating-form">
          {accounts
            ?.filter((a) => a.type === "AKTIV")
            .map((a) => (
              <label
                key={a.account_id}
                className="reserve-fund-panel__operating-row"
                title={accountLabel(a)}
              >
                <input
                  type="checkbox"
                  checked={operatingAccountDraft.includes(a.account_id)}
                  onChange={(e) => toggleOperatingAccount(a.account_id, e.target.checked)}
                />
                {accountLabel(a)}
              </label>
            ))}
          {operatingAccountsError && <p className="reserve-fund-panel__error">{operatingAccountsError}</p>}
          <div className="reserve-fund-panel__operating-form-actions">
            <button
              type="button"
              onClick={saveOperatingAccounts}
              disabled={setOperatingAccountsMutation.isPending}
            >
              {setOperatingAccountsMutation.isPending ? "Wird gespeichert…" : "Speichern"}
            </button>
            <button type="button" onClick={() => setEditingOperatingAccounts(false)}>
              Abbrechen
            </button>
          </div>
        </div>
      )}
    </div>
  );
}