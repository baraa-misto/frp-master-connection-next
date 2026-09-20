import type {
  ColumnBaseAnchorTrace,
  ColumnBaseDesignResponse,
  ColumnBasePreviewResponse,
  ColumnBaseVector,
  ColumnBaseVisualization,
  ColumnBaseWrench,
} from "../src/api/columnBaseWebAngleContracts";
import type { ClipAngleBoxTrace, ClipAngleQuantity } from "../src/api/clipAngleContracts";
import { loadColumnBaseWebAngleBenchmark } from "../src/fixtures/columnBaseWebAngleBenchmarks";

function q(value: string, unit = "in"): ClipAngleQuantity {
  return { value, unit, canonical_value: value, canonical_unit: unit };
}
function vector(s: string, t: string, longitudinal: string, unit = "in"): ColumnBaseVector {
  return { s: q(s, unit), t: q(t, unit), longitudinal: q(longitudinal, unit) };
}
function box(id: string, owner: string, role: string, center: readonly [string, string, string], size: readonly [string, string, string], element: string | null, region: string | null): ClipAngleBoxTrace {
  return { id, owner_id: owner, role, center: [q(center[0]), q(center[1]), q(center[2])], size_s: q(size[0]), size_p: q(size[1]), size_l: q(size[2]), physical_element_id: element, material_region_id: region, basis: [["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"]] };
}
function anchor(id: string, group: string, t: string, s: string): ColumnBaseAnchorTrace {
  return { anchor_id: id, group_id: group, coordinate_s_t_l: vector(s, t, "0"), axis_s_t_l: ["0", "0", "-1"], shank_start_s_t_l: vector(s, t, "0"), shank_end_s_t_l: vector(s, t, "-4"), exterior_washer_center_s_t_l: vector(s, t, "0.5545"), exterior_nut_reference_s_t_l: vector(s, t, "0.609"), penetrated_layers: ["BASE_ANGLE_HORIZONTAL_LEG", "CONCRETE_BASE"] };
}
function wrench(reference: readonly [string, string, string], force: readonly [string, string, string], moment: readonly [string, string, string]): ColumnBaseWrench {
  return { reference_s_t_l: vector(...reference), force_s_t_l: vector(force[0], force[1], force[2], "kip"), moment_s_t_l: vector(moment[0], moment[1], moment[2], "kip-in"), provenance: "EXACT_REFERENCE_TRANSLATION" };
}

