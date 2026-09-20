import type { ClipAngleRequest } from "../api/clipAngleContracts";

export function clipAngleValidationMessage(request: ClipAngleRequest): string | null {
  const quantities = [
    ...Object.values(request.connector_dimensions),
    ...Object.values(request.support_profile).filter(
      (value): value is { value: string; unit: "in" | "mm" } => (
        typeof value === "object" && value !== null && "value" in value && "unit" in value
      ),
    ),
    request.bolt_diameter,
    request.hole_diameter,
  ];
  if (quantities.some((value) => !Number.isFinite(Number(value.value)) || Number(value.value) <= 0)) {
    return "Physical dimensions must be finite and greater than zero.";
  }
  if (request.interface_a_layout.row_count < 1 || request.interface_a_layout.bolts_per_row < 1 || request.interface_b_layout.row_count < 1 || request.interface_b_layout.bolts_per_row < 1) {
    return "Each bolt group requires at least one row and one bolt per row.";
  }
  if (request.connected_member_end_trim_enabled && request.connected_member_end_clearance === null) {
    return "Enabled member-end trim requires a clearance.";
  }
  return null;
}
