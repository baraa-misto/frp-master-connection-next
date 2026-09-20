import type {
  ClipAngleBoltLayoutRequest,
  ClipAngleBoxTrace,
  ClipAngleMaterialRegionTrace,
  ClipAngleProfileRequest,
  ClipAngleProfileMaterialRegionTrace,
  ClipAngleQuantity,
  ClipAngleTriangleMeshTrace,
} from "./clipAngleContracts";
import type { MultiRowQuantity } from "./multirowContracts";
import type { PairedBoltGroupResult, PairedProfileFamily } from "./pairedClipAngleContracts";

export interface WallVector { readonly h: ClipAngleQuantity; readonly v: ClipAngleQuantity; readonly n: ClipAngleQuantity }
export interface WallWrench { readonly reference_hvn: WallVector; readonly force_hvn: WallVector; readonly moment_hvn: WallVector; readonly provenance: string }

interface BeamConcretePairedAngleRequestBase {
  request_id: string;
  unit_system: "US_CUSTOMARY" | "SI";
  source_length_unit: "in" | "mm";
  wall: {
    width: MultiRowQuantity; height: MultiRowQuantity; thickness: MultiRowQuantity;
    connection_origin_h: MultiRowQuantity; connection_origin_v: MultiRowQuantity;
  };
  beam_profile: ClipAngleProfileRequest & {
    role: "BEAM";
    profile_family: PairedProfileFamily;
  };
  beam_end_gap: MultiRowQuantity;
  connector_dimensions: {
    connected_leg_width: MultiRowQuantity; support_leg_width: MultiRowQuantity;
    thickness: MultiRowQuantity; connector_length: MultiRowQuantity;
  };
  connector_length_anchor_position: MultiRowQuantity;
  common_beam_layout: ClipAngleBoltLayoutRequest;
  wall_anchor_pattern: {
    row_count: number; anchors_per_row: number; pitch: MultiRowQuantity; gauge: MultiRowQuantity;
    centroid_offset_h: MultiRowQuantity; centroid_v: MultiRowQuantity;
  };
  common_bolt_diameter: MultiRowQuantity;
  common_hole_diameter: MultiRowQuantity;
  external_anchor: {
    nominal_diameter: MultiRowQuantity; hole_diameter: MultiRowQuantity;
    specified_embedment: MultiRowQuantity; washer_outside_diameter: MultiRowQuantity;
    washer_thickness: MultiRowQuantity;
    system_classification: "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR";
  };
}

export interface HistoricalBeamConcretePairedAngleRequest extends BeamConcretePairedAngleRequestBase {
  orchestration_contract_version: "3.5A-RC1" | "3.5A-R1-RC1";
  reaction_shear: MultiRowQuantity;
  user_force_hvn: { x: string; y: string; z: string; unit: "kip" | "kN" };
  user_moment_hvn: { x: string; y: string; z: string; unit: "kip-in" | "kN-mm" };
}

export interface BeamConcretePairedAngleR2Request extends BeamConcretePairedAngleRequestBase {
  orchestration_contract_version: "3.5A-R2-RC1";
  major_shear: MultiRowQuantity;
  minor_shear: MultiRowQuantity;
  axial_force: MultiRowQuantity;
  user_moment_hvn?: { x: string; y: string; z: string; unit: "kip-in" | "kN-mm" };
}

export type BeamConcretePairedAngleRequest =
  | HistoricalBeamConcretePairedAngleRequest
  | BeamConcretePairedAngleR2Request;

export interface ExternalAnchorTrace {
  anchor_id: string;
  group_id: "POSITIVE_WALL_ANCHOR_GROUP" | "NEGATIVE_WALL_ANCHOR_GROUP";
  coordinate_hvn: WallVector;
  wall_edge_distances: { negative_h: ClipAngleQuantity; positive_h: ClipAngleQuantity; negative_v: ClipAngleQuantity; positive_v: ClipAngleQuantity };
  shank_start_hvn: WallVector;
  shank_end_hvn: WallVector;
  hardware_configuration: "EXTERIOR_NUT_WASHER_WITH_BLIND_EMBEDDED_SHANK";
  capacity_status: "EXTERNAL_DESIGN_REQUIRED";
}

export interface WallAnchorGroupResult {
  group_id: ExternalAnchorTrace["group_id"];
  centroid_hvn: WallVector;
  anchors: readonly ExternalAnchorTrace[];
  wrench: WallWrench | null;
  nominal_demand: PairedBoltGroupResult["demand"] | null;
  demand_label: string;
  force_equilibrium: boolean;
  moment_equilibrium: boolean;
  geometry_fingerprint: string;
  result_fingerprint: string;
}

