import type { MultiRowQuantity } from "./multirowContracts";
import type { SharedSupportProfileRequest, SharedSupportTargetId } from "./sharedSupportContracts";
import type {
  FullThroughBoltTrace,
  SelectedSupportFlange,
  TeeProfileFamily,
  TeeProfileOrientation,
  TeeProfileSurface,
} from "./teeContracts";

export type ClipAngleHand = "POSITIVE_S_SIDE" | "NEGATIVE_S_SIDE";
export type ClipAngleSupportRole = "W_COLUMN_FLANGE" | "W_BEAM_FLANGE";
export type ClipAngleConnectedRole = "BRACE" | "BEAM";
export type ClipAngleLengthAnchor = "CENTER" | "POSITIVE_L_END" | "NEGATIVE_L_END";
export type ClipAnglePlacementMode =
  | "EDGE_DISTANCE_CONTROLLED"
  | "GROUP_OFFSET_CONTROLLED";

export interface ClipAngleProfileRequest {
  profile_id: string;
  role: ClipAngleConnectedRole;
  profile_family: Exclude<TeeProfileFamily, "ROUND_HOLLOW_SECTION">;
  size_basis: "CUSTOM_DIMENSIONS";
  dimensions: Record<string, MultiRowQuantity> & { member_length: MultiRowQuantity };
  profile_orientation: TeeProfileOrientation;
  selected_profile_surface: Exclude<TeeProfileSurface, null>;
}

export interface ClipAngleBoltLayoutRequest {
  row_count: number;
  bolts_per_row: number;
  pitch: MultiRowQuantity;
  gauge: MultiRowQuantity;
  heel_edge_distance: MultiRowQuantity;
  free_edge_distance: MultiRowQuantity;
  negative_end_distance: MultiRowQuantity;
  positive_end_distance: MultiRowQuantity;
  placement_mode?: ClipAnglePlacementMode;
  length_offset?: MultiRowQuantity | null;
  width_offset?: MultiRowQuantity | null;
}

export interface ClipAngleRequest {
  orchestration_contract_version: "3.3C2-RC1";
  request_id: string;
  unit_system: "US_CUSTOMARY" | "SI";
  source_length_unit: "in" | "mm";
  hand: ClipAngleHand;
  support_target_id: SharedSupportTargetId;
  support_profile: SharedSupportProfileRequest;
  connector_dimensions: {
    connected_leg_width: MultiRowQuantity;
    support_leg_width: MultiRowQuantity;
    thickness: MultiRowQuantity;
    connector_length: MultiRowQuantity;
  };
  connected_member_profile: ClipAngleProfileRequest;
  interface_a_layout: ClipAngleBoltLayoutRequest;
  interface_b_layout: ClipAngleBoltLayoutRequest;
  bolt_diameter: MultiRowQuantity;
  hole_diameter: MultiRowQuantity;
  hole_basis: "US_CUSTOMARY_PRINTED" | "SI_PRINTED";
  global_force: { x: string; y: string; z: string; unit: "kip" | "kN" };
  global_moment: { x: string; y: string; z: string; unit: "kip-in" | "kN-mm" };
  global_reference_point: { x: string; y: string; z: string; unit: "in" | "mm" };
  connected_member_inclination_degrees: string;
  connected_member_end_trim_enabled: boolean;
  connected_member_end_clearance: MultiRowQuantity | null;
  connector_length_anchor: ClipAngleLengthAnchor;
  connector_length_anchor_position: MultiRowQuantity;
  connector_material: "PULTRUDED_FRP";
  fastener_material: "STAINLESS_STEEL_316";
  fastener_snapshot_id: "ASTM_F593_17_GROUP_2_316_316L";
}

export interface LegacyClipAngleRequest extends Omit<
  ClipAngleRequest,
  "orchestration_contract_version" | "support_target_id" | "support_profile"
> {
  orchestration_contract_version: "3.3A-RC1";
  support_role: ClipAngleSupportRole;
  selected_support_flange: SelectedSupportFlange;
  support_dimensions: {
    member_length: MultiRowQuantity;
    overall_depth: MultiRowQuantity;
    flange_width: MultiRowQuantity;
    web_thickness: MultiRowQuantity;
    flange_thickness: MultiRowQuantity;
  };
}

export interface ClipAngleQuantity extends MultiRowQuantity {
  canonical_value: string;
  canonical_unit: string;
}

