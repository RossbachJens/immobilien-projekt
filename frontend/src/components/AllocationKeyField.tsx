// frontend/src/components/AllocationKeyField.tsx
import "./AllocationKeyField.css";

const STANDARD_KEYS = ["MEA", "Wohnflaeche"] as const;

interface AllocationKeyFieldProps {
  mode: "standard" | "custom";
  onModeChange: (mode: "standard" | "custom") => void;
  standardKey: string;
  onStandardKeyChange: (key: string) => void;
  customKey: string;
  onCustomKeyChange: (key: string) => void;
}

export function AllocationKeyField({
  mode,
  onModeChange,
  standardKey,
  onStandardKeyChange,
  customKey,
  onCustomKeyChange,
}: AllocationKeyFieldProps) {
  return (
    <fieldset className="allocation-key-field">
      <legend>Verteilerschlüssel</legend>
      <label className="allocation-key-field__radio">
        <input type="radio" checked={mode === "standard"} onChange={() => onModeChange("standard")} />
        Standard
      </label>
      {mode === "standard" && (
        <select value={standardKey} onChange={(e) => onStandardKeyChange(e.target.value)}>
          {STANDARD_KEYS.map((k) => (
            <option key={k} value={k}>
              {k === "MEA" ? "Miteigentumsanteile (MEA)" : "Wohnfläche"}
            </option>
          ))}
        </select>
      )}
      <label className="allocation-key-field__radio">
        <input type="radio" checked={mode === "custom"} onChange={() => onModeChange("custom")} />
        Individueller Umlageschlüssel
      </label>
      {mode === "custom" && (
        <input
          value={customKey}
          onChange={(e) => onCustomKeyChange(e.target.value)}
          placeholder="genauer key_type, z.B. Heizkosten_Verbrauch"
          required
        />
      )}
    </fieldset>
  );
}