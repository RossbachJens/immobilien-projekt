// frontend/src/features/documents/DocumentUploadForm.tsx
import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

import type { DocumentCategory, DocumentUploadPayload, DocumentVisibility } from "./api";
import "./DocumentUploadForm.css";

const CATEGORIES: DocumentCategory[] = [
  "Kontoauszug",
  "Rechnung",
  "Angebot",
  "Versicherung",
  "Vertrag",
  "Protokoll",
  "Sonstiges",
];

const VISIBILITY_LABELS: Record<DocumentVisibility, string> = {
  intern: "Intern (nur Verwalter/Admin)",
  eigentuemer: "Eigentümer (zusätzlich sichtbar)",
  alle: "Alle (zusätzlich Mieter)",
};

interface DocumentUploadFormProps {
  propertyId: number;
  // Gesetzt, wenn der Upload aus dem Kontext einer Buchung heraus gestartet
  // wurde (siehe features/journalEntries/JournalEntryDocuments.tsx) - das
  // Dokument wird dann direkt beim Anlegen als Beleg verknüpft.
  journalEntryId?: number | null;
  onSubmit: (payload: DocumentUploadPayload) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: string | null;
}

export function DocumentUploadForm({
  propertyId,
  journalEntryId,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: DocumentUploadFormProps) {
  const [category, setCategory] = useState<DocumentCategory>("Rechnung");
  const [title, setTitle] = useState("");
  const [visibility, setVisibility] = useState<DocumentVisibility>("intern");
  const [file, setFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setValidationError(null);
    if (!file) {
      setValidationError("Bitte eine Datei auswählen.");
      return;
    }
    onSubmit({
      property_id: propertyId,
      category,
      title,
      visibility,
      journal_entry_id: journalEntryId ?? undefined,
      file,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="document-upload-form">
      {journalEntryId != null && (
        <p className="document-upload-form__hint">Wird direkt als Beleg mit dieser Buchung verknüpft.</p>
      )}
      <label>
        Kategorie *
        <select value={category} onChange={(e) => setCategory(e.target.value as DocumentCategory)}>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      <label>
        Titel *
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="z.B. Kontoauszug März 2026" required />
      </label>
      <label>
        Sichtbarkeit
        <select value={visibility} onChange={(e) => setVisibility(e.target.value as DocumentVisibility)}>
          {(Object.keys(VISIBILITY_LABELS) as DocumentVisibility[]).map((v) => (
            <option key={v} value={v}>
              {VISIBILITY_LABELS[v]}
            </option>
          ))}
        </select>
      </label>
      <label>
        Datei *
        <input type="file" onChange={handleFileChange} required />
      </label>

      {(validationError || error) && <p className="document-upload-form__error">{validationError ?? error}</p>}

      <div className="document-upload-form__actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Wird hochgeladen…" : "Hochladen"}
        </button>
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}