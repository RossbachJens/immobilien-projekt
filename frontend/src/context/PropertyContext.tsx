// frontend/src/context/PropertyContext.tsx
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";

import type { Property } from "../features/properties/api";
import { useProperties } from "../features/properties/useProperties";

const STORAGE_KEY = "immobilien.currentPropertyId";

interface PropertyContextValue {
  propertyId: number | null;
  property: Property | null;
  properties: Property[];
  isLoading: boolean;
  setPropertyId: (propertyId: number | null) => void;
}

const PropertyContext = createContext<PropertyContextValue | undefined>(undefined);

function readStoredPropertyId(): number | null {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Zentrale Liegenschaftsauswahl (Sidebar-Dropdown, siehe Sidebar.tsx) statt
 * eines eigenen useState + <select> je Feature-Seite. Auswahl wird in
 * localStorage gehalten, damit sie Seitenwechsel und Reload übersteht.
 */
export function PropertyProvider({ children }: PropsWithChildren) {
  const { data: properties, isLoading } = useProperties();
  const [propertyId, setPropertyIdState] = useState<number | null>(() => readStoredPropertyId());

  // Sobald die Liegenschaftsliste vorliegt: gespeicherte Auswahl validieren
  // (z.B. nach Rollenwechsel/Neuanmeldung nicht mehr zugreifbar) und bei
  // fehlender/ungültiger Auswahl automatisch die erste verfügbare wählen -
  // so landet niemand ohne Weiteres auf einer leeren Seite.
  useEffect(() => {
    if (!properties) return;
    const stillValid = propertyId != null && properties.some((p) => p.property_id === propertyId);
    if (stillValid) return;
    setPropertyIdState(properties[0]?.property_id ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [properties]);

  function setPropertyId(next: number | null) {
    setPropertyIdState(next);
    if (next == null) {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, String(next));
    }
  }

  const property = useMemo(
    () => properties?.find((p) => p.property_id === propertyId) ?? null,
    [properties, propertyId],
  );

  const value: PropertyContextValue = {
    propertyId,
    property,
    properties: properties ?? [],
    isLoading,
    setPropertyId,
  };

  return <PropertyContext.Provider value={value}>{children}</PropertyContext.Provider>;
}

export function useCurrentProperty(): PropertyContextValue {
  const ctx = useContext(PropertyContext);
  if (!ctx) {
    throw new Error("useCurrentProperty muss innerhalb von <PropertyProvider> verwendet werden.");
  }
  return ctx;
}