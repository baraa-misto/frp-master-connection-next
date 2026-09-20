import type { MultiRowQuantity } from "../api/multirowContracts";
import type {
  ClipAngleBoltLayoutRequest,
  LegacyClipAngleRequest,
  ClipAngleRequest,
} from "../api/clipAngleContracts";
import { initialSharedSupport } from "../api/sharedSupportContracts";

export type ClipAngleBenchmarkUnitSystem = "US_CUSTOMARY" | "SI";

const INCH_TO_MM_UNSCALED = 254n;
const INCH_TO_MM_SCALE = 1;
const KIP_TO_KN_UNSCALED = 44_482_216_152_605n;
const KIP_TO_KN_SCALE = 13;
const KIP_IN_TO_KN_MM_UNSCALED = 112_984_829_027_616_7n;
const KIP_IN_TO_KN_MM_SCALE = 13;

function multiplyExactDecimal(value: string, multiplier: bigint, scale: number): string {
  const separator = value.indexOf(".");
  const whole = separator < 0 ? value : value.slice(0, separator);
  const fraction = separator < 0 ? "" : value.slice(separator + 1);
  const product = BigInt(`${whole}${fraction}`) * multiplier;
  const decimalPlaces = fraction.length + scale;
  const digits = product.toString().padStart(decimalPlaces + 1, "0");
  const integer = digits.slice(0, -decimalPlaces);
  const decimal = digits.slice(-decimalPlaces).replace(/0+$/u, "");
  return decimal === "" ? integer : `${integer}.${decimal}`;
}

function length(value: string, system: ClipAngleBenchmarkUnitSystem): MultiRowQuantity {
  return {
    value: system === "US_CUSTOMARY"
      ? value
      : multiplyExactDecimal(value, INCH_TO_MM_UNSCALED, INCH_TO_MM_SCALE),
    unit: system === "US_CUSTOMARY" ? "in" : "mm",
  };
}

function force(value: string, system: ClipAngleBenchmarkUnitSystem): string {
  return system === "US_CUSTOMARY"
    ? value
    : multiplyExactDecimal(value, KIP_TO_KN_UNSCALED, KIP_TO_KN_SCALE);
}

function moment(value: string, system: ClipAngleBenchmarkUnitSystem): string {
  return system === "US_CUSTOMARY"
    ? value
    : multiplyExactDecimal(value, KIP_IN_TO_KN_MM_UNSCALED, KIP_IN_TO_KN_MM_SCALE);
}

function layout(system: ClipAngleBenchmarkUnitSystem): ClipAngleBoltLayoutRequest {
  return {
    row_count: 2,
    bolts_per_row: 2,
    pitch: length("2", system),
    gauge: length("2", system),
    heel_edge_distance: length("0.75", system),
    free_edge_distance: length("0.75", system),
    negative_end_distance: length("3", system),
    positive_end_distance: length("3", system),
    placement_mode: "EDGE_DISTANCE_CONTROLLED",
    length_offset: null,
    width_offset: null,
  };
}

/** Return the controlled G1 physical fixture in either exact transport unit system. */
export function loadClipAngleBenchmark(
  system: ClipAngleBenchmarkUnitSystem,
): LegacyClipAngleRequest {
  const si = system === "SI";
  const lengthUnit = si ? "mm" : "in";
  return {
    orchestration_contract_version: "3.3A-RC1",
    request_id: `CLIP-ANGLE-WORKSPACE-${system}`,
    unit_system: system,
    source_length_unit: lengthUnit,
    hand: "POSITIVE_S_SIDE",
    support_role: "W_COLUMN_FLANGE",
    selected_support_flange: "POSITIVE_LOCAL_Z",
    connector_dimensions: {
      connected_leg_width: length("4", system),
      support_leg_width: length("4", system),
      thickness: length("0.5", system),
      connector_length: length("8", system),
    },
    support_dimensions: {
      member_length: length("16", system),
      overall_depth: length("8", system),
      flange_width: length("8", system),
      web_thickness: length("0.5", system),
      flange_thickness: length("0.75", system),
    },
    connected_member_profile: {
      profile_id: "clip-angle-connected-flat-plate",
      role: "BRACE",
      profile_family: "FLAT_PLATE",
      size_basis: "CUSTOM_DIMENSIONS",
      dimensions: {
        member_length: length("8", system),
        width: length("6", system),
        thickness: length("0.375", system),
      },
      profile_orientation: "ROTATION_0",
      selected_profile_surface: "FACE_POS",
    },
    interface_a_layout: layout(system),
    interface_b_layout: layout(system),
    bolt_diameter: length("0.5", system),
    hole_diameter: length("0.563", system),
    hole_basis: si ? "SI_PRINTED" : "US_CUSTOMARY_PRINTED",
    global_force: { x: "0", y: "0", z: force("3", system), unit: si ? "kN" : "kip" },
    global_moment: {
      x: "0",
      y: "0",
      z: moment("0", system),
      unit: si ? "kN-mm" : "kip-in",
    },
    global_reference_point: {
      x: length("2.25", system).value,
      y: length("2.25", system).value,
      z: "0",
      unit: lengthUnit,
    },
    connected_member_inclination_degrees: "0",
    connected_member_end_trim_enabled: false,
    connected_member_end_clearance: null,
    connector_length_anchor: "CENTER",
    connector_length_anchor_position: length("0", system),
    connector_material: "PULTRUDED_FRP",
    fastener_material: "STAINLESS_STEEL_316",
    fastener_snapshot_id: "ASTM_F593_17_GROUP_2_316_316L",
  };
}

/** Adapt the accepted G1 geometry to the shared C2 support contract. */
export function loadClipAngleC2Benchmark(
  system: ClipAngleBenchmarkUnitSystem,
): ClipAngleRequest {
  const legacy = loadClipAngleBenchmark(system);
  const {
    support_role: _supportRole,
    selected_support_flange: _selectedFlange,
    support_dimensions: legacySupport,
    orchestration_contract_version: _legacyVersion,
    ...base
  } = legacy;
  void [_supportRole, _selectedFlange, _legacyVersion];
  const support = initialSharedSupport(
    "W_COLUMN_FLANGE",
    legacy.source_length_unit,
    "clip-angle-support",
  );
  support.member_length = legacySupport.member_length;
  support.depth = legacySupport.overall_depth;
  support.flange_width = legacySupport.flange_width;
  support.web_thickness = legacySupport.web_thickness;
  support.flange_thickness = legacySupport.flange_thickness;
  return {
    ...base,
    orchestration_contract_version: "3.3C2-RC1",
    support_target_id: "W_COLUMN_FLANGE",
    support_profile: support,
  };
}
