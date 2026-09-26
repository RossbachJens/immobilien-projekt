// frontend/src/features/payments/PaymentForm.tsx
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { useHausgeldOverview } from "../hausgeldOverview/useHausgeldOverview";
import { useUnitLeases } from "../leases/useLeases";
import type { Unit } from "../units/api";

import type { PaymentPayload, PaymentType } from "./api";
import "./PaymentForm.css";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

interface PaymentFormProps {
  propertyId: number;
  units: Unit[];
  onSubmit: (payload: PaymentPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function PaymentForm({ propertyId, units, onSubmit, onCancel, isSubmitting, error }: PaymentFormProps) {
  const [unitId, setUnitId] = useState<number | "">("");
  const [paymentType, setPaymentType] = useState<PaymentType>("hausgeld");
  const [leaseId, setLeaseId] = useState<number | "">("");
  const [paymentDate, setPaymentDate] = useState(todayIso());
  const [documentReference, setDocumentReference] = useState("");

  // Miete: Kaltmiete / Nebenkostenvorauszahlung getrennt (1200/1210).
  const [coldRentAmount, setColdRentAmount] = useState("");
  const [additionalCostsAmount, setAdditionalCostsAmount] = useState("");

  // Hausgeld: Bewirtschaftungskosten / Instandhaltungsrücklage getrennt (1220/1225).
  const [operatingAmount, setOperatingAmount] = useState("");
  const [reserveAmount, setReserveAmount] = useState("");

  const { data: leases } = useUnitLeases(paymentType === "miete" && unitId !== "" ? unitId : undefined);

  // Vorbefüllung Hausgeld aus dem beschlossenen Wirtschaftsplan des
  // Zahlungsjahres - ohne beschlossenen Plan bleibt beides bei 0
  // (has_budget_plan=false, analog zur Hausgeldübersicht).
  const fiscalYear = new Date(paymentDate).getFullYear();
  const { data: hausgeldOverview } = useHausgeldOverview(
    paymentType === "hausgeld" ? propertyId : undefined,
    paymentType === "hausgeld" ? fiscalYear : undefined,
  );

  function handleUnitChange(value: number | "") {
    setUnitId(value);
    setLeaseId("");
    setColdRentAmount("");
    setAdditionalCostsAmount("");
    setOperatingAmount("");
    setReserveAmount("");
  }

  function handleLeaseChange(value: number | "") {
    setLeaseId(value);
    if (value === "") {
      setColdRentAmount("");
      setAdditionalCostsAmount("");
      return;
    }
    const lease = leases?.find((l) => l.lease_id === value);
    setColdRentAmount(lease ? String(lease.cold_rent) : "");
    setAdditionalCostsAmount(lease ? String(lease.additional_costs_prepayment) : "");
  }

  // Greift bei jedem Wechsel von Einheit/Zahlungsart oder sobald die
  // Übersicht (nach)lädt. Überschreibt dabei auch manuelle Korrekturen an
  // den beiden Feldern, falls die Übersicht zwischenzeitlich neu geladen
  // wird - im kurzlebigen Formular-Kontext ein vernachlässigbares Risiko.
  useEffect(() => {
    if (paymentType !== "hausgeld" || unitId === "" || !hausgeldOverview) return;
    const overviewEntry = hausgeldOverview.find((u) => u.unit_id === unitId);
    if (!overviewEntry) return;
    setOperatingAmount(String(overviewEntry.monthly_target - overviewEntry.monthly_target_reserve));
    setReserveAmount(String(overviewEntry.monthly_target_reserve));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paymentType, unitId, hausgeldOverview]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (unitId === "") return;
    if (paymentType === "miete" && leaseId === "") return;

    onSubmit({
      unit_id: unitId,
      payment_type: paymentType,
      lease_id: paymentType === "miete" ? leaseId : null,
      payment_date: paymentDate,
      document_reference: documentReference || null,
      cold_rent_amount: paymentType === "miete" ? Number(coldRentAmount) || 0 : undefined,
      additional_costs_amount: paymentType === "miete" ? Number(additionalCostsAmount) || 0 : undefined,
      operating_amount: paymentType === "hausgeld" ? Number(operatingAmount) || 0 : undefined,
      reserve_amount: paymentType === "hausgeld" ? Number(reserveAmount) || 0 : undefined,
    });
  }

  const mieteSumZero =
    paymentType === "miete" && (Number(coldRentAmount) || 0) + (Number(additionalCostsAmount) || 0) <= 0;
  const hausgeldSumZero =
    paymentType === "hausgeld" && (Number(operatingAmount) || 0) + (Number(reserveAmount) || 0) <= 0;

  return (
    <form onSubmit={handleSubmit} className="payment-form">
      <label>
        Einheit *
        <select
          value={unitId}
          onChange={(e) => handleUnitChange(e.target.value ? Number(e.target.value) : "")}
          required
        >
          <option value="">– Einheit wählen –</option>
          {units.map((u) => (
            <option key={u.unit_id} value={u.unit_id}>
              {u.unit_number}
            </option>
          ))}
        </select>
      </label>

      <fieldset className="payment-form__type">
        <legend>Zahlungsart</legend>
        <label>
          <input
            type="radio"
            name="payment-type"
            checked={paymentType === "hausgeld"}
            onChange={() => {
              setPaymentType("hausgeld");
              setColdRentAmount("");
              setAdditionalCostsAmount("");
              setLeaseId("");
            }}
          />
          Hausgeld (Eigentümer)
        </label>
        <label>
          <input
            type="radio"
            name="payment-type"
            checked={paymentType === "miete"}
            onChange={() => {
              setPaymentType("miete");
              setOperatingAmount("");
              setReserveAmount("");
            }}
          />
          Miete (Mieter)
        </label>
      </fieldset>

      {paymentType === "miete" && (
        <>
          <label>
            Mietvertrag *
            <select
              value={leaseId}
              onChange={(e) => handleLeaseChange(e.target.value ? Number(e.target.value) : "")}
              required
              disabled={unitId === ""}
            >
              <option value="">– Vertrag wählen –</option>
              {leases?.map((l) => (
                <option key={l.lease_id} value={l.lease_id}>
                  seit {l.start_date} · {l.cold_rent.toFixed(2)} € Kaltmiete ({l.status})
                </option>
              ))}
            </select>
          </label>
          <label>
            Kaltmiete (€)
            <input
              type="number"
              min="0"
              step="0.01"
              value={coldRentAmount}
              onChange={(e) => setColdRentAmount(e.target.value)}
            />
          </label>
          <label>
            Nebenkostenvorauszahlung (€)
            <input
              type="number"
              min="0"
              step="0.01"
              value={additionalCostsAmount}
              onChange={(e) => setAdditionalCostsAmount(e.target.value)}
            />
          </label>
        </>
      )}

      {paymentType === "hausgeld" && (
        <>
          <label>
            Bewirtschaftungskosten (€)
            <input
              type="number"
              min="0"
              step="0.01"
              value={operatingAmount}
              onChange={(e) => setOperatingAmount(e.target.value)}
            />
          </label>
          <label>
            Instandhaltungsrücklage (€)
            <input
              type="number"
              min="0"
              step="0.01"
              value={reserveAmount}
              onChange={(e) => setReserveAmount(e.target.value)}
            />
          </label>
        </>
      )}

      <label>
        Zahlungsdatum *
        <input type="date" value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} required />
      </label>
      <label>
        Belegnummer
        <input
          value={documentReference}
          onChange={(e) => setDocumentReference(e.target.value)}
          placeholder="optional"
        />
      </label>

      {(mieteSumZero || hausgeldSumZero) && (
        <p className="payment-form__error">Mindestens einer der beiden Beträge muss größer als 0 sein.</p>
      )}
      {error && <p className="payment-form__error">{error}</p>}
      <div className="payment-form__actions">
        <button type="submit" disabled={isSubmitting || mieteSumZero || hausgeldSumZero}>
          {isSubmitting ? "Wird gebucht…" : "Zahlung erfassen"}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}