export interface ClipAngleBoltTrace {
  bolt_id: string;
  row_id: string;
  bolt_line_id: string;
  width_coordinate: ClipAngleQuantity;
  length_coordinate: ClipAngleQuantity;
  global_center: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity];
  axis: readonly [string, string, string];
  layer_ids: readonly string[];
  stack_start: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity];
  stack_end: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity];
}

export interface ClipAngleClearanceTrace {
  heel: ClipAngleQuantity;
  free_edge: ClipAngleQuantity;
  positive_length_end: ClipAngleQuantity;
  negative_length_end: ClipAngleQuantity;
  minimum: ClipAngleQuantity;
  governing_bolt_id: string;
  governing_boundary_id: string;
  exact_deficit: ClipAngleQuantity | null;
  geometry_valid: boolean;
}

export interface ClipAnglePlacementTrace {
  interface_id: string;
  bolt_group_id: string;
  width_axis: readonly [string, string, string];
  length_axis: readonly [string, string, string];
  normal_axis: readonly [string, string, string];
  width_coordinates: readonly ClipAngleQuantity[];
  length_coordinates: readonly ClipAngleQuantity[];
  bolts: readonly ClipAngleBoltTrace[];
  clearances: ClipAngleClearanceTrace;
  geometry_fingerprint: string;
}

export interface ClipAngleInterfaceResult {
  interface_id: string;
  physical_name: string;
  bolt_group_id: string;
  normal_component: ClipAngleQuantity;
  normal_action_supported: boolean;
  automatic_axis_tension_generated: false;
  prying_generated: false;
  demand: {
    availability: string;
    method_applicability: string;
    qualification: string;
    scenarios: readonly {
      residual_moment: ClipAngleQuantity;
      per_bolt: readonly {
        bolt_id: string;
        total_force_magnitude: ClipAngleQuantity;
      }[];
    }[];
    input_fingerprint: string;
    result_fingerprint: string;
  };
  resistance: {
    automatic_handoff_results: readonly { overall_disposition: string; coverage: string }[];
    automatic_group_mode_integration: { overall_disposition: string } | null;
  } | null;
  placement: ClipAnglePlacementTrace;
  interface_fingerprint: string;
}

export interface ClipAngleBoxTrace {
  id: string;
  owner_id: string;
  role: string;
  center: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity];
  size_s: ClipAngleQuantity;
  size_p: ClipAngleQuantity;
  size_l: ClipAngleQuantity;
  physical_element_id: string | null;
  material_region_id: string | null;
  basis: readonly [
    readonly [string, string, string],
    readonly [string, string, string],
    readonly [string, string, string],
  ];
}

export interface ClipAngleMaterialRegionTrace {
  region_id: string;
  physical_element_id: string;
  lw: readonly [string, string, string];
  cw: readonly [string, string, string];
  tt: readonly [string, string, string];
  source_id: string;
  source_revision: string;
}

export interface ClipAngleProfileMaterialRegionTrace {
  id: string;
  physical_element_id: string;
  material_region_id: string;
  origin: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity];
  lw: readonly [string, string, string];
  cw: readonly [string, string, string];
  tt: readonly [string, string, string];
}

export interface ClipAngleSupportProfileTrace {
  target_id: SharedSupportTargetId;
  profile_id: string;
  profile_family: Exclude<TeeProfileFamily, "FLAT_PLATE" | "ROUND_HOLLOW_SECTION">;
  role: "COLUMN" | "BEAM";
  dimensions: Record<string, string>;
  orientation: TeeProfileOrientation;
  selected_surface: Exclude<TeeProfileSurface, null>;
}

export interface ClipAngleTriangleMeshTrace {
  id: string;
  owner_id: string;
  role: string;
  physical_element_id: string;
  material_region_id: string;
  points: readonly (readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity])[];
}

