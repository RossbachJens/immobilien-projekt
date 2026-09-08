// frontend/src/features/documents/DocumentsPage.tsx
import { useState } from "react";

import { Card } from "../../components/Card";
import { useProperties } from "../properties/useProperties";
import type { DocumentUploadPayload } from "./api";
import { documentDownloadUrl } from "./api";
import { DocumentUploadForm } from "./DocumentUploadForm";
import { useDeleteDocument, useDocuments, useUploadDocument } from "./useDocuments";
import "./DocumentsPage.css";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentsPage() {
  const { data: properties, isLoading: propertiesLoading } = useProperties();
  const [propertyId, setPropertyId] = useState<number | "">("");
  const selectedPropertyId = propertyId === "" ? undefined : propertyId;

  const listParams = selectedPropertyId !== undefined ? { property_id: selectedPropertyId } : undefined;
  const { data: documents, isLoading } = useDocuments(listParams);
  const uploadMutation = useUploadDocument(listParams);
  const deleteMutation = useDeleteDocument(listParams);

  const [uploading, setUploading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function handleUpload(payload: DocumentUploadPayload) {
    setFormError(null);
    uploadMutation.mutate(payload, {
      onSuccess: () => setUploading(false),
      onError: () => setFormError("Dokument konnte nicht hochgeladen werden - Datei eventuell zu groß."),
    });
  }

  function handleDelete(documentId: number) {
    if (!window.confirm("Dokument wirklich löschen?")) return;
    deleteMutation.mutate(documentId);
  }

  return (
    <div className="documents-page">
      <Card>
        <h1>Dokumente</h1>
        {propertiesLoading && <p>Lädt Liegenschaften…</p>}
        <label className="documents-page__property-select">
          Liegenschaft
          <select
            value={propertyId}
            onChange={(e) => {
              setPropertyId(e.target.value ? Number(e.target.value) : "");
              setUploading(false);
            }}
          >
            <option value="">– bitte wählen –</option>
            {properties?.map((p) => (
              <option key={p.property_id} value={p.property_id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
      </Card>

      {selectedPropertyId !== undefined && (
        <Card>
          <div className="documents-page__header">
            <h2>Abgelegte Dokumente</h2>
            {!uploading && (
              <button type="button" onClick={() => setUploading(true)}>
                Dokument hochladen
              </button>
            )}
          </div>

          {isLoading && <p>Lädt…</p>}
          {!isLoading && documents?.length === 0 && <p>Noch keine Dokumente abgelegt.</p>}

          <table className="documents-page__table">
            <thead>
              <tr>
                <th>Titel</th>
                <th>Kategorie</th>
                <th>Sichtbarkeit</th>
                <th>Größe</th>
                <th>Hochgeladen am</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {documents?.map((doc) => (
                <tr key={doc.document_id}>
                  <td>{doc.title}</td>
                  <td>{doc.category}</td>
                  <td>{doc.visibility}</td>
                  <td>{formatFileSize(doc.file_size_bytes)}</td>
                  <td>{new Date(doc.created_at).toLocaleDateString("de-DE")}</td>
                  <td className="documents-page__actions">
                    <a href={documentDownloadUrl(doc.document_id)} target="_blank" rel="noreferrer">
                      Öffnen
                    </a>
                    <button type="button" onClick={() => handleDelete(doc.document_id)}>
                      Löschen
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {uploading && selectedPropertyId !== undefined && (
        <Card>
          <h2>Neues Dokument hochladen</h2>
          <DocumentUploadForm
            propertyId={selectedPropertyId}
            onSubmit={handleUpload}
            onCancel={() => setUploading(false)}
            isSubmitting={uploadMutation.isPending}
            error={formError}
          />
        </Card>
      )}
    </div>
  );
}