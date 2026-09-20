import type {
  WIMomentSpliceDesignResponse,
  WIMomentSplicePreviewResponse,
  WIMomentSpliceVector,
  WIMomentSpliceVisualization,
} from "../src/api/wiMomentSpliceContracts";

const quantity = (value: string, unit = "in") => ({ value, unit });
const vector = (l: string, v: string, t: string, unit = "in"): WIMomentSpliceVector => ({
  l: quantity(l, unit), v: quantity(v, unit), t: quantity(t, unit),
});

export function wiMomentSpliceVisualizationFixture(system: "US_CUSTOMARY" | "SI" = "US_CUSTOMARY"): WIMomentSpliceVisualization {
  const unit = system === "SI" ? "mm" : "in";
  const force = system === "SI" ? "kN" : "kip";
  const moment = system === "SI" ? "kN-mm" : "kip-in";
  const scale = system === "SI" ? 25.4 : 1;
  const n = (value: number) => String(value * scale);
  const box = (component_id: string, role: string, l: number, v: number, t: number, sl: number, sv: number, st: number) => ({
    component_id, role, center_l_v_t: vector(n(l), n(v), n(t), unit), size_l_v_t: vector(n(sl), n(sv), n(st), unit),
  });
  const boxes = [
    box("BEAM_A_TOP_FLANGE", "BEAM_TOP_FLANGE", -9.25, 4.75, 0, 18, 0.5, 8),
    box("BEAM_A_WEB", "BEAM_WEB", -9.25, 0, 0, 18, 9, 0.5),
    box("BEAM_A_BOTTOM_FLANGE", "BEAM_BOTTOM_FLANGE", -9.25, -4.75, 0, 18, 0.5, 8),
    box("BEAM_B_TOP_FLANGE", "BEAM_TOP_FLANGE", 9.25, 4.75, 0, 18, 0.5, 8),
    box("BEAM_B_WEB", "BEAM_WEB", 9.25, 0, 0, 18, 9, 0.5),
    box("BEAM_B_BOTTOM_FLANGE", "BEAM_BOTTOM_FLANGE", 9.25, -4.75, 0, 18, 0.5, 8),
    box("WEB_SPLICE_PLATE_POSITIVE", "WEB_SPLICE_PLATE", 0, 0, 0.5, 16, 8, 0.5),
    box("WEB_SPLICE_PLATE_NEGATIVE", "WEB_SPLICE_PLATE", 0, 0, -0.5, 16, 8, 0.5),
    box("TOP_OUTER_FLANGE_SPLICE_PLATE", "OUTER_FLANGE_SPLICE_PLATE", 0, 5.25, 0, 16, 0.5, 8),
    box("TOP_INNER_NEGATIVE_FLANGE_SPLICE_PLATE", "INNER_FLANGE_SPLICE_PLATE", 0, 4.25, -2.5, 16, 0.5, 3),
    box("TOP_INNER_POSITIVE_FLANGE_SPLICE_PLATE", "INNER_FLANGE_SPLICE_PLATE", 0, 4.25, 2.5, 16, 0.5, 3),
    box("BOTTOM_OUTER_FLANGE_SPLICE_PLATE", "OUTER_FLANGE_SPLICE_PLATE", 0, -5.25, 0, 16, 0.5, 8),
    box("BOTTOM_INNER_NEGATIVE_FLANGE_SPLICE_PLATE", "INNER_FLANGE_SPLICE_PLATE", 0, -4.25, -2.5, 16, 0.5, 3),
    box("BOTTOM_INNER_POSITIVE_FLANGE_SPLICE_PLATE", "INNER_FLANGE_SPLICE_PLATE", 0, -4.25, 2.5, 16, 0.5, 3),
  ];
  const bolts = Array.from({ length: 24 }, (_, index) => {
    const flange = index >= 8;
    const side = index % 2 === 0 ? -1 : 1;
    const top = index < 16;
    const center = flange
      ? vector(n(side * (2.5 + (index % 4))), n(top ? 4.75 : -4.75), n(index % 3 === 0 ? -2.5 : 2.5), unit)
      : vector(n(side * 4), n(index % 4 < 2 ? -1.5 : 1.5), "0", unit);
    return {
      bolt_id: `BOLT_${String(index + 1)}`,
      group_id: `${flange ? "FLANGE" : "WEB"}_GROUP_${String(Math.floor(index / 2) + 1)}`,
      center_l_v_t: center,
      path_layers: flange
        ? ["OUTER_FLANGE_PLATE", "BEAM_FLANGE", "INNER_FLANGE_STRIP"] as const
        : ["WEB_PLATE_NEGATIVE", "BEAM_WEB", "WEB_PLATE_POSITIVE"] as const,
      stack_start_l_v_t: flange ? vector(center.l.value, n(top ? 5.75 : -5.75), center.t.value, unit) : vector(center.l.value, center.v.value, n(-1), unit),
      stack_end_l_v_t: flange ? vector(center.l.value, n(top ? 3.75 : -3.75), center.t.value, unit) : vector(center.l.value, center.v.value, n(1), unit),
    };
  });
  const material_regions = boxes.map((item) => ({
    component_id: item.component_id,
    region_id: item.component_id,
    lw_axis: ["1", "0", "0"] as const,
    cw_axis: ["0", "1", "0"] as const,
    tt_axis: ["0", "0", "1"] as const,
  }));
  return {
    frame_axes: ["L_S", "V_S", "T_S"], joint_reference_l_v_t: vector("0", "0", "0", unit),
    beam_end_planes_l: [quantity(n(-0.25), unit), quantity(n(0.25), unit)], boxes, bolts,
    web_bolt_diameter: quantity(n(0.5), unit), web_hole_diameter: quantity(n(0.563), unit),
    flange_bolt_diameter: quantity(n(0.5), unit), flange_hole_diameter: quantity(n(0.563), unit),
    material_regions, action_reference_l_v_t: vector("0", "0", "0", unit),
    applied_force_l_v_t: vector(system === "SI" ? "88.96443230521" : "20", system === "SI" ? "-44.482216152605" : "-10", "0", force),
    applied_moment_l_v_t: vector("0", "0", system === "SI" ? "11298.48290276167" : "100", moment),
  };
}

