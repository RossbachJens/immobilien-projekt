// frontend/src/features/properties/PropertiesPage.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { Card } from "../../components/Card";
import { useCreateProperty, useProperties } from "./useProperties";
import "./PropertiesPage.css";

export function PropertiesPage() {
  const { data: properties, isLoading } = useProperties();
  const createPropertyMutation = useCreateProperty();

  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [totalSquareMeters, setTotalSquareMeters] = useState("");
  const [constructionYear, setConstructionYear] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    createPropertyMutation.mutate(
      {
        name,
        address,
        total_square_meters: totalSquareMeters ? Number(totalSquareMeters) : null,
        construction_year: constructionYear ? Number(constructionYear) : null,
        description: description || null,
      },
      {
        onSuccess: () => {
          setName("");
          setAddress("");
          setTotalSquareMeters("");
          setConstructionYear("");
          setDescription("");
        },
        onError: () => setError("Liegenschaft konnte nicht angelegt werden."),
      },
    );
  }

  return (
    <div className="properties-page">
      <Card>
        <h1>Liegenschaften</h1>
        {isLoading && <p>Lädt…</p>}
        <ul className="properties-page__list">
          {properties?.map((property) => (
            <li key={property.property_id}>
              <strong>{property.name}</strong> — {property.address}
              {property.total_square_meters != null && <> · {property.total_square_meters} m²</>}
              {property.construction_year != null && <> · Baujahr {property.construction_year}</>}
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <h2>Neue Liegenschaft anlegen</h2>
        <form onSubmit={handleSubmit} className="properties-page__form">
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Adresse
            <input value={address} onChange={(e) => setAddress(e.target.value)} required />
          </label>
          <label>
            Wohn-/Nutzfläche gesamt (m²)
            <input
              type="number"
              min="0"
              step="0.01"
              value={totalSquareMeters}
              onChange={(e) => setTotalSquareMeters(e.target.value)}
            />
          </label>
          <label>
            Baujahr
            <input
              type="number"
              min="1800"
              max={new Date().getFullYear()}
              value={constructionYear}
              onChange={(e) => setConstructionYear(e.target.value)}
            />
          </label>
          <label>
            Beschreibung
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
          </label>
          {error && <p className="properties-page__error">{error}</p>}
          <button type="submit" disabled={createPropertyMutation.isPending}>
            {createPropertyMutation.isPending ? "Wird gespeichert…" : "Anlegen"}
          </button>
        </form>
      </Card>
    </div>
  );
}