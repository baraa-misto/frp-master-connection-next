import type { VisualizationSnapshot } from "./contracts";
import type {
  AutomaticDemandResult,
  AutomaticHandoffResult,
  MultiRowDesignResponse,
  MultiRowPreviewResponse,
  MultiRowQuantity,
} from "./multirowContracts";
import type { SharedSupportProfileRequest, SharedSupportTargetId } from "./sharedSupportContracts";

export type TeeSupportRole = "COLUMN" | "BEAM";
export type SelectedSupportFlange = "POSITIVE_LOCAL_Z" | "NEGATIVE_LOCAL_Z";
export type TeeProfileFamily =
  | "ANGLE"
  | "CHANNEL"
  | "WIDE_FLANGE_I"
  | "RECTANGULAR_HOLLOW_SECTION"
  | "SOLID_RECTANGULAR_SECTION"
  | "FLAT_PLATE"
  | "ROUND_HOLLOW_SECTION";
export type TeeProfileOrientation =
  | "ROTATION_0"
  | "ROTATION_90"
  | "ROTATION_180"
  | "ROTATION_270";
export type TeeBoltPlacementMode =
  | "EDGE_DISTANCE_CONTROLLED"
  | "GROUP_OFFSET_CONTROLLED";
export type TeeConnectorLengthAnchor =
  | "CENTER"
  | "POSITIVE_L_END"
  | "NEGATIVE_L_END";
export type TeeProfileSurface =
  | "LEG_Y_OUTER"
  | "LEG_Z_OUTER"
  | "WEB_OUTER"
  | "WEB_POS_FACE"
  | "WEB_NEG_FACE"
  | "FLANGE_POS_OUTER"
  | "FLANGE_NEG_OUTER"
  | "Y_POS_FACE"
  | "Y_NEG_FACE"
  | "Z_POS_FACE"
  | "Z_NEG_FACE"
  | "FACE_POS"
  | "FACE_NEG";

export interface TeeConnectedMemberProfileRequest {
  profile_id: string;
  role: "BRACE";
  profile_family: TeeProfileFamily;
  size_basis: "CUSTOM_DIMENSIONS";
  dimensions: Record<string, MultiRowQuantity> & { member_length: MultiRowQuantity };
  profile_orientation: TeeProfileOrientation;
  selected_profile_surface: TeeProfileSurface;
  material_kind: "PULTRUDED_FRP";
}

export interface TeeConnectedMemberProfileTrace {
  profile_id: string;
  member_id: string;
  role: "BRACE";
  profile_family: TeeProfileFamily;
  size_basis: "CUSTOM_DIMENSIONS";
  dimensions: Record<string, string>;
  profile_orientation: TeeProfileOrientation;
  selected_profile_surface: TeeProfileSurface;
  material_kind: "PULTRUDED_FRP";
  member_profile_fingerprint: string;
  profile_geometry_fingerprint: string;
  surface_patch_id: string;
  physical_element_role: string;
  brace_inclination_degrees: string;
  brace_inclination_sine: string;
  brace_inclination_cosine: string;
  brace_placement_frame: {
    origin: { x: string; y: string; z: string };
    x_axis: { x: string; y: string; z: string };
    y_axis: { x: string; y: string; z: string };
    z_axis: { x: string; y: string; z: string };
  };
}

export interface TeeBoltLayoutRequest {
  row_count: number;
  bolts_per_row: number;
  pitch: MultiRowQuantity;
  gauge: MultiRowQuantity;
  unloaded_end_distance: MultiRowQuantity;
  loaded_end_distance: MultiRowQuantity;
  negative_side_distance: MultiRowQuantity;
  positive_side_distance: MultiRowQuantity;
  placement_mode?: TeeBoltPlacementMode;
  vertical_offset?: MultiRowQuantity;
  horizontal_offset?: MultiRowQuantity;
}

export interface TeeInterfacePlacementTrace {
  datum_id: string;
  datum_point: { x: string; y: string; z: string };
  vertical_axis: { x: string; y: string; z: string };
  horizontal_axis: { x: string; y: string; z: string };
  normal_axis: { x: string; y: string; z: string };
  placement_mode: TeeBoltPlacementMode;
  vertical_offset: MultiRowQuantity;
  horizontal_offset: MultiRowQuantity;
  equivalent_edge_distances: {
    row_count: number;
    bolts_per_row: number;
    pitch: string;
    gauge: string;
    unloaded_end_distance: string;
    loaded_end_distance: string;
    negative_side_distance: string;
    positive_side_distance: string;
    placement_mode: TeeBoltPlacementMode;
    vertical_offset: string | null;
    horizontal_offset: string | null;
  };
  clearances: {
    vertical_positive: MultiRowQuantity;
    vertical_negative: MultiRowQuantity;
    horizontal_positive: MultiRowQuantity;
    horizontal_negative: MultiRowQuantity;
    minimum: MultiRowQuantity;
    governing_bolt_id: string;
    governing_boundary_id: string;
    exact_deficit: MultiRowQuantity | null;
    geometry_valid: boolean;
    minimum_complete_hole_containment: MultiRowQuantity | null;
    tee_positive_end_coordinate: MultiRowQuantity;
    tee_negative_end_coordinate: MultiRowQuantity;
    tee_positive_end_complete_hole_clearance: MultiRowQuantity;
    tee_negative_end_complete_hole_clearance: MultiRowQuantity;
    governing_tee_end_id: "TEE_POSITIVE_L_END" | "TEE_NEGATIVE_L_END";
    governing_tee_end_bolt_id: string;
    minimum_tee_end_complete_hole_clearance: MultiRowQuantity;
  };
  physical_geometry_fingerprint: string;
  method_compatibility:
    | "COMPATIBLE"
    | "ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN";
  bolt_centers_hvn: { x: string; y: string; z: string }[];
}

