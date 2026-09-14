// frontend/src/features/documents/DocumentsPage.tsx
import { useEffect, useState } from "react";

import { Card } from "../../components/Card";
import { useCurrentProperty } from "../../context/PropertyContext";
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
  const { propertyId, property, properties, isLoading: propertiesLoading } = useCurrentProperty();

  const listParams = propertyId != null ? { property_id: propertyId } : undefined;
  const { data: documents, isLoading } = useDocuments(listParams);
  const uploadMutation = useUploadDocument(listParams);
  const deleteMutation = useDeleteDocument(listParams);

  const [uploading, setUploading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    setUploading(false);
    setFormError(null);
  }, [propertyId]);

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

  if (propertiesLoading) {
    return (
      <div className="documents-page">
        <Card>
          <p>Lädt Liegenschaften…</p>
        </Card>
      </div>
    );
  }

  if (propertyId == null || properties.length === 0) {
    return (
      <div className="documents-page">
        <Card>
          <h1>Dokumente</h1>
          <p>Bitte zuerst links in der Sidebar eine Liegenschaft auswählen.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="documents-page">
      <Card>
        <h1>Dokumente – {property?.name}</h1>
      </Card>

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

      {uploading && (
        <Card>
          <h2>Neues Dokument hochladen</h2>
          <DocumentUploadForm
            propertyId={propertyId}
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