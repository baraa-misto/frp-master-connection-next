import type { ChannelMomentSpliceDesignResponse, ChannelMomentSplicePreviewResponse, ChannelMomentSpliceVector, ChannelMomentSpliceVisualization } from "../src/api/channelMomentSpliceContracts";

const quantity = (value: string, unit = "in") => ({ value, unit });
const vector = (l: string, v: string, t: string, unit = "in"): ChannelMomentSpliceVector => ({ l: quantity(l, unit), v: quantity(v, unit), t: quantity(t, unit) });

export function channelMomentSpliceVisualizationFixture(system: "US_CUSTOMARY" | "SI" = "US_CUSTOMARY"): ChannelMomentSpliceVisualization {
  const unit = system === "SI" ? "mm" : "in";
  const force = system === "SI" ? "kN" : "kip";
  const moment = system === "SI" ? "kN-mm" : "kip-in";
  const scale = system === "SI" ? 25.4 : 1;
  const n = (value: number) => String(value * scale);
  const box = (component_id: string, role: string, l: number, v: number, t: number, sl: number, sv: number, st: number) => ({ component_id, role, center_l_v_t: vector(n(l), n(v), n(t), unit), size_l_v_t: vector(n(sl), n(sv), n(st), unit) });
  const boxes = [
    box("BEAM_A_TOP_FLANGE", "CHANNEL_TOP_FLANGE", -9.25, 3.75, 2, 18, 0.5, 4),
    box("BEAM_A_WEB", "CHANNEL_WEB", -9.25, 0, 0.25, 18, 7, 0.5),
    box("BEAM_A_BOTTOM_FLANGE", "CHANNEL_BOTTOM_FLANGE", -9.25, -3.75, 2, 18, 0.5, 4),
    box("BEAM_B_TOP_FLANGE", "CHANNEL_TOP_FLANGE", 9.25, 3.75, 2, 18, 0.5, 4),
    box("BEAM_B_WEB", "CHANNEL_WEB", 9.25, 0, 0.25, 18, 7, 0.5),
    box("BEAM_B_BOTTOM_FLANGE", "CHANNEL_BOTTOM_FLANGE", 9.25, -3.75, 2, 18, 0.5, 4),
    box("BACK_WEB_SPLICE_PLATE", "BACK_WEB_SPLICE_PLATE", 0, 0, -0.25, 16, 5.5, 0.5),
    box("OPENING_WEB_SPLICE_PLATE", "OPENING_WEB_SPLICE_PLATE", 0, 0, 0.75, 16, 5.5, 0.5),
    box("TOP_OUTER_FLANGE_SPLICE_PLATE", "TOP_OUTER_FLANGE_SPLICE_PLATE", 0, 4.25, 2, 16, 0.5, 4),
    box("TOP_INNER_FLANGE_SPLICE_PLATE", "TOP_INNER_FLANGE_SPLICE_PLATE", 0, 3.25, 2, 16, 0.5, 3),
    box("BOTTOM_OUTER_FLANGE_SPLICE_PLATE", "BOTTOM_OUTER_FLANGE_SPLICE_PLATE", 0, -4.25, 2, 16, 0.5, 4),
    box("BOTTOM_INNER_FLANGE_SPLICE_PLATE", "BOTTOM_INNER_FLANGE_SPLICE_PLATE", 0, -3.25, 2, 16, 0.5, 3),
  ];
  const bolts = Array.from({ length: 24 }, (_, index) => {
    const flange = index >= 8;
    const beam = index % 2 === 0 ? -1 : 1;
    const top = index < 16;
    const center = flange ? vector(n(beam * 4), n(top ? 3.75 : -3.75), n(index % 4 < 2 ? 1.25 : 2.75), unit) : vector(n(beam * 4), n(index % 4 < 2 ? -1.5 : 1.5), n(0.25), unit);
    return {
      bolt_id: `CHANNEL_BOLT_${String(index + 1)}`,
      group_id: `${flange ? "FLANGE" : "WEB"}_GROUP_${String(Math.floor(index / 2) + 1)}`,
      center_l_v_t: center,
      path_layers: flange ? ["OUTER_FLANGE_PLATE", "CHANNEL_FLANGE", "INNER_FLANGE_PLATE"] as const : ["BACK_WEB_SPLICE_PLATE", "CHANNEL_WEB", "OPENING_WEB_SPLICE_PLATE"] as const,
      stack_start_l_v_t: flange ? vector(center.l.value, n(top ? 4.75 : -4.75), center.t.value, unit) : vector(center.l.value, center.v.value, n(-0.75), unit),
      stack_end_l_v_t: flange ? vector(center.l.value, n(top ? 2.75 : -2.75), center.t.value, unit) : vector(center.l.value, center.v.value, n(1.25), unit),
    };
  });
  const material_regions = boxes.map((item) => ({ component_id: item.component_id, region_id: item.component_id, lw_axis: ["1", "0", "0"] as const, cw_axis: ["0", "1", "0"] as const, tt_axis: ["0", "0", "1"] as const }));
  return {
    frame_axes: ["L_CH", "V_CH", "T_CH"], joint_reference_l_v_t: vector("0", "0", "0", unit),
    channel_centroid_l_v_t: vector("0", "0", n(1.21875), unit), channel_shear_center_l_v_t: vector("0", "0", n(-1.878), unit),
    beam_end_planes_l: [quantity(n(-0.25), unit), quantity(n(0.25), unit)], boxes, bolts,
    web_bolt_diameter: quantity(n(0.5), unit), web_hole_diameter: quantity(n(0.563), unit), flange_bolt_diameter: quantity(n(0.5), unit), flange_hole_diameter: quantity(n(0.563), unit), material_regions,
    action_reference_l_v_t: vector("0", "0", n(1.21875), unit),
    applied_force_l_v_t: vector(system === "SI" ? "88.96443230521" : "20", system === "SI" ? "-44.482216152605" : "-10", "0", force),
    applied_moment_l_v_t: vector(system === "SI" ? "-3499" : "-30.97", "0", system === "SI" ? "11298.48290276167" : "100", moment),
    generated_centroidal_torsion: quantity(system === "SI" ? "-3499" : "-30.97", moment), xray_inner_components: true,
  };
}

