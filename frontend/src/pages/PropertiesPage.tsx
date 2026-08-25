import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import { createProperty, listProperties } from "../api/properties";

export default function PropertiesPage() {
  const queryClient = useQueryClient();
  const { data: properties, isLoading } = useQuery({
    queryKey: ["properties"],
    queryFn: listProperties,
  });

  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await createProperty({ name, address });
      setName("");
      setAddress("");
      await queryClient.invalidateQueries({ queryKey: ["properties"] });
    } catch {
      setError("Liegenschaft konnte nicht angelegt werden.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <p>
        <Link to="/">← Zurück</Link>
      </p>
      <h1>Liegenschaften</h1>

      {isLoading && <p>Lädt…</p>}
      <ul>
        {properties?.map((property) => (
          <li key={property.property_id}>
            <strong>{property.name}</strong> — {property.address}
          </li>
        ))}
      </ul>

      <h2>Neue Liegenschaft anlegen</h2>
      <form onSubmit={handleSubmit} style={{ maxWidth: 400 }}>
        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="name" style={{ display: "block" }}>
            Name
          </label>
          <input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            style={{ width: "100%", padding: 8, boxSizing: "border-box" }}
          />
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="address" style={{ display: "block" }}>
            Adresse
          </label>
          <input
            id="address"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            required
            style={{ width: "100%", padding: 8, boxSizing: "border-box" }}
          />
        </div>
        {error && <p style={{ color: "#d9534f" }}>{error}</p>}
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird gespeichert…" : "Anlegen"}
        </button>
      </form>
    </main>
  );
}
