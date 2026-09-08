// frontend/src/features/documents/api.ts
import { apiClient } from "../../api/client";

export type DocumentCategory =
  | "Kontoauszug"
  | "Rechnung"
  | "Angebot"
  | "Versicherung"
  | "Vertrag"
  | "Protokoll"
  | "Sonstiges";

export type DocumentVisibility = "intern" | "eigentuemer" | "alle";

export interface Document {
  document_id: number;
  property_id: number;
  category: DocumentCategory;
  unit_id: number | null;
  owner_id: number | null;
  tenant_id: number | null;
  settlement_id: number | null;
  journal_entry_id: number | null;
  meeting_id: number | null;
  title: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  visibility: DocumentVisibility;
  uploaded_by: number | null;
  created_at: string;
}

export interface DocumentUploadPayload {
  property_id: number;
  category: DocumentCategory;
  title: string;
  visibility: DocumentVisibility;
  unit_id?: number | null;
  owner_id?: number | null;
  tenant_id?: number | null;
  settlement_id?: number | null;
  journal_entry_id?: number | null;
  meeting_id?: number | null;
  file: File;
}

export interface ListDocumentsParams {
  property_id?: number;
  category?: DocumentCategory;
  unit_id?: number;
  settlement_id?: number;
}

export async function listDocuments(params?: ListDocumentsParams): Promise<Document[]> {
  const { data } = await apiClient.get<Document[]>("/documents", { params });
  return data;
}

export async function uploadDocument(payload: DocumentUploadPayload): Promise<Document> {
  const formData = new FormData();
  formData.append("property_id", String(payload.property_id));
  formData.append("category", payload.category);
  formData.append("title", payload.title);
  formData.append("visibility", payload.visibility);
  if (payload.unit_id != null) formData.append("unit_id", String(payload.unit_id));
  if (payload.owner_id != null) formData.append("owner_id", String(payload.owner_id));
  if (payload.tenant_id != null) formData.append("tenant_id", String(payload.tenant_id));
  if (payload.settlement_id != null) formData.append("settlement_id", String(payload.settlement_id));
  if (payload.journal_entry_id != null) formData.append("journal_entry_id", String(payload.journal_entry_id));
  if (payload.meeting_id != null) formData.append("meeting_id", String(payload.meeting_id));
  formData.append("file", payload.file);

  const { data } = await apiClient.post<Document>("/documents", formData);
  return data;
}

export async function deleteDocument(documentId: number): Promise<void> {
  await apiClient.delete(`/documents/${documentId}`);
}

export function documentDownloadUrl(documentId: number): string {
  return `${apiClient.defaults.baseURL}/documents/${documentId}/download`;
}