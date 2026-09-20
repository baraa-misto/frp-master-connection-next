import type {
  ClipAngleBoltTrace,
  ClipAngleBoxTrace,
  ClipAngleMaterialRegionTrace,
  ClipAngleQuantity,
} from "./clipAngleContracts";
import type { MultiRowQuantity } from "./multirowContracts";

export type ColumnBaseHistoricalAssembly = "SINGLE_BASE_ANGLE" | "SYMMETRIC_DOUBLE_BASE_ANGLES";
export type ColumnBaseAssembly = "SINGLE_BASE_ANGLE" | "DOUBLE_BASE_ANGLES";
export type ColumnBaseSide = "+T_C" | "-T_C";
export type ColumnBaseProfileFamily =
  | "WIDE_FLANGE_I"
  | "RECTANGULAR_HOLLOW_SECTION"
  | "SOLID_RECTANGULAR_SECTION"
  | "ANGLE";

export interface ColumnBaseVector {
  readonly s: ClipAngleQuantity;
  readonly t: ClipAngleQuantity;
  readonly longitudinal: ClipAngleQuantity;
}

export interface ColumnBaseWrench {
  readonly reference_s_t_l: ColumnBaseVector;
  readonly force_s_t_l: ColumnBaseVector;
  readonly moment_s_t_l: ColumnBaseVector;
  readonly provenance: string;
}

export interface ColumnBaseWebAngleHistoricalRequest {
  orchestration_contract_version: "3.5C-RC1";
  request_id: string;
  unit_system: "US_CUSTOMARY" | "SI";
  source_length_unit: "in" | "mm";
  concrete: { s_dimension: MultiRowQuantity; t_dimension: MultiRowQuantity; depth: MultiRowQuantity };
  column: {
    profile_family: "WIDE_FLANGE_I";
    depth_s: MultiRowQuantity;
    flange_width_t: MultiRowQuantity;
    web_thickness: MultiRowQuantity;
    flange_thickness: MultiRowQuantity;
    display_height: MultiRowQuantity;
  };
  assembly: ColumnBaseHistoricalAssembly;
  single_side: ColumnBaseSide;
  angle: {
    connected_leg_width: MultiRowQuantity;
    support_leg_width: MultiRowQuantity;
    thickness: MultiRowQuantity;
    connector_length: MultiRowQuantity;
  };
  web_group: {
    row_count: number;
    bolts_per_row: number;
    pitch: MultiRowQuantity;
    gauge: MultiRowQuantity;
    centroid_height_l: MultiRowQuantity;
  };
  anchor_pattern: {
    row_count: number;
    anchors_per_row: number;
    pitch: MultiRowQuantity;
    gauge: MultiRowQuantity;
    centroid_offset_t: MultiRowQuantity;
  };
  web_bolt_diameter: MultiRowQuantity;
  web_hole_diameter: MultiRowQuantity;
  external_anchor: {
    nominal_diameter: MultiRowQuantity;
    hole_diameter: MultiRowQuantity;
    specified_embedment: MultiRowQuantity;
    washer_outside_diameter: MultiRowQuantity;
    washer_thickness: MultiRowQuantity;
    system_classification: "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR";
  };
  axial_compression: MultiRowQuantity;
  web_plane_shear: MultiRowQuantity;
  web_normal_shear: MultiRowQuantity;
  action_reference_s_t_l: { x: string; y: string; z: string; unit: "in" | "mm" };
}

export interface ColumnBaseWebAngleSignedRequest extends Omit<
  ColumnBaseWebAngleHistoricalRequest,
  "orchestration_contract_version" | "axial_compression"
> {
  orchestration_contract_version: "3.5C-R2-RC1";
  signed_axial_force: MultiRowQuantity;
}

interface ColumnBaseProfileTransportBase {
  profile_id: string;
  role: "COLUMN";
  size_basis: "CUSTOM_DIMENSIONS";
  profile_orientation: "ROTATION_0" | "ROTATION_90" | "ROTATION_180" | "ROTATION_270";
  material_kind: "PULTRUDED_FRP";
}

