// frontend/src/features/meetings/AgendaItemsPanel.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { AgendaItemPayload } from "./api";
import { useAgendaItems, useCreateAgendaItem, useDeleteAgendaItem } from "./useMeetings";
import "./AgendaItemsPanel.css";

interface AgendaItemsPanelProps {
  meetingId: number;
}

export function AgendaItemsPanel({ meetingId }: AgendaItemsPanelProps) {
  const { data: items, isLoading } = useAgendaItems(meetingId);
  const createMutation = useCreateAgendaItem(meetingId);
  const deleteMutation = useDeleteAgendaItem(meetingId);

  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const nextPosition = (items?.length ?? 0) + 1;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const payload: AgendaItemPayload = { position: nextPosition, title, description: description || null };
    createMutation.mutate(payload, {
      onSuccess: () => {
        setShowForm(false);
        setTitle("");
        setDescription("");
      },
      onError: () => setError("TOP konnte nicht angelegt werden."),
    });
  }

  function handleDelete(itemId: number) {
    if (!window.confirm("Diesen Tagesordnungspunkt wirklich löschen?")) return;
    deleteMutation.mutate(itemId);
  }

  return (
    <div className="agenda-items-panel">
      <h4>Tagesordnung</h4>
      {isLoading && <p>Lädt…</p>}
      {!isLoading && items?.length === 0 && (
        <p className="agenda-items-panel__empty">Noch keine TOPs erfasst.</p>
      )}

      {items && items.length > 0 && (
        <ol className="agenda-items-panel__list">
          {items.map((item) => (
            <li key={item.item_id}>
              <div className="agenda-items-panel__item-row">
                <span>
                  <strong>TOP {item.position}</strong> – {item.title}
                </span>
                <button type="button" onClick={() => handleDelete(item.item_id)}>
                  Löschen
                </button>
              </div>
              {item.description && <p className="agenda-items-panel__description">{item.description}</p>}
            </li>
          ))}
        </ol>
      )}

      {!showForm && (
        <button type="button" onClick={() => setShowForm(true)}>
          TOP hinzufügen
        </button>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="agenda-items-panel__form">
          <label>
            Titel (TOP {nextPosition}) *
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Beschreibung
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
          </label>
          {error && <p className="agenda-items-panel__error">{error}</p>}
          <div className="agenda-items-panel__form-actions">
            <button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Wird gespeichert…" : "Hinzufügen"}
            </button>
            <button type="button" onClick={() => setShowForm(false)}>
              Abbrechen
            </button>
          </div>
        </form>
      )}
    </div>
  );
}