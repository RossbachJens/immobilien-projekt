// frontend/src/features/meetings/useMeetings.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createAgendaItem,
  createMeeting,
  deleteAgendaItem,
  listAgendaItems,
  listMeetings,
  updateAgendaItem,
  updateMeeting,
  type AgendaItemPayload,
  type AgendaItemUpdatePayload,
  type MeetingPayload,
  type MeetingUpdatePayload,
} from "./api";

const meetingsKey = (propertyId?: number) => ["meetings", propertyId ?? "all"];
const agendaItemsKey = (meetingId: number) => ["meetings", meetingId, "agenda-items"];

export function useMeetings(propertyId?: number) {
  return useQuery({
    queryKey: meetingsKey(propertyId),
    queryFn: () => listMeetings(propertyId),
    enabled: propertyId !== undefined,
    retry: false,
  });
}

export function useCreateMeeting(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: MeetingPayload) => createMeeting(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: meetingsKey(propertyId) }),
  });
}

export function useUpdateMeeting(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ meetingId, payload }: { meetingId: number; payload: MeetingUpdatePayload }) =>
      updateMeeting(meetingId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: meetingsKey(propertyId) }),
  });
}

// Optional, da ResolutionForm die TOP-Liste erst nach Auswahl einer
// Versammlung laden kann (meetingId dort anfangs "").
export function useAgendaItems(meetingId: number | undefined) {
  return useQuery({
    queryKey: agendaItemsKey(meetingId ?? -1),
    queryFn: () => listAgendaItems(meetingId as number),
    enabled: meetingId !== undefined,
  });
}

export function useCreateAgendaItem(meetingId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AgendaItemPayload) => createAgendaItem(meetingId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: agendaItemsKey(meetingId) }),
  });
}

export function useUpdateAgendaItem(meetingId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, payload }: { itemId: number; payload: AgendaItemUpdatePayload }) =>
      updateAgendaItem(meetingId, itemId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: agendaItemsKey(meetingId) }),
  });
}

export function useDeleteAgendaItem(meetingId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (itemId: number) => deleteAgendaItem(meetingId, itemId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: agendaItemsKey(meetingId) }),
  });
}