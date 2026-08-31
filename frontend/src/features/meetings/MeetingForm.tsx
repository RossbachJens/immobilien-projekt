// frontend/src/features/meetings/MeetingForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { MeetingPayload } from "./api";
import "./MeetingForm.css";

const MEETING_TYPES = [
  "ordentliche Eigentümerversammlung",
  "außerordentliche Eigentümerversammlung",
  "Umlaufbeschluss",
];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

interface MeetingFormProps {
  propertyId: number;
  onSubmit: (payload: MeetingPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function MeetingForm({ propertyId, onSubmit, onCancel, isSubmitting, error }: MeetingFormProps) {
  const [meetingType, setMeetingType] = useState(MEETING_TYPES[0]);
  const [meetingDate, setMeetingDate] = useState(todayIso());
  const [meetingTime, setMeetingTime] = useState("");
  const [location, setLocation] = useState("");
  const [agendaIntro, setAgendaIntro] = useState("");

  const isCircular = meetingType === "Umlaufbeschluss";

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      property_id: propertyId,
      meeting_type: meetingType,
      meeting_date: meetingDate,
      meeting_time: !isCircular && meetingTime ? meetingTime : null,
      location: !isCircular && location ? location : null,
      agenda_intro: agendaIntro || null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="meeting-form">
      <label>
        Art *
        <select value={meetingType} onChange={(e) => setMeetingType(e.target.value)}>
          {MEETING_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>
      <label>
        {isCircular ? "Frist zur Stimmabgabe *" : "Termin *"}
        <input type="date" value={meetingDate} onChange={(e) => setMeetingDate(e.target.value)} required />
      </label>
      {!isCircular && (
        <>
          <label>
            Uhrzeit
            <input type="time" value={meetingTime} onChange={(e) => setMeetingTime(e.target.value)} />
          </label>
          <label>
            Ort
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="z.B. Schildergasse 101a, 50667 Köln"
            />
          </label>
        </>
      )}
      <label>
        Einleitungstext für die Einladung
        <textarea
          value={agendaIntro}
          onChange={(e) => setAgendaIntro(e.target.value)}
          rows={3}
          placeholder="hiermit laden wir Sie herzlich ein…"
        />
      </label>

      {error && <p className="meeting-form__error">{error}</p>}
      <div className="meeting-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird gespeichert…" : "Anlegen"}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}