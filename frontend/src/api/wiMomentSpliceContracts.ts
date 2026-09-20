import type { MultiRowQuantity } from "./multirowContracts";

export interface WIMomentSpliceVector {
  readonly l: MultiRowQuantity;
  readonly v: MultiRowQuantity;
  readonly t: MultiRowQuantity;
}

export interface WIMomentSpliceRequest {
  orchestration_contract_version: "4.1A-RC1";
  request_id: string;
  unit_system: "US_CUSTOMARY" | "SI";
  source_length_unit: "in" | "mm";
  profile_family: "WIDE_FLANGE_I";
  beams_locked_identical: boolean;
  beam: {
    profile_family: "WIDE_FLANGE_I";
    depth: MultiRowQuantity;
    flange_width: MultiRowQuantity;
    web_thickness: MultiRowQuantity;
    flange_thickness: MultiRowQuantity;
    display_length_each_side: MultiRowQuantity;
  };
  beam_end_gap: MultiRowQuantity;
  web_splice_plate: {
    length: MultiRowQuantity;
    height: MultiRowQuantity;
    thickness: MultiRowQuantity;
    count: number;
    locked_identical: boolean;
  };
  web_bolt_group: {
    rows: number;
    bolts_per_row: number;
    vertical_pitch: MultiRowQuantity;
    longitudinal_gauge: MultiRowQuantity;
    centroid_offset: MultiRowQuantity;
    locked_identical_mirror: boolean;
  };
  web_fastener: WIMomentSpliceFastener;
  flange_geometry: {
    plate_length: MultiRowQuantity;
    plate_thickness: MultiRowQuantity;
    inner_strip_width: MultiRowQuantity;
    bolts_per_line: number;
    longitudinal_pitch: MultiRowQuantity;
    group_centroid_distance: MultiRowQuantity;
    outer_plate_count_per_flange: number;
    inner_strip_count_per_flange: number;
    locked_top_bottom_identical: boolean;
    locked_inner_symmetric: boolean;
  };
  flange_fastener: WIMomentSpliceFastener;
  actions: {
    axial_force_l: MultiRowQuantity;
    major_shear_v: MultiRowQuantity;
    major_moment_t: MultiRowQuantity;
  };
}

export interface WIMomentSpliceFastener {
  bolt_diameter: MultiRowQuantity;
  hole_diameter: MultiRowQuantity;
  source_authority_id: string;
  thread_condition: "INCLUDED" | "EXCLUDED";
  nominal_shear_stress: MultiRowQuantity | null;
}

export interface WIMomentSpliceVisualization {
  readonly frame_axes: readonly [string, string, string];
  readonly joint_reference_l_v_t: WIMomentSpliceVector;
  readonly beam_end_planes_l: readonly [MultiRowQuantity, MultiRowQuantity];
  readonly boxes: readonly {
    readonly component_id: string;
    readonly role: string;
    readonly center_l_v_t: WIMomentSpliceVector;
    readonly size_l_v_t: WIMomentSpliceVector;
  }[];
  readonly bolts: readonly {
    readonly bolt_id: string;
    readonly group_id: string;
    readonly center_l_v_t: WIMomentSpliceVector;
    readonly path_layers: readonly [string, string, string];
    readonly stack_start_l_v_t: WIMomentSpliceVector;
    readonly stack_end_l_v_t: WIMomentSpliceVector;
  }[];
  readonly web_bolt_diameter: MultiRowQuantity;
  readonly web_hole_diameter: MultiRowQuantity;
  readonly flange_bolt_diameter: MultiRowQuantity;
  readonly flange_hole_diameter: MultiRowQuantity;
  readonly material_regions: readonly {
    readonly component_id: string;
    readonly region_id: string;
    readonly lw_axis: readonly [string, string, string];
    readonly cw_axis: readonly [string, string, string];
    readonly tt_axis: readonly [string, string, string];
  }[];
  readonly action_reference_l_v_t: WIMomentSpliceVector;
  readonly applied_force_l_v_t: WIMomentSpliceVector;
  readonly applied_moment_l_v_t: WIMomentSpliceVector;
}