export type ColumnBaseProfileTransport =
  | (ColumnBaseProfileTransportBase & {
    profile_family: "WIDE_FLANGE_I";
    selected_profile_surface: "WEB_POS_FACE" | "WEB_NEG_FACE";
    dimensions: {
      member_length: MultiRowQuantity;
      depth: MultiRowQuantity;
      flange_width: MultiRowQuantity;
      web_thickness: MultiRowQuantity;
      flange_thickness: MultiRowQuantity;
    };
  })
  | (ColumnBaseProfileTransportBase & {
    profile_family: "RECTANGULAR_HOLLOW_SECTION";
    selected_profile_surface: "Y_POS_FACE" | "Y_NEG_FACE" | "Z_POS_FACE" | "Z_NEG_FACE";
    dimensions: {
      member_length: MultiRowQuantity;
      depth: MultiRowQuantity;
      width: MultiRowQuantity;
      wall_thickness: MultiRowQuantity;
    };
  })
  | (ColumnBaseProfileTransportBase & {
    profile_family: "SOLID_RECTANGULAR_SECTION";
    selected_profile_surface: "Y_POS_FACE" | "Y_NEG_FACE" | "Z_POS_FACE" | "Z_NEG_FACE";
    dimensions: {
      member_length: MultiRowQuantity;
      depth: MultiRowQuantity;
      width: MultiRowQuantity;
    };
  })
  | (ColumnBaseProfileTransportBase & {
    profile_family: "ANGLE";
    selected_profile_surface: "LEG_Y_OUTER" | "LEG_Z_OUTER";
    dimensions: {
      member_length: MultiRowQuantity;
      leg_y: MultiRowQuantity;
      leg_z: MultiRowQuantity;
      thickness: MultiRowQuantity;
    };
  });

export interface ColumnBaseWebAngleRequest extends Omit<
  ColumnBaseWebAngleSignedRequest,
  | "orchestration_contract_version"
  | "column"
  | "assembly"
  | "web_plane_shear"
  | "web_normal_shear"
  | "action_reference_s_t_l"
> {
  orchestration_contract_version: "3.7A-RC1";
  column_profile: ColumnBaseProfileTransport;
  assembly: ColumnBaseAssembly;
  connection_plane_shear: MultiRowQuantity;
  connection_normal_shear: MultiRowQuantity;
  angle_double_topology: "SAME_SELECTED_LEG_OPPOSITE_FACES";
}

export type ColumnBaseWebAngleAnyRequest =
  | ColumnBaseWebAngleHistoricalRequest
  | ColumnBaseWebAngleSignedRequest
  | ColumnBaseWebAngleRequest;

export interface ColumnBaseHistoricalComponentTransfer {
  readonly column_web_axial_demand: ClipAngleQuantity;
  readonly column_web_fraction: string;
  readonly column_web_material_direction: "LW";
  readonly angle_system_axial_demand: ClipAngleQuantity;
  readonly angle_system_fraction: string;
  readonly angle_vertical_leg_material_direction: "CW";
  readonly positive_angle_axial_demand: ClipAngleQuantity | null;
  readonly negative_angle_axial_demand: ClipAngleQuantity | null;
  readonly single_angle_axial_demand: ClipAngleQuantity | null;
  readonly branch_fraction: string;
  readonly foundation_axial_action: ClipAngleQuantity;
  readonly component_design_demands_summed_for_equilibrium: false;
}

export interface ColumnBaseSignedComponentTransfer {
  readonly axial_mode: "COMPRESSION" | "UPLIFT" | "ZERO";
  readonly column_web_signed_axial_action: ClipAngleQuantity;
  readonly column_web_design_magnitude: ClipAngleQuantity;
  readonly column_web_fraction: string;
  readonly column_web_material_direction: "LW";
  readonly column_web_signed_material_direction: "+LW" | "-LW" | "LW";
  readonly angle_system_signed_axial_action: ClipAngleQuantity;
  readonly angle_system_design_magnitude: ClipAngleQuantity;
  readonly angle_system_fraction: string;
  readonly angle_vertical_leg_material_direction: "CW";
  readonly angle_vertical_leg_signed_material_direction: "+CW" | "-CW" | "CW";
  readonly positive_angle_signed_axial_action: ClipAngleQuantity | null;
  readonly negative_angle_signed_axial_action: ClipAngleQuantity | null;
  readonly single_angle_signed_axial_action: ClipAngleQuantity | null;
  readonly branch_fraction: string;
  readonly foundation_signed_axial_action: ClipAngleQuantity;
  readonly component_design_demands_summed_for_equilibrium: false;
}

