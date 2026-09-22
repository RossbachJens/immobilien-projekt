// frontend/src/features/meetings/MeetingsPage.tsx
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import { Card } from "../../components/Card";
import { useCurrentProperty } from "../../context/PropertyContext";
import { AgendaItemsPanel } from "./AgendaItemsPanel";
import { downloadInvitation, downloadInvitationBatch, downloadMinutes } from "./api";
import type { Meeting, MeetingPayload, MeetingStatus } from "./api";
import { MeetingForm } from "./MeetingForm";
import { useCreateMeeting, useMeetings, useUpdateMeeting } from "./useMeetings";
import "./MeetingsPage.css";

const STATUS_LABELS: Record<MeetingStatus, string> = {
  Geplant: "Geplant",
  Eingeladen: "Eingeladen",
  Durchgeführt: "Durchgeführt",
  Protokolliert: "Protokolliert",
};

type QuorumDraft = "" | "true" | "false";

export function MeetingsPage() {
  const { propertyId, property, properties, isLoading: propertiesLoading } = useCurrentProperty();

  const { data: meetings, isLoading, isError, error } = useMeetings(propertyId ?? undefined);
  const createMutation = useCreateMeeting(propertyId ?? -1);
  const updateMutation = useUpdateMeeting(propertyId ?? -1);

  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const [minutesDraft, setMinutesDraft] = useState("");
  const [chairpersonDraft, setChairpersonDraft] = useState("");
  const [minuteTakerDraft, setMinuteTakerDraft] = useState("");
  const [endTimeDraft, setEndTimeDraft] = useState("");
  const [representedSharesDraft, setRepresentedSharesDraft] = useState("");
  const [quorumMetDraft, setQuorumMetDraft] = useState<QuorumDraft>("");
  const [votingKeyDraft, setVotingKeyDraft] = useState("");
  const [minutesError, setMinutesError] = useState<string | null>(null);

  useEffect(() => {
    setCreating(false);
    setExpandedId(null);
    setFormError(null);
    setDownloadError(null);
  }, [propertyId]);

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

  function toggleExpand(meeting: Meeting) {
    if (expandedId === meeting.meeting_id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(meeting.meeting_id);
    setMinutesDraft(meeting.minutes_text ?? "");
    setChairpersonDraft(meeting.chairperson ?? "");
    setMinuteTakerDraft(meeting.minute_taker ?? "");
    setEndTimeDraft(meeting.end_time ? meeting.end_time.slice(0, 5) : "");
    setRepresentedSharesDraft(meeting.represented_shares != null ? String(meeting.represented_shares) : "");
    setQuorumMetDraft(meeting.quorum_met == null ? "" : meeting.quorum_met ? "true" : "false");
    setVotingKeyDraft(meeting.voting_key ?? "");
    setMinutesError(null);
  }

  function saveNiederschrift(event: FormEvent, meetingId: number) {
    event.preventDefault();
    setMinutesError(null);
    updateMutation.mutate(
      {
        meetingId,
        payload: {
          minutes_text: minutesDraft || null,
          chairperson: chairpersonDraft || null,
          minute_taker: minuteTakerDraft || null,
          end_time: endTimeDraft || null,
          represented_shares: representedSharesDraft ? Number(representedSharesDraft) : null,
          quorum_met: quorumMetDraft === "" ? null : quorumMetDraft === "true",
          voting_key: votingKeyDraft || null,
        },
      },
      { onError: () => setMinutesError("Niederschrift konnte nicht gespeichert werden.") },
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

  async function handleInvitationBatch(meetingId: number) {
    setDownloadError(null);
    try {
      await downloadInvitationBatch(meetingId);
    } catch {
      setDownloadError(
        "Einladung (Sammelversand) konnte nicht erzeugt werden - fehlt eventuell eine Tagesordnung " +
          "oder ein aktuell zugeordneter Eigentümer?",
      );
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

  if (propertiesLoading) {
    return (
      <div className="meetings-page">
        <Card>
          <p>Lädt Liegenschaften…</p>
        </Card>
      </div>
    );
  }

  if (propertyId == null || properties.length === 0) {
    return (
      <div className="meetings-page">
        <Card>
          <h1>Eigentümerversammlungen</h1>
          <p>Bitte zuerst links in der Sidebar eine Liegenschaft auswählen.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="meetings-page">
      <Card>
        <h1>Eigentümerversammlungen – {property?.name}</h1>
      </Card>

      {isForbidden && (
        <Card>
          <p>Kein Zugriff auf Versammlungen mit diesem Konto.</p>
        </Card>
      )}

      {!isForbidden && (
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
                    <button type="button" onClick={() => handleInvitationBatch(m.meeting_id)}>
                      Einladung Sammelversand (Post)
                    </button>
                    <button type="button" onClick={() => handleMinutes(m.meeting_id)}>
                      Niederschrift (PDF)
                    </button>
                    <Link to={`/documents?meeting_id=${m.meeting_id}`} className="meetings-page__archive-link">
                      Archivierte PDFs
                    </Link>
                    <button type="button" onClick={() => toggleExpand(m)}>
                      {expandedId === m.meeting_id ? "Details ausblenden" : "Details"}
                    </button>
                  </div>
                </div>

                {expandedId === m.meeting_id && (
                  <div className="meetings-page__detail">
                    <AgendaItemsPanel meetingId={m.meeting_id} />

                    <form
                      onSubmit={(e) => saveNiederschrift(e, m.meeting_id)}
                      className="meetings-page__minutes-form"
                    >
                      <h4>Niederschrift – Kopfdaten</h4>
                      {m.meeting_type !== "Umlaufbeschluss" && (
                        <>
                          <label>
                            Versammlungsleiter
                            <input
                              value={chairpersonDraft}
                              onChange={(e) => setChairpersonDraft(e.target.value)}
                            />
                          </label>
                          <label>
                            Protokollführer
                            <input
                              value={minuteTakerDraft}
                              onChange={(e) => setMinuteTakerDraft(e.target.value)}
                            />
                          </label>
                          <label>
                            Ende
                            <input
                              type="time"
                              value={endTimeDraft}
                              onChange={(e) => setEndTimeDraft(e.target.value)}
                            />
                          </label>
                        </>
                      )}
                      <label>
                        Vertretene Miteigentumsanteile
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={representedSharesDraft}
                          onChange={(e) => setRepresentedSharesDraft(e.target.value)}
                        />
                      </label>
                      <label>
                        Beschlussfähigkeit
                        <select
                          value={quorumMetDraft}
                          onChange={(e) => setQuorumMetDraft(e.target.value as QuorumDraft)}
                        >
                          <option value="">– keine Angabe –</option>
                          <option value="true">ja</option>
                          <option value="false">nein</option>
                        </select>
                      </label>
                      <label>
                        Abstimmungsschlüssel
                        <input
                          value={votingKeyDraft}
                          onChange={(e) => setVotingKeyDraft(e.target.value)}
                          placeholder="z.B. Miteigentumsanteile"
                        />
                      </label>
                      <label>
                        Niederschriftstext (freier Vermerk, erscheint über der Tagesordnung)
                        <textarea
                          value={minutesDraft}
                          onChange={(e) => setMinutesDraft(e.target.value)}
                          rows={4}
                          placeholder="z.B. Begrüßung, Feststellung der ordentlichen Ladung…"
                        />
                      </label>
                      {minutesError && <p className="meetings-page__error">{minutesError}</p>}
                      <button type="submit" disabled={updateMutation.isPending}>
                        {updateMutation.isPending ? "Wird gespeichert…" : "Niederschrift speichern"}
                      </button>
                    </form>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {creating && (
        <Card>
          <h2>Neue Versammlung anlegen</h2>
          <MeetingForm
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