export function channelMomentSplicePreviewFixture(status: "VALID" | "INVALID_GEOMETRY" = "VALID"): ChannelMomentSplicePreviewResponse {
  const component = (region_id: "TOP_FLANGE" | "WEB" | "BOTTOM_FLANGE", force: string, shear: string, localMoment: string, minorMoment: string) => ({
    region_id,
    wrench: { reference_lvt: vector("0", region_id === "TOP_FLANGE" ? "3.75" : region_id === "BOTTOM_FLANGE" ? "-3.75" : "0", "1.2"), force_lvt: vector(force, shear, "0", "kip"), moment_lvt: vector("0", "0", localMoment, "kip-in") },
    global_minor_moment: quantity(minorMoment, "kip-in"),
  });
  const branch = (flange_id: "TOP" | "BOTTOM", sign: string) => ({ flange_id, flange_force: quantity(sign, "kip"), flange_local_moment: quantity("0.5", "kip-in"), outer_force: quantity(flange_id === "TOP" ? "8.035" : "-2.702", "kip"), inner_total_force: quantity(flange_id === "TOP" ? "7.917" : "-2.584", "kip"), exact_force_equilibrium: true, exact_local_moment_equilibrium: true });
  const invalid = status === "INVALID_GEOMETRY";
  const result = {
    product_id: "CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE" as const, contract_version: "4.1B-RC1" as const,
    geometry_status: status, geometry_invalid_reasons: invalid ? ["POSITIVE_BEAM_END_GAP_REQUIRED"] : [], assembly_status: invalid ? "INVALID_GEOMETRY" as const : "NOT_EVALUATED" as const, design_check_ready: !invalid,
    slice6_result: {
      section_properties: { channel_centroid_t_absolute: quantity("1.21875") },
      shear_center: { method: "RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1", absolute_coordinate_t: quantity("-1.8784722222222222"), centroid_to_shear_center: quantity("-3.0972222222222222"), controlling_source_provenance: "PROJECT_CONTROLLED_RATIONAL_CHANNEL_SHEAR_CENTER_RC1" },
      components: [component("TOP_FLANGE", "15.95", "0.47", "0.44", "-19.45"), component("WEB", "2.10", "-10.94", "0.11", "-2.56"), component("BOTTOM_FLANGE", "-5.29", "0.47", "0.44", "6.45")],
      torsion_diagnostics: { generated_centroidal_torsion: quantity("-30.972222222222222", "kip-in"), web_free_torsion: quantity("-28.861111111111111", "kip-in") }, result_fingerprint: "slice6-fingerprint",
    },
    top_flange: branch("TOP", "15.95"), bottom_flange: branch("BOTTOM", "-5.29"),
    web_faces: { back_normal_force: quantity("1.05", "kip"), opening_normal_force: quantity("1.05", "kip"), back_major_shear: quantity("-19.0625", "kip"), opening_major_shear: quantity("9.0625", "kip"), web_free_torsion: quantity("-28.861111111111111", "kip-in"), exact_normal_force_recovery: true, exact_major_shear_recovery: true, exact_local_major_moment_recovery: true, exact_free_torsion_recovery: true, blind_equal_shear_assumption_used: false as const, method: "RATIONAL_CHANNEL_WEB_FACE_SHEAR_CENTER_COUPLE_DECOMPOSITION_RC1" },
    web_group_demands: Array.from({ length: 4 }, (_, index) => ({ group_id: `WEB_${String(index + 1)}` })), flange_group_demands: Array.from({ length: 8 }, (_, index) => ({ group_id: `FLANGE_${String(index + 1)}` })),
    equilibrium: { whole_connection_six_component_exact: true, beam_a_b_equal_opposite_complete_wrenches: true }, visualization: channelMomentSpliceVisualizationFixture(), rational_method_engineering_review_required: true as const, connection_element_qualification: "REQUIRED_2_3_2" as const,
    moment_connection_stiffness_classification: "NOT_EVALUATED" as const, moment_rotation_capacity: "NOT_EVALUATED" as const, full_strength_classification: "NOT_EVALUATED" as const, warping_connection_response: "NOT_EVALUATED" as const,
    disclaimer_id: "CHANNEL_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1", disclaimer_text: "Rational-method engineering review and Section 2.3.2 qualification are required.", engineering_fingerprint: "channel-engineering-fingerprint", application_fingerprint: "channel-application-fingerprint",
  };
  return { api_transport_schema_version: "4.1B-API-RC1", orchestration_contract_version: "4.1B-RC1", preview_schema_version: "4.1B-PREVIEW-RC1", request_id: "stage-4.1b-us_customary", geometry_status: status, geometry_invalid_reasons: result.geometry_invalid_reasons, assembly_status: result.assembly_status, ordinary_pass_allowed: false, resistance_evaluated: false, design_check_ready: !invalid, engineering_fingerprint: result.engineering_fingerprint, application_fingerprint: result.application_fingerprint, result };
}

export function channelMomentSpliceDesignFixture(): ChannelMomentSpliceDesignResponse {
  return { api_transport_schema_version: "4.1B-API-RC1", orchestration_contract_version: "4.1B-RC1", request_id: "stage-4.1b-us_customary", assembly_status: "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED", required_check_status: "RATIONAL_METHOD_REVIEW_REQUIRED", ordinary_pass_allowed: false, failed_check_ids: [], unavailable_check_ids: ["F593_COMMON_BOLT_DOUBLE_SHEAR"], result_fingerprint: "channel-design-fingerprint", result: { governing_utilization: "0.82", governing_check_id: "BACK_WEB_PLATE_BODY", disclaimer_id: "CHANNEL_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1", disclaimer_text: "Rational-method review required.", rational_method_engineering_review_required: true } };
}
