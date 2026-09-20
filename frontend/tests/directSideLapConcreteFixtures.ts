import type {
  DirectSideLapAnchorTrace,
  DirectSideLapDesignResponse,
  DirectSideLapPreviewResponse,
  SideLapVector,
  SideLapWrench,
} from "../src/api/directSideLapConcreteContracts";
import type { ClipAngleQuantity } from "../src/api/clipAngleContracts";

function q(value: string, unit: string): ClipAngleQuantity {
  return { value, unit, canonical_value: value, canonical_unit: unit };
}

function vector(values: readonly [string, string, string], unit: string): SideLapVector {
  return { l: q(values[0], unit), s: q(values[1], unit), n: q(values[2], unit) };
}

function wrench(): SideLapWrench {
  return {
    reference_lsn: vector(["-152.4", "0", "0"], "mm"),
    force_lsn: vector(["0", "-17792.886461042", "0"], "N"),
    moment_lsn: vector(["534794.8573973857", "0", "-2711635.8966628008"], "N-mm"),
    provenance: "exact Decimal translation",
  };
}

function anchor(id: string, coordinateL: string): DirectSideLapAnchorTrace {
  return {
    anchor_id: id,
    group_id: "DIRECT_SIDE_LAP_WALL_ANCHOR_GROUP",
    coordinate_lsn: vector([coordinateL, "0", "0"], "in"),
    edge_distances: {
      behind_wall_free_end: q(String(-Number(coordinateL)), "in"),
      behind_wall_back_end: q("40", "in"),
      negative_transverse_wall_edge: q("24", "in"),
      positive_transverse_wall_edge: q("24", "in"),
      negative_overlap_edge: q("4", "in"),
      positive_overlap_edge: q("8", "in"),
    },
    shank_start_lsn: vector([coordinateL, "0", "0.5"], "in"),
    shank_end_lsn: vector([coordinateL, "0", "-4"], "in"),
    penetrated_layers: ["CHANNEL_WEB", "CONCRETE_EMBEDMENT"],
    hardware_configuration: "EXTERIOR_NUT_WASHER_WITH_BLIND_EMBEDDED_SHANK",
    capacity_status: "EXTERNAL_DESIGN_REQUIRED",
  };
}

