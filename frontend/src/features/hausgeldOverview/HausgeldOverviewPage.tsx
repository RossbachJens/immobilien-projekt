// frontend/src/features/hausgeldOverview/HausgeldOverviewPage.tsx
import { Fragment, useState } from "react";

import { Card } from "../../components/Card";
import { useOwners } from "../owners/useOwners";
import { useProperties } from "../properties/useProperties";
import { useHausgeldOverview, useHausgeldPayments } from "./useHausgeldOverview";
import "./HausgeldOverviewPage.css";

function currentYear(): number {
  return new Date().getFullYear();
}

export function HausgeldOverviewPage() {
  const { data: properties, isLoading: propertiesLoading } = useProperties();
  const { data: owners } = useOwners();
  const [propertyId, setPropertyId] = useState<number | "">("");
  const [fiscalYear, setFiscalYear] = useState(String(currentYear()));
  const [expandedUnitId, setExpandedUnitId] = useState<number | null>(null);

  const selectedPropertyId = propertyId === "" ? undefined : propertyId;
  const selectedFiscalYear = Number(fiscalYear) || undefined;

  const { data: overview, isLoading, isError, error } = useHausgeldOverview(
    selectedPropertyId,
    selectedFiscalYear,
  );

  const isForbidden =
    isError &&
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    (error as { response?: { status?: number } }).response?.status === 403;

  function ownerLabel(ownerId: number | null): string {
    if (ownerId == null) return "– kein Eigentümer zugeordnet –";
    const owner = owners?.find((o) => o.owner_id === ownerId);
    if (!owner) return `Eigentümer #${ownerId}`;
    return owner.company_name ?? `${owner.first_name ?? ""} ${owner.last_name}`.trim();
  }

  const totalTarget = overview?.reduce((sum, u) => sum + u.target_amount, 0) ?? 0;
  const totalPaid = overview?.reduce((sum, u) => sum + u.paid_amount, 0) ?? 0;
  const totalBalance = overview?.reduce((sum, u) => sum + u.balance, 0) ?? 0;

  return (
    <div className="hausgeld-overview-page">
      <Card>
        <h1>Hausgeldübersicht</h1>
        <p className="hausgeld-overview-page__hint">
          Soll (aus dem beschlossenen Wirtschaftsplan) vs. Ist (Zahlungseingänge) je Einheit, kumuliert bis
          zum laufenden Monat des gewählten Jahres.
        </p>
        {propertiesLoading && <p>Lädt Liegenschaften…</p>}
        <div className="hausgeld-overview-page__filters">
          <label>
            Liegenschaft
            <select
              value={propertyId}
              onChange={(e) => {
                setPropertyId(e.target.value ? Number(e.target.value) : "");
                setExpandedUnitId(null);
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
          <label>
            Jahr
            <input
              type="number"
              value={fiscalYear}
              onChange={(e) => {
                setFiscalYear(e.target.value);
                setExpandedUnitId(null);
              }}
            />
          </label>
        </div>
      </Card>

      {selectedPropertyId !== undefined && isForbidden && (
        <Card>
          <p>Kein Zugriff auf die Hausgeldübersicht mit diesem Konto.</p>
        </Card>
      )}

      {selectedPropertyId !== undefined && !isForbidden && (
        <Card>
          {isLoading && <p>Lädt…</p>}
          {!isLoading && overview?.length === 0 && <p>Keine Einheiten in dieser Liegenschaft.</p>}
          {!isLoading && overview && overview.length > 0 && !overview[0].has_budget_plan && (
            <p className="hausgeld-overview-page__no-plan">
              Kein beschlossener Wirtschaftsplan für {fiscalYear} – Soll-Beträge sind 0,00 €.
            </p>
          )}

          {overview && overview.length > 0 && (
            <table className="hausgeld-overview-page__table">
              <thead>
                <tr>
                  <th>Einheit</th>
                  <th>Eigentümer</th>
                  <th>Monatssoll</th>
                  <th>Soll (bis heute)</th>
                  <th>Ist</th>
                  <th>Saldo</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {overview.map((u) => (
                  <Fragment key={u.unit_id}>
                    <tr>
                      <td>{u.unit_number}</td>
                      <td>{ownerLabel(u.owner_id)}</td>
                      <td>{u.monthly_target.toFixed(2)} €</td>
                      <td>{u.target_amount.toFixed(2)} €</td>
                      <td>{u.paid_amount.toFixed(2)} €</td>
                      <td
                        className={
                          u.balance > 0
                            ? "hausgeld-overview-page__balance--due"
                            : u.balance < 0
                              ? "hausgeld-overview-page__balance--credit"
                              : undefined
                        }
                      >
                        {u.balance > 0
                          ? `${u.balance.toFixed(2)} € Rückstand`
                          : u.balance < 0
                            ? `${Math.abs(u.balance).toFixed(2)} € Guthaben`
                            : "0,00 €"}
                      </td>
                      <td>
                        <button
                          type="button"
                          onClick={() => setExpandedUnitId(expandedUnitId === u.unit_id ? null : u.unit_id)}
                        >
                          {expandedUnitId === u.unit_id ? "Zahlungen ausblenden" : "Zahlungen"}
                        </button>
                      </td>
                    </tr>
                    {expandedUnitId === u.unit_id && (
                      <tr>
                        <td colSpan={7}>
                          <UnitPaymentsList
                            propertyId={selectedPropertyId}
                            unitId={u.unit_id}
                            fiscalYear={selectedFiscalYear as number}
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={3}>Summe</td>
                  <td>{totalTarget.toFixed(2)} €</td>
                  <td>{totalPaid.toFixed(2)} €</td>
                  <td>{totalBalance.toFixed(2)} €</td>
                  <td />
                </tr>
              </tfoot>
            </table>
          )}
        </Card>
      )}
    </div>
  );
}

interface UnitPaymentsListProps {
  propertyId: number;
  unitId: number;
  fiscalYear: number;
}

function UnitPaymentsList({ propertyId, unitId, fiscalYear }: UnitPaymentsListProps) {
  const { data: payments, isLoading } = useHausgeldPayments(propertyId, unitId, fiscalYear);

  if (isLoading) return <p>Lädt Zahlungen…</p>;
  if (!payments || payments.length === 0) return <p>Keine Zahlungen in diesem Zeitraum.</p>;

  return (
    <table className="hausgeld-overview-page__payments-table">
      <thead>
        <tr>
          <th>Datum</th>
          <th>Betrag</th>
          <th>Beleg-Nr.</th>
        </tr>
      </thead>
      <tbody>
        {payments.map((p) => (
          <tr key={p.entry_id}>
            <td>{p.entry_date}</td>
            <td>{p.amount.toFixed(2)} €</td>
            <td>{p.document_reference ?? "–"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}