import type { QuantityResult } from "../api/contracts";

const FRIENDLY_ID_LABELS: Readonly<Record<string, string>> = {
  "member-a": "Angle brace",
  "member-b": "W column",
  "layer-A": "Angle Connected Leg",
  "layer-B": "W Column Flange",
  "bolt-1": "Selected bolt",
  "interface-1": "Brace-to-column interface",
  "bolt-group-1": "One-bolt group",
  LEG_1: "Angle Connected Leg",
  LEG_2: "Angle return leg",
  TOP_FLANGE: "W Column Flange",
  BOTTOM_FLANGE: "W Column Opposite Flange",
  WEB: "W Column Web",
};

export function friendlyIdentifier(value: string | null): string {
  if (value === null) return "Bolt";
  const bolt = /^B_R(\d+)_L(\d+)$/u.exec(value);
  if (bolt !== null) return `Bolt · Row ${String(bolt[1])} · Line ${String(bolt[2])}`;
  const row = /^ROW_(\d+)$/u.exec(value);
  if (row !== null) return `Row ${String(row[1])}`;
  const line = /^BOLT_LINE_(\d+)$/u.exec(value);
  if (line !== null) return `Bolt Line ${String(line[1])}`;
  return FRIENDLY_ID_LABELS[value] ?? value;
}

export function friendlyEnum(value: string | null): string {
  if (value === null) return "Not evaluated";
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.length === 0 ? part : `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

export function formatDecimal(value: string | null, places = 3): string {
  if (value === null) return "—";
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(places) : value;
}

export function formatEditableDecimal(value: string, places = 3): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return value;
  return numeric.toFixed(places).replace(/(\.\d*?[1-9])0+$/u, "$1").replace(/\.0+$/u, "");
}

export function formatQuantity(value: QuantityResult | null): string {
  return value === null ? "—" : `${formatDecimal(value.value)} ${value.unit}`;
}

export function formatUtilization(value: string | null): string {
  if (value === null) return "—";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return value;
  return `${numeric.toFixed(3)} (${(numeric * 100).toFixed(1)}%)`;
}

export function exactQuantity(value: QuantityResult | null): string {
  return value === null ? "—" : `${value.value} ${value.unit}`;
}

type DisplayUnitSystem = "US_CUSTOMARY" | "SI";

const DISPLAY_CONVERSIONS: Readonly<
  Record<string, Readonly<Record<DisplayUnitSystem, readonly [number, string]>>>
> = {
  in: { US_CUSTOMARY: [1, "in"], SI: [25.4, "mm"] },
  mm: { US_CUSTOMARY: [1 / 25.4, "in"], SI: [1, "mm"] },
  kip: { US_CUSTOMARY: [1, "kip"], SI: [4.4482216152605, "kN"] },
  kN: { US_CUSTOMARY: [1 / 4.4482216152605, "kip"], SI: [1, "kN"] },
  N: { US_CUSTOMARY: [1 / 4448.2216152605, "kip"], SI: [0.001, "kN"] },
};

export function formatDisplayQuantity(
  value: { readonly value: string; readonly unit: string } | null,
  unitSystem: DisplayUnitSystem,
): string {
  if (value === null) return "—";
  const conversion = DISPLAY_CONVERSIONS[value.unit]?.[unitSystem];
  const numeric = Number(value.value);
  if (conversion === undefined || !Number.isFinite(numeric)) {
    return `${value.value} ${value.unit}`;
  }
  const [factor, unit] = conversion;
  const concise = Number((numeric * factor).toPrecision(7)).toString();
  return `${concise} ${unit}`;
}
