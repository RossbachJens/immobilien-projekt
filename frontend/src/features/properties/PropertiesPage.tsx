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
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    createPropertyMutation.mutate(
      { name, address },
      {
        onSuccess: () => {
          setName("");
          setAddress("");
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
          {error && <p className="properties-page__error">{error}</p>}
          <button type="submit" disabled={createPropertyMutation.isPending}>
            {createPropertyMutation.isPending ? "Wird gespeichert…" : "Anlegen"}
          </button>
        </form>
      </Card>
    </div>
  );
}