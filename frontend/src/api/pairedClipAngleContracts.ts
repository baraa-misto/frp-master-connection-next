import type {
  ClipAngleBoltLayoutRequest,
  ClipAngleBoltTrace,
  ClipAngleBoxTrace,
  ClipAngleMaterialRegionTrace,
  ClipAngleProfileMaterialRegionTrace,
  ClipAngleQuantity,
  ClipAngleRequest,
  LegacyClipAngleRequest,
  ClipAngleTriangleMeshTrace,
  ClipAngleVisualization,
} from "./clipAngleContracts";

export type PairedProfileFamily =
  | "FLAT_PLATE"
  | "WIDE_FLANGE_I"
  | "CHANNEL"
  | "ANGLE"
  | "RECTANGULAR_HOLLOW_SECTION"
  | "SOLID_RECTANGULAR_SECTION";

export interface PairedClipAngleRequest extends Omit<
  ClipAngleRequest,
  "orchestration_contract_version" | "hand" | "interface_a_layout" | "interface_b_layout"
> {
  orchestration_contract_version: "3.3C3-RC1";
  connected_member_profile: ClipAngleRequest["connected_member_profile"] & {
    profile_family: PairedProfileFamily;
  };
  common_member_layout: ClipAngleBoltLayoutRequest;
  mirrored_support_layout: ClipAngleBoltLayoutRequest;
  pair_symmetry: "LOCKED_IDENTICAL_MIRROR";
}

export interface LegacyPairedClipAngleRequest extends Omit<
  LegacyClipAngleRequest,
  "orchestration_contract_version" | "hand" | "interface_a_layout" | "interface_b_layout"
> {
  orchestration_contract_version: "3.3B-RC1";
  connected_member_profile: ClipAngleRequest["connected_member_profile"] & {
    profile_family: "FLAT_PLATE" | "WIDE_FLANGE_I" | "CHANNEL";
  };
  common_member_layout: ClipAngleBoltLayoutRequest;
  mirrored_support_layout: ClipAngleBoltLayoutRequest;
  pair_symmetry: "LOCKED_IDENTICAL_MIRROR";
}

export interface PairedLayerDemandTrace {
  bolt_id: string;
  layer_id: "POSITIVE_CONNECTED_LEG" | "CONNECTED_MEMBER" | "NEGATIVE_CONNECTED_LEG";
  parent_total_force: { u: ClipAngleQuantity; v: ClipAngleQuantity };
  fraction_of_total: string;
  force_u: ClipAngleQuantity;
  force_v: ClipAngleQuantity;
  total_force_magnitude: ClipAngleQuantity;
  parent_demand_fingerprint: string;
  symmetry_proof_fingerprint: string;
}

export interface PairedBoltGroupResult {
  group_id: "COMMON_MEMBER_THROUGH_BOLT_GROUP" | "POSITIVE_SUPPORT_BOLT_GROUP" | "NEGATIVE_SUPPORT_BOLT_GROUP";
  physical_name: string;
  placement: {
    bolt_group_id: string;
    bolts: readonly ClipAngleBoltTrace[];
    clearances: { minimum: ClipAngleQuantity; geometry_valid: boolean };
    geometry_fingerprint: string;
  };
  demand: {
    availability: string;
    method_applicability: string;
    qualification: string;
    scenarios: readonly {
      per_bolt: readonly { bolt_id: string; total_force_magnitude: ClipAngleQuantity }[];
    }[];
  } | null;
  resistance: {
    automatic_handoff_results: readonly { overall_disposition: string; coverage: string }[];
  } | null;
  layer_demands: readonly PairedLayerDemandTrace[];
  result_fingerprint: string;
}

export interface PairedClipAngleVisualization extends Omit<
  ClipAngleVisualization,
  "connected_member_role" | "connected_member_profile_orientation" | "interface_a_bolts" | "interface_b_bolts" | "global_force" | "global_moment" | "global_reference_point"
