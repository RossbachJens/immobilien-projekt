// frontend/src/features/meetings/AgendaItemsPanel.tsx
import { useState } from "react";
import type { FormEvent } from "react";

import type { AgendaItemPayload } from "./api";
import {
  useAgendaItems,
  useCreateAgendaItem,
  useDeleteAgendaItem,
  useUpdateAgendaItem,
} from "./useMeetings";
import "./AgendaItemsPanel.css";

interface AgendaItemsPanelProps {
  meetingId: number;
}

export function AgendaItemsPanel({ meetingId }: AgendaItemsPanelProps) {
  const { data: items, isLoading } = useAgendaItems(meetingId);
  const createMutation = useCreateAgendaItem(meetingId);
  const updateMutation = useUpdateAgendaItem(meetingId);
  const deleteMutation = useDeleteAgendaItem(meetingId);

  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  // item_id, für das gerade der Protokolltext bearbeitet wird.
  const [editingProtocolId, setEditingProtocolId] = useState<number | null>(null);
  const [protocolDraft, setProtocolDraft] = useState("");
  const [protocolError, setProtocolError] = useState<string | null>(null);

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

  function startProtocolEdit(itemId: number, currentText: string | null) {
    setEditingProtocolId(itemId);
    setProtocolDraft(currentText ?? "");
    setProtocolError(null);
  }

  function saveProtocol(event: FormEvent, itemId: number) {
    event.preventDefault();
    setProtocolError(null);
    updateMutation.mutate(
      { itemId, payload: { protocol_text: protocolDraft || null } },
      {
        onSuccess: () => setEditingProtocolId(null),
        onError: () => setProtocolError("Protokolltext konnte nicht gespeichert werden."),
      },
    );
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
                <div className="agenda-items-panel__item-actions">
                  <button type="button" onClick={() => startProtocolEdit(item.item_id, item.protocol_text)}>
                    {item.protocol_text ? "Protokolltext bearbeiten" : "Protokolltext erfassen"}
                  </button>
                  <button type="button" onClick={() => handleDelete(item.item_id)}>
                    Löschen
                  </button>
                </div>
              </div>
              {item.description && <p className="agenda-items-panel__description">{item.description}</p>}

              {editingProtocolId === item.item_id ? (
                <form
                  onSubmit={(e) => saveProtocol(e, item.item_id)}
                  className="agenda-items-panel__protocol-form"
                >
                  <label>
                    Protokolltext (Verlauf, erscheint in der Niederschrift unter diesem TOP)
                    <textarea
                      value={protocolDraft}
                      onChange={(e) => setProtocolDraft(e.target.value)}
                      rows={4}
                      placeholder="z.B. Bericht des Verwaltungsbeirats…"
                    />
                  </label>
                  {protocolError && <p className="agenda-items-panel__error">{protocolError}</p>}
                  <div className="agenda-items-panel__form-actions">
                    <button type="submit" disabled={updateMutation.isPending}>
                      {updateMutation.isPending ? "Wird gespeichert…" : "Speichern"}
                    </button>
                    <button type="button" onClick={() => setEditingProtocolId(null)}>
                      Abbrechen
                    </button>
                  </div>
                </form>
              ) : (
                item.protocol_text && (
                  <p className="agenda-items-panel__protocol">{item.protocol_text}</p>
                )
              )}
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
            Beschreibung (Ankündigungstext für die Einladung)
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