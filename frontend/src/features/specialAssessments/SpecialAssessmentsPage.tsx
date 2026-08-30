// frontend/src/features/specialAssessments/SpecialAssessmentsPage.tsx
import { useState } from "react";

import { Card } from "../../components/Card";
import { useProperties } from "../properties/useProperties";
import { useResolutions } from "../resolutions/useResolutions";
import { useUnits } from "../units/useUnits";
import type { SpecialAssessmentPayload, SpecialAssessmentStatus } from "./api";
import { SpecialAssessmentForm } from "./SpecialAssessmentForm";
import {
  useCreateSpecialAssessment,
  useSpecialAssessments,
  useUpdateSharePaymentStatus,
  useUpdateSpecialAssessmentStatus,
} from "./useSpecialAssessments";
import "./SpecialAssessmentsPage.css";

const NEXT_STATUS_LABEL: Record<SpecialAssessmentStatus, { next: SpecialAssessmentStatus; label: string }[]> = {
  Geplant: [
    { next: "Eingefordert", label: "Einfordern" },
    { next: "Storniert", label: "Stornieren" },
  ],
  Eingefordert: [{ next: "Storniert", label: "Stornieren" }],
  Storniert: [],
};

export function SpecialAssessmentsPage() {
  const { data: properties, isLoading: propertiesLoading } = useProperties();
  const [propertyId, setPropertyId] = useState<number | "">("");
  const selectedPropertyId = propertyId === "" ? undefined : propertyId;

  const { data: assessments, isLoading } = useSpecialAssessments(selectedPropertyId);
  const { data: units } = useUnits(selectedPropertyId);
  const { data: resolutions } = useResolutions(selectedPropertyId);

  const createMutation = useCreateSpecialAssessment(selectedPropertyId ?? -1);
  const updateStatusMutation = useUpdateSpecialAssessmentStatus(selectedPropertyId ?? -1);
  const updateShareMutation = useUpdateSharePaymentStatus(selectedPropertyId ?? -1);

  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  function unitLabel(unitId: number): string {
    const unit = units?.find((u) => u.unit_id === unitId);
    return unit ? unit.unit_number : `#${unitId}`;
  }

  function resolutionLabel(resolutionId: number | null): string | null {
    if (resolutionId == null) return null;
    const r = resolutions?.find((x) => x.resolution_id === resolutionId);
    return r ? `Lfd. Nr. ${r.lfd_nr} – ${r.title}` : `Beschluss #${resolutionId}`;
  }

  function handleCreate(payload: SpecialAssessmentPayload) {
    setFormError(null);
    createMutation.mutate(payload, {
      onSuccess: () => setCreating(false),
      onError: () =>
        setFormError("Sonderumlage konnte nicht angelegt werden - Verteilerschlüssel eventuell ungültig."),
    });
  }

  return (
    <div className="special-assessments-page">
      <Card>
        <h1>Sonderumlagen</h1>
        {propertiesLoading && <p>Lädt Liegenschaften…</p>}
        <label className="special-assessments-page__property-select">
          Liegenschaft
          <select
            value={propertyId}
            onChange={(e) => {
              setPropertyId(e.target.value ? Number(e.target.value) : "");
              setExpandedId(null);
              setCreating(false);
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
          <div className="special-assessments-page__header">
            <h2>Sonderumlagen</h2>
            {!creating && (
              <button type="button" onClick={() => setCreating(true)}>
                Neue Sonderumlage
              </button>
            )}
          </div>

          {isLoading && <p>Lädt…</p>}
          {!isLoading && assessments?.length === 0 && <p>Noch keine Sonderumlagen erfasst.</p>}

          <ul className="special-assessments-page__list">
            {assessments?.map((a) => (
              <li key={a.assessment_id} className="special-assessments-page__entry">
                <div className="special-assessments-page__entry-row">
                  <div>
                    <strong>{a.title}</strong> · {a.total_required_amount.toFixed(2)} € · fällig {a.due_date}{" "}
                    <span className={`special-assessments-page__status special-assessments-page__status--${a.status}`}>
                      {a.status}
                    </span>
                    {resolutionLabel(a.resolution_id) && (
                      <div className="special-assessments-page__resolution">
                        Beschluss: {resolutionLabel(a.resolution_id)}
                      </div>
                    )}
                  </div>
                  <div className="special-assessments-page__entry-actions">
                    <button type="button" onClick={() => setExpandedId(expandedId === a.assessment_id ? null : a.assessment_id)}>
                      {expandedId === a.assessment_id ? "Details ausblenden" : "Details"}
                    </button>
                    {NEXT_STATUS_LABEL[a.status].map(({ next, label }) => (
                      <button
                        key={next}
                        type="button"
                        onClick={() => {
                          if (next === "Storniert" && !window.confirm("Sonderumlage wirklich stornieren?")) return;
                          updateStatusMutation.mutate({ assessmentId: a.assessment_id, status: next });
                        }}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {expandedId === a.assessment_id && (
                  <table className="special-assessments-page__shares-table">
                    <thead>
                      <tr>
                        <th>Einheit</th>
                        <th>Betrag</th>
                        <th>Bezahlt</th>
                      </tr>
                    </thead>
                    <tbody>
                      {a.unit_shares.map((share) => (
                        <tr key={share.unit_assessment_id}>
                          <td>{unitLabel(share.unit_id)}</td>
                          <td>{share.allocated_assessment_amount.toFixed(2)} €</td>
                          <td>
                            <input
                              type="checkbox"
                              checked={share.is_paid}
                              onChange={(e) =>
                                updateShareMutation.mutate({
                                  assessmentId: a.assessment_id,
                                  unitAssessmentId: share.unit_assessment_id,
                                  isPaid: e.target.checked,
                                })
                              }
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {creating && selectedPropertyId !== undefined && (
        <Card>
          <h2>Neue Sonderumlage anlegen</h2>
          <SpecialAssessmentForm
            propertyId={selectedPropertyId}
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