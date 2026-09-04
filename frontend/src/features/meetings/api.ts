// frontend/src/features/meetings/api.ts
import { apiClient } from "../../api/client";

export type MeetingStatus = "Geplant" | "Eingeladen" | "Durchgeführt" | "Protokolliert";

export interface Meeting {
  meeting_id: number;
  property_id: number;
  meeting_type: string;
  meeting_date: string;
  meeting_time: string | null;
  location: string | null;
  invitation_date: string | null;
  agenda_intro: string | null;
  minutes_text: string | null;
  status: MeetingStatus;
  created_by: number | null;
  created_at: string;
  chairperson: string | null;
  minute_taker: string | null;
  end_time: string | null;
  represented_shares: number | null;
  quorum_met: boolean | null;
  voting_key: string | null;
}

export interface MeetingPayload {
  property_id: number;
  meeting_type: string;
  meeting_date: string;
  meeting_time?: string | null;
  location?: string | null;
  agenda_intro?: string | null;
}

export interface MeetingUpdatePayload {
  meeting_type?: string;
  meeting_date?: string;
  meeting_time?: string | null;
  location?: string | null;
  invitation_date?: string | null;
  agenda_intro?: string | null;
  minutes_text?: string | null;
  status?: MeetingStatus;
  chairperson?: string | null;
  minute_taker?: string | null;
  end_time?: string | null;
  represented_shares?: number | null;
  quorum_met?: boolean | null;
  voting_key?: string | null;
}

export interface AgendaItem {
  item_id: number;
  meeting_id: number;
  position: number;
  title: string;
  description: string | null;
  protocol_text: string | null;
}

export interface AgendaItemPayload {
  position: number;
  title: string;
  description?: string | null;
}

export interface AgendaItemUpdatePayload {
  position?: number;
  title?: string;
  description?: string | null;
  protocol_text?: string | null;
}

export async function listMeetings(propertyId?: number): Promise<Meeting[]> {
  const { data } = await apiClient.get<Meeting[]>("/meetings", {
    params: propertyId ? { property_id: propertyId } : undefined,
  });
  return data;
}

export async function createMeeting(payload: MeetingPayload): Promise<Meeting> {
  const { data } = await apiClient.post<Meeting>("/meetings", payload);
  return data;
}

export async function updateMeeting(meetingId: number, payload: MeetingUpdatePayload): Promise<Meeting> {
  const { data } = await apiClient.patch<Meeting>(`/meetings/${meetingId}`, payload);
  return data;
}

export async function listAgendaItems(meetingId: number): Promise<AgendaItem[]> {
  const { data } = await apiClient.get<AgendaItem[]>(`/meetings/${meetingId}/agenda-items`);
  return data;
}

export async function createAgendaItem(meetingId: number, payload: AgendaItemPayload): Promise<AgendaItem> {
  const { data } = await apiClient.post<AgendaItem>(`/meetings/${meetingId}/agenda-items`, payload);
  return data;
}

export async function updateAgendaItem(
  meetingId: number,
  itemId: number,
  payload: AgendaItemUpdatePayload,
): Promise<AgendaItem> {
  const { data } = await apiClient.patch<AgendaItem>(`/meetings/${meetingId}/agenda-items/${itemId}`, payload);
  return data;
}

export async function deleteAgendaItem(meetingId: number, itemId: number): Promise<void> {
  await apiClient.delete(`/meetings/${meetingId}/agenda-items/${itemId}`);
}

async function downloadPdf(url: string, filename: string): Promise<void> {
  const response = await apiClient.get(url, { responseType: "blob" });
  const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export async function downloadInvitation(meetingId: number): Promise<void> {
  await downloadPdf(`/meetings/${meetingId}/invitation.pdf`, `Einladung_Versammlung_${meetingId}.pdf`);
}

export async function downloadMinutes(meetingId: number): Promise<void> {
  await downloadPdf(`/meetings/${meetingId}/minutes.pdf`, `Niederschrift_Versammlung_${meetingId}.pdf`);
}