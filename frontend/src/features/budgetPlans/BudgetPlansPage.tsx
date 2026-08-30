// frontend/src/features/budgetPlans/BudgetPlansPage.tsx
import { useState } from "react";

import { Card } from "../../components/Card";
import { accountLabel } from "../accounts/format";
import { useAccounts } from "../accounts/useAccounts";
import { useProperties } from "../properties/useProperties";
import { useUnits } from "../units/useUnits";
import type { BudgetPlanPayload, BudgetPlanStatus, BudgetPositionPayload } from "./api";
import { BudgetPlanForm } from "./BudgetPlanForm";
import { BudgetPositionForm } from "./BudgetPositionForm";
import {
  useBudgetPlans,
  useBudgetPositions,
  useCreateBudgetPlan,
  useCreateBudgetPosition,
  useUpdateBudgetPlanStatus,
} from "./useBudgetPlans";
import "./BudgetPlansPage.css";

const NEXT_STATUS_LABEL: Record<BudgetPlanStatus, { next: BudgetPlanStatus; label: string }[]> = {
  Entwurf: [
    { next: "Beschlossen", label: "Beschließen" },
    { next: "Inaktiv", label: "Verwerfen" },
  ],
  Beschlossen: [{ next: "Inaktiv", label: "Deaktivieren" }],
  Inaktiv: [],
};

