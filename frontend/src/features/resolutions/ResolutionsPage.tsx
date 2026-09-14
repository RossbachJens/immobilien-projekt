// frontend/src/features/resolutions/ResolutionsPage.tsx
import { useEffect, useState } from "react";

import { Card } from "../../components/Card";
import { useCurrentProperty } from "../../context/PropertyContext";
import { useMeetings } from "../meetings/useMeetings";
import type { ResolutionPayload } from "./api";
import { ResolutionForm } from "./ResolutionForm";
import { useCreateResolution, useResolutions } from "./useResolutions";
import "./ResolutionsPage.css";

const RESOLUTION_TYPE_LABELS: Record<string, string> = {
  Eigentuemerversammlung: "Eigentümerversammlung",
  "ordentliche Eigentümerversammlung": "ordentliche Eigentümerversammlung",
  "außerordentliche Eigentümerversammlung": "außerordentliche Eigentümerversammlung",
  Umlaufbeschluss: "Umlaufbeschluss",
};

export function ResolutionsPage() {
  const { propertyId, property, properties, isLoading: propertiesLoading } = useCurrentProperty();

  const { data: resolutions, isLoading, isError, error } = useResolutions(propertyId ?? undefined);
  const { data: meetings } = useMeetings(propertyId ?? undefined);
  const createMutation = useCreateResolution(propertyId ?? -1);

  // number = resolution_id, zu dem ein Folgeeintrag erfasst wird.
  const [mode, setMode] = useState<"idle" | "creating" | number>("idle");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    setMode("idle");
    setFormError(null);
  }, [propertyId]);

  const isForbidden =
    isError &&
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    (error as { response?: { status?: number } }).response?.status === 403;

  const followUpTarget = typeof mode === "number" ? resolutions?.find((r) => r.resolution_id === mode) : undefined;

  function meetingLabel(meetingId: number | null): string | null {
    if (meetingId == null) return null;
    const m = meetings?.find((x) => x.meeting_id === meetingId);
    return m ? `${m.meeting_type} – ${m.meeting_date}` : `Versammlung #${meetingId}`;
  }

  function handleCreate(payload: ResolutionPayload) {
    setFormError(null);
    createMutation.mutate(payload, {
      onSuccess: () => setMode("idle"),
      onError: () => setFormError("Eintrag konnte nicht angelegt werden."),
    });
  }

  if (propertiesLoading) {
    return (
      <div className="resolutions-page">
        <Card>
          <p>Lädt Liegenschaften…</p>
        </Card>
      </div>
    );
  }

  if (propertyId == null || properties.length === 0) {
    return (
      <div className="resolutions-page">
        <Card>
          <h1>Beschluss-Sammlung</h1>
          <p>Bitte zuerst links in der Sidebar eine Liegenschaft auswählen.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="resolutions-page">
      <Card>
        <h1>Beschluss-Sammlung – {property?.name}</h1>
        <p className="resolutions-page__hint">
          Gesetzlich vorgeschriebene Dokumentation nach § 24 WEG. Einträge werden nicht bearbeitet
          oder gelöscht — spätere Entwicklungen (z.B. eine Gerichtsentscheidung) werden als
          Folgeeintrag erfasst.
        </p>
      </Card>

      {isForbidden && (
        <Card>
          <p>Kein Zugriff auf die Beschluss-Sammlung mit diesem Konto.</p>
        </Card>
      )}

      {!isForbidden && (
        <Card>
          <div className="resolutions-page__header">
            <h2>Beschlüsse</h2>
            {mode === "idle" && (
              <button type="button" onClick={() => setMode("creating")}>
                Neuer Beschluss
              </button>
            )}
          </div>

          {isLoading && <p>Lädt…</p>}
          {!isLoading && resolutions?.length === 0 && <p>Noch keine Beschlüsse erfasst.</p>}

          <ul className="resolutions-page__list">
            {resolutions?.map((r) => {
              const referenced =
                r.refers_to_resolution_id != null
                  ? resolutions.find((x) => x.resolution_id === r.refers_to_resolution_id)
                  : undefined;

              return (
                <li key={r.resolution_id} className="resolutions-page__entry">
                  <div className="resolutions-page__entry-header">
                    <span className="resolutions-page__lfd-nr">Lfd. Nr. {r.lfd_nr}</span>
                    <strong>{r.resolution_date}</strong>
                    <span>{r.title}</span>
                  </div>

                  {referenced && (
                    <p className="resolutions-page__ref">
                      → Folgeeintrag zu lfd. Nr. {referenced.lfd_nr} („{referenced.title}“)
                    </p>
                  )}

                  {(r.resolution_type || r.meeting_location || r.agenda_item) && (
                    <p className="resolutions-page__meeting">
                      {r.resolution_type && (RESOLUTION_TYPE_LABELS[r.resolution_type] ?? r.resolution_type)}
                      {r.meeting_location && <> · {r.meeting_location}</>}
                      {r.agenda_item && <> · {r.agenda_item}</>}
                    </p>
                  )}

                  {meetingLabel(r.meeting_id) && (
                    <p className="resolutions-page__meeting">Versammlung: {meetingLabel(r.meeting_id)}</p>
                  )}
                  {(r.votes_yes != null || r.votes_no != null || r.votes_abstain != null) && (
                    <p className="resolutions-page__votes">
                      Abstimmung: JA {r.votes_yes ?? "–"} · NEIN {r.votes_no ?? "–"} · Enthaltungen {r.votes_abstain ?? "–"}
                    </p>
                  )}
                  {r.description && <p className="resolutions-page__description">{r.description}</p>}

                  {r.status_note && <p className="resolutions-page__status">Vermerke: {r.status_note}</p>}

                  {(r.court_name || r.court_case_number || r.court_ruling_text) && (
                    <div className="resolutions-page__court">
                      <strong>Gerichtsentscheidung</strong>
                      <p>
                        {r.court_name}
                        {r.court_case_number && <> · Az. {r.court_case_number}</>}
                        {r.court_decision_date && <> · {r.court_decision_date}</>}
                      </p>
                      {r.court_parties && <p>{r.court_parties}</p>}
                      {r.court_ruling_text && <p>{r.court_ruling_text}</p>}
                    </div>
                  )}

                  <button type="button" onClick={() => setMode(r.resolution_id)}>
                    Folgeeintrag hinzufügen
                  </button>
                </li>
              );
            })}
          </ul>
        </Card>
      )}

      {(mode === "creating" || typeof mode === "number") && (
        <Card>
          <h2>{typeof mode === "number" ? "Folgeeintrag erfassen" : "Neuen Beschluss erfassen"}</h2>
          <ResolutionForm
            propertyId={propertyId}
            meetings={meetings}
            referencedResolution={followUpTarget}
            submitLabel={typeof mode === "number" ? "Folgeeintrag anlegen" : "Anlegen"}
            onSubmit={handleCreate}
            onCancel={() => setMode("idle")}
            isSubmitting={createMutation.isPending}
            error={formError}
          />
        </Card>
      )}
    </div>
  );
}