export function directSideLapPreviewFixture(
  status: "NOT_EVALUATED" | "FAIL" | "INVALID_GEOMETRY" = "NOT_EVALUATED",
): DirectSideLapPreviewResponse {
  const first = anchor("DIRECT-LAP-R1-A1", "-8");
  const second = anchor("DIRECT-LAP-R2-A1", "-4");
  const invalid = status === "INVALID_GEOMETRY";
  const visualization = {
    schema_version: "0.1.0-draft" as const,
    side_lap_frame: {
      l_axis: ["1", "0", "0"] as const,
      s_axis: ["0", "1", "0"] as const,
      n_axis: ["0", "0", "1"] as const,
    },
    boxes: [
      { id: "MEMBER:clip-angle-connected-member:WEB:0", owner_id: "clip-angle-connected-member", role: "WEB", center: [q("2", "in"), q("-0.25", "in"), q("0", "in")] as const, size_s: q("28", "in"), size_p: q("0.5", "in"), size_l: q("7", "in"), physical_element_id: "WEB", material_region_id: "WEB", basis: [["1", "0", "0"], ["0", "-1", "0"], ["0", "0", "-1"]] as const },
      { id: "MEMBER:clip-angle-connected-member:TOP_FLANGE:0", owner_id: "clip-angle-connected-member", role: "TOP_FLANGE", center: [q("2", "in"), q("-2", "in"), q("-3.75", "in")] as const, size_s: q("28", "in"), size_p: q("4", "in"), size_l: q("0.5", "in"), physical_element_id: "TOP_FLANGE", material_region_id: "FLANGES", basis: [["1", "0", "0"], ["0", "-1", "0"], ["0", "0", "-1"]] as const },
      { id: "MEMBER:clip-angle-connected-member:BOTTOM_FLANGE:0", owner_id: "clip-angle-connected-member", role: "BOTTOM_FLANGE", center: [q("2", "in"), q("-2", "in"), q("3.75", "in")] as const, size_s: q("28", "in"), size_p: q("4", "in"), size_l: q("0.5", "in"), physical_element_id: "BOTTOM_FLANGE", material_region_id: "FLANGES", basis: [["1", "0", "0"], ["0", "-1", "0"], ["0", "0", "-1"]] as const },
      { id: "direct-side-lap-concrete-wall", owner_id: "direct-side-lap-concrete-wall", role: "CONCRETE_WALL", center: [q("-24", "in"), q("4", "in"), q("0", "in")] as const, size_s: q("48", "in"), size_p: q("8", "in"), size_l: q("48", "in"), physical_element_id: null, material_region_id: null, basis: [["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"]] as const },
    ],
    material_regions: [
      { id: "clip-angle-connected-member:WEB:material-axes", physical_element_id: "WEB", material_region_id: "WEB", origin: [q("2", "in"), q("-2", "in"), q("0", "in")] as const, lw: ["1", "0", "0"] as const, cw: ["0", "0", "1"] as const, tt: ["0", "-1", "0"] as const },
      { id: "clip-angle-connected-member:TOP_FLANGE:material-axes", physical_element_id: "TOP_FLANGE", material_region_id: "FLANGES", origin: [q("2", "in"), q("-2", "in"), q("0", "in")] as const, lw: ["1", "0", "0"] as const, cw: ["0", "-1", "0"] as const, tt: ["0", "0", "-1"] as const },
      { id: "clip-angle-connected-member:BOTTOM_FLANGE:material-axes", physical_element_id: "BOTTOM_FLANGE", material_region_id: "FLANGES", origin: [q("2", "in"), q("-2", "in"), q("0", "in")] as const, lw: ["1", "0", "0"] as const, cw: ["0", "-1", "0"] as const, tt: ["0", "0", "-1"] as const },
    ],
    external_anchors: [first, second],
    external_anchor_geometry: { nominal_diameter: q("0.5", "in"), hole_diameter: q("0.563", "in"), specified_embedment: q("4", "in"), washer_outside_diameter: q("1.0625", "in"), washer_thickness: q("0.109", "in"), system_classification: "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR" as const },
    connected_profile_family: "CHANNEL" as const,
    selected_profile_surface: "WEB_OUTER" as const,
    member_start_l: q("-12", "in"), member_end_l: q("16", "in"), wall_free_end_l: q("0", "in"),
    overlap_interval_l: [q("-12", "in"), q("0", "in")] as const,
    action_reference_lsn: vector(["0", "0", "30.05666666666666666666666667"], "mm"),
    anchor_group_reference_lsn: vector(["-152.4", "0", "0"], "mm"),
    user_force_lsn: vector(["0", "-4", "0"], "kip"), user_moment_lsn: vector(["0", "0", "0"], "kip-in"),
    selected_wall_surface_id: "CONCRETE_WALL:FINITE_EXTERIOR_FACE" as const,
  };
  const result = {
    request_id: "STAGE-3.5B-G1-US_CUSTOMARY", orchestration_contract_version: "3.5B-RC1" as const,
    preview_schema_version: "0.1.0-draft" as const, connector_kind: "DIRECT_SIDE_LAP_ANGLE_CHANNEL_TO_CONCRETE_WALL" as const,
    geometry_status: invalid ? "INVALID_GEOMETRY" as const : "VALID" as const,
    geometry_invalid_reasons: invalid ? ["ANCHOR_OUTSIDE_PHYSICAL_SIDE_LAP_OVERLAP"] : [], assembly_status: status,
    ordinary_pass_allowed: false as const, resistance_evaluated: false, design_check_ready: !invalid,
    external_design_required: true as const, anchor_group_id: "DIRECT_SIDE_LAP_WALL_ANCHOR_GROUP" as const,
    anchor_group_centroid_lsn: vector(["-152.4", "0", "0"], "mm"), anchor_group_wrench: wrench(),
    nominal_in_plane_demand_status: "AVAILABLE_WITH_EXISTING_METHODS", supported_local_frp_failure_present: status === "FAIL",
    limitations: [["DIRECT_SIDE_LAP_CONNECTION_QUALIFICATION", "NOT_EVALUATED"], ["CONCRETE_SUBSTRATE_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"]] as const,
    warnings: [], external_anchor_handoff: { handoff_fingerprint: "a".repeat(64) }, external_anchor_handoff_json: '{"handoff_fingerprint":"' + "a".repeat(64) + '"}',
    canonical_input_fingerprint: "b".repeat(64), geometry_fingerprint: "c".repeat(64), engineering_fingerprint: "d".repeat(64), application_fingerprint: "e".repeat(64),
    visualization: invalid ? null : visualization,
  };
  return { api_transport_schema_version: "0.1.0-draft", orchestration_contract_version: "3.5B-RC1", preview_schema_version: "0.1.0-draft", request_id: result.request_id, geometry_status: result.geometry_status, geometry_invalid_reasons: result.geometry_invalid_reasons, assembly_status: status, ordinary_pass_allowed: false, resistance_evaluated: false, design_check_ready: !invalid, external_design_required: true, engineering_fingerprint: result.engineering_fingerprint, application_fingerprint: result.application_fingerprint, result };
}

export function directSideLapDesignFixture(): DirectSideLapDesignResponse {
  const preview = directSideLapPreviewFixture("FAIL").result;
  return { api_transport_schema_version: "0.1.0-draft", orchestration_contract_version: "3.5B-RC1", request_id: preview.request_id, assembly_status: "FAIL", required_check_status: "NOT_EVALUATED", ordinary_pass_allowed: false, external_design_required: true, supported_local_frp_failure_present: true, result_fingerprint: "f".repeat(64), result: { preview } };
}
