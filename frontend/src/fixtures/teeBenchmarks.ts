import type { MultiRowQuantity } from "../api/multirowContracts";
import type {
  TeeBoltLayoutRequest,
  TeeConnectorRequest,
} from "../api/teeContracts";
import { initialSharedSupport } from "../api/sharedSupportContracts";

export type TeeBenchmarkUnitSystem = "US_CUSTOMARY" | "SI";

const INCH_TO_MM_UNSCALED = 254n;
const INCH_TO_MM_SCALE = 1;
const KIP_TO_KN_UNSCALED = 44_482_216_152_605n;
const KIP_TO_KN_SCALE = 13;

function multiplyExactDecimal(
  value: string,
  multiplier: bigint,
  multiplierScale: number,
): string {
  const separator = value.indexOf(".");
  const whole = separator < 0 ? value : value.slice(0, separator);
  const fraction = separator < 0 ? "" : value.slice(separator + 1);
  const product = BigInt(`${whole}${fraction}`) * multiplier;
  const decimalPlaces = fraction.length + multiplierScale;
  const digits = product.toString().padStart(decimalPlaces + 1, "0");
  const integer = digits.slice(0, -decimalPlaces);
  const decimal = digits.slice(-decimalPlaces).replace(/0+$/u, "");
  return decimal.length === 0 ? integer : `${integer}.${decimal}`;
}

function exactLength(valueInches: string, unitSystem: TeeBenchmarkUnitSystem): string {
  return unitSystem === "US_CUSTOMARY"
    ? valueInches
    : multiplyExactDecimal(valueInches, INCH_TO_MM_UNSCALED, INCH_TO_MM_SCALE);
}

function exactForce(valueKip: string, unitSystem: TeeBenchmarkUnitSystem): string {
  return unitSystem === "US_CUSTOMARY"
    ? valueKip
    : multiplyExactDecimal(valueKip, KIP_TO_KN_UNSCALED, KIP_TO_KN_SCALE);
}

function lengthQuantity(
  valueInches: string,
  unitSystem: TeeBenchmarkUnitSystem,
): MultiRowQuantity {
  return {
    value: exactLength(valueInches, unitSystem),
    unit: unitSystem === "US_CUSTOMARY" ? "in" : "mm",
  };
}

function layout(unitSystem: TeeBenchmarkUnitSystem): TeeBoltLayoutRequest {
  return {
    row_count: 2,
    bolts_per_row: 2,
    pitch: lengthQuantity("2", unitSystem),
    gauge: lengthQuantity("2", unitSystem),
    unloaded_end_distance: lengthQuantity("1", unitSystem),
    loaded_end_distance: lengthQuantity("1", unitSystem),
    negative_side_distance: lengthQuantity("1", unitSystem),
    positive_side_distance: lengthQuantity("1", unitSystem),
  };
}

/** Build one exact physical Tee benchmark in either governed display system. */
export function loadTeeBenchmark(unitSystem: TeeBenchmarkUnitSystem): TeeConnectorRequest {
  const si = unitSystem === "SI";
  const lengthUnit = si ? "mm" : "in";
  return {
    orchestration_contract_version: "3.3C2-RC1",
    request_id: `TEE-WORKSPACE-${unitSystem}`,
    unit_system: unitSystem,
    source_length_unit: lengthUnit,
    support_target_id: "W_COLUMN_FLANGE",
    support_profile: {
      ...initialSharedSupport("W_COLUMN_FLANGE", lengthUnit, "tee-support"),
      member_length: lengthQuantity("16", unitSystem),
      flange_thickness: lengthQuantity("0.75", unitSystem),
    },
    connected_member_end_trim_enabled: false,
    connected_member_end_clearance: null,
    connector_length_anchor: "CENTER",
    connector_length_anchor_position: lengthQuantity("0", unitSystem),
    connector_dimensions: {
      connector_length: lengthQuantity("8", unitSystem),
      flange_width: lengthQuantity("6", unitSystem),
      flange_thickness: lengthQuantity("0.5", unitSystem),
      stem_depth: lengthQuantity("4", unitSystem),
      stem_thickness: lengthQuantity("0.375", unitSystem),
    },
    connected_member_profile: {
      profile_id: "tee-connected-brace-profile",
      role: "BRACE",
      profile_family: "FLAT_PLATE",
      size_basis: "CUSTOM_DIMENSIONS",
      dimensions: {
        width: lengthQuantity("8", unitSystem),
        thickness: lengthQuantity("0.375", unitSystem),
        member_length: lengthQuantity("6", unitSystem),
      },
      profile_orientation: "ROTATION_0",
      selected_profile_surface: "FACE_POS",
      material_kind: "PULTRUDED_FRP",
    },
    interface_a_layout: layout(unitSystem),
    interface_b_layout: layout(unitSystem),
    bolt_diameter: lengthQuantity("0.5", unitSystem),
    // Both transports describe the same U.S.-printed physical hole.
    hole_basis: "US_CUSTOMARY_PRINTED",
    global_force: {
      x: "0",
      y: "0",
      z: exactForce("0.1", unitSystem),
      unit: si ? "kN" : "kip",
    },
    global_moment: {
      x: "0",
      y: "0",
      z: "0",
      unit: si ? "kN-mm" : "kip-in",
    },
    global_reference_point: {
      x: exactLength("0", unitSystem),
      y: exactLength("0", unitSystem),
      z: exactLength("0", unitSystem),
      unit: lengthUnit,
    },
    brace_inclination_degrees: "0",
    connector_material: "PULTRUDED_FRP",
    fastener_material: "STAINLESS_STEEL_316",
    fastener_snapshot_id: "ASTM_F593_17_GROUP_2_316_316L",
  };
}
