// frontend/src/features/resolutions/ResolutionForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { Resolution, ResolutionPayload } from "./api";
// frontend/src/features/resolutions/ResolutionForm.tsx — Props + Feld ergänzen
import type { Meeting } from "../meetings/api";
import "./ResolutionForm.css";

interface ResolutionFormProps {
  propertyId: number;
  meetings?: Meeting[];   // NEU
  referencedResolution?: Resolution;
  submitLabel: string;
  onSubmit: (payload: ResolutionPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

const MEETING_TYPES = [
  "ordentliche Eigentümerversammlung",
  "außerordentliche Eigentümerversammlung",
  "Umlaufbeschluss",
];

const STATUS_SUGGESTIONS = [
  "angenommen",
  "abgelehnt",
  "bestandskräftig",
  "aufgehoben",
  "gelöscht",
  "bedeutungslos",
  "rechtskräftig",
];

export function ResolutionForm({
  propertyId,
  meetings,
  referencedResolution,
  submitLabel,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: ResolutionFormProps) {
  const isFollowUp = referencedResolution !== undefined;

  const [resolutionDate, setResolutionDate] = useState(todayIso());
  const [title, setTitle] = useState(
    isFollowUp ? `Update zu „${referencedResolution.title}“` : "",
  );
  const [resolutionType, setResolutionType] = useState("");
  const [meetingLocation, setMeetingLocation] = useState("");
  const [agendaItem, setAgendaItem] = useState("");
  const [description, setDescription] = useState("");
  const [statusNote, setStatusNote] = useState("");
  const [showCourtFields, setShowCourtFields] = useState(isFollowUp);
  const [courtName, setCourtName] = useState("");
  const [courtCaseNumber, setCourtCaseNumber] = useState("");
  const [courtDecisionDate, setCourtDecisionDate] = useState("");
  const [courtRulingText, setCourtRulingText] = useState("");
  const [courtParties, setCourtParties] = useState("");
    const [meetingId, setMeetingId] = useState<number | "">("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      property_id: propertyId,
      resolution_date: resolutionDate,
      title,
      description: description || null,
      resolution_type: resolutionType || null,
      meeting_location: meetingLocation || null,
      agenda_item: agendaItem || null,
      status_note: statusNote || null,
      court_name: showCourtFields ? courtName || null : null,
      court_case_number: showCourtFields ? courtCaseNumber || null : null,
      court_decision_date: showCourtFields ? courtDecisionDate || null : null,
      court_ruling_text: showCourtFields ? courtRulingText || null : null,
      court_parties: showCourtFields ? courtParties || null : null,
      refers_to_resolution_id: referencedResolution?.resolution_id ?? null,
      meeting_id: meetingId !== "" ? meetingId : null,  // NEU
    });
  }
  

  return (
    <form onSubmit={handleSubmit} className="resolution-form">
            {meetings && meetings.length > 0 && (
        <label>
          Zugehörige Versammlung
          <select value={meetingId} onChange={(e) => setMeetingId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">– keine –</option>
            {meetings.map((m) => (
              <option key={m.meeting_id} value={m.meeting_id}>
                {m.meeting_type} – {m.meeting_date}
              </option>
            ))}
          </select>
        </label>
      )}
      {isFollowUp && (
        <p className="resolution-form__reference">
          Folgeeintrag zu lfd. Nr. {referencedResolution.lfd_nr} – „{referencedResolution.title}“
        </p>
      )}

      <label>
        Datum * {isFollowUp && "(Eintragung/Verkündung)"}
        <input type="date" value={resolutionDate} onChange={(e) => setResolutionDate(e.target.value)} required />
      </label>
      <label>
        Titel *
        <input value={title} onChange={(e) => setTitle(e.target.value)} required />
      </label>

      {!isFollowUp && (
        <>
          <label>
            Art
            <select value={resolutionType} onChange={(e) => setResolutionType(e.target.value)}>
              <option value="">– keine Angabe –</option>
              {MEETING_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ort
            <input
              value={meetingLocation}
              onChange={(e) => setMeetingLocation(e.target.value)}
              placeholder="z.B. Schildergasse 101a, 50667 Köln"
            />
          </label>
          <label>
            TOP (Tagesordnungspunkt)
            <input value={agendaItem} onChange={(e) => setAgendaItem(e.target.value)} placeholder="z.B. TOP 4" />
          </label>
          <label>
            Beschlusswortlaut
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} />
          </label>
        </>
      )}

      <label>
        Vermerke
        <input
          value={statusNote}
          onChange={(e) => setStatusNote(e.target.value)}
          placeholder="z.B. angenommen"
          list="resolution-status-suggestions"
        />
      </label>
      <datalist id="resolution-status-suggestions">
        {STATUS_SUGGESTIONS.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>

      {!isFollowUp && !showCourtFields && (
        <button type="button" className="resolution-form__toggle-court" onClick={() => setShowCourtFields(true)}>
          + Gerichtsentscheidung erfassen
        </button>
      )}

      {showCourtFields && (
        <fieldset className="resolution-form__court">
          <legend>Gerichtsentscheidung</legend>
          <label>
            Gericht
            <input value={courtName} onChange={(e) => setCourtName(e.target.value)} placeholder="z.B. AG Köln" />
          </label>
          <label>
            Aktenzeichen (Az.)
            <input value={courtCaseNumber} onChange={(e) => setCourtCaseNumber(e.target.value)} />
          </label>
          <label>
            Datum der Entscheidung
            <input type="date" value={courtDecisionDate} onChange={(e) => setCourtDecisionDate(e.target.value)} />
          </label>
          <label>
            Parteien
            <input
              value={courtParties}
              onChange={(e) => setCourtParties(e.target.value)}
              placeholder='z.B. W. ./. WEG "..."'
            />
          </label>
          <label>
            Tenor
            <textarea value={courtRulingText} onChange={(e) => setCourtRulingText(e.target.value)} rows={3} />
          </label>
          {!isFollowUp && (
            <button type="button" onClick={() => setShowCourtFields(false)}>
              Gerichtsentscheidung entfernen
            </button>
          )}
        </fieldset>
      )}

      {error && <p className="resolution-form__error">{error}</p>}

      <div className="resolution-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird gespeichert…" : submitLabel}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}