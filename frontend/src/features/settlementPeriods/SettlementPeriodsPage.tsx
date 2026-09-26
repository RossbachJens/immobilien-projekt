// frontend/src/features/settlementPeriods/SettlementPeriodsPage.tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Card } from "../../components/Card";
import { useCurrentProperty } from "../../context/PropertyContext";
import { accountLabel } from "../accounts/format";
import { useAccounts } from "../accounts/useAccounts";
import { ReserveFundPanel } from "../reserveFund/ReserveFundPanel";
import { useResolutions } from "../resolutions/useResolutions";
import type { Unit } from "../units/api";
import { useUnits } from "../units/useUnits";
import type {
  LeaseSettlementSummary,
  SettlementPeriodPayload,
  SettlementPositionPayload,
  SettlementStatus,
} from "./api";
import { SettlementPeriodForm } from "./SettlementPeriodForm";
import { SettlementPositionForm } from "./SettlementPositionForm";
import {
  useCreateSettlementPeriod,
  useCreateSettlementPosition,
  useDeleteSettlementPosition,
  useExportLeaseSettlement,
  useExportSettlementBatch,
  useExportSettlementTenantBatch,
  useExportUnitSettlement,
  useLeaseSummaries,
  useRecalculateSettlement,
  useSettlementPeriods,
  useSettlementPositions,
  useUnitSummaries,
  useUpdateSettlementPeriod,
  useUpdateSettlementPosition,
} from "./useSettlementPeriods";
import "./SettlementPeriodsPage.css";

const NEXT_STATUS_LABEL: Record<SettlementStatus, { next: SettlementStatus; label: string }[]> = {
  Entwurf: [
    { next: "Beschlossen", label: "Beschließen" },
    { next: "Inaktiv", label: "Verwerfen" },
  ],
  Beschlossen: [{ next: "Inaktiv", label: "Deaktivieren" }],
  Inaktiv: [],
};