> {
  semantic_frame: ClipAngleVisualization["semantic_frame"] & { symmetry_plane: string };
  symmetry_plane: string;
  connected_member_profile_family: PairedProfileFamily;
  boxes: readonly ClipAngleBoxTrace[];
  meshes: readonly ClipAngleTriangleMeshTrace[];
  common_member_bolts: readonly ClipAngleBoltTrace[];
  positive_support_bolts: readonly ClipAngleBoltTrace[];
  negative_support_bolts: readonly ClipAngleBoltTrace[];
  material_regions: readonly ClipAngleMaterialRegionTrace[];
  connected_member_material_regions: readonly ClipAngleProfileMaterialRegionTrace[];
  parent_force: ClipAngleVisualization["global_force"];
  parent_moment: ClipAngleVisualization["global_moment"];
  parent_reference_point: ClipAngleVisualization["global_reference_point"];
  branch_actions: readonly {
    branch_id: "POSITIVE_CLIP_ANGLE" | "NEGATIVE_CLIP_ANGLE";
    force: ClipAngleVisualization["global_force"];
    moment: ClipAngleVisualization["global_moment"];
    reference_point: ClipAngleVisualization["global_reference_point"];
    parent_action_id: string;
  }[];
}

export type PairedClipAngleStatus = "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY";

export interface PairedClipAnglePreviewResult {
  request_id: string;
  orchestration_contract_version: "3.3B-RC1" | "3.3C3-RC1";
  preview_schema_version: "0.1.0-draft";
  connector_kind: "SYMMETRIC_PAIRED_CLIP_ANGLES";
  assembly_identity: "SYMMETRIC_PAIRED_CLIP_ANGLES";
  symmetry_proof: {
    geometry_proven: boolean;
    action_proven: boolean;
    equal_sharing_eligible: boolean;
    reasons: readonly string[];
  };
  branch_actions: PairedClipAngleVisualization["branch_actions"];
  common_member_group: PairedBoltGroupResult;
  positive_support_group: PairedBoltGroupResult;
  negative_support_group: PairedBoltGroupResult;
  material_regions: readonly ClipAngleMaterialRegionTrace[];
  required_checks: readonly string[];
  required_check_status: "NOT_EVALUATED";
  geometry_status: "VALID" | "INVALID_GEOMETRY";
  geometry_invalid_reasons: readonly string[];
  assembly_status: PairedClipAngleStatus;
  ordinary_pass_allowed: false;
  resistance_evaluated: boolean;
  design_check_ready: boolean;
  warnings: readonly string[];
  canonical_input_fingerprint: string;
  connector_geometry_fingerprint: string;
  engineering_fingerprint: string;
  visualization: PairedClipAngleVisualization | null;
  rectangular_full_through_paths: ClipAngleVisualization["rectangular_full_through_paths"];
  limitations: readonly string[];
  support_target_id: ClipAngleVisualization["support_target_id"];
}

export interface PairedClipAnglePreviewResponse {
  api_transport_schema_version: "0.1.0-draft";
  orchestration_contract_version: "3.3B-RC1" | "3.3C3-RC1";
  preview_schema_version: "0.1.0-draft";
  request_id: string;
  geometry_status: PairedClipAnglePreviewResult["geometry_status"];
  geometry_invalid_reasons: readonly string[];
  assembly_status: PairedClipAngleStatus;
  ordinary_pass_allowed: false;
  resistance_evaluated: false;
  design_check_ready: boolean;
  warnings: readonly string[];
  engineering_fingerprint: string;
  result: PairedClipAnglePreviewResult;
}

export interface PairedClipAngleDesignResponse {
  api_transport_schema_version: "0.1.0-draft";
  orchestration_contract_version: "3.3B-RC1" | "3.3C3-RC1";
  request_id: string;
  assembly_status: PairedClipAngleStatus;
  required_check_status: "NOT_EVALUATED";
  ordinary_pass_allowed: false;
  supported_interface_failure_present: boolean;
  result_fingerprint: string;
  result: {
    preview: PairedClipAnglePreviewResult;
    assembly_status: PairedClipAngleStatus;
    required_check_status: "NOT_EVALUATED";
    ordinary_pass_allowed: false;
    supported_interface_failure_present: boolean;
    result_fingerprint: string;
  };
}
