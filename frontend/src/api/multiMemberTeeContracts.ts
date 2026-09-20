import type { MultiRowQuantity } from "./multirowContracts";
import type { TeeVisualization } from "./teeContracts";
import type { TeeConnectedMemberProfileRequest } from "./teeContracts";
import type { SharedSupportProfileRequest, SharedSupportTargetId } from "./sharedSupportContracts";

export type MultiMemberTeeSlotId = "UPPER_BRACE" | "MIDDLE_BEAM" | "LOWER_BRACE";
export type NodeUnitSystem = "US_CUSTOMARY" | "SI";
export interface NodeVector { x: string; y: string; z: string; unit: string }
export interface NodeBoltGroup {
  row_count: number;
  bolts_per_row: number;
  pitch: MultiRowQuantity;
  gauge: MultiRowQuantity;
}
export interface NodeAction {
  force_hvn: NodeVector;
  moment_hvn: NodeVector;
  reference_hvn: NodeVector;
}
interface NodeSlotBase {
  anchor_h: MultiRowQuantity;
  anchor_v: MultiRowQuantity;
  bolt_group: NodeBoltGroup;
  action: NodeAction;
  profile_roll_degrees: string;
  trim_enabled: boolean;
  trim_clearance: MultiRowQuantity | null;
}
export interface NodeAngleSlot extends NodeSlotBase {
  slot_id: "UPPER_BRACE" | "LOWER_BRACE";
  leg_y: MultiRowQuantity;
  leg_z: MultiRowQuantity;
  thickness: MultiRowQuantity;
  member_length: MultiRowQuantity;
  selected_profile_surface: "LEG_Y_OUTER" | "LEG_Z_OUTER";
  inclination_degrees: string;
}
export interface NodeBeamSlot extends NodeSlotBase {
  slot_id: "MIDDLE_BEAM";
  depth: MultiRowQuantity;
  flange_width: MultiRowQuantity;
  web_thickness: MultiRowQuantity;
  flange_thickness: MultiRowQuantity;
  member_length: MultiRowQuantity;
  selected_profile_surface: "WEB_POS_FACE" | "WEB_NEG_FACE";
  inclination_degrees: "0";
}
export interface NodeExpandedSlot extends NodeSlotBase {
  slot_id: MultiMemberTeeSlotId;
  profile: TeeConnectedMemberProfileRequest;
  inclination_degrees: string;
}
export type NodeSlot = NodeAngleSlot | NodeBeamSlot | NodeExpandedSlot;
interface MultiMemberTeeRequestBase {
  request_id: string;
  unit_system: NodeUnitSystem;
  source_length_unit: "in" | "mm";
  connector_dimensions: {
    connector_length: MultiRowQuantity;
    flange_width: MultiRowQuantity;
    flange_thickness: MultiRowQuantity;
    stem_depth: MultiRowQuantity;
    stem_thickness: MultiRowQuantity;
  };
  connector_length_anchor: "CENTER";
  connector_length_anchor_position: MultiRowQuantity;
  support_group: NodeBoltGroup;
  support_reference_hvn: NodeVector;
  bolt_diameter: MultiRowQuantity;
  hole_basis: "US_CUSTOMARY_PRINTED" | "SI_PRINTED";
}
export interface HistoricalMultiMemberTeeRequest extends MultiMemberTeeRequestBase {
  orchestration_contract_version: "3.4A-RC1";
  support_dimensions: {
    member_length: MultiRowQuantity;
    depth: MultiRowQuantity;
    flange_width: MultiRowQuantity;
    web_thickness: MultiRowQuantity;
    flange_thickness: MultiRowQuantity;
  };
  upper_brace?: NodeAngleSlot;
  middle_beam?: NodeBeamSlot;
  lower_brace?: NodeAngleSlot;
}
export interface ExpandedMultiMemberTeeRequest extends MultiMemberTeeRequestBase {
  orchestration_contract_version: "3.4B-RC1";
  support_target_id: SharedSupportTargetId;
  support_profile: SharedSupportProfileRequest;
  upper_brace?: NodeExpandedSlot;
  middle_beam?: NodeExpandedSlot;
  lower_brace?: NodeExpandedSlot;
}
export type MultiMemberTeeRequest = HistoricalMultiMemberTeeRequest | ExpandedMultiMemberTeeRequest;
export interface NodeWrenchContribution {
  slot_id: MultiMemberTeeSlotId;
  force: { h: MultiRowQuantity; v: MultiRowQuantity; n: MultiRowQuantity };
  shifted_moment: { h: MultiRowQuantity; v: MultiRowQuantity; n: MultiRowQuantity };
  action_fingerprint: string;
}
export interface NodeSlotResult {
  slot_id: MultiMemberTeeSlotId;
  connected_role: "BRACE" | "BEAM";
  connected_member_id: string;
  bolt_group_id: string;
  profile: Record<string, unknown> | null;
  trim: { enabled: boolean; geometry_valid: boolean } | null;
  preview: Record<string, unknown> | null;
  geometry_fingerprint: string;
  interface_fingerprint: string;
  action_fingerprint: string;
}
export interface MultiMemberTeeVisualization {
  schema_version: "0.1.0-draft";
  slots: readonly {
    slot_id: MultiMemberTeeSlotId;
    connected_member_id: string;
    bolt_group_id: string;
    visualization: TeeVisualization;
  }[];
}
export interface MultiMemberTeePreviewResult {
  assembly_status: "INVALID_GEOMETRY" | "NOT_EVALUATED" | "FAIL";
  active_slot_ids: readonly MultiMemberTeeSlotId[];
  slots: readonly NodeSlotResult[];
  support: { bolt_group_id: "TEE_FLANGE_TO_SUPPORT"; interface_fingerprint: string };
  support_wrench: {
    force: { h: MultiRowQuantity; v: MultiRowQuantity; n: MultiRowQuantity };
    moment: { h: MultiRowQuantity; v: MultiRowQuantity; n: MultiRowQuantity };
    reference_point: { h: MultiRowQuantity; v: MultiRowQuantity; n: MultiRowQuantity };
    contributions: readonly NodeWrenchContribution[];
    wrench_fingerprint: string;
    application_provenance_fingerprint: string;
  };
  required_limitations: readonly string[];
  warnings: readonly string[];
  input_fingerprint: string;
  engineering_fingerprint: string;
  visualization: MultiMemberTeeVisualization | null;
}
export interface MultiMemberTeePreviewResponse {
  api_transport_schema_version: "0.1.0-draft";
  orchestration_contract_version: "3.4A-RC1" | "3.4B-RC1";
  preview_schema_version: "0.1.0-draft";
  request_id: string;
  assembly_status: MultiMemberTeePreviewResult["assembly_status"];
  ordinary_pass_allowed: false;
  resistance_evaluated: false;
  design_check_ready: boolean;
  engineering_fingerprint: string;
  result: MultiMemberTeePreviewResult;
}
export interface MultiMemberTeeDesignResponse {
  api_transport_schema_version: "0.1.0-draft";
  orchestration_contract_version: "3.4A-RC1" | "3.4B-RC1";
  request_id: string;
  assembly_status: MultiMemberTeePreviewResult["assembly_status"];
  ordinary_pass_allowed: false;
  supported_failure_present: boolean;
  result_fingerprint: string;
  result: { preview: MultiMemberTeePreviewResult; required_limitations: readonly string[] };
}
