import type { MultiRowQuantity } from "./multirowContracts";

export interface WebSpliceVector {
  readonly l: MultiRowQuantity;
  readonly v: MultiRowQuantity;
  readonly t: MultiRowQuantity;
}

export interface WebSpliceWrench {
  readonly reference_l_v_t: WebSpliceVector;
  readonly force_l_v_t: WebSpliceVector;
  readonly moment_l_v_t: WebSpliceVector;
  readonly provenance: string;
}

export interface WebSpliceRequest {
  orchestration_contract_version: "3.6A-RC1" | "3.6B-RC2";
  request_id: string;
  unit_system: "US_CUSTOMARY" | "SI";
  source_length_unit: "in" | "mm";
  beam: {
    profile_family: "WIDE_FLANGE_I";
    depth: MultiRowQuantity;
    flange_width: MultiRowQuantity;
    web_thickness: MultiRowQuantity;
    flange_thickness: MultiRowQuantity;
    display_length_each_side: MultiRowQuantity;
  };
  beam_end_gap: MultiRowQuantity;
  splice_plate: {
    length: MultiRowQuantity;
    height: MultiRowQuantity;
    thickness: MultiRowQuantity;
    count: 2;
    locked_identical: true;
  };
  bolt_group: {
    rows: number;
    bolts_per_row: number;
    vertical_pitch: MultiRowQuantity;
    longitudinal_gauge: MultiRowQuantity;
    centroid_offset: MultiRowQuantity;
    locked_identical_mirror: true;
  };
  bolt_diameter: MultiRowQuantity;
  hole_diameter: MultiRowQuantity;
  transfer_force: {
    axial_force: MultiRowQuantity;
    major_shear: MultiRowQuantity;
    minor_shear: MultiRowQuantity;
  };
  user_moment_l_v_t: { readonly x: "0"; readonly y: "0"; readonly z: "0"; readonly unit: "kip-in" | "kN-mm" };
  flange_splice_enabled: false;
}

export interface WebSpliceVisualization {
  readonly frame_axes: readonly ["L_S", "V_S", "T_S"];
  readonly joint_reference_l_v_t: WebSpliceVector;
  readonly beam_end_planes_l: readonly [MultiRowQuantity, MultiRowQuantity];
  readonly boxes: readonly {
    readonly component_id: string;
    readonly role: string;
    readonly center_l_v_t: WebSpliceVector;
    readonly size_l_v_t: WebSpliceVector;
  }[];
  readonly bolts: readonly {
    readonly bolt_id: string;
    readonly group_id: string;
    readonly center_l_v_t: WebSpliceVector;
    readonly path_layers: readonly string[];
    readonly stack_start_l_v_t: WebSpliceVector;
    readonly stack_end_l_v_t: WebSpliceVector;
    readonly shank_length: MultiRowQuantity;
  }[];
  readonly bolt_diameter: MultiRowQuantity;
  readonly hole_diameter: MultiRowQuantity;
  readonly material_regions: readonly {
    readonly component_id: string;
    readonly region_id: string;
    readonly lw_axis: readonly [string, string, string];
    readonly cw_axis: readonly [string, string, string];
    readonly tt_axis: readonly [string, string, string];
  }[];
  readonly action_reference_l_v_t: WebSpliceVector;
  readonly applied_force_l_v_t: WebSpliceVector;
}

export interface WebSplicePreviewResult {
  readonly beam_a_group: { readonly group_id: string; readonly wrench: WebSpliceWrench; readonly group_fingerprint: string };
  readonly beam_b_group: { readonly group_id: string; readonly wrench: WebSpliceWrench; readonly group_fingerprint: string };
  readonly geometry_status: "VALID" | "INVALID_GEOMETRY";
  readonly geometry_invalid_reasons: readonly string[];
  readonly assembly_status: "NOT_EVALUATED" | "INVALID_GEOMETRY";
  readonly limitations: readonly string[];
  readonly visualization: WebSpliceVisualization;
  readonly engineering_fingerprint: string;
  readonly application_fingerprint: string;
  readonly clear_body_plan?: {
    readonly left_clear_boundary: MultiRowQuantity;
    readonly right_clear_boundary: MultiRowQuantity;
    readonly clear_body_length: MultiRowQuantity;
    readonly critical_section_ids: readonly string[];
    readonly exact_linear_envelope_proven: boolean;
    readonly rational_method: string;
    readonly panel_model: string;
    readonly slice4_commit: string;
    readonly slice4_method_ids: readonly string[];
    readonly physical_shear_plane_count: number;
    readonly bolt_source_authority_id: string;
    readonly bolt_source_authorized: boolean;
    readonly engineering_review_required: boolean;
    readonly qualification: string;
    readonly disclaimer_id: string;
  };
}