function visualization(): ColumnBaseVisualization {
  const positive = anchor("POS-A1", "POSITIVE_BASE_ANCHOR_GROUP", "3.25", "0");
  const negative = anchor("NEG-A1", "NEGATIVE_BASE_ANCHOR_GROUP", "-3.25", "0");
  return {
    schema_version: "0.1.0-draft",
    profile_family: "WIDE_FLANGE_I",
    selected_surface: "WEB_POS_FACE",
    boxes: [
      box("CONCRETE-BASE", "concrete-base", "CONCRETE_BASE", ["0", "0", "-6"], ["36", "36", "12"], null, null),
      box("COLUMN-WEB", "column", "COLUMN_WEB", ["0", "0", "12"], ["9", "0.5", "24"], "COLUMN_WEB", "COLUMN_WEB_MATERIAL_REGION"),
      box("COLUMN-FLANGE-POS-S", "column", "COLUMN_FLANGE", ["4.75", "0", "12"], ["0.5", "8", "24"], "COLUMN_POSITIVE_FLANGE", "COLUMN_POSITIVE_FLANGE_MATERIAL_REGION"),
      box("COLUMN-FLANGE-NEG-S", "column", "COLUMN_FLANGE", ["-4.75", "0", "12"], ["0.5", "8", "24"], "COLUMN_NEGATIVE_FLANGE", "COLUMN_NEGATIVE_FLANGE_MATERIAL_REGION"),
      box("POSITIVE-BASE-ANGLE-VERTICAL", "positive-base-angle", "BASE_ANGLE_VERTICAL_LEG", ["0", "0.5", "3"], ["6", "0.5", "6"], "POSITIVE_BASE_ANGLE_VERTICAL_LEG", "POSITIVE_BASE_ANGLE_VERTICAL_MATERIAL_REGION"),
      box("POSITIVE-BASE-ANGLE-HORIZONTAL", "positive-base-angle", "BASE_ANGLE_HORIZONTAL_LEG", ["0", "3.25", "0.25"], ["6", "6", "0.5"], "POSITIVE_BASE_ANGLE_HORIZONTAL_LEG", "POSITIVE_BASE_ANGLE_HORIZONTAL_MATERIAL_REGION"),
      box("NEGATIVE-BASE-ANGLE-VERTICAL", "negative-base-angle", "BASE_ANGLE_VERTICAL_LEG", ["0", "-0.5", "3"], ["6", "0.5", "6"], "NEGATIVE_BASE_ANGLE_VERTICAL_LEG", "NEGATIVE_BASE_ANGLE_VERTICAL_MATERIAL_REGION"),
      box("NEGATIVE-BASE-ANGLE-HORIZONTAL", "negative-base-angle", "BASE_ANGLE_HORIZONTAL_LEG", ["0", "-3.25", "0.25"], ["6", "6", "0.5"], "NEGATIVE_BASE_ANGLE_HORIZONTAL_LEG", "NEGATIVE_BASE_ANGLE_HORIZONTAL_MATERIAL_REGION"),
    ],
    web_bolts: [{ bolt_id: "COLUMN-WEB-R1-B1", row_id: "ROW_1", bolt_line_id: "BOLT_LINE_1", width_coordinate: q("0"), length_coordinate: q("3"), global_center: [q("0"), q("0"), q("3")], axis: ["0", "1", "0"], layer_ids: ["POSITIVE_BASE_ANGLE_VERTICAL_LEG", "COLUMN_WEB", "NEGATIVE_BASE_ANGLE_VERTICAL_LEG"], stack_start: [q("0"), q("0.75"), q("3")], stack_end: [q("0"), q("-0.75"), q("3")] }],
    anchors: [positive, negative],
    web_bolt_diameter: q("0.5"), web_hole_diameter: q("0.563"),
    external_anchor_geometry: { nominal_diameter: q("0.5"), hole_diameter: q("0.563"), specified_embedment: q("4"), washer_outside_diameter: q("1.0625"), washer_thickness: q("0.109"), system_classification: "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR" },
    material_regions: [
      { region_id: "COLUMN_WEB_MATERIAL_REGION", physical_element_id: "COLUMN_WEB", lw: ["0", "0", "1"], cw: ["1", "0", "0"], tt: ["0", "1", "0"], source_id: "ICE_LOCKED_PULTRUDED_FRP", source_revision: "RC2" },
      { region_id: "COLUMN_POSITIVE_FLANGE_MATERIAL_REGION", physical_element_id: "COLUMN_POSITIVE_FLANGE", lw: ["0", "0", "1"], cw: ["0", "-1", "0"], tt: ["1", "0", "0"], source_id: "ICE_LOCKED_PULTRUDED_FRP", source_revision: "RC2" },
      { region_id: "COLUMN_NEGATIVE_FLANGE_MATERIAL_REGION", physical_element_id: "COLUMN_NEGATIVE_FLANGE", lw: ["0", "0", "1"], cw: ["0", "1", "0"], tt: ["-1", "0", "0"], source_id: "ICE_LOCKED_PULTRUDED_FRP", source_revision: "RC2" },
      { region_id: "POSITIVE_BASE_ANGLE_VERTICAL_MATERIAL_REGION", physical_element_id: "POSITIVE_BASE_ANGLE_VERTICAL_LEG", lw: ["1", "0", "0"], cw: ["0", "0", "1"], tt: ["0", "-1", "0"], source_id: "ICE_LOCKED_PULTRUDED_FRP", source_revision: "RC2" },
      { region_id: "POSITIVE_BASE_ANGLE_HORIZONTAL_MATERIAL_REGION", physical_element_id: "POSITIVE_BASE_ANGLE_HORIZONTAL_LEG", lw: ["1", "0", "0"], cw: ["0", "1", "0"], tt: ["0", "0", "1"], source_id: "ICE_LOCKED_PULTRUDED_FRP", source_revision: "RC2" },
      { region_id: "NEGATIVE_BASE_ANGLE_VERTICAL_MATERIAL_REGION", physical_element_id: "NEGATIVE_BASE_ANGLE_VERTICAL_LEG", lw: ["1", "0", "0"], cw: ["0", "0", "1"], tt: ["0", "1", "0"], source_id: "ICE_LOCKED_PULTRUDED_FRP", source_revision: "RC2" },
      { region_id: "NEGATIVE_BASE_ANGLE_HORIZONTAL_MATERIAL_REGION", physical_element_id: "NEGATIVE_BASE_ANGLE_HORIZONTAL_LEG", lw: ["1", "0", "0"], cw: ["0", "-1", "0"], tt: ["0", "0", "-1"], source_id: "ICE_LOCKED_PULTRUDED_FRP", source_revision: "RC2" },
    ],
    applied_force_s_t_l: vector("4", "0", "-20", "kip"), action_reference_s_t_l: vector("0", "0", "4"), selected_surfaces: ["COLUMN_WEB_POSITIVE_FACE", "COLUMN_WEB_NEGATIVE_FACE"],
  };
}

