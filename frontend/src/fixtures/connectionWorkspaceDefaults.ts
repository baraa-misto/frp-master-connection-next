/** Owner-controlled startup inputs, separate from frozen engineering benchmarks. */
import type { MultiRowQuantity } from "../api/multirowContracts";
import type { ClipAngleBoltLayoutRequest, ClipAngleRequest } from "../api/clipAngleContracts";
import type { PairedClipAngleRequest } from "../api/pairedClipAngleContracts";
import type { TeeConnectorRequest } from "../api/teeContracts";
import type { ExpandedMultiMemberTeeRequest } from "../api/multiMemberTeeContracts";
import { initialConnectedMemberProfile } from "../workspace/teeProfileOptions";
import { initializeGroupOffsetPlacement } from "../workspace/teePlacement";
import { loadTeeBenchmark } from "./teeBenchmarks";
import { loadClipAngleC2Benchmark } from "./clipAngleBenchmarks";
import { loadPairedClipAngleBenchmark } from "./pairedClipAngleBenchmarks";
import { loadMultiMemberTeeBenchmark } from "./multiMemberTeeBenchmarks";

type Units = "US_CUSTOMARY" | "SI";

/** Exact 25.4 mm/in transport of fixed defaults, never a geometry calculation. */
function length(inches: string, units: Units): MultiRowQuantity {
  if (units === "US_CUSTOMARY") return { value: inches, unit: "in" };
  const point = inches.indexOf(".");
  const scale = point < 0 ? 1 : inches.length - point;
  const integer = BigInt(inches.replace(".", "")) * 254n;
  const negative = integer < 0n;
  const digits = (negative ? -integer : integer).toString().padStart(scale + 1, "0");
  const decimal = digits.slice(-scale).replace(/0+$/u, "");
  return { value: `${negative ? "-" : ""}${digits.slice(0, -scale)}${decimal === "" ? "" : `.${decimal}`}`, unit: "mm" };
}

function wide(units: Units, small = false) {
  return {
    depth: length(small ? "6" : "8", units),
    flange_width: length(small ? "3" : "6", units),
    web_thickness: length(small ? "0.25" : "0.375", units),
    flange_thickness: length(small ? "0.25" : "0.375", units),
  };
}

function clipLayout(layout: ClipAngleBoltLayoutRequest, units: Units): void {
  layout.bolts_per_row = 1;
  // Fixed 7.25-in extrusion, centered two-row group, retained 2-in pitch.
  layout.negative_end_distance = length("2.625", units);
  layout.positive_end_distance = length("2.625", units);
}

export function loadTeeWorkspaceDefault(units: Units): TeeConnectorRequest {
  const request = loadTeeBenchmark(units);
  Object.assign(request.support_profile, wide(units));
  request.connected_member_profile = initialConnectedMemberProfile(units === "SI" ? "mm" : "in");
  request.connected_member_profile.dimensions.leg_z = length("4", units);
  initializeGroupOffsetPlacement(request.interface_a_layout, request.connector_dimensions.connector_length.value, request.connector_dimensions.stem_depth.value);
  initializeGroupOffsetPlacement(request.interface_b_layout, request.connector_dimensions.connector_length.value, request.connector_dimensions.flange_width.value);
  request.interface_a_layout.bolts_per_row = 1;
  request.interface_a_layout.vertical_offset = length("2", units);
  request.brace_inclination_degrees = "45";
  request.connected_member_end_trim_enabled = true;
  request.connected_member_end_clearance = length("0", units);
  return request;
}

export function loadClipAngleWorkspaceDefault(units: Units): ClipAngleRequest {
  const request = loadClipAngleC2Benchmark(units);
  Object.assign(request.support_profile, wide(units));
  request.connected_member_profile = {
    profile_id: "clip-angle-connected-member-profile",
    role: "BRACE",
    size_basis: "CUSTOM_DIMENSIONS",
    profile_orientation: "ROTATION_0",
    profile_family: "WIDE_FLANGE_I",
    selected_profile_surface: "WEB_POS_FACE",
    dimensions: { member_length: length("8", units), ...wide(units) },
  };
  request.connector_dimensions.connector_length = length("7.25", units);
  clipLayout(request.interface_a_layout, units);
  clipLayout(request.interface_b_layout, units);
  return request;
}

export function loadPairedClipAngleWorkspaceDefault(units: Units): PairedClipAngleRequest {
  const request = loadPairedClipAngleBenchmark(units);
  Object.assign(request.support_profile, wide(units));
  request.connected_member_profile = {
    ...request.connected_member_profile,
    profile_family: "WIDE_FLANGE_I",
    selected_profile_surface: "WEB_POS_FACE",
    dimensions: { member_length: length("8", units), ...wide(units) },
  };
  request.connector_dimensions.connector_length = length("7.25", units);
  clipLayout(request.common_member_layout, units);
  clipLayout(request.mirrored_support_layout, units);
  return request;
}

export function loadMultiMemberTeeWorkspaceDefault(units: Units): ExpandedMultiMemberTeeRequest {
  const request = loadMultiMemberTeeBenchmark(units);
  Object.assign(request.support_profile, wide(units));
  request.support_group.row_count = 3;
  request.support_group.pitch = length("7.5", units);
  for (const [key, position] of [["upper_brace", "7.5"], ["lower_brace", "-7.5"]] as const) {
    const slot = request[key];
    Object.assign(slot.profile.dimensions, { leg_y: length("4", units), leg_z: length("4", units), thickness: length("0.5", units) });
    slot.anchor_v = length(position, units);
    slot.bolt_group.bolts_per_row = 1;
    slot.trim_enabled = true;
    slot.trim_clearance = length("0", units);
  }
  Object.assign(request.middle_beam.profile.dimensions, wide(units, true));
  request.middle_beam.bolt_group.bolts_per_row = 1;
  return request;
}
