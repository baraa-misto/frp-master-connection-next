import type { WebSpliceDesignResponse, WebSplicePreviewResponse, WebSpliceVector, WebSpliceVisualization } from "../src/api/webSpliceContracts";

const quantity = (value: string, unit: string) => ({ value, unit, canonical_value: value, canonical_unit: unit });
const vector = (l: string, v: string, t: string, unit: string): WebSpliceVector => ({ l: quantity(l, unit), v: quantity(v, unit), t: quantity(t, unit) });
const lengthVector = (l: string, v: string, t: string) => vector(l, v, t, "in");
const forceVector = (l: string, v: string, t: string) => vector(l, v, t, "kip");
const momentVector = (l: string, v: string, t: string) => vector(l, v, t, "kip-in");

export function webSpliceVisualizationFixture(): WebSpliceVisualization {
  const boxes = [
    { component_id: "BEAM_A_WEB", role: "FRP_WIDE_FLANGE_WEB", center_l_v_t: lengthVector("-9.25", "0", "0"), size_l_v_t: lengthVector("18", "9", "0.5") },
    { component_id: "BEAM_A_TOP_FLANGE", role: "FRP_WIDE_FLANGE_TOP_FLANGE", center_l_v_t: lengthVector("-9.25", "4.75", "0"), size_l_v_t: lengthVector("18", "0.5", "8") },
    { component_id: "BEAM_A_BOTTOM_FLANGE", role: "FRP_WIDE_FLANGE_BOTTOM_FLANGE", center_l_v_t: lengthVector("-9.25", "-4.75", "0"), size_l_v_t: lengthVector("18", "0.5", "8") },
    { component_id: "BEAM_B_WEB", role: "FRP_WIDE_FLANGE_WEB", center_l_v_t: lengthVector("9.25", "0", "0"), size_l_v_t: lengthVector("18", "9", "0.5") },
    { component_id: "BEAM_B_TOP_FLANGE", role: "FRP_WIDE_FLANGE_TOP_FLANGE", center_l_v_t: lengthVector("9.25", "4.75", "0"), size_l_v_t: lengthVector("18", "0.5", "8") },
    { component_id: "BEAM_B_BOTTOM_FLANGE", role: "FRP_WIDE_FLANGE_BOTTOM_FLANGE", center_l_v_t: lengthVector("9.25", "-4.75", "0"), size_l_v_t: lengthVector("18", "0.5", "8") },
    { component_id: "POSITIVE_WEB_SPLICE_PLATE", role: "FRP_WEB_SPLICE_PLATE", center_l_v_t: lengthVector("0", "0", "0.5"), size_l_v_t: lengthVector("16", "8", "0.5") },
    { component_id: "NEGATIVE_WEB_SPLICE_PLATE", role: "FRP_WEB_SPLICE_PLATE", center_l_v_t: lengthVector("0", "0", "-0.5"), size_l_v_t: lengthVector("16", "8", "0.5") },
  ];
  const centers = [["-5.5", "-1.5"], ["-2.5", "-1.5"], ["-5.5", "1.5"], ["-2.5", "1.5"], ["2.5", "-1.5"], ["5.5", "-1.5"], ["2.5", "1.5"], ["5.5", "1.5"]] as const;
  const bolts = centers.map(([l, v], index) => ({ bolt_id: `${index < 4 ? "BEAM_A" : "BEAM_B"}_B${String(index % 4 + 1)}`, group_id: index < 4 ? "BEAM_A_WEB_SPLICE_GROUP" : "BEAM_B_WEB_SPLICE_GROUP", center_l_v_t: lengthVector(l, v, "0"), path_layers: ["POSITIVE_WEB_SPLICE_PLATE", index < 4 ? "BEAM_A_WEB" : "BEAM_B_WEB", "NEGATIVE_WEB_SPLICE_PLATE"], stack_start_l_v_t: lengthVector(l, v, "0.75"), stack_end_l_v_t: lengthVector(l, v, "-0.75"), shank_length: quantity("1.5", "in") }));
  const regions = ["BEAM_A_WEB", "BEAM_A_TOP_FLANGE", "BEAM_A_BOTTOM_FLANGE", "BEAM_B_WEB", "BEAM_B_TOP_FLANGE", "BEAM_B_BOTTOM_FLANGE", "POSITIVE_WEB_SPLICE_PLATE", "NEGATIVE_WEB_SPLICE_PLATE"].map((region) => ({ component_id: region.startsWith("BEAM_A") ? "BEAM_A" : region.startsWith("BEAM_B") ? "BEAM_B" : region, region_id: region, lw_axis: [region.startsWith("BEAM_B") ? "-1" : "1", "0", "0"] as [string, string, string], cw_axis: ["0", "1", "0"] as [string, string, string], tt_axis: ["0", "0", region.startsWith("BEAM_B") ? "-1" : "1"] as [string, string, string] }));
  return { frame_axes: ["L_S", "V_S", "T_S"], joint_reference_l_v_t: lengthVector("0", "0", "0"), beam_end_planes_l: [quantity("-0.25", "in"), quantity("0.25", "in")], boxes, bolts, bolt_diameter: quantity("0.5", "in"), hole_diameter: quantity("0.563", "in"), material_regions: regions, action_reference_l_v_t: lengthVector("0", "0", "0"), applied_force_l_v_t: forceVector("0", "-10", "0") };
}

