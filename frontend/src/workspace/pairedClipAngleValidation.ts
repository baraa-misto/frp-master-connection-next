import type { PairedClipAngleRequest } from "../api/pairedClipAngleContracts";

function positive(value: string): boolean {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0;
}

/** Client-side completeness only; the backend remains geometry and symmetry authority. */
export function pairedClipAngleValidationMessage(
  request: PairedClipAngleRequest,
): string | null {
  if (!(["FLAT_PLATE", "WIDE_FLANGE_I", "CHANNEL", "ANGLE", "RECTANGULAR_HOLLOW_SECTION", "SOLID_RECTANGULAR_SECTION"] as const).includes(
    request.connected_member_profile.profile_family,
  )) return "Paired clip angles require one of the six authorized planar profiles.";
  const supportDimensions = Object.values(request.support_profile).filter(
    (item): item is { value: string; unit: string } => (
      typeof item === "object" && item !== null && "value" in item && "unit" in item
    ),
  );
  const dimensions = [
    ...Object.values(request.connector_dimensions),
    ...Object.values(request.connected_member_profile.dimensions),
    ...supportDimensions,
    request.bolt_diameter,
    request.hole_diameter,
  ];
  if (!dimensions.every((item) => positive(item.value))) {
    return "All connector, support, bolt, and hole dimensions must be finite and positive.";
  }
  for (const layout of [request.common_member_layout, request.mirrored_support_layout]) {
    if (!Number.isInteger(layout.row_count) || layout.row_count < 1
      || !Number.isInteger(layout.bolts_per_row) || layout.bolts_per_row < 1) {
      return "Each physical paired-angle bolt group requires positive integer row and line counts.";
    }
  }
  if (request.connected_member_end_trim_enabled
    && (request.connected_member_end_clearance === null
      || !Number.isFinite(Number(request.connected_member_end_clearance.value))
      || Number(request.connected_member_end_clearance.value) < 0)) {
    return "Enabled paired-angle trim requires a finite nonnegative clearance.";
  }
  return null;
}