export interface TeeConnectorRequest {
  orchestration_contract_version: "3.3C2-RC1";
  request_id: string;
  unit_system: "US_CUSTOMARY" | "SI";
  source_length_unit: "in" | "mm";
  support_target_id: SharedSupportTargetId;
  support_profile: SharedSupportProfileRequest;
  connector_dimensions: {
    connector_length: MultiRowQuantity;
    flange_width: MultiRowQuantity;
    flange_thickness: MultiRowQuantity;
    stem_depth: MultiRowQuantity;
    stem_thickness: MultiRowQuantity;
  };
  connected_member_profile: TeeConnectedMemberProfileRequest;
  interface_a_layout: TeeBoltLayoutRequest;
  interface_b_layout: TeeBoltLayoutRequest;
  bolt_diameter: MultiRowQuantity;
  hole_basis: "US_CUSTOMARY_PRINTED" | "SI_PRINTED";
  global_force: { x: string; y: string; z: string; unit: "kip" | "kN" };
  global_moment: { x: string; y: string; z: string; unit: "kip-in" | "kN-mm" };
  global_reference_point: { x: string; y: string; z: string; unit: "in" | "mm" };
  brace_inclination_degrees: string;
  connected_member_end_trim_enabled: boolean;
  connected_member_end_clearance: MultiRowQuantity | null;
  connector_length_anchor: TeeConnectorLengthAnchor;
  connector_length_anchor_position: MultiRowQuantity;
  connector_material: "PULTRUDED_FRP";
  fastener_material: "STAINLESS_STEEL_316";
  fastener_snapshot_id: "ASTM_F593_17_GROUP_2_316_316L";
}

export interface TeeMemberEndTrimTrace {
  enabled: boolean;
  normalized_clearance: MultiRowQuantity | null;
  reference_plane_id: "TEE_FLANGE_INNER_CLEARANCE_PLANE";
  reference_plane_origin: { x: string; y: string; z: string };
  reference_plane_normal: { x: string; y: string; z: string };
  cut_plane_id: "CONNECTED_MEMBER_END_CUT_PLANE" | null;
  cut_plane_origin: { x: string; y: string; z: string } | null;
  cut_plane_normal: { x: string; y: string; z: string } | null;
  measured_plane_clearance: MultiRowQuantity | null;
  interference_status:
    | "CLEAR"
    | "INTERFERENCE_DETECTED"
    | "TRIMMED_CLEAR"
    | "REMAINING_INTERFERENCE";
  interfering_physical_element_ids: string[];
  trimmed_member_geometry_identity: string | null;
  fabricated_trim_edge_ids: string[];
  bolt_clearances: {
    bolt_id: string;
    center_to_trim_edge: MultiRowQuantity;
    hole_edge_to_trim_edge: MultiRowQuantity;
    trim_edge_id: string;
  }[];
  governing_bolt_id: string | null;
  governing_trim_edge_id: string | null;
  minimum_hole_edge_clearance: MultiRowQuantity | null;
  exact_deficit: MultiRowQuantity | null;
  recovery_guidance: string | null;
  geometry_valid: boolean;
}

export interface TeeLongitudinalPlacementTrace {
  tee_longitudinal_datum_id: "TEE_TEMPLATE_LONGITUDINAL_DATUM";
  datum_point: { x: string; y: string; z: string };
  longitudinal_axis: { x: string; y: string; z: string };
  connector_length_anchor: TeeConnectorLengthAnchor;
  connector_length_anchor_position: MultiRowQuantity;
  body_center_coordinate: MultiRowQuantity;
  positive_end_coordinate: MultiRowQuantity;
  negative_end_coordinate: MultiRowQuantity;
  body_geometry_fingerprint: string;
}

export interface TeeInterfaceResult {
  interface_id: string;
  bolt_group_id: string;
  normal_component: MultiRowQuantity | null;
  automatic_axis_tension_generated: false;
  normal_action_supported: boolean;
  preview: MultiRowPreviewResponse;
  design: MultiRowDesignResponse | null;
  interface_fingerprint: string;
  placement: TeeInterfacePlacementTrace;
}