export function webSplicePreviewFixture(status: "VALID" | "INVALID_GEOMETRY" = "VALID"): WebSplicePreviewResponse {
  const wrenchA = { reference_l_v_t: lengthVector("-4", "0", "0"), force_l_v_t: forceVector("0", "-10", "0"), moment_l_v_t: momentVector("0", "0", "-40"), provenance: "cross product" };
  const wrenchB = { reference_l_v_t: lengthVector("4", "0", "0"), force_l_v_t: forceVector("0", "10", "0"), moment_l_v_t: momentVector("0", "0", "-40"), provenance: "cross product" };
  const invalid = status === "INVALID_GEOMETRY";
  return { api_transport_schema_version: "0.1.0-draft", orchestration_contract_version: "3.6A-RC1", preview_schema_version: "0.1.0-draft", request_id: "stage-3.6a-us_customary", geometry_status: status, geometry_invalid_reasons: invalid ? ["COMPLETE_HOLE_NOT_CONTAINED_IN_BEAM_WEB"] : [], assembly_status: invalid ? "INVALID_GEOMETRY" : "NOT_EVALUATED", ordinary_pass_allowed: false, resistance_evaluated: false, design_check_ready: !invalid, engineering_fingerprint: "engineering", application_fingerprint: "application", result: { beam_a_group: { group_id: "BEAM_A_WEB_SPLICE_GROUP", wrench: wrenchA, group_fingerprint: "group-a" }, beam_b_group: { group_id: "BEAM_B_WEB_SPLICE_GROUP", wrench: wrenchB, group_fingerprint: "group-b" }, geometry_status: status, geometry_invalid_reasons: invalid ? ["COMPLETE_HOLE_NOT_CONTAINED_IN_BEAM_WEB"] : [], assembly_status: invalid ? "INVALID_GEOMETRY" : "NOT_EVALUATED", limitations: ["WEB_SPLICE_PLATE_INTERGROUP_BODY_TRANSFER", "WEB_SPLICE_COMMON_BOLT_DOUBLE_SHEAR", "WEB_SPLICE_MEMBER_FLEXURAL_MOMENT_TRANSFER"], visualization: webSpliceVisualizationFixture(), engineering_fingerprint: "engineering", application_fingerprint: "application" } };
}

export function webSpliceDesignFixture(): WebSpliceDesignResponse {
  return { api_transport_schema_version: "0.1.0-draft", orchestration_contract_version: "3.6A-RC1", request_id: "stage-3.6a-us_customary", assembly_status: "NOT_EVALUATED", required_check_status: "NOT_EVALUATED", ordinary_pass_allowed: false, supported_local_checks_executed: true, supported_local_failure_present: false, local_check_ids: ["BEAM_A:PIN_BEARING"], failed_local_check_ids: [], local_resistance_warnings: ["WEB_SPLICE_PLATE_INTERGROUP_BODY_TRANSFER"], result_fingerprint: "result", result: { preview: webSplicePreviewFixture().result } };
}