export interface BeamConcretePairedAngleVisualization {
  schema_version: "0.1.0-draft";
  wall_frame: { h_axis: readonly [string, string, string]; v_axis: readonly [string, string, string]; n_axis: readonly [string, string, string] };
  boxes: readonly ClipAngleBoxTrace[];
  meshes: readonly ClipAngleTriangleMeshTrace[];
  common_beam_bolts: readonly import("./clipAngleContracts").ClipAngleBoltTrace[];
  external_anchors: readonly ExternalAnchorTrace[];
  common_bolt_diameter: ClipAngleQuantity;
  common_hole_diameter: ClipAngleQuantity;
  external_anchor_geometry: {
    nominal_diameter: ClipAngleQuantity; hole_diameter: ClipAngleQuantity;
    specified_embedment: ClipAngleQuantity; washer_outside_diameter: ClipAngleQuantity;
    washer_thickness: ClipAngleQuantity;
    system_classification: "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR";
  };
  material_regions: readonly ClipAngleMaterialRegionTrace[];
  beam_material_regions: readonly ClipAngleProfileMaterialRegionTrace[];
  reaction_shear: ClipAngleQuantity;
  user_force_hvn?: WallVector;
  user_moment_hvn?: WallVector;
  beam_reference_hvn: WallVector;
  wall_reference_hvn: WallVector;
  positive_branch_wrench: WallWrench | null;
  negative_branch_wrench: WallWrench | null;
  combined_wall_wrench: WallWrench;
  selected_wall_surface_id: "CONCRETE_WALL:EXTERIOR_FACE";
}

export interface BeamConcretePairedAnglePreviewResult {
  request_id: string;
  orchestration_contract_version: "3.5A-RC1" | "3.5A-R1-RC1" | "3.5A-R2-RC1";
  preview_schema_version: "0.1.0-draft";
  connector_kind: "BEAM_TO_CONCRETE_WALL_SYMMETRIC_PAIRED_CLIP_ANGLES";
  symmetry_proof: { geometry_proven: boolean; action_proven: boolean; equal_sharing_eligible: boolean; reasons: readonly string[] };
  common_beam_group: PairedBoltGroupResult;
  positive_wall_group: WallAnchorGroupResult;
  negative_wall_group: WallAnchorGroupResult;
  combined_wall_wrench: WallWrench;
  external_anchor_handoff: Record<string, unknown>;
  external_anchor_handoff_json: string;
  geometry_status: "VALID" | "INVALID_GEOMETRY";
  geometry_invalid_reasons: readonly string[];
  assembly_status: "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY";
  ordinary_pass_allowed: false;
  resistance_evaluated: boolean;
  design_check_ready: boolean;
  external_design_required: true;
  limitations: readonly (readonly [string, string])[];
  warnings: readonly string[];
  engineering_fingerprint: string;
  application_fingerprint: string;
  visualization: BeamConcretePairedAngleVisualization | null;
  handoff_mode?: "BRANCH_RESOLVED" | "COMBINED_LAYOUT";
  branch_allocation_status?: "RESOLVED" | "NOT_EVALUATED";
  common_group_normal_action?: ClipAngleQuantity;
  action_reference_hvn?: WallVector;
}

export interface BeamConcretePairedAnglePreviewResponse {
  api_transport_schema_version: "0.1.0-draft";
  orchestration_contract_version: "3.5A-RC1" | "3.5A-R1-RC1" | "3.5A-R2-RC1";
  preview_schema_version: "0.1.0-draft";
  request_id: string;
  geometry_status: BeamConcretePairedAnglePreviewResult["geometry_status"];
  geometry_invalid_reasons: readonly string[];
  assembly_status: BeamConcretePairedAnglePreviewResult["assembly_status"];
  ordinary_pass_allowed: false;
  resistance_evaluated: false;
  design_check_ready: boolean;
  external_design_required: true;
  engineering_fingerprint: string;
  application_fingerprint: string;
  result: BeamConcretePairedAnglePreviewResult;
}

export interface BeamConcretePairedAngleDesignResponse {
  api_transport_schema_version: "0.1.0-draft";
  orchestration_contract_version: "3.5A-RC1" | "3.5A-R1-RC1" | "3.5A-R2-RC1";
  request_id: string;
  assembly_status: BeamConcretePairedAnglePreviewResult["assembly_status"];
  required_check_status: "NOT_EVALUATED";
  ordinary_pass_allowed: false;
  external_design_required: true;
  supported_beam_side_failure_present: boolean;
  result_fingerprint: string;
  result: { preview: BeamConcretePairedAnglePreviewResult };
}
