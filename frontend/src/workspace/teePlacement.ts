import type {
  TeeBoltLayoutRequest,
  TeeBoltPlacementMode,
  TeeInterfacePlacementTrace,
} from "../api/teeContracts";

/** Exact presentation-state conversion between edge and group-offset placement. */
export function exactOffset(
  edge: string,
  count: number,
  spacing: string,
  extent: string,
): string {
  const inputs = [edge, spacing, extent];
  const scales = inputs.map((item) => item.split(".")[1]?.length ?? 0);
  const scale = Math.max(...scales);
  const denominator = 10n ** BigInt(scale);
  const scaled = inputs.map((item, index) => {
    const [whole = "0", fraction = ""] = item.split(".");
    const sign = whole.startsWith("-") ? -1n : 1n;
    const digits = `${whole.replace("-", "")}${fraction.padEnd(scale, "0")}`;
    return sign * BigInt(digits || "0") * (index === 1 ? BigInt(count - 1) : 1n);
  });
  const [scaledEdge, scaledSpacing, scaledExtent] = scaled as [bigint, bigint, bigint];
  const numerator = 2n * scaledEdge + scaledSpacing - scaledExtent;
  const negative = numerator < 0n;
  const absolute = negative ? -numerator : numerator;
  const doubledScale = denominator * 2n;
  const whole = absolute / doubledScale;
  const remainder = absolute % doubledScale;
  if (remainder === 0n) return `${negative ? "-" : ""}${whole.toString()}`;
  const fractional = ((remainder * 10n ** BigInt(scale + 1)) / doubledScale)
    .toString()
    .padStart(scale + 1, "0")
    .replace(/0+$/u, "");
  return `${negative ? "-" : ""}${whole.toString()}.${fractional}`;
}

export function requirePlacementOffset<T>(value: T | undefined): T {
  if (value === undefined) throw new Error("Group-offset state requires both in-plane offsets.");
  return value;
}

export function initializeGroupOffsetPlacement(
  layout: TeeBoltLayoutRequest,
  verticalExtent: string,
  horizontalExtent: string,
): void {
  layout.placement_mode = "GROUP_OFFSET_CONTROLLED";
  layout.vertical_offset = {
    value: exactOffset(
      layout.unloaded_end_distance.value,
      layout.row_count,
      layout.pitch.value,
      verticalExtent,
    ),
    unit: layout.unloaded_end_distance.unit,
  };
  layout.horizontal_offset = {
    value: exactOffset(
      layout.negative_side_distance.value,
      layout.bolts_per_row,
      layout.gauge.value,
      horizontalExtent,
    ),
    unit: layout.negative_side_distance.unit,
  };
}

function traceMatchesPattern(
  layout: TeeBoltLayoutRequest,
  trace: TeeInterfacePlacementTrace,
): boolean {
  const equivalent = trace.equivalent_edge_distances;
  return equivalent.row_count === layout.row_count
    && equivalent.bolts_per_row === layout.bolts_per_row
    && equivalent.pitch === layout.pitch.value
    && equivalent.gauge === layout.gauge.value;
}

/** Apply only a current backend-authored exact alternate representation. */
export function applyExactPlacementMode(
  layout: TeeBoltLayoutRequest,
  mode: TeeBoltPlacementMode,
  trace: TeeInterfacePlacementTrace | null,
): boolean {
  const currentMode = layout.placement_mode ?? "EDGE_DISTANCE_CONTROLLED";
  if (mode === currentMode) return true;
  if (trace === null || !traceMatchesPattern(layout, trace)) return false;

  layout.placement_mode = mode;
  if (mode === "GROUP_OFFSET_CONTROLLED") {
    layout.vertical_offset = structuredClone(trace.vertical_offset);
    layout.horizontal_offset = structuredClone(trace.horizontal_offset);
    return true;
  }

  const equivalent = trace.equivalent_edge_distances;
  layout.unloaded_end_distance.value = equivalent.unloaded_end_distance;
  layout.loaded_end_distance.value = equivalent.loaded_end_distance;
  layout.negative_side_distance.value = equivalent.negative_side_distance;
  layout.positive_side_distance.value = equivalent.positive_side_distance;
  delete layout.vertical_offset;
  delete layout.horizontal_offset;
  return true;
}

export interface ClearanceRecovery {
  readonly clearance: string;
  readonly unit: string;
  readonly direction: string;
}

const BOUNDARY_RECOVERY_DIRECTIONS: Readonly<Record<string, string>> = {
  VERTICAL_POSITIVE: "down",
  VERTICAL_NEGATIVE: "up",
  HORIZONTAL_POSITIVE: "toward negative H",
  HORIZONTAL_NEGATIVE: "toward positive H",
};

/** Read an exact backend-authored containment deficit without deriving geometry locally. */
export function clearanceRecoveryFromBackendDetail(
  detail: string | null,
  interfaceId: string,
): ClearanceRecovery | null {
  if (detail === null) return null;
  const match = /Complete-hole clearance (-[0-9]+(?:\.[0-9]+)?) ([A-Za-z-]+); governing boundary ([^;]+);/u.exec(detail);
  if (match === null) return null;
  const clearance = match[1];
  const unit = match[2];
  const boundaryId = match[3];
  /* v8 ignore next -- the fixed regex contract always supplies all three captures */
  if (clearance === undefined || unit === undefined || boundaryId === undefined) return null;
  if (!boundaryId.startsWith(`${interfaceId}:`)) return null;
  const boundary = boundaryId.slice(interfaceId.length + 1);
  const direction = BOUNDARY_RECOVERY_DIRECTIONS[boundary];
  if (direction === undefined) return null;
  return { clearance, unit, direction };
}