export function SettlementPeriodsPage() {
  const { propertyId, property, properties, isLoading: propertiesLoading } = useCurrentProperty();

  const { data: periods, isLoading: periodsLoading } = useSettlementPeriods(propertyId ?? undefined);
  const { data: accounts } = useAccounts({ property_id: propertyId ?? undefined });
  const { data: units } = useUnits(propertyId ?? undefined);
  const { data: resolutions } = useResolutions(propertyId ?? undefined);

  const createMutation = useCreateSettlementPeriod(propertyId ?? -1);
  const updateMutation = useUpdateSettlementPeriod(propertyId ?? -1);

  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [approvingId, setApprovingId] = useState<number | null>(null);
  const [approveResolutionId, setApproveResolutionId] = useState<number | "">("");

  useEffect(() => {
    setCreating(false);
    setFormError(null);
    setExpandedId(null);
    setApprovingId(null);
    setApproveResolutionId("");
  }, [propertyId]);

  function handleCreate(payload: SettlementPeriodPayload) {
    setFormError(null);
    createMutation.mutate(payload, {
      onSuccess: () => setCreating(false),
      onError: () => setFormError("Abrechnung konnte nicht angelegt werden - Jahr eventuell schon vergeben."),
    });
  }

  function handleStatusChange(settlementId: number, next: SettlementStatus, hasResolution: boolean) {
    if (next === "Beschlossen" && !hasResolution) {
      setApprovingId(settlementId);
      setApproveResolutionId("");
      return;
    }
    if (next === "Inaktiv" && !window.confirm("Abrechnung wirklich auf 'Inaktiv' setzen?")) return;
    updateMutation.mutate({ settlementId, payload: { status: next } });
  }

  function confirmApproval(settlementId: number) {
    if (approveResolutionId === "") return;
    updateMutation.mutate(
      { settlementId, payload: { status: "Beschlossen", resolution_id: approveResolutionId } },
      { onSuccess: () => setApprovingId(null) },
    );
  }

  function resolutionLabel(resolutionId: number | null): string | null {
    if (resolutionId == null) return null;
    const r = resolutions?.find((x) => x.resolution_id === resolutionId);
    return r ? `Lfd. Nr. ${r.lfd_nr} – ${r.title}` : `Beschluss #${resolutionId}`;
  }

  function unitLabel(unitId: number): string {
    const unit = units?.find((u) => u.unit_id === unitId);
    return unit ? unit.unit_number : `#${unitId}`;
  }

  if (propertiesLoading) {
    return (
      <div className="settlement-periods-page">
        <Card>
          <p>Lädt Liegenschaften…</p>
        </Card>
      </div>
    );
  }

  if (propertyId == null || properties.length === 0) {
    return (
      <div className="settlement-periods-page">
        <Card>
          <h1>Nebenkostenabrechnung</h1>
          <p>Bitte zuerst links in der Sidebar eine Liegenschaft auswählen.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="settlement-periods-page">
      <Card>
        <h1>Nebenkostenabrechnung – {property?.name}</h1>
      </Card>

      <Card>
        <div className="settlement-periods-page__header">
          <h2>Abrechnungen</h2>
          {!creating && (
            <button type="button" onClick={() => setCreating(true)}>
              Neue Abrechnung
            </button>
          )}
        </div>

        {periodsLoading && <p>Lädt…</p>}
        {!periodsLoading && periods?.length === 0 && <p>Noch keine Abrechnungen erfasst.</p>}

        <ul className="settlement-periods-page__list">
          {periods?.map((period) => (
            <li key={period.settlement_id} className="settlement-periods-page__period">
              <div className="settlement-periods-page__period-row">
                <div>
                  <strong>{period.fiscal_year}</strong> · {period.title} · {period.period_start} –{" "}
                  {period.period_end}{" "}
                  <span className={`settlement-periods-page__status settlement-periods-page__status--${period.status}`}>
                    {period.status}
                  </span>
                  {resolutionLabel(period.resolution_id) && (
                    <div className="settlement-periods-page__resolution">
                      Beschluss: {resolutionLabel(period.resolution_id)}
                    </div>
                  )}
                </div>
                <div className="settlement-periods-page__period-actions">
                  <Link
                    to={`/documents?settlement_id=${period.settlement_id}`}
                    className="settlement-periods-page__archive-link"
                  >
                    Archivierte PDFs
                  </Link>
                  <button
                    type="button"
                    onClick={() => setExpandedId(expandedId === period.settlement_id ? null : period.settlement_id)}
                  >
                    {expandedId === period.settlement_id ? "Details ausblenden" : "Details"}
                  </button>
                  {NEXT_STATUS_LABEL[period.status].map(({ next, label }) => (
                    <button
                      key={next}
                      type="button"
                      onClick={() => handleStatusChange(period.settlement_id, next, period.resolution_id != null)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {approvingId === period.settlement_id && (
                <div className="settlement-periods-page__approve">
                  <label>
                    Beschluss zuordnen, um zu beschließen
                    <select
                      value={approveResolutionId}
                      onChange={(e) => setApproveResolutionId(e.target.value ? Number(e.target.value) : "")}
                    >
                      <option value="">– bitte wählen –</option>
                      {resolutions?.map((r) => (
                        <option key={r.resolution_id} value={r.resolution_id}>
                          Lfd. Nr. {r.lfd_nr} – {r.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="settlement-periods-page__approve-actions">
                    <button
                      type="button"
                      disabled={approveResolutionId === "" || updateMutation.isPending}
                      onClick={() => confirmApproval(period.settlement_id)}
                    >
                      Beschließen
                    </button>
                    <button type="button" onClick={() => setApprovingId(null)}>
                      Abbrechen
                    </button>
                  </div>
                  {(!resolutions || resolutions.length === 0) && (
                    <p className="settlement-periods-page__approve-hint">
                      Noch keine Beschlüsse für diese Liegenschaft erfasst - zuerst in der Beschluss-Sammlung
                      anlegen.
                    </p>
                  )}
                </div>
              )}

              {expandedId === period.settlement_id && (
                <SettlementPeriodDetails
                  settlementId={period.settlement_id}
                  propertyId={propertyId}
                  fiscalYear={period.fiscal_year}
                  periodStatus={period.status}
                  units={units ?? []}
                  accountLabelFor={(id) => {
                    const a = accounts?.find((acc) => acc.account_id === id);
                    return a ? accountLabel(a) : `Konto #${id}`;
                  }}
                  unitLabelFor={unitLabel}
                />
              )}
            </li>
          ))}
        </ul>
      </Card>

      {creating && (
        <Card>
          <h2>Neue Abrechnung anlegen</h2>
          <SettlementPeriodForm
            propertyId={propertyId}
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

interface SettlementPeriodDetailsProps {
  settlementId: number;
  propertyId: number;
  fiscalYear: number;
  periodStatus: SettlementStatus;
  units: Unit[];
  accountLabelFor: (accountId: number) => string;
  unitLabelFor: (unitId: number) => string;
}

function SettlementPeriodDetails({
  settlementId,
  propertyId,
  fiscalYear,
  periodStatus,
  units,
  accountLabelFor,
  unitLabelFor,
}: SettlementPeriodDetailsProps) {
  const { data: positions, isLoading: positionsLoading } = useSettlementPositions(settlementId);
  const { data: summaries, isLoading: summariesLoading } = useUnitSummaries(settlementId);
  const { data: leaseSummaries, isLoading: leaseSummariesLoading } = useLeaseSummaries(settlementId);
  const createPositionMutation = useCreateSettlementPosition(settlementId);
  const updatePositionMutation = useUpdateSettlementPosition(settlementId);
  const deletePositionMutation = useDeleteSettlementPosition(settlementId);
  const recalculateMutation = useRecalculateSettlement(settlementId);
  const exportMutation = useExportUnitSettlement();
  const exportBatchMutation = useExportSettlementBatch();
  const exportLeaseMutation = useExportLeaseSettlement();
  const exportTenantBatchMutation = useExportSettlementTenantBatch();

  const isDraft = periodStatus === "Entwurf";

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingPositionId, setEditingPositionId] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  function handleCreate(payload: SettlementPositionPayload) {
    setFormError(null);
    createPositionMutation.mutate(payload, {
      onSuccess: () => setShowCreateForm(false),
      onError: () =>
        setFormError(
          "Position konnte nicht angelegt werden - Verteilerschlüssel eventuell für keine Einheit gültig.",
        ),
    });
  }

  function handleUpdate(positionId: number, payload: SettlementPositionPayload) {
    setFormError(null);
    updatePositionMutation.mutate(
      { positionId, payload },
      {
        onSuccess: () => setEditingPositionId(null),
        onError: () =>
          setFormError(
            "Position konnte nicht aktualisiert werden - Verteilerschlüssel eventuell für keine Einheit gültig.",
          ),
      },
    );
  }

  function handleDelete(positionId: number) {
    if (!window.confirm("Diese Position wirklich löschen?")) return;
    deletePositionMutation.mutate(positionId);
  }

  function startEditing(positionId: number) {
    setFormError(null);
    setShowCreateForm(false);
    setEditingPositionId(positionId);
  }

  function handleExport(unitId: number) {
    exportMutation.mutate({
      settlementId,
      unitId,
      filename: `Abrechnung_${fiscalYear}_${unitLabelFor(unitId)}.pdf`,
    });
  }

  function handleLeaseExport(leaseId: number, unitNumber: string, tenantLastName: string) {
    exportLeaseMutation.mutate({
      settlementId,
      leaseId,
      filename: `Betriebskostenabrechnung_${fiscalYear}_${unitNumber}_${tenantLastName}.pdf`,
    });
  }

  // Sprechende Bezeichnung für einen Mietvertrag - z.B. "Wohnung 3 – Schnurr
  // (03.01.2024 – laufend)". lease_id kommt sowohl aus den Positions-Anteilen
  // (tenant_shares) als auch aus den Ergebniszeilen (leaseSummaries); beide
  // stammen aus derselben Berechnung, daher genügt ein einziger Lookup.
  function leaseLabel(leaseId: number): string {
    const entry = leaseSummaries?.find((s) => s.lease_id === leaseId);
    if (!entry) return `Vertrag #${leaseId}`;
    return `${unitLabelFor(entry.unit_id)} – ${entry.tenant_first_name} ${entry.tenant_last_name}`.trim();
  }

  function leasePeriodLabel(entry: LeaseSettlementSummary): string {
    return `${entry.lease_start_date} – ${entry.lease_end_date ?? "laufend"}`;
  }

  const totalActual = positions?.reduce((sum, p) => sum + p.actual_amount, 0) ?? 0;

  // Einheiten ohne Ergebniszeile in leaseSummaries hatten im gesamten
  // Zeitraum keinen aktiven Mietvertrag - das ist bei Eigennutzung durch den
  // Eigentümer der Regelfall, kann aber auch schlicht Leerstand bedeuten.
  // Nur informativ, kein Fehlerzustand (Chat vom 24.09.2026).
  const unitsWithoutLease =
    leaseSummaries !== undefined
      ? units.filter((u) => !leaseSummaries.some((s) => s.unit_id === u.unit_id))
      : [];

  return (
    <div className="settlement-period-details">
      <h4>Positionen (Ist-Kosten)</h4>
      {positionsLoading && <p>Lädt Positionen…</p>}
      {!positionsLoading && positions?.length === 0 && <p>Noch keine Positionen erfasst.</p>}

      {positions?.map((position) =>
        editingPositionId === position.position_id ? (
          <SettlementPositionForm
            key={position.position_id}
            propertyId={propertyId}
            initialValues={position}
            submitLabel="Speichern"
            onSubmit={(payload) => handleUpdate(position.position_id, payload)}
            onCancel={() => setEditingPositionId(null)}
            isSubmitting={updatePositionMutation.isPending}
            error={formError}
          />
        ) : (
          <details key={position.position_id} className="settlement-period-details__position">
            <summary>
            {position.description ?? position.account_ids.map(accountLabelFor).join(", ")} ·{" "}
            {position.actual_amount.toFixed(2)} € · {position.allocation_key_type}
            {!position.is_apportionable && " · nicht umlagefähig"}
            {position.tax_category !== "keine" && (
              <> · § 35a ({position.tax_category === "haushaltsnahe_dienstleistung" ? "haushaltsnah" : "Handwerker"}
              , {position.deductible_amount?.toFixed(2)} € Lohnanteil)</>
            )}
          </summary>
          <p className="settlement-period-details__account">
            Konten: {position.account_ids.map(accountLabelFor).join(", ")}
          </p>
            <table className="settlement-period-details__shares-table">
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
                    <td>{share.allocated_actual_amount.toFixed(2)} €</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {position.tax_shares.length > 0 && (
              <>
                <p className="settlement-period-details__account">§ 35a-Lohnanteil je Einheit</p>
                <table className="settlement-period-details__shares-table">
                  <thead>
                    <tr>
                      <th>Einheit</th>
                      <th>Anteiliger Lohnanteil</th>
                    </tr>
                  </thead>
                  <tbody>
                    {position.tax_shares.map((share) => (
                      <tr key={share.share_id}>
                        <td>{unitLabelFor(share.unit_id)}</td>
                        <td>{share.allocated_deductible_amount.toFixed(2)} €</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
            {position.is_apportionable && (
              <>
                <p className="settlement-period-details__account">
                  Taggenauer Anteil je Mietvertrag
                  {position.tenant_shares.length === 0 && " – keine Einheit dieser Position aktuell vermietet"}
                </p>
                {position.tenant_shares.length > 0 && (
                  <table className="settlement-period-details__shares-table">
                    <thead>
                      <tr>
                        <th>Mietvertrag</th>
                        <th>Anteiliger Betrag</th>
                      </tr>
                    </thead>
                    <tbody>
                      {position.tenant_shares.map((share) => (
                        <tr key={share.share_id}>
                          <td>{leaseLabel(share.lease_id)}</td>
                          <td>{share.allocated_amount.toFixed(2)} €</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </>
            )}
            {isDraft && (
              <div className="settlement-period-details__position-actions">
                <button type="button" onClick={() => startEditing(position.position_id)}>
                  Bearbeiten
                </button>
                <button type="button" onClick={() => handleDelete(position.position_id)}>
                  Löschen
                </button>
              </div>
            )}
          </details>
        ),
      )}

      {positions && positions.length > 0 && (
        <p className="settlement-period-details__total">Summe Ist-Kosten: {totalActual.toFixed(2)} €</p>
      )}

      {isDraft && (
        <div className="settlement-period-details__actions">
          {!showCreateForm && editingPositionId === null && (
            <button type="button" onClick={() => setShowCreateForm(true)}>
              Neue Position
            </button>
          )}
          <button
            type="button"
            onClick={() => recalculateMutation.mutate()}
            disabled={recalculateMutation.isPending}
            title="Zieht Ist-Kosten aller Positionen frisch aus den Buchungen (z.B. nach nachträglichen Buchungen/Stornos)"
          >
            {recalculateMutation.isPending ? "Wird neu berechnet…" : "Neu berechnen"}
          </button>
        </div>
      )}
      {!isDraft && (
        <p className="settlement-period-details__locked">
          Abrechnung ist "{periodStatus}" - Positionen können nicht mehr geändert werden.
        </p>
      )}

      {showCreateForm && (
        <SettlementPositionForm
          propertyId={propertyId}
          onSubmit={handleCreate}
          onCancel={() => setShowCreateForm(false)}
          isSubmitting={createPositionMutation.isPending}
          error={formError}
        />
      )}
      <button
        type="button"
        onClick={() =>
          exportBatchMutation.mutate({
            settlementId,
            filename: `Abrechnungen_${fiscalYear}_Sammelversand.pdf`,
          })
        }
        disabled={exportBatchMutation.isPending}
      >
        {exportBatchMutation.isPending ? "Wird erstellt…" : "Alle als Sammel-PDF (Post)"}
      </button>
      <h4 className="settlement-period-details__summaries-heading">Ergebnis je Einheit (Eigentümer)</h4>
      {summariesLoading && <p>Lädt…</p>}
      {!summariesLoading && summaries?.length === 0 && (
        <p>Noch keine Ergebnisse - Positionen anlegen, um zu verteilen.</p>
      )}
      {summaries && summaries.length > 0 && (
        <table className="settlement-period-details__summary-table">
          <thead>
            <tr>
              <th>Einheit</th>
              <th>Ist-Kosten</th>
              <th>Vorauszahlungen</th>
              <th>Ergebnis</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {summaries.map((s) => (
              <tr key={s.summary_id}>
                <td>{unitLabelFor(s.unit_id)}</td>
                <td>{s.total_actual_costs.toFixed(2)} €</td>
                <td>{s.total_prepayments.toFixed(2)} €</td>
                <td
                  className={
                    s.balance > 0
                      ? "settlement-period-details__balance--due"
                      : "settlement-period-details__balance--refund"
                  }
                >
                  {s.balance > 0
                    ? `Nachzahlung: ${s.balance.toFixed(2)} €`
                    : `Erstattung: ${Math.abs(s.balance).toFixed(2)} €`}
                </td>
                <td>
                  <button type="button" onClick={() => handleExport(s.unit_id)} disabled={exportMutation.isPending}>
                    PDF
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h4 className="settlement-period-details__summaries-heading">Ergebnis je Mietvertrag</h4>
      <p className="settlement-period-details__lease-hint">
        Nur die umlagefähigen Kosten (mit demselben Verteilerschlüssel wie beim Eigentümer), taggenau auf die
        im Zeitraum aktiven Mietverträge verteilt. Als Vorauszahlung zählt ausschließlich, was getrennt als
        Nebenkostenvorauszahlung gebucht wurde (nicht die Kaltmiete).
      </p>
      {leaseSummariesLoading && <p>Lädt…</p>}
      {!leaseSummariesLoading && leaseSummaries?.length === 0 && (
        <p>Keine Einheit dieser Liegenschaft war im Abrechnungszeitraum vermietet.</p>
      )}
      {leaseSummaries && leaseSummaries.length > 0 && (
        <table className="settlement-period-details__summary-table">
          <thead>
            <tr>
              <th>Einheit</th>
              <th>Mieter</th>
              <th>Vertragszeitraum</th>
              <th>Ist-Kosten</th>
              <th>Vorauszahlung</th>
              <th>Ergebnis</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {leaseSummaries.map((s) => (
              <tr key={s.summary_id}>
                <td>{unitLabelFor(s.unit_id)}</td>
                <td>
                  {s.tenant_first_name} {s.tenant_last_name}
                </td>
                <td>{leasePeriodLabel(s)}</td>
                <td>{s.total_actual_costs.toFixed(2)} €</td>
                <td>{s.total_prepayments.toFixed(2)} €</td>
                <td
                  className={
                    s.balance > 0
                      ? "settlement-period-details__balance--due"
                      : "settlement-period-details__balance--refund"
                  }
                >
                  {s.balance > 0
                    ? `Nachzahlung: ${s.balance.toFixed(2)} €`
                    : `Erstattung: ${Math.abs(s.balance).toFixed(2)} €`}
                </td>
                <td>
                  <button
                    type="button"
                    onClick={() => handleLeaseExport(s.lease_id, unitLabelFor(s.unit_id), s.tenant_last_name)}
                    disabled={exportLeaseMutation.isPending}
                  >
                    PDF
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {leaseSummaries && leaseSummaries.length > 0 && (
        <button
          type="button"
          onClick={() =>
            exportTenantBatchMutation.mutate({
              settlementId,
              filename: `Betriebskostenabrechnungen_${fiscalYear}_Sammelversand.pdf`,
            })
          }
          disabled={exportTenantBatchMutation.isPending}
        >
          {exportTenantBatchMutation.isPending ? "Wird erstellt…" : "Alle Mieter als Sammel-PDF (Post)"}
        </button>
      )}
      {!leaseSummariesLoading && unitsWithoutLease.length > 0 && (
        <p className="settlement-period-details__lease-hint">
          Ohne Mietvertrag in diesem Zeitraum (Eigennutzung durch den Eigentümer oder Leerstand):{" "}
          {unitsWithoutLease.map((u) => u.unit_number).join(", ")}.
        </p>
      )}

      <ReserveFundPanel
        settlementId={settlementId}
        propertyId={propertyId}
        periodStatus={periodStatus}
        unitLabelFor={unitLabelFor}
      />
    </div>
  );
}