import type {
  ClipAngleBoxTrace,
  ClipAngleProfileMaterialRegionTrace,
  ClipAngleQuantity,
  ClipAngleProfileRequest,
} from "./clipAngleContracts";
import type { MultiRowQuantity } from "./multirowContracts";

export type DirectSideLapProfileFamily = "ANGLE" | "CHANNEL";

export interface SideLapVector {
  readonly l: ClipAngleQuantity;
  readonly s: ClipAngleQuantity;
  readonly n: ClipAngleQuantity;
}

export interface SideLapWrench {
  readonly reference_lsn: SideLapVector;
  readonly force_lsn: SideLapVector;
  readonly moment_lsn: SideLapVector;
  readonly provenance: string;
}

export interface DirectSideLapConcreteRequest {
  orchestration_contract_version: "3.5B-RC1";
  request_id: string;
  unit_system: "US_CUSTOMARY" | "SI";
  source_length_unit: "in" | "mm";
  wall: {
    run_length: MultiRowQuantity;
    transverse_width: MultiRowQuantity;
    thickness: MultiRowQuantity;
  };
  side_lap_length: MultiRowQuantity;
  member_projection_beyond_wall: MultiRowQuantity;
  connected_profile: ClipAngleProfileRequest & {
    role: "BRACE";
    profile_family: DirectSideLapProfileFamily;
  };
  anchor_pattern: {
    row_count: number;
    anchors_per_row: number;
    pitch: MultiRowQuantity;
    gauge: MultiRowQuantity;
    centroid_distance_behind_free_end: MultiRowQuantity;
    transverse_offset: MultiRowQuantity;
  };
  external_anchor: {
    nominal_diameter: MultiRowQuantity;
    hole_diameter: MultiRowQuantity;
    specified_embedment: MultiRowQuantity;
    washer_outside_diameter: MultiRowQuantity;
    washer_thickness: MultiRowQuantity;
    system_classification: "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR";
  };
  axial_force: MultiRowQuantity;
  major_shear: MultiRowQuantity;
  minor_shear: MultiRowQuantity;
}

export interface DirectSideLapAnchorTrace {
  readonly anchor_id: string;
  readonly group_id: "DIRECT_SIDE_LAP_WALL_ANCHOR_GROUP";
  readonly coordinate_lsn: SideLapVector;
  readonly edge_distances: Record<string, ClipAngleQuantity>;
  readonly shank_start_lsn: SideLapVector;
  readonly shank_end_lsn: SideLapVector;
  readonly penetrated_layers: readonly [string, "CONCRETE_EMBEDMENT"];
  readonly hardware_configuration: "EXTERIOR_NUT_WASHER_WITH_BLIND_EMBEDDED_SHANK";
  readonly capacity_status: "EXTERNAL_DESIGN_REQUIRED";
}

export interface DirectSideLapVisualization {
  readonly schema_version: "0.1.0-draft";
  readonly side_lap_frame: {
    readonly l_axis: readonly [string, string, string];
    readonly s_axis: readonly [string, string, string];
    readonly n_axis: readonly [string, string, string];
  };
  readonly boxes: readonly ClipAngleBoxTrace[];
  readonly material_regions: readonly ClipAngleProfileMaterialRegionTrace[];
  readonly external_anchors: readonly DirectSideLapAnchorTrace[];
  readonly external_anchor_geometry: {
    readonly nominal_diameter: ClipAngleQuantity;
    readonly hole_diameter: ClipAngleQuantity;
    readonly specified_embedment: ClipAngleQuantity;
    readonly washer_outside_diameter: ClipAngleQuantity;
    readonly washer_thickness: ClipAngleQuantity;
    readonly system_classification: "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR";
  };
  readonly connected_profile_family: DirectSideLapProfileFamily;
  readonly selected_profile_surface: "WEB_OUTER" | "LEG_Y_OUTER" | "LEG_Z_OUTER";
  readonly member_start_l: ClipAngleQuantity;
  readonly member_end_l: ClipAngleQuantity;
  readonly wall_free_end_l: ClipAngleQuantity;
  readonly overlap_interval_l: readonly [ClipAngleQuantity, ClipAngleQuantity];
  readonly action_reference_lsn: SideLapVector;
  readonly anchor_group_reference_lsn: SideLapVector;
  readonly user_force_lsn: SideLapVector;
  readonly user_moment_lsn: SideLapVector;
  readonly selected_wall_surface_id: "CONCRETE_WALL:FINITE_EXTERIOR_FACE";
}

export interface DirectSideLapPreviewResult {
  readonly request_id: string;
  readonly orchestration_contract_version: "3.5B-RC1";
  readonly preview_schema_version: "0.1.0-draft";
  readonly connector_kind: "DIRECT_SIDE_LAP_ANGLE_CHANNEL_TO_CONCRETE_WALL";
  readonly geometry_status: "VALID" | "INVALID_GEOMETRY";
  readonly geometry_invalid_reasons: readonly string[];
  readonly assembly_status: "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY";
  readonly ordinary_pass_allowed: false;
  readonly resistance_evaluated: boolean;
  readonly design_check_ready: boolean;
  readonly external_design_required: true;
  readonly anchor_group_id: "DIRECT_SIDE_LAP_WALL_ANCHOR_GROUP";
  readonly anchor_group_centroid_lsn: SideLapVector;
  readonly anchor_group_wrench: SideLapWrench;
  readonly nominal_in_plane_demand_status: string;
  readonly supported_local_frp_failure_present: boolean;
  readonly limitations: readonly (readonly [string, string])[];
  readonly warnings: readonly string[];
  readonly external_anchor_handoff: Record<string, unknown>;
  readonly external_anchor_handoff_json: string;
  readonly canonical_input_fingerprint: string;
  readonly geometry_fingerprint: string;
  readonly engineering_fingerprint: string;
  readonly application_fingerprint: string;
  readonly visualization: DirectSideLapVisualization | null;
}

export interface DirectSideLapPreviewResponse {
  readonly api_transport_schema_version: "0.1.0-draft";
  readonly orchestration_contract_version: "3.5B-RC1";
  readonly preview_schema_version: "0.1.0-draft";
  readonly request_id: string;
  readonly geometry_status: DirectSideLapPreviewResult["geometry_status"];
  readonly geometry_invalid_reasons: readonly string[];
  readonly assembly_status: DirectSideLapPreviewResult["assembly_status"];
  readonly ordinary_pass_allowed: false;
  readonly resistance_evaluated: false;
  readonly design_check_ready: boolean;
  readonly external_design_required: true;
  readonly engineering_fingerprint: string;
  readonly application_fingerprint: string;
  readonly result: DirectSideLapPreviewResult;
}

export interface DirectSideLapDesignResponse {
  readonly api_transport_schema_version: "0.1.0-draft";
  readonly orchestration_contract_version: "3.5B-RC1";
  readonly request_id: string;
  readonly assembly_status: DirectSideLapPreviewResult["assembly_status"];
  readonly required_check_status: "NOT_EVALUATED";
  readonly ordinary_pass_allowed: false;
  readonly external_design_required: true;
  readonly supported_local_frp_failure_present: boolean;
  readonly result_fingerprint: string;
  readonly result: { readonly preview: DirectSideLapPreviewResult };
}