export function wiMomentSplicePreviewFixture(status: "VALID" | "INVALID_GEOMETRY" = "VALID"): WIMomentSplicePreviewResponse {
  const wrench = (region: "TOP_FLANGE" | "WEB" | "BOTTOM_FLANGE", force: string, shear: string, localMoment: string) => ({
    region_id: region,
    wrench: { reference_lvt: vector("0", region === "TOP_FLANGE" ? "4.75" : region === "BOTTOM_FLANGE" ? "-4.75" : "0", "0"), force_lvt: vector(force, shear, "0", "kip"), moment_lvt: vector("0", "0", localMoment, "kip-in") },
  });
  const branch = (flange_id: "TOP" | "BOTTOM", sign: string) => ({
    flange_id, flange_force: quantity(sign, "kip"), flange_local_moment: quantity("25", "kip-in"),
    outer_force: quantity(flange_id === "TOP" ? "20" : "-20", "kip"), inner_total_force: quantity(flange_id === "TOP" ? "5" : "-5", "kip"),
    inner_negative_force: quantity(flange_id === "TOP" ? "2.5" : "-2.5", "kip"), inner_positive_force: quantity(flange_id === "TOP" ? "2.5" : "-2.5", "kip"),
    exact_force_equilibrium: true, exact_local_moment_equilibrium: true,
  });
  const invalid = status === "INVALID_GEOMETRY";
  const result = {
    product_id: "WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE" as const, contract_version: "4.1A-RC1" as const,
    geometry_status: status, geometry_invalid_reasons: invalid ? ["BEAM_END_GAP_MUST_BE_POSITIVE"] : [],
    assembly_status: invalid ? "INVALID_GEOMETRY" as const : "NOT_EVALUATED" as const, design_check_ready: !invalid,
    slice5_result: {
      components: [wrench("TOP_FLANGE", "25", "1", "25"), wrench("WEB", "0", "-12", "50"), wrench("BOTTOM_FLANGE", "-5", "1", "25")],
      couple_diagnostics: { full_moment_over_z_reference_force: quantity("10.526315789473684210526315789473684210526315789474", "kip"), full_moment_over_z_is_controlling: false as const },
      result_fingerprint: "slice5-fingerprint",
    },
    top_flange: branch("TOP", "25"), bottom_flange: branch("BOTTOM", "-5"),
    web_preview: { beam_a_group: { wrench: { reference_l_v_t: vector("-4", "0", "0"), force_l_v_t: vector("0", "-12", "0", "kip"), moment_l_v_t: vector("0", "0", "2", "kip-in"), provenance: "SLICE5_WEB" } } },
    flange_group_demands: Array.from({ length: 12 }, (_, index) => ({ group_id: `FLANGE_GROUP_${String(index + 1)}`, per_bolt_plane_demands: [{ bolt_id: `BOLT_${String(index + 9)}`, force_l: quantity(index % 2 === 0 ? "3" : "1", "kip"), force_t: quantity("0", "kip") }] })),
    flange_clear_body_length: quantity("0.5"), rational_face_sublayer_thickness: quantity("0.25"),
    equilibrium: { whole_joint_exact: true, beam_a_b_equal_opposite: true }, visualization: wiMomentSpliceVisualizationFixture(),
    rational_method_engineering_review_required: true as const, connection_element_qualification: "REQUIRED_2_3_2" as const,
    moment_connection_stiffness_classification: "NOT_EVALUATED" as const, moment_rotation_capacity: "NOT_EVALUATED" as const, full_strength_classification: "NOT_EVALUATED" as const,
    disclaimer_id: "STAGE_4_1A_RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED", disclaimer_text: "Rational-method engineering review and report disclaimer required.",
    engineering_fingerprint: "engineering-fingerprint", application_fingerprint: "application-fingerprint",
  };
  return {
    api_transport_schema_version: "4.1A-API-RC1", orchestration_contract_version: "4.1A-RC1", preview_schema_version: "4.1A-PREVIEW-RC1",
    request_id: "stage-4.1a-us_customary", geometry_status: status, geometry_invalid_reasons: result.geometry_invalid_reasons,
    assembly_status: result.assembly_status, ordinary_pass_allowed: false, resistance_evaluated: false, design_check_ready: !invalid,
    engineering_fingerprint: result.engineering_fingerprint, application_fingerprint: result.application_fingerprint, result,
  };
}

export function wiMomentSpliceDesignFixture(): WIMomentSpliceDesignResponse {
  return {
    api_transport_schema_version: "4.1A-API-RC1", orchestration_contract_version: "4.1A-RC1", request_id: "stage-4.1a-us_customary",
    assembly_status: "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED", required_check_status: "RATIONAL_METHOD_REVIEW_REQUIRED", ordinary_pass_allowed: false,
    failed_check_ids: [], unavailable_check_ids: ["F593_COMMON_BOLT_DOUBLE_SHEAR"], result_fingerprint: "design-fingerprint",
    result: { preview: wiMomentSplicePreviewFixture().result, governing_utilization: "0.75", governing_check_id: "TOP_OUTER_PLATE_BODY", disclaimer_id: "STAGE_4_1A_RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED", disclaimer_text: "Rational-method engineering review and report disclaimer required.", rational_method_engineering_review_required: true },
  };
}
