// frontend/src/features/resolutions/ResolutionForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { Meeting } from "../meetings/api";
import { useAgendaItems } from "../meetings/useMeetings";
import type { Resolution, ResolutionPayload } from "./api";
import "./ResolutionForm.css";

interface ResolutionFormProps {
  propertyId: number;
  meetings?: Meeting[];
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
  "einstimmig angenommen",
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
  const [agendaItemId, setAgendaItemId] = useState<number | "">("");
  const [votesYes, setVotesYes] = useState("");
  const [votesNo, setVotesNo] = useState("");
  const [votesAbstain, setVotesAbstain] = useState("");

  const { data: agendaItems } = useAgendaItems(meetingId !== "" ? meetingId : undefined);

  function handleMeetingChange(value: number | "") {
    setMeetingId(value);
    setAgendaItemId("");
  }

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
      meeting_id: meetingId !== "" ? meetingId : null,
      agenda_item_id: !isFollowUp && agendaItemId !== "" ? agendaItemId : null,
      votes_yes: !isFollowUp && votesYes !== "" ? Number(votesYes) : null,
      votes_no: !isFollowUp && votesNo !== "" ? Number(votesNo) : null,
      votes_abstain: !isFollowUp && votesAbstain !== "" ? Number(votesAbstain) : null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="resolution-form">
      {meetings && meetings.length > 0 && (
        <label>
          Zugehörige Versammlung
          <select
            value={meetingId}
            onChange={(e) => handleMeetingChange(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">– keine –</option>
            {meetings.map((m) => (
              <option key={m.meeting_id} value={m.meeting_id}>
                {m.meeting_type} – {m.meeting_date}
              </option>
            ))}
          </select>
        </label>
      )}

      {!isFollowUp && meetingId !== "" && agendaItems && agendaItems.length > 0 && (
        <label>
          Tagesordnungspunkt
          <select
            value={agendaItemId}
            onChange={(e) => setAgendaItemId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">– kein TOP zugeordnet –</option>
            {agendaItems.map((item) => (
              <option key={item.item_id} value={item.item_id}>
                TOP {item.position} – {item.title}
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
            TOP (Tagesordnungspunkt, Freitext)
            <input value={agendaItem} onChange={(e) => setAgendaItem(e.target.value)} placeholder="z.B. TOP 4" />
          </label>
          <label>
            Beschlusswortlaut
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} />
          </label>

          <fieldset className="resolution-form__votes">
            <legend>Abstimmungsergebnis (optional)</legend>
            <label>
              JA-Stimmen
              <input
                type="number"
                min="0"
                step="0.01"
                value={votesYes}
                onChange={(e) => setVotesYes(e.target.value)}
              />
            </label>
            <label>
              NEIN-Stimmen
              <input
                type="number"
                min="0"
                step="0.01"
                value={votesNo}
                onChange={(e) => setVotesNo(e.target.value)}
              />
            </label>
            <label>
              Enthaltungen
              <input
                type="number"
                min="0"
                step="0.01"
                value={votesAbstain}
                onChange={(e) => setVotesAbstain(e.target.value)}
              />
            </label>
          </fieldset>
        </>
      )}

      <label>
        Vermerke (Beschlussstatus)
        <input
          value={statusNote}
          onChange={(e) => setStatusNote(e.target.value)}
          placeholder="z.B. einstimmig angenommen"
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