export interface TeeVisualization {
  schema_version: "0.3.0-draft";
  base_connection: VisualizationSnapshot;
  interface_b_connection: VisualizationSnapshot;
  interface_zones: VisualizationSnapshot["interface_zones"];
  interface_a_bolts: VisualizationSnapshot["bolt"][];
  interface_b_bolts: VisualizationSnapshot["bolt"][];
  selected_support_surface_id: string;
  connected_member_profile: TeeConnectedMemberProfileTrace;
  selected_connected_surface_id: TeeProfileSurface;
  selected_connected_surface_patch_id: string;
  support_target_id: SharedSupportTargetId;
  support_profile: {
    target_id: SharedSupportTargetId;
    profile_family: TeeProfileFamily;
    selected_profile_surface: TeeProfileSurface;
  };
  rectangular_full_through_paths: readonly FullThroughBoltTrace[];
}

export interface FullThroughBoltTrace {
  path: {
    bolt_id: string;
    segments: readonly {
      kind: "MATERIAL_LAYER" | "FREE_SHANK_SPAN";
      identity: string;
      length: string;
    }[];
  };
  hardware: {
    bolt_id: string;
    shank_length: string;
    head_location: "EXTERIOR_NEAR_SIDE";
    nut_location: "EXTERIOR_FAR_SIDE";
    washer_locations: readonly ["EXTERIOR_NEAR_SIDE", "EXTERIOR_FAR_SIDE"];
    physical_bolt_count: 1;
    continuous_shank_count: 1;
    internal_hardware_count: 0;
  };
  physical_start_point: { readonly x: string; readonly y: string; readonly z: string };
  physical_end_point: { readonly x: string; readonly y: string; readonly z: string };
  geometry_valid: boolean;
  path_fingerprint: string;
}

export interface TeePreviewResult {
  request_id: string;
  orchestration_contract_version: "3.3C2-RC1";
  preview_schema_version: "0.3.0-draft";
  support_role: TeeSupportRole;
  selected_support_flange: SelectedSupportFlange;
  connector_dimensions: Record<string, string>;
  tee_longitudinal_placement: TeeLongitudinalPlacementTrace;
  connected_member_profile: TeeConnectedMemberProfileTrace;
  connected_member_end_trim: TeeMemberEndTrimTrace;
  material_authority: {
    connector_material_family: "PULTRUDED_FRP";
    fastener_material_family: "STAINLESS_STEEL_316";
    fastener_snapshot_id: "ASTM_F593_17_GROUP_2_316_316L";
    metallic_bolt_eligibility: { status: string };
  };
  interface_a: TeeInterfaceResult;
  interface_b: TeeInterfaceResult;
  tee_body_resistance_status: "NOT_EVALUATED";
  assembly_status: "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY";
  ordinary_pass_allowed: false;
  resistance_evaluated: false;
  design_check_ready: boolean;
  warnings: string[];
  engineering_fingerprint: string;
  visualization: TeeVisualization | null;
  support_target_id: SharedSupportTargetId;
  rectangular_full_through_paths: readonly FullThroughBoltTrace[];
  design_limitations: readonly string[];
}

export interface TeeConnectorPreviewResponse {
  api_transport_schema_version: "0.1.0-draft";
  orchestration_contract_version: "3.3C2-RC1";
  preview_schema_version: "0.3.0-draft";
  request_id: string;
  support_role: TeeSupportRole;
  selected_support_flange: SelectedSupportFlange;
  assembly_status: TeePreviewResult["assembly_status"];
  ordinary_pass_allowed: false;
  resistance_evaluated: false;
  design_check_ready: boolean;
  warnings: string[];
  engineering_fingerprint: string;
  result: TeePreviewResult;
}

export interface TeeConnectorDesignResponse {
  api_transport_schema_version: "0.1.0-draft";
  orchestration_contract_version: "3.3C2-RC1";
  request_id: string;
  assembly_status: TeePreviewResult["assembly_status"];
  tee_body_resistance_status: "NOT_EVALUATED";
  ordinary_pass_allowed: false;
  supported_interface_failure_present: boolean;
  result_fingerprint: string;
  result: {
    preview: TeePreviewResult;
    interface_a: TeeInterfaceResult;
    interface_b: TeeInterfaceResult;
    tee_body_resistance_status: "NOT_EVALUATED";
    assembly_status: TeePreviewResult["assembly_status"];
    ordinary_pass_allowed: false;
    supported_interface_failure_present: boolean;
    result_fingerprint: string;
  };
}

export function interfaceDemand(
  value: TeeInterfaceResult,
): AutomaticDemandResult | null {
  return value.design?.automatic_demand_result ?? value.preview.automatic_demand_result;
}

export function interfaceHandoff(
  value: TeeInterfaceResult,
): AutomaticHandoffResult | null {
  return value.design?.automatic_handoff_results[0] ?? null;
}