export function columnBasePreviewFixture(status: "NOT_EVALUATED" | "FAIL" | "INVALID_GEOMETRY" = "NOT_EVALUATED"): ColumnBasePreviewResponse {
  const request = loadColumnBaseWebAngleBenchmark("US_CUSTOMARY");
  const invalid = status === "INVALID_GEOMETRY";
  const combined = wrench(["0", "0", "0"], ["4", "0", "-20"], ["0", "16", "0"]);
  const component = { axial_mode: "COMPRESSION" as const, column_signed_axial_action: q("-20", "kip"), column_design_magnitude: q("20", "kip"), column_fraction: "1" as const, column_material_direction: "LW" as const, column_signed_material_direction: "-LW" as const, base_angle_system_signed_axial_action: q("-20", "kip"), base_angle_system_design_magnitude: q("20", "kip"), base_angle_system_fraction: "1" as const, base_angle_vertical_leg_material_direction: "CW" as const, base_angle_vertical_leg_signed_material_direction: "-CW" as const, positive_angle_signed_axial_action: q("-10", "kip"), negative_angle_signed_axial_action: q("-10", "kip"), single_angle_signed_axial_action: null, branch_fraction: "0.5", complete_branch_allocation: "EXACT_HALF_SHARING" as const, foundation_signed_axial_action: q("-20", "kip"), component_design_demands_summed_for_equilibrium: false as const };
  const branch = wrench(["0", "3.25", "0"], ["2", "0", "-10"], ["0", "8", "-6.5"]);
  const groups = [
    { group_id: "POSITIVE_BASE_ANCHOR_GROUP", side: "+T_C" as const, centroid_s_t_l: vector("0", "3.25", "0"), anchors: [], branch_wrench: branch, capacity_status: "EXTERNAL_DESIGN_REQUIRED" as const },
    { group_id: "NEGATIVE_BASE_ANCHOR_GROUP", side: "-T_C" as const, centroid_s_t_l: vector("0", "-3.25", "0"), anchors: [], branch_wrench: branch, capacity_status: "EXTERNAL_DESIGN_REQUIRED" as const },
  ];
  const result = { profile_family: "WIDE_FLANGE_I" as const, selected_surface: "WEB_POS_FACE", assembly: "DOUBLE_BASE_ANGLES" as const, single_side: "+T_C" as const, component_transfer: component, combined_foundation_wrench: combined, anchor_groups: groups, external_handoff: { handoff_fingerprint: "c".repeat(64) }, external_handoff_json: '{"schema_version":"3.7A-RC1"}', geometry_status: invalid ? "INVALID_GEOMETRY" as const : "VALID" as const, geometry_invalid_reasons: invalid ? ["ANGLE_INTERFERENCE"] : [], assembly_status: status, limitations: [["COLUMN_END_VS_BASE_ANGLE_BEARING_PARTITION", "EXTERNAL_DESIGN_REQUIRED"]] as const, warnings: [], engineering_fingerprint: "d".repeat(64), application_fingerprint: "e".repeat(64), visualization: invalid ? null : visualization() };
  return { api_transport_schema_version: "0.1.0-draft", orchestration_contract_version: "3.7A-RC1", preview_schema_version: "0.1.0-draft", request_id: request.request_id, geometry_status: result.geometry_status, geometry_invalid_reasons: result.geometry_invalid_reasons, assembly_status: status, ordinary_pass_allowed: false, resistance_evaluated: false, design_check_ready: !invalid, external_design_required: true, engineering_fingerprint: result.engineering_fingerprint, application_fingerprint: result.application_fingerprint, result };
}

export function columnBaseDesignFixture(): ColumnBaseDesignResponse {
  const preview = columnBasePreviewFixture("FAIL").result;
  return { api_transport_schema_version: "0.1.0-draft", orchestration_contract_version: "3.7A-RC1", request_id: "STAGE-3.7A-WIDE_FLANGE_I-US_CUSTOMARY", assembly_status: "FAIL", required_check_status: "NOT_EVALUATED", ordinary_pass_allowed: false, external_design_required: true, supported_local_failure_present: true, result_fingerprint: "f".repeat(64), result: { preview } };
}
