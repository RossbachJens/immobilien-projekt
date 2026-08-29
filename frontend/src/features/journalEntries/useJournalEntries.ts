// frontend/src/features/journalEntries/useJournalEntries.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createJournalEntry,
  listJournalEntries,
  stornoJournalEntry,
  type JournalEntryPayload,
} from "./api";

const journalEntriesKey = (propertyId?: number) => ["journal-entries", propertyId ?? "all"];

export function useJournalEntries(propertyId?: number) {
  return useQuery({
    queryKey: journalEntriesKey(propertyId),
    queryFn: () => listJournalEntries(propertyId),
    enabled: propertyId !== undefined,
  });
}

export function useCreateJournalEntry(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: JournalEntryPayload) => createJournalEntry(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: journalEntriesKey(propertyId) }),
  });
}

export function useStornoJournalEntry(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entryId: number) => stornoJournalEntry(entryId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: journalEntriesKey(propertyId) }),
  });
}