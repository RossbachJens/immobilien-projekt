// frontend/src/features/journalEntries/api.ts
import { apiClient } from "../../api/client";

export type EntryDirection = "DEBIT" | "CREDIT";

export interface EntryLine {
  line_id: number;
  account_id: number;
  property_id: number | null;
  unit_id: number | null;
  lease_id: number | null;
  amount: number;
  direction: EntryDirection;
}

export interface JournalEntry {
  entry_id: number;
  property_id: number;
  entry_date: string;
  document_reference: string | null;
  description: string;
  created_by: number | null;
  created_at: string;
  locked_at: string | null;
  reversed_entry_id: number | null;
  lines: EntryLine[];
}

export interface EntryLinePayload {
  account_id: number;
  unit_id?: number | null;
  lease_id?: number | null;
  amount: number;
  direction: EntryDirection;
}

export interface JournalEntryPayload {
  property_id: number;
  entry_date: string;
  document_reference?: string | null;
  description: string;
  lines: EntryLinePayload[];
}

export async function listJournalEntries(propertyId?: number): Promise<JournalEntry[]> {
  const { data } = await apiClient.get<JournalEntry[]>("/journal-entries", {
    params: propertyId ? { property_id: propertyId } : undefined,
  });
  return data;
}

export async function createJournalEntry(payload: JournalEntryPayload): Promise<JournalEntry> {
  const { data } = await apiClient.post<JournalEntry>("/journal-entries", payload);
  return data;
}

export async function stornoJournalEntry(entryId: number): Promise<JournalEntry> {
  const { data } = await apiClient.post<JournalEntry>(`/journal-entries/${entryId}/storno`);
  return data;
}