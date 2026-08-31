// frontend/src/features/payments/PaymentForm.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { useUnitLeases } from "../leases/useLeases";
import type { Unit } from "../units/api";

import type { PaymentPayload, PaymentType } from "./api";
import "./PaymentForm.css";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

interface PaymentFormProps {
  units: Unit[];
  onSubmit: (payload: PaymentPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function PaymentForm({ units, onSubmit, onCancel, isSubmitting, error }: PaymentFormProps) {
  const [unitId, setUnitId] = useState<number | "">("");
  const [paymentType, setPaymentType] = useState<PaymentType>("hausgeld");
  const [leaseId, setLeaseId] = useState<number | "">("");
  const [amount, setAmount] = useState("");
  const [paymentDate, setPaymentDate] = useState(todayIso());
  const [documentReference, setDocumentReference] = useState("");

  const { data: leases } = useUnitLeases(paymentType === "miete" && unitId !== "" ? unitId : undefined);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (unitId === "") return;
    if (paymentType === "miete" && leaseId === "") return;

    onSubmit({
      unit_id: unitId,
      payment_type: paymentType,
      lease_id: paymentType === "miete" ? leaseId : null,
      amount: Number(amount),
      payment_date: paymentDate,
      document_reference: documentReference || null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="payment-form">
      <label>
        Einheit *
        <select
          value={unitId}
          onChange={(e) => {
            setUnitId(e.target.value ? Number(e.target.value) : "");
            setLeaseId("");
          }}
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
            onChange={() => setPaymentType("miete")}
          />
          Miete (Mieter)
        </label>
      </fieldset>

      {paymentType === "miete" && (
        <label>
          Mietvertrag *
          <select
            value={leaseId}
            onChange={(e) => setLeaseId(e.target.value ? Number(e.target.value) : "")}
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
      )}

      <label>
        Betrag (€) *
        <input
          type="number"
          min="0.01"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          required
        />
      </label>
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

      {error && <p className="payment-form__error">{error}</p>}
      <div className="payment-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird gebucht…" : "Zahlung erfassen"}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}