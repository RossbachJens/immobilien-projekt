// frontend/src/features/settlementPeriods/SettlementPeriodForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { useResolutions } from "../resolutions/useResolutions";

import type { SettlementPeriodPayload } from "./api";
import "./SettlementPeriodForm.css";

interface SettlementPeriodFormProps {
  propertyId: number;
  onSubmit: (payload: SettlementPeriodPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

function previousYear(): number {
  return new Date().getFullYear() - 1;
}

export function SettlementPeriodForm({
  propertyId,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: SettlementPeriodFormProps) {
  const { data: resolutions } = useResolutions(propertyId);

  const [fiscalYear, setFiscalYear] = useState(String(previousYear()));
  const [title, setTitle] = useState("");
  const [periodStart, setPeriodStart] = useState(`${previousYear()}-01-01`);
  const [periodEnd, setPeriodEnd] = useState(`${previousYear()}-12-31`);
  const [resolutionId, setResolutionId] = useState<number | "">("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      property_id: propertyId,
      fiscal_year: Number(fiscalYear),
      period_start: periodStart,
      period_end: periodEnd,
      title,
      resolution_id: resolutionId === "" ? null : resolutionId,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="settlement-period-form">
      <label>
        Abrechnungsjahr *
        <input type="number" value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)} required />
      </label>
      <label>
        Titel *
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={`z.B. Jahresabrechnung ${fiscalYear}`}
          required
        />
      </label>
      <label>
        Zeitraum von *
        <input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} required />
      </label>
      <label>
        Zeitraum bis *
        <input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} required />
      </label>
      <label>
        Zugehöriger Beschluss (optional)
        <select value={resolutionId} onChange={(e) => setResolutionId(e.target.value ? Number(e.target.value) : "")}>
          <option value="">– noch kein Beschluss –</option>
          {resolutions?.map((r) => (
            <option key={r.resolution_id} value={r.resolution_id}>
              Lfd. Nr. {r.lfd_nr} – {r.title}
            </option>
          ))}
        </select>
      </label>
      {error && <p className="settlement-period-form__error">{error}</p>}
      <div className="settlement-period-form__actions">
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