// frontend/src/features/meetings/MeetingsPage.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { Card } from "../../components/Card";
import { useProperties } from "../properties/useProperties";
import { AgendaItemsPanel } from "./AgendaItemsPanel";
import { downloadInvitation, downloadMinutes } from "./api";
import type { MeetingPayload, MeetingStatus } from "./api";
import { MeetingForm } from "./MeetingForm";
import { useCreateMeeting, useMeetings, useUpdateMeeting } from "./useMeetings";
import "./MeetingsPage.css";

const STATUS_LABELS: Record<MeetingStatus, string> = {
  Geplant: "Geplant",
  Eingeladen: "Eingeladen",
  Durchgeführt: "Durchgeführt",
  Protokolliert: "Protokolliert",
};

export function MeetingsPage() {
  const { data: properties, isLoading: propertiesLoading } = useProperties();
  const [propertyId, setPropertyId] = useState<number | "">("");
  const selectedPropertyId = propertyId === "" ? undefined : propertyId;

  const { data: meetings, isLoading, isError, error } = useMeetings(selectedPropertyId);
  const createMutation = useCreateMeeting(selectedPropertyId ?? -1);
  const updateMutation = useUpdateMeeting(selectedPropertyId ?? -1);

  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [minutesDraft, setMinutesDraft] = useState("");
  const [minutesError, setMinutesError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const isForbidden =
    isError &&
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    (error as { response?: { status?: number } }).response?.status === 403;

  function handleCreate(payload: MeetingPayload) {
    setFormError(null);
    createMutation.mutate(payload, {
      onSuccess: () => setCreating(false),
      onError: () => setFormError("Versammlung konnte nicht angelegt werden."),
    });
  }

  function toggleExpand(meetingId: number, currentMinutes: string | null) {
    if (expandedId === meetingId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(meetingId);
    setMinutesDraft(currentMinutes ?? "");
    setMinutesError(null);
  }

  function saveMinutes(event: FormEvent, meetingId: number) {
    event.preventDefault();
    setMinutesError(null);
    updateMutation.mutate(
      { meetingId, payload: { minutes_text: minutesDraft || null } },
      { onError: () => setMinutesError("Niederschriftstext konnte nicht gespeichert werden.") },
    );
  }

  async function handleInvitation(meetingId: number) {
    setDownloadError(null);
    try {
      await downloadInvitation(meetingId);
    } catch {
      setDownloadError("Einladung konnte nicht erzeugt werden - fehlt eventuell eine Tagesordnung?");
    }
  }

  async function handleMinutes(meetingId: number) {
    setDownloadError(null);
    try {
      await downloadMinutes(meetingId);
    } catch {
      setDownloadError("Niederschrift konnte nicht erzeugt werden.");
    }
  }

  return (
    <div className="meetings-page">
      <Card>
        <h1>Eigentümerversammlungen</h1>
        {propertiesLoading && <p>Lädt Liegenschaften…</p>}
        <label className="meetings-page__property-select">
          Liegenschaft
          <select
            value={propertyId}
            onChange={(e) => {
              setPropertyId(e.target.value ? Number(e.target.value) : "");
              setCreating(false);
              setExpandedId(null);
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

      {selectedPropertyId !== undefined && isForbidden && (
        <Card>
          <p>Kein Zugriff auf Versammlungen mit diesem Konto.</p>
        </Card>
      )}

      {selectedPropertyId !== undefined && !isForbidden && (
        <Card>
          <div className="meetings-page__header">
            <h2>Versammlungen</h2>
            {!creating && (
              <button type="button" onClick={() => setCreating(true)}>
                Neue Versammlung
              </button>
            )}
          </div>

          {isLoading && <p>Lädt…</p>}
          {!isLoading && meetings?.length === 0 && <p>Noch keine Versammlungen erfasst.</p>}
          {downloadError && <p className="meetings-page__error">{downloadError}</p>}

          <ul className="meetings-page__list">
            {meetings?.map((m) => (
              <li key={m.meeting_id} className="meetings-page__entry">
                <div className="meetings-page__entry-row">
                  <div>
                    <strong>{m.meeting_type}</strong> ·{" "}
                    {m.meeting_type === "Umlaufbeschluss" ? `Frist bis ${m.meeting_date}` : m.meeting_date}
                    {m.location && <> · {m.location}</>}{" "}
                    <span className={`meetings-page__status meetings-page__status--${m.status}`}>
                      {STATUS_LABELS[m.status]}
                    </span>
                  </div>
                  <div className="meetings-page__entry-actions">
                    <button type="button" onClick={() => handleInvitation(m.meeting_id)}>
                      Einladung (PDF)
                    </button>
                    <button type="button" onClick={() => handleMinutes(m.meeting_id)}>
                      Niederschrift (PDF)
                    </button>
                    <button type="button" onClick={() => toggleExpand(m.meeting_id, m.minutes_text)}>
                      {expandedId === m.meeting_id ? "Details ausblenden" : "Details"}
                    </button>
                  </div>
                </div>

                {expandedId === m.meeting_id && (
                  <div className="meetings-page__detail">
                    <AgendaItemsPanel meetingId={m.meeting_id} />

                    <form onSubmit={(e) => saveMinutes(e, m.meeting_id)} className="meetings-page__minutes-form">
                      <label>
                        Niederschriftstext (freier Vermerk, erscheint über der Beschlussliste)
                        <textarea
                          value={minutesDraft}
                          onChange={(e) => setMinutesDraft(e.target.value)}
                          rows={4}
                          placeholder="z.B. Anwesenheit, Beschlussfähigkeit, Ablauf…"
                        />
                      </label>
                      {minutesError && <p className="meetings-page__error">{minutesError}</p>}
                      <button type="submit" disabled={updateMutation.isPending}>
                        {updateMutation.isPending ? "Wird gespeichert…" : "Text speichern"}
                      </button>
                    </form>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {creating && selectedPropertyId !== undefined && (
        <Card>
          <h2>Neue Versammlung anlegen</h2>
          <MeetingForm
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