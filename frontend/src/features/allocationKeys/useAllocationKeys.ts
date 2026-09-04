// frontend/src/features/allocationKeys/useAllocationKeys.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  closeAllocationKey,
  createAllocationKey,
  listAllocationKeys,
  type AllocationKey,
  type AllocationKeyCreatePayload,
} from "./api";

const allocationKeysKey = (propertyId?: number) => ["allocation-keys", propertyId ?? "all"];

export function useAllocationKeys(propertyId?: number) {
  return useQuery({
    queryKey: allocationKeysKey(propertyId),
    queryFn: () => listAllocationKeys(propertyId),
    enabled: propertyId !== undefined,
  });
}

/**
 * Wirft diesen Fehler, wenn beim Anlegen einer Gruppe (mehrere Einheiten
 * gleichzeitig) mindestens eine Einheit fehlgeschlagen ist - i.d.R. wegen
 * eines überlappenden Gültigkeitszeitraums (excl_unit_allocation_keys_no_overlap,
 * s. 01_schema.sql). Bereits erfolgreich angelegte Einheiten bleiben dabei
 * bestehen, da es keinen Batch-Endpoint mit gemeinsamer Transaktion gibt.
 */
export class AllocationKeyGroupError extends Error {
  failedUnitIds: number[];

  constructor(failedUnitIds: number[]) {
    super("Einige Einheiten konnten nicht angelegt werden.");
    this.name = "AllocationKeyGroupError";
    this.failedUnitIds = failedUnitIds;
  }
}

export function useCreateAllocationKeyGroup(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payloads: AllocationKeyCreatePayload[]): Promise<AllocationKey[]> => {
      const results = await Promise.allSettled(payloads.map((p) => createAllocationKey(p)));
      const failedUnitIds = results
        .map((r, i) => ({ r, unitId: payloads[i].unit_id }))
        .filter((x) => x.r.status === "rejected")
        .map((x) => x.unitId);

      if (failedUnitIds.length > 0) {
        throw new AllocationKeyGroupError(failedUnitIds);
      }
      return results.map((r) => (r as PromiseFulfilledResult<AllocationKey>).value);
    },
    // onSettled statt onSuccess: auch bei Teilausfall wurden ggf. einzelne
    // Zeilen erfolgreich angelegt - die Liste muss trotzdem neu geladen werden.
    onSettled: () => queryClient.invalidateQueries({ queryKey: allocationKeysKey(propertyId) }),
  });
}

export function useCloseAllocationKeyGroup(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ keyIds, validToYear }: { keyIds: number[]; validToYear: number }) => {
      const results = await Promise.allSettled(
        keyIds.map((keyId) => closeAllocationKey(keyId, { valid_to_year: validToYear })),
      );
      const failedCount = results.filter((r) => r.status === "rejected").length;
      if (failedCount > 0) {
        throw new Error(`${failedCount} von ${keyIds.length} Einheiten-Zeilen konnten nicht geschlossen werden.`);
      }
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: allocationKeysKey(propertyId) }),
  });
}