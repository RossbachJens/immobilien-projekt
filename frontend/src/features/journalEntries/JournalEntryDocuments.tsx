// frontend/src/features/journalEntries/JournalEntryDocuments.tsx
import { useState } from "react";

import type { DocumentUploadPayload } from "../documents/api";
import { documentDownloadUrl } from "../documents/api";
import { DocumentUploadForm } from "../documents/DocumentUploadForm";
import { useDocuments, useUpdateDocumentJournalEntryLink, useUploadDocument } from "../documents/useDocuments";
import "./JournalEntryDocuments.css";

interface JournalEntryDocumentsProps {
  propertyId: number;
  journalEntryId: number;
}

export function JournalEntryDocuments({ propertyId, journalEntryId }: JournalEntryDocumentsProps) {
  const { data: linkedDocuments, isLoading } = useDocuments({
    property_id: propertyId,
    journal_entry_id: journalEntryId,
  });
  const { data: allDocuments } = useDocuments({ property_id: propertyId });

  const uploadMutation = useUploadDocument();
  const linkMutation = useUpdateDocumentJournalEntryLink();

  const [showUploadForm, setShowUploadForm] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [showLinkExisting, setShowLinkExisting] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | "">("");
  const [linkError, setLinkError] = useState<string | null>(null);

  const linkedIds = new Set((linkedDocuments ?? []).map((d) => d.document_id));
  const linkableDocuments = (allDocuments ?? []).filter((d) => !linkedIds.has(d.document_id));

  function handleUpload(payload: DocumentUploadPayload) {
    setUploadError(null);
    uploadMutation.mutate(payload, {
      onSuccess: () => setShowUploadForm(false),
      onError: () => setUploadError("Beleg konnte nicht hochgeladen werden."),
    });
  }

  function handleLinkExisting() {
    if (selectedDocumentId === "") return;
    setLinkError(null);
    linkMutation.mutate(
      { documentId: selectedDocumentId, payload: { journal_entry_id: journalEntryId } },
      {
        onSuccess: () => {
          setSelectedDocumentId("");
          setShowLinkExisting(false);
        },
        onError: () => setLinkError("Dokument konnte nicht verknüpft werden."),
      },
    );
  }

  function handleUnlink(documentId: number) {
    if (!window.confirm("Diesen Beleg von der Buchung lösen? Das Dokument bleibt im Archiv erhalten.")) return;
    linkMutation.mutate(
      { documentId, payload: { journal_entry_id: null } },
      { onError: () => window.alert("Beleg konnte nicht gelöst werden.") },
    );
  }

  return (
    <div className="journal-entry-documents">
      {isLoading && <p>Lädt Belege…</p>}
      {!isLoading && linkedDocuments?.length === 0 && (
        <p className="journal-entry-documents__empty">Noch keine Belege zu dieser Buchung.</p>
      )}

      {linkedDocuments && linkedDocuments.length > 0 && (
        <ul className="journal-entry-documents__list">
          {linkedDocuments.map((doc) => (
            <li key={doc.document_id}>
              <a href={documentDownloadUrl(doc.document_id)} target="_blank" rel="noreferrer">
                {doc.title}
              </a>
              <span className="journal-entry-documents__category">{doc.category}</span>
              <button type="button" onClick={() => handleUnlink(doc.document_id)}>
                Lösen
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="journal-entry-documents__actions">
        {!showUploadForm && (
          <button type="button" onClick={() => setShowUploadForm(true)}>
            Neuen Beleg hochladen
          </button>
        )}
        {!showLinkExisting && (
          <button type="button" onClick={() => setShowLinkExisting(true)}>
            Vorhandenes Dokument verknüpfen
          </button>
        )}
      </div>

      {showUploadForm && (
        <DocumentUploadForm
          propertyId={propertyId}
          journalEntryId={journalEntryId}
          onSubmit={handleUpload}
          onCancel={() => setShowUploadForm(false)}
          isSubmitting={uploadMutation.isPending}
          error={uploadError}
        />
      )}

      {showLinkExisting && (
        <div className="journal-entry-documents__link-form">
          <select
            value={selectedDocumentId}
            onChange={(e) => setSelectedDocumentId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">– Dokument wählen –</option>
            {linkableDocuments.map((doc) => (
              <option key={doc.document_id} value={doc.document_id}>
                {doc.title} ({doc.category})
                {doc.journal_entry_id != null ? " – bereits einer anderen Buchung zugeordnet" : ""}
              </option>
            ))}
          </select>
          {linkError && <p className="journal-entry-documents__error">{linkError}</p>}
          <div className="journal-entry-documents__link-form-actions">
            <button
              type="button"
              onClick={handleLinkExisting}
              disabled={selectedDocumentId === "" || linkMutation.isPending}
            >
              {linkMutation.isPending ? "Wird verknüpft…" : "Verknüpfen"}
            </button>
            <button type="button" onClick={() => setShowLinkExisting(false)}>
              Abbrechen
            </button>
          </div>
        </div>
      )}
    </div>
  );
}