export interface ColumnBaseProfileComponentTransfer {
  readonly axial_mode: "COMPRESSION" | "UPLIFT" | "ZERO";
  readonly column_signed_axial_action: ClipAngleQuantity;
  readonly column_design_magnitude: ClipAngleQuantity;
  readonly column_fraction: "1";
  readonly column_material_direction: "LW";
  readonly column_signed_material_direction: "+LW" | "-LW" | "LW";
  readonly base_angle_system_signed_axial_action: ClipAngleQuantity;
  readonly base_angle_system_design_magnitude: ClipAngleQuantity;
  readonly base_angle_system_fraction: "1";
  readonly base_angle_vertical_leg_material_direction: "CW";
  readonly base_angle_vertical_leg_signed_material_direction: "+CW" | "-CW" | "CW";
  readonly positive_angle_signed_axial_action: ClipAngleQuantity | null;
  readonly negative_angle_signed_axial_action: ClipAngleQuantity | null;
  readonly single_angle_signed_axial_action: ClipAngleQuantity | null;
  readonly branch_fraction: string;
  readonly complete_branch_allocation: "EXACT_HALF_SHARING" | "NOT_EVALUATED" | "SINGLE_FULL_SYSTEM";
  readonly foundation_signed_axial_action: ClipAngleQuantity;
  readonly component_design_demands_summed_for_equilibrium: false;
}

export type ColumnBaseComponentTransfer =
  | ColumnBaseHistoricalComponentTransfer
  | ColumnBaseSignedComponentTransfer
  | ColumnBaseProfileComponentTransfer;

export interface ColumnBasePhysicalBoltPath {
  readonly bolt_id: string;
  readonly selected_surface: string;
  readonly opposite_surface: string;
  readonly segments: readonly {
    readonly kind: "MATERIAL_LAYER" | "FREE_SHANK_SPAN";
    readonly identity: string;
    readonly length: ClipAngleQuantity;
    readonly material_region_id: string | null;
    readonly has_material_axes: boolean;
  }[];
  readonly stack_start_s_t_l: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity];
  readonly stack_end_s_t_l: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity];
  readonly physical_bolt_count: 1;
  readonly continuous_shank_count: 1;
  readonly internal_hardware_count: 0;
  readonly head_location: "EXTERIOR_NEAR_SIDE";
  readonly nut_location: "EXTERIOR_FAR_SIDE";
  readonly washer_locations: readonly ["EXTERIOR_NEAR_SIDE", "EXTERIOR_FAR_SIDE"];
  readonly containment_status: "VALID" | "INVALID_GEOMETRY";
  readonly path_fingerprint: string;
}

export interface ColumnBaseAnchorTrace {
  readonly anchor_id: string;
  readonly group_id: string;
  readonly coordinate_s_t_l: ColumnBaseVector;
  readonly axis_s_t_l: readonly [string, string, string];
  readonly shank_start_s_t_l: ColumnBaseVector;
  readonly shank_end_s_t_l: ColumnBaseVector;
  readonly exterior_washer_center_s_t_l: ColumnBaseVector;
  readonly exterior_nut_reference_s_t_l: ColumnBaseVector;
  readonly penetrated_layers: readonly string[];
}

export interface ColumnBaseAnchorGroup {
  readonly group_id: string;
  readonly side: ColumnBaseSide;
  readonly centroid_s_t_l: ColumnBaseVector;
  readonly anchors: readonly ColumnBaseAnchorTrace[];
  readonly branch_wrench: ColumnBaseWrench | null;
  readonly capacity_status: "EXTERNAL_DESIGN_REQUIRED";
}