export interface WIMomentSplicePreviewResult {
  readonly product_id: "WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE";
  readonly contract_version: "4.1A-RC1";
  readonly geometry_status: "VALID" | "INVALID_GEOMETRY";
  readonly geometry_invalid_reasons: readonly string[];
  readonly assembly_status: "NOT_EVALUATED" | "INVALID_GEOMETRY";
  readonly design_check_ready: boolean;
  readonly slice5_result: {
    readonly components: readonly {
      readonly region_id: "TOP_FLANGE" | "WEB" | "BOTTOM_FLANGE";
      readonly wrench: {
        readonly reference_lvt: WIMomentSpliceVector;
        readonly force_lvt: WIMomentSpliceVector;
        readonly moment_lvt: WIMomentSpliceVector;
      };
    }[];
    readonly couple_diagnostics: {
      readonly full_moment_over_z_reference_force: MultiRowQuantity;
      readonly full_moment_over_z_is_controlling: false;
    };
    readonly result_fingerprint: string;
  };
  readonly top_flange: WIMomentSpliceBranch;
  readonly bottom_flange: WIMomentSpliceBranch;
  readonly web_preview: {
    readonly beam_a_group: { readonly wrench: WIMomentSpliceWrench };
  };
  readonly flange_group_demands: readonly {
    readonly group_id: string;
    readonly per_bolt_plane_demands: readonly {
      readonly bolt_id: string;
      readonly force_l: MultiRowQuantity;
      readonly force_t: MultiRowQuantity;
    }[];
  }[];
  readonly flange_clear_body_length: MultiRowQuantity;
  readonly rational_face_sublayer_thickness: MultiRowQuantity;
  readonly equilibrium: {
    readonly whole_joint_exact: boolean;
    readonly beam_a_b_equal_opposite: boolean;
  };
  readonly visualization: WIMomentSpliceVisualization;
  readonly rational_method_engineering_review_required: true;
  readonly connection_element_qualification: "REQUIRED_2_3_2";
  readonly moment_connection_stiffness_classification: "NOT_EVALUATED";
  readonly moment_rotation_capacity: "NOT_EVALUATED";
  readonly full_strength_classification: "NOT_EVALUATED";
  readonly disclaimer_id: string;
  readonly disclaimer_text: string;
  readonly engineering_fingerprint: string;
  readonly application_fingerprint: string;
}

export interface WIMomentSpliceWrench {
  readonly reference_l_v_t: WIMomentSpliceVector;
  readonly force_l_v_t: WIMomentSpliceVector;
  readonly moment_l_v_t: WIMomentSpliceVector;
  readonly provenance: string;
}

export interface WIMomentSpliceBranch {
  readonly flange_id: "TOP" | "BOTTOM";
  readonly flange_force: MultiRowQuantity;
  readonly flange_local_moment: MultiRowQuantity;
  readonly outer_force: MultiRowQuantity;
  readonly inner_total_force: MultiRowQuantity;
  readonly inner_negative_force: MultiRowQuantity;
  readonly inner_positive_force: MultiRowQuantity;
  readonly exact_force_equilibrium: boolean;
  readonly exact_local_moment_equilibrium: boolean;
}

export interface WIMomentSplicePreviewResponse {
  readonly api_transport_schema_version: "4.1A-API-RC1";
  readonly orchestration_contract_version: "4.1A-RC1";
  readonly preview_schema_version: "4.1A-PREVIEW-RC1";
  readonly request_id: string;
  readonly geometry_status: "VALID" | "INVALID_GEOMETRY";
  readonly geometry_invalid_reasons: readonly string[];
  readonly assembly_status: "NOT_EVALUATED" | "INVALID_GEOMETRY";
  readonly ordinary_pass_allowed: false;
  readonly resistance_evaluated: false;
  readonly design_check_ready: boolean;
  readonly engineering_fingerprint: string;
  readonly application_fingerprint: string;
  readonly result: WIMomentSplicePreviewResult;
}

export interface WIMomentSpliceDesignResponse {
  readonly api_transport_schema_version: "4.1A-API-RC1";
  readonly orchestration_contract_version: "4.1A-RC1";
  readonly request_id: string;
  readonly assembly_status: "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY" | "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED";
  readonly required_check_status: string;
  readonly ordinary_pass_allowed: false;
  readonly failed_check_ids: readonly string[];
  readonly unavailable_check_ids: readonly string[];
  readonly result_fingerprint: string;
  readonly result: {
    readonly preview: WIMomentSplicePreviewResult;
    readonly governing_utilization: string | null;
    readonly governing_check_id: string | null;
    readonly disclaimer_id: string;
    readonly disclaimer_text: string;
    readonly rational_method_engineering_review_required: true;
  };
}