export function webSpliceRC2PreviewFixture(): WebSplicePreviewResponse {
  const historical = webSplicePreviewFixture();
  return {
    ...historical,
    orchestration_contract_version: "3.6B-RC2",
    preview_schema_version: "0.2.0-draft",
    request_id: "stage-3.6b-us_customary",
    result: {
      ...historical.result,
      limitations: ["WEB_SPLICE_MEMBER_FLEXURAL_MOMENT_TRANSFER"],
      clear_body_plan: {
        left_clear_boundary: quantity("-2.2185", "in"),
        right_clear_boundary: quantity("2.2185", "in"),
        clear_body_length: quantity("4.437", "in"),
        critical_section_ids: ["SECTION_A_CLEAR_BOUNDARY", "SECTION_JOINT", "SECTION_B_CLEAR_BOUNDARY"],
        exact_linear_envelope_proven: true,
        rational_method: "RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1",
        panel_model: "RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1",
        slice4_commit: "a93aa5d127a51dc81a6c7cd108af15c44d59ff9f",
        slice4_method_ids: ["TENSION", "COMPRESSION", "SHEAR"],
        physical_shear_plane_count: 2,
        bolt_source_authority_id: "ASTM_F593_17_GROUP_2_316_316L",
        bolt_source_authorized: false,
        engineering_review_required: true,
        qualification: "REQUIRED_2_3_2",
        disclaimer_id: "WEB_SPLICE_RATIONAL_BODY_INTERACTION_DISCLAIMER_RC1",
      },
    },
  };
}

export function webSpliceRC2DesignFixture(): WebSpliceDesignResponse {
  const preview = webSpliceRC2PreviewFixture();
  return {
    api_transport_schema_version: "0.1.0-draft",
    orchestration_contract_version: "3.6B-RC2",
    request_id: preview.request_id,
    assembly_status: "NOT_EVALUATED",
    required_check_status: "NOT_EVALUATED",
    ordinary_pass_allowed: false,
    supported_local_checks_executed: true,
    supported_local_failure_present: false,
    local_check_ids: ["BEAM_A:PIN_BEARING"],
    failed_local_check_ids: [],
    local_resistance_warnings: [],
    result_fingerprint: "rc2-result",
    result: {
      preview: preview.result,
      plate_body_interaction: {
        method: "RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1",
        panel_model: "RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1",
        status: "PASS_RATIONAL_METHOD",
        governing_section_id: "SECTION_A_CLEAR_BOUNDARY",
        governing_fiber_id: "FIBER_POSITIVE_V",
        governing_signed_normal_stress: quantity("2.07984375", "ksi"),
        governing_signed_shear_stress: quantity("-1.25", "ksi"),
        tension_design_stress: quantity("15.015", "ksi"),
        compression_design_stress: quantity("11.825", "ksi"),
        shear_design_stress: quantity("5.6", "ksi"),
        normal_utilization: "0.175",
        shear_utilization: "0.223",
        rational_utilization: "0.398",
        slice4_advisories: ["C7_6_3_NARROW_PLATE_VALIDATION_CAUTION"],
        engineering_review_required: true,
        qualification: "REQUIRED_2_3_2",
      },
      double_shear_results: [{
        bolt_id: "BEAM_A_WEB_SPLICE_GROUP_B1",
        physical_shear_plane_count: 2,
        thread_condition: "EXCLUDED",
        source_authority_id: "ASTM_F593_17_GROUP_2_316_316L",
        source_authorized: false,
        physical_in_plane_demand: quantity("6.7185", "kip"),
        per_plane_demand: quantity("3.35925", "kip"),
        per_plane_design_capacity: null,
        two_plane_design_capacity: null,
        utilization: null,
        status: "NOT_EVALUATED",
        source_required_reason: "SOURCE_AUTHORIZED_FNV_REQUIRED",
      }],
      double_shear_governing_bolt_id: null,
      double_shear_governing_utilization: null,
      double_shear_status: "NOT_EVALUATED",
      rational_method_engineering_review_required: true,
      connection_element_qualification: "REQUIRED_2_3_2",
      disclaimer_id: "WEB_SPLICE_RATIONAL_BODY_INTERACTION_DISCLAIMER_RC1",
    },
  };
}