export interface ClipAngleVisualization {
  schema_version: "0.1.0-draft";
  semantic_frame: {
    s_axis: readonly [string, string, string];
    p_axis: readonly [string, string, string];
    l_axis: readonly [string, string, string];
    handedness: string;
  };
  connected_member_profile_id: string;
  connected_member_role: ClipAngleConnectedRole;
  connected_member_profile_family: ClipAngleProfileRequest["profile_family"];
  connected_member_profile_orientation: TeeProfileOrientation;
  boxes: readonly ClipAngleBoxTrace[];
  meshes: readonly ClipAngleTriangleMeshTrace[];
  interface_a_bolts: readonly ClipAngleBoltTrace[];
  interface_b_bolts: readonly ClipAngleBoltTrace[];
  bolt_diameter: ClipAngleQuantity;
  hole_diameter: ClipAngleQuantity;
  material_regions: readonly ClipAngleMaterialRegionTrace[];
  connected_member_material_regions: readonly ClipAngleProfileMaterialRegionTrace[];
  selected_support_surface_id: string;
  selected_connected_surface_id: string;
  trim: {
    enabled: boolean;
    reference_plane_id: string;
    reference_plane_origin: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity];
    reference_plane_normal: readonly [string, string, string];
    cut_plane_id: string | null;
    cut_plane_origin: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity] | null;
    cut_plane_normal: readonly [string, string, string] | null;
    measured_plane_clearance: ClipAngleQuantity | null;
    interference_status: string;
    geometry_valid: boolean;
    trimmed_member_geometry_identity: string | null;
    fabricated_trim_edge_ids: readonly string[];
    fabricated_trim_edge_id: string | null;
    bolt_clearances: readonly {
      bolt_id: string;
      center_to_trim_edge: ClipAngleQuantity;
      hole_edge_to_trim_edge: ClipAngleQuantity;
      trim_edge_id: string;
    }[];
    governing_bolt_id: string | null;
    governing_trim_edge_id: string | null;
    minimum_hole_edge_clearance: ClipAngleQuantity | null;
    exact_deficit: ClipAngleQuantity | null;
  };
  global_force: { x: ClipAngleQuantity; y: ClipAngleQuantity; z: ClipAngleQuantity };
  global_moment: { x: ClipAngleQuantity; y: ClipAngleQuantity; z: ClipAngleQuantity };
  global_reference_point: { x: ClipAngleQuantity; y: ClipAngleQuantity; z: ClipAngleQuantity };
  support_target_id: SharedSupportTargetId;
  support_profile: ClipAngleSupportProfileTrace;
  support_material_regions: readonly ClipAngleProfileMaterialRegionTrace[];
  rectangular_full_through_paths: readonly FullThroughBoltTrace[];
}

export interface ClipAnglePreviewResult {
  request_id: string;
  orchestration_contract_version: "3.3C2-RC1";
  preview_schema_version: "0.1.0-draft";
  connector_kind: "SINGLE_CLIP_ANGLE";
  hand: ClipAngleHand;
  support_role: ClipAngleSupportRole;
  interface_a: ClipAngleInterfaceResult;
  interface_b: ClipAngleInterfaceResult;
  connector_body_required_check: "SINGLE_CLIP_ANGLE_CONNECTOR_BODY_RESISTANCE";
  connector_body_status: "NOT_EVALUATED";
  geometry_status: "VALID" | "INVALID_GEOMETRY";
  geometry_invalid_reasons: readonly string[];
  assembly_status: "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY";
  ordinary_pass_allowed: false;
  resistance_evaluated: boolean;
  design_check_ready: boolean;
  warnings: readonly string[];
  engineering_fingerprint: string;
  visualization: ClipAngleVisualization | null;
  support_target_id: SharedSupportTargetId;
  rectangular_full_through_paths: readonly FullThroughBoltTrace[];
  design_limitations: readonly string[];
}

export interface ClipAnglePreviewResponse {
  api_transport_schema_version: "0.1.0-draft";
  orchestration_contract_version: "3.3C2-RC1";
  preview_schema_version: "0.1.0-draft";
  request_id: string;
  geometry_status: ClipAnglePreviewResult["geometry_status"];
  geometry_invalid_reasons: readonly string[];
  assembly_status: ClipAnglePreviewResult["assembly_status"];
  ordinary_pass_allowed: false;
  resistance_evaluated: false;
  design_check_ready: boolean;
  warnings: readonly string[];
  engineering_fingerprint: string;
  result: ClipAnglePreviewResult;
}

export interface ClipAngleDesignResponse {
  api_transport_schema_version: "0.1.0-draft";
  orchestration_contract_version: "3.3C2-RC1";
  request_id: string;
  assembly_status: ClipAnglePreviewResult["assembly_status"];
  connector_body_status: "NOT_EVALUATED";
  ordinary_pass_allowed: false;
  supported_interface_failure_present: boolean;
  result_fingerprint: string;
  result: {
    preview: ClipAnglePreviewResult;
    interface_a: ClipAngleInterfaceResult;
    interface_b: ClipAngleInterfaceResult;
    assembly_status: ClipAnglePreviewResult["assembly_status"];
  };
}
