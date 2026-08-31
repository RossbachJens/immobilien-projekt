// frontend/src/features/payments/usePayments.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createPayment, type PaymentPayload } from "./api";

export function useCreatePayment(propertyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PaymentPayload) => createPayment(payload),
    onSuccess: () => {
      // Zahlungen sind journal_entries - Buchungsliste dieser Liegenschaft
      // invalidieren, damit sie sofort in der Buchhaltungsübersicht auftaucht.
      queryClient.invalidateQueries({ queryKey: ["journal-entries", propertyId] });
    },
  });
}