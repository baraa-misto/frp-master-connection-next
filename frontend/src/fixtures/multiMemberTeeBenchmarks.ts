import type {
  ExpandedMultiMemberTeeRequest,
  HistoricalMultiMemberTeeRequest,
  NodeAngleSlot,
  NodeAction,
  NodeBeamSlot,
  NodeBoltGroup,
  NodeUnitSystem,
  NodeVector,
} from "../api/multiMemberTeeContracts";
import type { MultiRowQuantity } from "../api/multirowContracts";
import {
  initialSharedSupport,
  type SharedSupportProfileRequest,
  type SharedSupportTargetId,
} from "../api/sharedSupportContracts";
import type { TeeConnectedMemberProfileRequest, TeeProfileFamily } from "../api/teeContracts";

const US_TO_SI: Readonly<Record<string, string>> = {
  "0.5": "12.7", "0.75": "19.05", "2": "50.8", "3": "76.2", "4": "101.6", "6": "152.4",
  "8": "203.2", "10": "254", "12": "304.8", "16": "406.4", "30": "762", "40": "1016", "-10": "-254",
};
const FORCE_SI: Readonly<Record<string, string>> = {
  "0": "0", "2": "8.896443230521", "-2": "-8.896443230521", "3.4641016151377544": "15.4090916819145687953847410212", "6": "26.689329691563",
};
function quantity(value: string, system: NodeUnitSystem): MultiRowQuantity {
  return { value: system === "SI" ? US_TO_SI[value] ?? value : value, unit: system === "SI" ? "mm" : "in" };
}
function vector(values: readonly [string, string, string], unit: string): NodeVector {
  return { x: values[0], y: values[1], z: values[2], unit };
}
function action(
  force: readonly [string, string, string],
  reference: readonly [string, string, string],
  system: NodeUnitSystem,
): NodeAction {
  const isSi = system === "SI";
  return {
    force_hvn: vector(force.map((value) => isSi ? String(FORCE_SI[value]) : value) as [string, string, string], isSi ? "kN" : "kip"),
    moment_hvn: vector(["0", "0", "0"], isSi ? "kN-mm" : "kip-in"),
    reference_hvn: vector(reference.map((value) => isSi ? US_TO_SI[value] ?? value : value) as [string, string, string], isSi ? "mm" : "in"),
  };
}
function group(system: NodeUnitSystem): NodeBoltGroup {
  return { row_count: 2, bolts_per_row: 2, pitch: quantity("2", system), gauge: quantity("2", system) };
}
export type CompleteHistoricalMultiMemberTeeBenchmark = HistoricalMultiMemberTeeRequest & {
  readonly upper_brace: NodeAngleSlot;
  readonly middle_beam: NodeBeamSlot;
  readonly lower_brace: NodeAngleSlot;
};

export function loadHistoricalMultiMemberTeeBenchmark(system: NodeUnitSystem): CompleteHistoricalMultiMemberTeeBenchmark {
  const isSi = system === "SI";
  const angle = (slot_id: "UPPER_BRACE" | "LOWER_BRACE", inclination: string, anchor: string, verticalForce: string) => ({
    slot_id, leg_y: quantity("6", system), leg_z: quantity("6", system), thickness: quantity("0.5", system),
    member_length: quantity("12", system), selected_profile_surface: "LEG_Y_OUTER" as const,
    inclination_degrees: inclination, profile_roll_degrees: "0", anchor_h: quantity("3", system),
    anchor_v: quantity(anchor, system), bolt_group: group(system),
    action: action(["3.4641016151377544", verticalForce, "0"], ["3", anchor, "0"], system),
    trim_enabled: false, trim_clearance: null,
  });
  return {
    orchestration_contract_version: "3.4A-RC1", request_id: `MULTI-MEMBER-TEE-${system}`,
    unit_system: system, source_length_unit: isSi ? "mm" : "in",
    connector_dimensions: { connector_length: quantity("30", system), flange_width: quantity("8", system), flange_thickness: quantity("0.5", system), stem_depth: quantity("6", system), stem_thickness: quantity("0.5", system) },
    connector_length_anchor: "CENTER", connector_length_anchor_position: quantity("0", system),
    support_dimensions: { member_length: quantity("40", system), depth: quantity("8", system), flange_width: quantity("8", system), web_thickness: quantity("0.5", system), flange_thickness: quantity("0.5", system) },
    support_group: group(system), support_reference_hvn: vector(["0", "0", "0"], isSi ? "mm" : "in"),
    bolt_diameter: quantity("0.5", system), hole_basis: isSi ? "SI_PRINTED" : "US_CUSTOMARY_PRINTED",
    upper_brace: angle("UPPER_BRACE", "30", "10", "2"),
    middle_beam: { slot_id: "MIDDLE_BEAM", depth: quantity("10", system), flange_width: quantity("8", system), web_thickness: quantity("0.5", system), flange_thickness: quantity("0.75", system), member_length: quantity("12", system), selected_profile_surface: "WEB_POS_FACE", inclination_degrees: "0", profile_roll_degrees: "0", anchor_h: quantity("3", system), anchor_v: quantity("0", system), bolt_group: group(system), action: action(["6", "0", "0"], ["3", "0", "0"], system), trim_enabled: false, trim_clearance: null },
    lower_brace: angle("LOWER_BRACE", "-30", "-10", "-2"),
  };
}