export interface WebSplicePreviewResponse {
  readonly api_transport_schema_version: "0.1.0-draft";
  readonly orchestration_contract_version: "3.6A-RC1" | "3.6B-RC2";
  readonly preview_schema_version: "0.1.0-draft" | "0.2.0-draft";
  readonly request_id: string;
  readonly geometry_status: "VALID" | "INVALID_GEOMETRY";
  readonly geometry_invalid_reasons: readonly string[];
  readonly assembly_status: "NOT_EVALUATED" | "INVALID_GEOMETRY";
  readonly ordinary_pass_allowed: false;
  readonly resistance_evaluated: false;
  readonly design_check_ready: boolean;
  readonly engineering_fingerprint: string;
  readonly application_fingerprint: string;
  readonly result: WebSplicePreviewResult;
}

export interface WebSpliceDesignResponse {
  readonly api_transport_schema_version: "0.1.0-draft";
  readonly orchestration_contract_version: "3.6A-RC1" | "3.6B-RC2";
  readonly request_id: string;
  readonly assembly_status: "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY" | "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED";
  readonly required_check_status: "FAIL" | "NOT_EVALUATED" | "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED";
  readonly ordinary_pass_allowed: false;
  readonly supported_local_checks_executed: boolean;
  readonly supported_local_failure_present: boolean;
  readonly local_check_ids: readonly string[];
  readonly failed_local_check_ids: readonly string[];
  readonly local_resistance_warnings: readonly string[];
  readonly result_fingerprint: string;
  readonly result: {
    readonly preview: WebSplicePreviewResult;
    readonly plate_body_interaction?: {
      readonly method: string;
      readonly panel_model: string;
      readonly status: "PASS_RATIONAL_METHOD" | "FAIL_RATIONAL_METHOD" | "NOT_EVALUATED";
      readonly governing_section_id: string | null;
      readonly governing_fiber_id: string | null;
      readonly governing_signed_normal_stress: MultiRowQuantity | null;
      readonly governing_signed_shear_stress: MultiRowQuantity | null;
      readonly tension_design_stress: MultiRowQuantity | null;
      readonly compression_design_stress: MultiRowQuantity | null;
      readonly shear_design_stress: MultiRowQuantity | null;
      readonly normal_utilization: string | null;
      readonly shear_utilization: string | null;
      readonly rational_utilization: string | null;
      readonly slice4_advisories: readonly string[];
      readonly engineering_review_required: boolean;
      readonly qualification: string;
    };
    readonly double_shear_results?: readonly {
      readonly bolt_id: string;
      readonly physical_shear_plane_count: number;
      readonly thread_condition: string;
      readonly source_authority_id: string;
      readonly source_authorized: boolean;
      readonly physical_in_plane_demand: MultiRowQuantity;
      readonly per_plane_demand: MultiRowQuantity;
      readonly per_plane_design_capacity: MultiRowQuantity | null;
      readonly two_plane_design_capacity: MultiRowQuantity | null;
      readonly utilization: string | null;
      readonly status: "PASS" | "FAIL" | "NOT_EVALUATED";
      readonly source_required_reason: string | null;
    }[];
    readonly double_shear_governing_bolt_id?: string | null;
    readonly double_shear_governing_utilization?: string | null;
    readonly double_shear_status?: "PASS" | "FAIL" | "NOT_EVALUATED";
    readonly rational_method_engineering_review_required?: boolean;
    readonly connection_element_qualification?: string;
    readonly disclaimer_id?: string;
  };
}
