import type { MultiRowQuantity } from "./multirowContracts";

export interface ChannelMomentSpliceVector {
  readonly l: MultiRowQuantity;
  readonly v: MultiRowQuantity;
  readonly t: MultiRowQuantity;
}

export interface ChannelMomentSpliceFastener {
  bolt_diameter: MultiRowQuantity;
  hole_diameter: MultiRowQuantity;
  source_authority_id: string;
  thread_condition: "INCLUDED" | "EXCLUDED";
  nominal_shear_stress: MultiRowQuantity | null;
}

export interface ChannelMomentSpliceRequest {
  orchestration_contract_version: "4.1B-RC1";
  request_id: string;
  unit_system: "US_CUSTOMARY" | "SI";
  source_length_unit: "in" | "mm";
  beams_locked_identical: true;
  beams_same_orientation: true;
  opening_direction: "+T_CH";
  beam: {
    profile_family: "CHANNEL";
    depth: MultiRowQuantity;
    flange_width: MultiRowQuantity;
    web_thickness: MultiRowQuantity;
    flange_thickness: MultiRowQuantity;
    display_length_each_side: MultiRowQuantity;
    equal_flange: true;
    lipped: false;
    back_to_back: false;
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
  web_fastener: ChannelMomentSpliceFastener;
  flange_geometry: {
    plate_length: MultiRowQuantity;
    plate_thickness: MultiRowQuantity;
    inner_plate_width: MultiRowQuantity;
    transverse_gauge: MultiRowQuantity;
    bolts_per_transverse_line: number;
    longitudinal_pitch: MultiRowQuantity;
    group_centroid_distance: MultiRowQuantity;
    outer_plate_count_per_flange: 1;
    inner_plate_count_per_flange: 1;
    locked_top_bottom_identical: true;
  };
  flange_fastener: ChannelMomentSpliceFastener;
  actions: {
    axial_force_l: MultiRowQuantity;
    major_shear_v: MultiRowQuantity;
    major_moment_t: MultiRowQuantity;
  };
  shear_center: {
    method: "RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1";
    explicit_coordinate_t: null;
    explicit_provenance: null;
    include_rational_comparison: boolean;
  } | {
    method: "EXPLICIT_VERIFIED_CHANNEL_SHEAR_CENTER_RC1";
    explicit_coordinate_t: MultiRowQuantity;
    explicit_provenance: string;
    include_rational_comparison: boolean;
  };
}

export interface ChannelMomentSpliceBranch {
  readonly flange_id: "TOP" | "BOTTOM";
  readonly flange_force: MultiRowQuantity;
  readonly flange_local_moment: MultiRowQuantity;
  readonly outer_force: MultiRowQuantity;
  readonly inner_total_force: MultiRowQuantity;
  readonly exact_force_equilibrium: boolean;
  readonly exact_local_moment_equilibrium: boolean;
}

export interface ChannelMomentSpliceVisualization {
  readonly frame_axes: readonly [string, string, string];
  readonly joint_reference_l_v_t: ChannelMomentSpliceVector;
  readonly channel_centroid_l_v_t: ChannelMomentSpliceVector;
  readonly channel_shear_center_l_v_t: ChannelMomentSpliceVector;
  readonly beam_end_planes_l: readonly [MultiRowQuantity, MultiRowQuantity];
  readonly boxes: readonly {
    readonly component_id: string;
    readonly role: string;
    readonly center_l_v_t: ChannelMomentSpliceVector;
    readonly size_l_v_t: ChannelMomentSpliceVector;
  }[];
  readonly bolts: readonly {
    readonly bolt_id: string;
    readonly group_id: string;
    readonly center_l_v_t: ChannelMomentSpliceVector;
    readonly path_layers: readonly [string, string, string];
    readonly stack_start_l_v_t: ChannelMomentSpliceVector;
    readonly stack_end_l_v_t: ChannelMomentSpliceVector;
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
  readonly action_reference_l_v_t: ChannelMomentSpliceVector;
  readonly applied_force_l_v_t: ChannelMomentSpliceVector;
  readonly applied_moment_l_v_t: ChannelMomentSpliceVector;
  readonly generated_centroidal_torsion: MultiRowQuantity;
  readonly xray_inner_components: true;
}

export interface ChannelMomentSplicePreviewResult {
  readonly product_id: "CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE";
  readonly contract_version: "4.1B-RC1";
  readonly geometry_status: "VALID" | "INVALID_GEOMETRY";
  readonly geometry_invalid_reasons: readonly string[];
  readonly assembly_status: "NOT_EVALUATED" | "INVALID_GEOMETRY";
  readonly design_check_ready: boolean;
  readonly slice6_result: {
    readonly section_properties: { readonly channel_centroid_t_absolute: MultiRowQuantity };
    readonly shear_center: {
      readonly method: string;
      readonly absolute_coordinate_t: MultiRowQuantity;
      readonly centroid_to_shear_center: MultiRowQuantity;
      readonly controlling_source_provenance: string;
    };
    readonly components: readonly {
      readonly region_id: "TOP_FLANGE" | "WEB" | "BOTTOM_FLANGE";
      readonly wrench: {
        readonly reference_lvt: ChannelMomentSpliceVector;
        readonly force_lvt: ChannelMomentSpliceVector;
        readonly moment_lvt: ChannelMomentSpliceVector;
      };
      readonly global_minor_moment: MultiRowQuantity;
    }[];
    readonly torsion_diagnostics: {
      readonly generated_centroidal_torsion: MultiRowQuantity;
      readonly web_free_torsion: MultiRowQuantity;
    };
    readonly result_fingerprint: string;
  };
  readonly top_flange: ChannelMomentSpliceBranch;
  readonly bottom_flange: ChannelMomentSpliceBranch;
  readonly web_faces: {
    readonly back_normal_force: MultiRowQuantity;
    readonly opening_normal_force: MultiRowQuantity;
    readonly back_major_shear: MultiRowQuantity;
    readonly opening_major_shear: MultiRowQuantity;
    readonly web_free_torsion: MultiRowQuantity;
    readonly exact_normal_force_recovery: boolean;
    readonly exact_major_shear_recovery: boolean;
    readonly exact_local_major_moment_recovery: boolean;
    readonly exact_free_torsion_recovery: boolean;
    readonly blind_equal_shear_assumption_used: false;
    readonly method: string;
  };
  readonly web_group_demands: readonly { readonly group_id: string }[];
  readonly flange_group_demands: readonly { readonly group_id: string }[];
  readonly equilibrium: {
    readonly whole_connection_six_component_exact: boolean;
    readonly beam_a_b_equal_opposite_complete_wrenches: boolean;
  };
  readonly visualization: ChannelMomentSpliceVisualization;
  readonly rational_method_engineering_review_required: true;
  readonly connection_element_qualification: "REQUIRED_2_3_2";
  readonly moment_connection_stiffness_classification: "NOT_EVALUATED";
  readonly moment_rotation_capacity: "NOT_EVALUATED";
  readonly full_strength_classification: "NOT_EVALUATED";
  readonly warping_connection_response: "NOT_EVALUATED";
  readonly disclaimer_id: string;
  readonly disclaimer_text: string;
  readonly engineering_fingerprint: string;
  readonly application_fingerprint: string;
}

export interface ChannelMomentSplicePreviewResponse {
  readonly api_transport_schema_version: "4.1B-API-RC1";
  readonly orchestration_contract_version: "4.1B-RC1";
  readonly preview_schema_version: "4.1B-PREVIEW-RC1";
  readonly request_id: string;
  readonly geometry_status: "VALID" | "INVALID_GEOMETRY";
  readonly geometry_invalid_reasons: readonly string[];
  readonly assembly_status: "NOT_EVALUATED" | "INVALID_GEOMETRY";
  readonly ordinary_pass_allowed: false;
  readonly resistance_evaluated: false;
  readonly design_check_ready: boolean;
  readonly engineering_fingerprint: string;
  readonly application_fingerprint: string;
  readonly result: ChannelMomentSplicePreviewResult;
}

export interface ChannelMomentSpliceDesignResponse {
  readonly api_transport_schema_version: "4.1B-API-RC1";
  readonly orchestration_contract_version: "4.1B-RC1";
  readonly request_id: string;
  readonly assembly_status: "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY" | "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED";
  readonly required_check_status: string;
  readonly ordinary_pass_allowed: false;
  readonly failed_check_ids: readonly string[];
  readonly unavailable_check_ids: readonly string[];
  readonly result_fingerprint: string;
  readonly result: {
    readonly governing_utilization: string | null;
    readonly governing_check_id: string | null;
    readonly disclaimer_id: string;
    readonly disclaimer_text: string;
    readonly rational_method_engineering_review_required: true;
  };
}