function profile(
  family: Exclude<TeeProfileFamily, "ROUND_HOLLOW_SECTION">,
  system: NodeUnitSystem,
  profileId: string,
): TeeConnectedMemberProfileRequest {
  const dimensions = (() => {
    if (family === "FLAT_PLATE") return { width: quantity("6", system), thickness: quantity("0.5", system), member_length: quantity("12", system) };
    if (family === "ANGLE") return { leg_y: quantity("6", system), leg_z: quantity("6", system), thickness: quantity("0.5", system), member_length: quantity("12", system) };
    if (family === "CHANNEL") return { depth: quantity("8", system), flange_width: quantity("4", system), web_thickness: quantity("0.5", system), flange_thickness: quantity("0.5", system), member_length: quantity("12", system) };
    if (family === "WIDE_FLANGE_I") return { depth: quantity("10", system), flange_width: quantity("8", system), web_thickness: quantity("0.5", system), flange_thickness: quantity("0.75", system), member_length: quantity("12", system) };
    if (family === "RECTANGULAR_HOLLOW_SECTION") return { depth: quantity("6", system), width: quantity("4", system), wall_thickness: quantity("0.5", system), member_length: quantity("12", system) };
    return { depth: quantity("6", system), width: quantity("4", system), member_length: quantity("12", system) };
  })();
  const surface = {
    FLAT_PLATE: "FACE_POS",
    ANGLE: "LEG_Y_OUTER",
    CHANNEL: "WEB_OUTER",
    WIDE_FLANGE_I: "WEB_POS_FACE",
    RECTANGULAR_HOLLOW_SECTION: "Y_POS_FACE",
    SOLID_RECTANGULAR_SECTION: "Y_POS_FACE",
  }[family] as TeeConnectedMemberProfileRequest["selected_profile_surface"];
  return { profile_id: profileId, role: "BRACE", profile_family: family, size_basis: "CUSTOM_DIMENSIONS", dimensions, profile_orientation: "ROTATION_0", selected_profile_surface: surface, material_kind: "PULTRUDED_FRP" };
}

export function initialMultiMemberTeeProfile(
  family: Exclude<TeeProfileFamily, "ROUND_HOLLOW_SECTION">,
  system: NodeUnitSystem,
  profileId: string,
): TeeConnectedMemberProfileRequest {
  return profile(family, system, profileId);
}

export function initialMultiMemberTeeSupport(
  target: SharedSupportTargetId,
  system: NodeUnitSystem,
): SharedSupportProfileRequest {
  const unit = system === "SI" ? "mm" : "in";
  const result = initialSharedSupport(target, unit, "multi-member-tee-support");
  result.member_length = quantity("16", system);
  if (target === "W_COLUMN_FLANGE" || target === "W_BEAM_FLANGE" || target === "W_COLUMN_WEB") {
    result.depth = quantity("8", system);
    result.flange_width = quantity("8", system);
    result.web_thickness = quantity("0.5", system);
    result.flange_thickness = quantity("0.75", system);
  } else if (target === "CHANNEL_COLUMN_WEB") {
    result.depth = quantity("8", system);
    result.flange_width = quantity("4", system);
    result.web_thickness = quantity("0.5", system);
    result.flange_thickness = quantity("0.5", system);
  } else if (target === "ANGLE_COLUMN_LEG") {
    result.leg_y = quantity("8", system);
    result.leg_z = quantity("8", system);
    result.thickness = quantity("0.5", system);
  } else if (target === "RECTANGULAR_HOLLOW_COLUMN_WALL") {
    result.width = quantity("10", system);
    result.depth = quantity("6", system);
    result.wall_thickness = quantity("0.5", system);
  } else {
    result.width = quantity("10", system);
    result.depth = quantity("6", system);
  }
  return result;
}

export type CompleteMultiMemberTeeBenchmark = ExpandedMultiMemberTeeRequest & {
  readonly upper_brace: NonNullable<ExpandedMultiMemberTeeRequest["upper_brace"]>;
  readonly middle_beam: NonNullable<ExpandedMultiMemberTeeRequest["middle_beam"]>;
  readonly lower_brace: NonNullable<ExpandedMultiMemberTeeRequest["lower_brace"]>;
};

export function loadMultiMemberTeeBenchmark(system: NodeUnitSystem): CompleteMultiMemberTeeBenchmark {
  const historical = loadHistoricalMultiMemberTeeBenchmark(system);
  const expanded = (slot: NodeAngleSlot | NodeBeamSlot, family: Exclude<TeeProfileFamily, "ROUND_HOLLOW_SECTION">) => ({
    slot_id: slot.slot_id,
    profile: profile(
      family,
      system,
      `multi-member-tee-${slot.slot_id.toLowerCase()}-profile`,
    ),
    inclination_degrees: slot.inclination_degrees,
    profile_roll_degrees: slot.profile_roll_degrees,
    anchor_h: slot.anchor_h,
    anchor_v: slot.anchor_v,
    bolt_group: slot.bolt_group,
    action: slot.action,
    trim_enabled: slot.trim_enabled,
    trim_clearance: slot.trim_clearance,
  });
  return {
    orchestration_contract_version: "3.4B-RC1",
    request_id: `MULTI-MEMBER-TEE-EXPANDED-${system}`,
    unit_system: historical.unit_system,
    source_length_unit: historical.source_length_unit,
    connector_dimensions: historical.connector_dimensions,
    connector_length_anchor: historical.connector_length_anchor,
    connector_length_anchor_position: historical.connector_length_anchor_position,
    support_target_id: "W_COLUMN_FLANGE",
    support_profile: initialMultiMemberTeeSupport("W_COLUMN_FLANGE", system),
    support_group: historical.support_group,
    support_reference_hvn: historical.support_reference_hvn,
    bolt_diameter: historical.bolt_diameter,
    hole_basis: historical.hole_basis,
    upper_brace: expanded(historical.upper_brace, "ANGLE"),
    middle_beam: expanded(historical.middle_beam, "WIDE_FLANGE_I"),
    lower_brace: expanded(historical.lower_brace, "ANGLE"),
  };
}