export function BudgetPlansPage() {
  const { data: properties, isLoading: propertiesLoading } = useProperties();
  const [propertyId, setPropertyId] = useState<number | "">("");
  const selectedPropertyId = propertyId === "" ? undefined : propertyId;

  const { data: plans, isLoading: plansLoading } = useBudgetPlans(selectedPropertyId);
  const { data: accounts } = useAccounts({ property_id: selectedPropertyId });
  const { data: units } = useUnits(selectedPropertyId);

  const createPlanMutation = useCreateBudgetPlan(selectedPropertyId ?? -1);
  const updateStatusMutation = useUpdateBudgetPlanStatus(selectedPropertyId ?? -1);

  const [creatingPlan, setCreatingPlan] = useState(false);
  const [planFormError, setPlanFormError] = useState<string | null>(null);
  const [expandedPlanId, setExpandedPlanId] = useState<number | null>(null);

  function handleCreatePlan(payload: BudgetPlanPayload) {
    setPlanFormError(null);
    createPlanMutation.mutate(payload, {
      onSuccess: () => setCreatingPlan(false),
      onError: () =>
        setPlanFormError("Wirtschaftsplan konnte nicht angelegt werden - Jahr eventuell schon vergeben."),
    });
  }

  function unitLabel(unitId: number): string {
    const unit = units?.find((u) => u.unit_id === unitId);
    return unit ? unit.unit_number : `#${unitId}`;
  }

  return (
    <div className="budget-plans-page">
      <Card>
        <h1>Wirtschaftspläne</h1>
        {propertiesLoading && <p>Lädt Liegenschaften…</p>}
        <label className="budget-plans-page__property-select">
          Liegenschaft
          <select
            value={propertyId}
            onChange={(e) => {
              setPropertyId(e.target.value ? Number(e.target.value) : "");
              setExpandedPlanId(null);
              setCreatingPlan(false);
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
          <div className="budget-plans-page__header">
            <h2>Pläne</h2>
            {!creatingPlan && (
              <button type="button" onClick={() => setCreatingPlan(true)}>
                Neuer Wirtschaftsplan
              </button>
            )}
          </div>

          {plansLoading && <p>Lädt…</p>}
          {!plansLoading && plans?.length === 0 && <p>Noch keine Wirtschaftspläne erfasst.</p>}

          <ul className="budget-plans-page__list">
            {plans?.map((plan) => (
              <li key={plan.budget_id} className="budget-plans-page__plan">
                <div className="budget-plans-page__plan-row">
                  <div>
                    <strong>{plan.fiscal_year}</strong> · {plan.title}{" "}
                    <span className={`budget-plans-page__status budget-plans-page__status--${plan.status}`}>
                      {plan.status}
                    </span>
                  </div>
                  <div className="budget-plans-page__plan-actions">
                    <button
                      type="button"
                      onClick={() => setExpandedPlanId(expandedPlanId === plan.budget_id ? null : plan.budget_id)}
                    >
                      {expandedPlanId === plan.budget_id ? "Positionen ausblenden" : "Positionen"}
                    </button>
                    {NEXT_STATUS_LABEL[plan.status].map(({ next, label }) => (
                      <button
                        key={next}
                        type="button"
                        onClick={() => {
                          if (
                            next === "Inaktiv" &&
                            !window.confirm(`Wirtschaftsplan ${plan.fiscal_year} wirklich auf "Inaktiv" setzen?`)
                          )
                            return;
                          updateStatusMutation.mutate({ budgetId: plan.budget_id, status: next });
                        }}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {expandedPlanId === plan.budget_id && (
                  <BudgetPlanPositions
                    budgetId={plan.budget_id}
                    propertyId={selectedPropertyId}
                    planStatus={plan.status}
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
      )}

      {creatingPlan && selectedPropertyId !== undefined && (
        <Card>
          <h2>Neuen Wirtschaftsplan anlegen</h2>
          <BudgetPlanForm
            propertyId={selectedPropertyId}
            onSubmit={handleCreatePlan}
            onCancel={() => setCreatingPlan(false)}
            isSubmitting={createPlanMutation.isPending}
            error={planFormError}
          />
        </Card>
      )}
    </div>
  );
}

interface BudgetPlanPositionsProps {
  budgetId: number;
  propertyId: number;
  planStatus: BudgetPlanStatus;
  accountLabelFor: (accountId: number) => string;
  unitLabelFor: (unitId: number) => string;
}

function BudgetPlanPositions({
  budgetId,
  propertyId,
  planStatus,
  accountLabelFor,
  unitLabelFor,
}: BudgetPlanPositionsProps) {
  const { data: positions, isLoading } = useBudgetPositions(budgetId);
  const createPositionMutation = useCreateBudgetPosition(budgetId);

  const [showForm, setShowForm] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function handleCreate(payload: BudgetPositionPayload) {
    setFormError(null);
    createPositionMutation.mutate(payload, {
      onSuccess: () => setShowForm(false),
      onError: () =>
        setFormError(
          "Position konnte nicht angelegt werden - Verteilerschlüssel eventuell für keine Einheit gültig.",
        ),
    });
  }

  const totalPlanned = positions?.reduce((sum, p) => sum + p.planned_amount, 0) ?? 0;

  return (
    <div className="budget-plan-positions">
      {isLoading && <p>Lädt Positionen…</p>}
      {!isLoading && positions?.length === 0 && <p>Noch keine Positionen erfasst.</p>}

      {positions?.map((position) => (
        <details key={position.position_id} className="budget-plan-positions__position">
          <summary>
            {accountLabelFor(position.account_id)} · {position.planned_amount.toFixed(2)} € ·{" "}
            {position.allocation_key_type}
          </summary>
          <table className="budget-plan-positions__shares-table">
            <thead>
              <tr>
                <th>Einheit</th>
                <th>Anteiliger Betrag</th>
                <th>Monatsrate</th>
              </tr>
            </thead>
            <tbody>
              {position.unit_shares.map((share) => (
                <tr key={share.share_id}>
                  <td>{unitLabelFor(share.unit_id)}</td>
                  <td>{share.allocated_planned_amount.toFixed(2)} €</td>
                  <td>{share.monthly_installment.toFixed(2)} €</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      ))}

      {positions && positions.length > 0 && (
        <p className="budget-plan-positions__total">Summe geplant: {totalPlanned.toFixed(2)} €</p>
      )}

      {planStatus === "Entwurf" && !showForm && (
        <button type="button" onClick={() => setShowForm(true)}>
          Neue Position
        </button>
      )}
      {planStatus !== "Entwurf" && (
        <p className="budget-plan-positions__locked">
          Plan ist "{planStatus}" - Positionen können nicht mehr geändert werden.
        </p>
      )}

      {showForm && (
        <BudgetPositionForm
          propertyId={propertyId}
          onSubmit={handleCreate}
          onCancel={() => setShowForm(false)}
          isSubmitting={createPositionMutation.isPending}
          error={formError}
        />
      )}
    </div>
  );
}