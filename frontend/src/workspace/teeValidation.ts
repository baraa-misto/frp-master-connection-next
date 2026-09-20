import type { TeeConnectorRequest } from "../api/teeContracts";

export function teeValidationMessage(request: TeeConnectorRequest): string | null {
  if (
    request.connector_length_anchor_position.value.trim() === ""
    || !Number.isFinite(Number(request.connector_length_anchor_position.value))
  ) {
    return "Tee longitudinal position must be a finite value.";
  }
  if (request.connected_member_end_trim_enabled) {
    const clearance = request.connected_member_end_clearance;
    if (
      clearance === null
      || clearance.value.trim() === ""
      || !Number.isFinite(Number(clearance.value))
      || Number(clearance.value) < 0
    ) {
      return "End clearance to Tee flange must be a finite nonnegative value.";
    }
  }
  const positiveLayoutQuantities = (layout: TeeConnectorRequest["interface_a_layout"]) => [
    layout.pitch,
    layout.gauge,
    layout.unloaded_end_distance,
    layout.loaded_end_distance,
    layout.negative_side_distance,
    layout.positive_side_distance,
  ];
  const quantities = [
    ...Object.values(request.connector_dimensions),
    ...Object.values(request.support_profile).filter(
      (value): value is { value: string; unit: "in" | "mm" } => (
        typeof value === "object" && value !== null && "value" in value && "unit" in value
      ),
    ),
    ...Object.values(request.connected_member_profile.dimensions),
    request.bolt_diameter,
    ...positiveLayoutQuantities(request.interface_a_layout),
    ...positiveLayoutQuantities(request.interface_b_layout),
  ];
  if (quantities.some((value) => !Number.isFinite(Number(value.value)) || Number(value.value) <= 0)) {
    return "All Tee and bolt-group dimensions must be finite and greater than zero.";
  }
  for (const layout of [request.interface_a_layout, request.interface_b_layout]) {
    if (layout.placement_mode === "GROUP_OFFSET_CONTROLLED") {
      if (
        layout.vertical_offset === undefined ||
        layout.horizontal_offset === undefined ||
        [layout.vertical_offset, layout.horizontal_offset].some(
          (value) => value.value.trim() === "" || !Number.isFinite(Number(value.value)),
        )
      ) {
        return "Group-offset placement requires finite vertical and horizontal offsets.";
      }
    }
  }
  if (request.connected_member_profile.profile_family === "ROUND_HOLLOW_SECTION") {
    return "Round tube requires a separately defined compatible interface or adapter; direct Tee-stem contact is unavailable.";
  }
  if (
    !Number.isInteger(request.interface_a_layout.row_count) ||
    !Number.isInteger(request.interface_a_layout.bolts_per_row) ||
    !Number.isInteger(request.interface_b_layout.row_count) ||
    !Number.isInteger(request.interface_b_layout.bolts_per_row) ||
    request.interface_a_layout.row_count < 1 ||
    request.interface_a_layout.bolts_per_row < 1 ||
    request.interface_b_layout.row_count < 1 ||
    request.interface_b_layout.bolts_per_row < 1
  ) {
    return "Each interface requires positive row and bolt counts.";
  }
  const inclination = Number(request.brace_inclination_degrees);
  if (
    request.brace_inclination_degrees.trim() === "" ||
    !Number.isFinite(inclination) ||
    inclination < -90 ||
    inclination > 90
  ) {
    return "Brace inclination must be a finite value from -90° through +90°.";
  }
  const vectors = [
    request.global_force,
    request.global_moment,
    request.global_reference_point,
  ];
  if (vectors.some((value) => [value.x, value.y, value.z].some(
    (component) => component.trim() === "" || !Number.isFinite(Number(component)),
  ))) {
    return "Action and reference-point components must be finite decimals.";
  }
  return null;
}
