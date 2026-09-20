import type { MultiRowQuantity } from "./multirowContracts";
import type { HardwareEnvelope, SupportHardware, FRPSupportLocalCheck, FRPSupportBoltCheck } from "./wiFrpSupportMomentContracts";
import type { WallMomentAngle, WallMomentHardware, WallMomentPart, WallMomentVector, WallMomentWrench, WIWallMomentDesign } from "./wiWallMomentContracts";

export interface AngleBaseConnector {
  angle: WallMomentAngle;
  extrusion_center: MultiRowQuantity;
  member_hardware: SupportHardware;
  normal_response_source_reference: string;
  fastener_source_reference: string;
}
export interface AngleBaseRequest {
  request_id: string;
  contract: "4.4-RC1";
  column: {leg_x: MultiRowQuantity; leg_y: MultiRowQuantity; thickness: MultiRowQuantity; view_length: MultiRowQuantity; material_id: "ICE_LOCKED_PULTRUDED_FRP"};
  foundation: {width_x: MultiRowQuantity; width_y: MultiRowQuantity; depth: MultiRowQuantity};
  leg_1: AngleBaseConnector;
  leg_2: AngleBaseConnector;
  actions: {axial: MultiRowQuantity; shear_x: MultiRowQuantity; shear_y: MultiRowQuantity; moment_x: MultiRowQuantity; moment_y: MultiRowQuantity; applied_torque_z: MultiRowQuantity};
  response_source_reference: string;
  column_zone_source_reference: string;
}
export interface AngleBasePreview {
  readonly product: "ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION";
  readonly contract: "4.4-RC1";
  readonly input: AngleBaseRequest;
  readonly geometry: {
    readonly status: string; readonly reasons: readonly string[];
    readonly parts: readonly WallMomentPart[]; readonly display_parts: readonly WallMomentPart[];
    readonly member_bolts: readonly WallMomentHardware[];
    readonly foundation_attachments: readonly WallMomentHardware[];
    readonly member_hardware_envelopes: readonly HardwareEnvelope[];
    readonly foundation_washers: readonly WallMomentHardware[];
    readonly column_centroid: WallMomentVector;
    readonly angles: readonly {readonly connector_id: string; readonly heel: WallMomentVector; readonly member_reference_global: WallMomentVector; readonly support_reference_global: WallMomentVector; readonly frame: {readonly a: readonly [string,string,string]; readonly b: readonly [string,string,string]; readonly c: readonly [string,string,string]}}[];
  };
  readonly column_on_base: WallMomentWrench;
  readonly required_total_foundation_action: WallMomentWrench;
  readonly opposite_foundation_reaction: WallMomentWrench;
  readonly branch_allocation_status: string;
  readonly response: {readonly status: string; readonly reasons: readonly string[]; readonly exact_equilibrium: boolean|null; readonly qualified: boolean};
  readonly transfers: readonly {
    readonly connector_id: string;
    readonly core: {readonly request: {readonly member_action: WallMomentWrench}; readonly heel: WallMomentWrench; readonly connector_on_support: WallMomentWrench; readonly fingerprint: string};
    readonly connector_on_foundation: WallMomentWrench; readonly foundation_reaction: WallMomentWrench; readonly foundation_at_report: WallMomentWrench;
    readonly native_core_equilibrium: boolean;
    readonly member_out_of_plane_f_c_m_a_m_b: readonly MultiRowQuantity[];
    readonly in_plane_input: unknown; readonly in_plane_demand: unknown;
  }[];
  readonly direct_column_contact: WallMomentWrench|null;
  readonly foundation_breakdowns: readonly {readonly domain:{readonly connector_id:string}; readonly status:string; readonly reasons:readonly string[]; readonly record:{readonly reference:string;readonly issuer:string;readonly applicability:string;readonly actions:readonly unknown[]}|null;readonly proof:{readonly passed:boolean}|null}[];
  readonly assembled_foundation_action: WallMomentWrench|null;
  readonly assembled_force_residual: WallMomentVector|null;
  readonly assembled_moment_residual: WallMomentVector|null;
  readonly exact_total_transport: boolean; readonly engineering_fingerprint: string;
  readonly disclaimer: string; readonly resistance_evaluated: false;
  readonly foundation_strength_status: string; readonly overall_column_status: string; readonly classification_status: string;
}
export interface AngleBaseDesign {
  readonly status: string; readonly status_reason: string;
  readonly native_governing_check_ids: readonly string[]; readonly failed_check_ids: readonly string[];
  readonly missing_sources: readonly string[]; readonly scope_statuses: readonly (readonly [string,string])[];
  readonly member_bolts: readonly FRPSupportBoltCheck[];
  readonly local_checks: readonly FRPSupportLocalCheck[];
  readonly connector_results: WIWallMomentDesign["connector_results"];
  readonly member_attachment_results: WIWallMomentDesign["attachment_results"];
  readonly member_responses: readonly {readonly status: string; readonly reasons: readonly string[]; readonly proof_scope: string}[];
  readonly local_zone: {readonly status: string; readonly reasons: readonly string[]; readonly required_coverage: readonly string[]}|null;
  readonly result_fingerprint: string;
}
export interface AngleBaseResponse {
  readonly api_transport_schema_version: "4.4-API-RC1"; readonly contract: "4.4-RC1";
  readonly request_id: string; readonly geometry_status: string; readonly geometry_invalid_reasons: readonly string[];
  readonly assembly_status: string; readonly ordinary_pass_allowed: false; readonly resistance_evaluated: boolean; readonly design_check_ready: boolean;
  readonly engineering_fingerprint: string; readonly result_fingerprint: string;
  readonly whole_connection_status: "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED";
  readonly result: {readonly preview: AngleBasePreview; readonly design: AngleBaseDesign|null};
}