export interface ColumnBaseVisualization {
  readonly schema_version: "0.1.0-draft";
  readonly base_frame?: {
    readonly s_axis: readonly [string, string, string];
    readonly t_axis: readonly [string, string, string];
    readonly l_axis: readonly [string, string, string];
    readonly handedness: "S_C cross T_C = L_C";
  };
  readonly connection_frame?: {
    readonly selected_surface: string;
    readonly origin_profile_xyz: readonly [string, string, string];
    readonly s_axis_profile_xyz: readonly [string, string, string];
    readonly t_axis_profile_xyz: readonly [string, string, string];
    readonly l_axis_profile_xyz: readonly [string, string, string];
    readonly handedness: "S_C cross T_C = L_C";
  };
  readonly boxes: readonly ClipAngleBoxTrace[];
  readonly web_bolts: readonly ClipAngleBoltTrace[];
  readonly profile_family?: ColumnBaseProfileFamily;
  readonly selected_surface?: string;
  readonly physical_bolt_paths?: readonly ColumnBasePhysicalBoltPath[];
  readonly anchors: readonly ColumnBaseAnchorTrace[];
  readonly web_bolt_diameter: ClipAngleQuantity;
  readonly web_hole_diameter: ClipAngleQuantity;
  readonly external_anchor_geometry: {
    readonly nominal_diameter: ClipAngleQuantity;
    readonly hole_diameter: ClipAngleQuantity;
    readonly specified_embedment: ClipAngleQuantity;
    readonly washer_outside_diameter: ClipAngleQuantity;
    readonly washer_thickness: ClipAngleQuantity;
    readonly system_classification: "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR";
  };
  readonly material_regions: readonly ClipAngleMaterialRegionTrace[];
  readonly applied_force_s_t_l: ColumnBaseVector;
  readonly action_reference_s_t_l: ColumnBaseVector;
  readonly selected_surfaces: readonly string[];
}

export interface ColumnBasePreviewResult {
  readonly profile_family?: ColumnBaseProfileFamily;
  readonly selected_surface?: string;
  readonly assembly: ColumnBaseHistoricalAssembly | ColumnBaseAssembly;
  readonly single_side: ColumnBaseSide;
  readonly component_transfer: ColumnBaseComponentTransfer;
  readonly physical_bolt_paths?: readonly ColumnBasePhysicalBoltPath[];
  readonly combined_foundation_wrench: ColumnBaseWrench;
  readonly anchor_groups: readonly ColumnBaseAnchorGroup[];
  readonly external_handoff: { readonly handoff_fingerprint: string };
  readonly external_handoff_json: string;
  readonly geometry_status: "VALID" | "INVALID_GEOMETRY";
  readonly geometry_invalid_reasons: readonly string[];
  readonly assembly_status: "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY";
  readonly limitations: readonly (readonly [string, string])[];
  readonly warnings: readonly string[];
  readonly engineering_fingerprint: string;
  readonly application_fingerprint: string;
  readonly visualization: ColumnBaseVisualization | null;
}

export interface ColumnBasePreviewResponse {
  readonly api_transport_schema_version: "0.1.0-draft";
  readonly orchestration_contract_version: "3.5C-RC1" | "3.5C-R2-RC1" | "3.7A-RC1";
  readonly preview_schema_version: "0.1.0-draft";
  readonly request_id: string;
  readonly geometry_status: "VALID" | "INVALID_GEOMETRY";
  readonly geometry_invalid_reasons: readonly string[];
  readonly assembly_status: "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY";
  readonly ordinary_pass_allowed: false;
  readonly resistance_evaluated: false;
  readonly design_check_ready: boolean;
  readonly external_design_required: true;
  readonly engineering_fingerprint: string;
  readonly application_fingerprint: string;
  readonly result: ColumnBasePreviewResult;
}

export interface ColumnBaseDesignResponse {
  readonly api_transport_schema_version: "0.1.0-draft";
  readonly orchestration_contract_version: "3.5C-RC1" | "3.5C-R2-RC1" | "3.7A-RC1";
  readonly request_id: string;
  readonly assembly_status: "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY";
  readonly required_check_status: "NOT_EVALUATED";
  readonly ordinary_pass_allowed: false;
  readonly external_design_required: true;
  readonly supported_local_failure_present: boolean;
  readonly result_fingerprint: string;
  readonly result: { readonly preview: ColumnBasePreviewResult };
}
