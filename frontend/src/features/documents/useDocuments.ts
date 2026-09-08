// frontend/src/features/documents/useDocuments.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  deleteDocument,
  listDocuments,
  uploadDocument,
  type DocumentUploadPayload,
  type ListDocumentsParams,
} from "./api";

const documentsKey = (params?: ListDocumentsParams) => ["documents", params ?? {}];

export function useDocuments(params?: ListDocumentsParams) {
  return useQuery({
    queryKey: documentsKey(params),
    queryFn: () => listDocuments(params),
    enabled: params?.property_id !== undefined,
  });
}

export function useUploadDocument(params?: ListDocumentsParams) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DocumentUploadPayload) => uploadDocument(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentsKey(params) }),
  });
}

export function useDeleteDocument(params?: ListDocumentsParams) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: number) => deleteDocument(documentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentsKey(params) }),
  });
}