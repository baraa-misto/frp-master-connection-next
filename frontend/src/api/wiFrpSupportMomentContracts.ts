import type { MultiRowQuantity } from "./multirowContracts";
import type { WIWallMomentDesign, WallMomentAngle, WallMomentHardware, WallMomentPart, WallMomentVector, WallMomentWrench, WallMomentPattern } from "./wiWallMomentContracts";
import type { WIMomentSpliceRequest } from "./wiMomentSpliceContracts";

export type SupportMode = "WI_FLANGE" | "WI_WEB" | "HOLLOW_SQUARE" | "SOLID_SQUARE" | "CHANNEL_WEB";
export const supportFaces: Readonly<Record<SupportMode,readonly [string,...string[]]>> = {
  WI_FLANGE: ["FLANGE_POS_OUTER","FLANGE_NEG_OUTER"], WI_WEB: ["WEB_NEG_FACE","WEB_POS_FACE"],
  HOLLOW_SQUARE: ["Y_POS_FACE","Y_NEG_FACE","Z_POS_FACE","Z_NEG_FACE"], SOLID_SQUARE: ["Y_POS_FACE","Y_NEG_FACE","Z_POS_FACE","Z_NEG_FACE"],
  CHANNEL_WEB: ["WEB_OUTER","WEB_INNER"],
};
export interface SupportHardware { washer_diameter: MultiRowQuantity; washer_thickness: MultiRowQuantity; head_across_flats: MultiRowQuantity; head_height: MultiRowQuantity; nut_across_flats: MultiRowQuantity; nut_height: MultiRowQuantity; end_extension: MultiRowQuantity; geometry_source: string }
export interface FRPSupportFastener { bolt_diameter: MultiRowQuantity; hole_diameter: MultiRowQuantity; source_authority_id: string; thread_condition: "INCLUDED" | "EXCLUDED" }
export interface FRPMomentAngle {
  geometry: WallMomentAngle["geometry"]; member_pattern: WallMomentPattern; support_pattern: WallMomentPattern;
  fastener: FRPSupportFastener; support_fastener: FRPSupportFastener; member_hardware: SupportHardware; support_hardware: SupportHardware;
  connector_source_reference: string; attachment_source_reference: string; material_id: "ICE_LOCKED_PULTRUDED_FRP"; provider_id: "FRP";
}
export interface ReceivingSupport {
  mode: SupportMode; face: string; depth: MultiRowQuantity; width: MultiRowQuantity; web_or_wall_thickness: MultiRowQuantity; flange_thickness: MultiRowQuantity;
  physical_length: MultiRowQuantity; connection_height: MultiRowQuantity; connection_transverse: MultiRowQuantity; view_length: MultiRowQuantity; material_id: "ICE_LOCKED_PULTRUDED_FRP";
}
export interface WIFrpSupportMomentRequest {
  contract: "4.3-RC1"; request_id: string; beam: WIMomentSpliceRequest["beam"]; beam_physical_length: MultiRowQuantity; gap: MultiRowQuantity; support: ReceivingSupport;
  top: FRPMomentAngle; bottom: FRPMomentAngle; positive_web: FRPMomentAngle; negative_web: FRPMomentAngle;
  actions: { axial: MultiRowQuantity; major_shear: MultiRowQuantity; structural_major_moment: MultiRowQuantity };
  response_source_reference: string; local_zone_source_reference: string; beam_material_id: "ICE_LOCKED_PULTRUDED_FRP";
}
export interface HardwareEnvelope extends Readonly<Omit<SupportHardware,"geometry_source">> {
  readonly bolt_id: string; readonly source: string; readonly start: WallMomentVector; readonly end: WallMomentVector;
  readonly head_start: WallMomentVector; readonly head_end: WallMomentVector; readonly head_washer_start: WallMomentVector; readonly head_washer_end: WallMomentVector;
  readonly nut_washer_start: WallMomentVector; readonly nut_washer_end: WallMomentVector; readonly nut_start: WallMomentVector; readonly nut_end: WallMomentVector;
  readonly shank_start: WallMomentVector; readonly shank_end: WallMomentVector;
}
export interface WIFrpSupportMomentPreview {
  readonly product: string; readonly contract: "4.3-RC1"; readonly input: WIFrpSupportMomentRequest;
  readonly geometry: {
    readonly status: string; readonly reasons: readonly string[]; readonly parts: readonly WallMomentPart[]; readonly display_parts: readonly WallMomentPart[];
    readonly member_bolts: readonly WallMomentHardware[];
    readonly support_bolts: readonly { readonly hardware: WallMomentHardware; readonly crossing: { readonly layer_ids: readonly string[]; readonly material_thicknesses: readonly string[]; readonly depth: string; readonly physical_face: string }; readonly support_point: WallMomentVector; readonly loaded_planes_status: string }[];
    readonly hardware_envelopes: readonly HardwareEnvelope[];
    readonly support_contact_patches: readonly { readonly patch_id: string; readonly group_id: string; readonly face_id: string; readonly corners: readonly WallMomentVector[] }[];
    readonly support: { readonly centroid: WallMomentVector; readonly centroid_authority: string };
    readonly angles: readonly { readonly connector_id: string; readonly heel: WallMomentVector; readonly member_reference_global: WallMomentVector; readonly support_reference_global: WallMomentVector }[];
  };
  readonly connectors: readonly { readonly connector_id: string; readonly core: { readonly request: {readonly member_action: WallMomentWrench}; readonly heel: WallMomentWrench; readonly connector_on_support: WallMomentWrench; readonly fingerprint: string }; readonly support_lvt: WallMomentWrench; readonly support_uvn: WallMomentWrench; readonly support_at_centroid: WallMomentWrench; readonly support_in_plane_scope: string; readonly support_in_plane_demand: unknown; readonly member_out_of_plane_f_c_m_a_m_b: readonly MultiRowQuantity[]; readonly support_out_of_plane_f_n_m_u_m_v: readonly MultiRowQuantity[]; readonly flange_demand: unknown; readonly web_demand: unknown }[];
  readonly slice5: unknown; readonly joint_right_hand_action: WallMomentWrench; readonly support_contribution: WallMomentWrench | null; readonly support_reaction: WallMomentWrench | null;
  readonly equilibrium: { readonly proof_passed: boolean; readonly serialized_force_residual: WallMomentVector; readonly serialized_moment_residual: WallMomentVector } | null;
  readonly engineering_fingerprint: string; readonly disclaimer: string; readonly beam_allocation_applicability: string;
  readonly source_availability: readonly (readonly [string, string, string])[];
}
export interface FRPSupportLocalCheck {
  readonly check_id: string; readonly connector_id: string; readonly layer_id: string; readonly bolt_id: string | null; readonly method: string; readonly status: string;
  readonly demand: MultiRowQuantity | null; readonly resistance: MultiRowQuantity | null; readonly applicability: string; readonly source: string; readonly material_direction: string;
}
export interface FRPSupportBoltCheck {
  readonly check_id: string; readonly connector_id: string; readonly bolt_id: string; readonly section_id: string; readonly layer_ids: readonly string[];
  readonly status: string; readonly reason: string; readonly shear_magnitude: MultiRowQuantity | null; readonly total_tension_including_prying: MultiRowQuantity | null;
}
export interface WIFrpSupportMomentDesign extends Pick<WIWallMomentDesign,"status"|"status_reason"|"native_governing_check_ids"|"native_failed_checks"|"missing_sources"|"connector_results"|"attachment_results"|"common_web_bolts"> {
  readonly preview: WIFrpSupportMomentPreview; readonly beam_local_checks: WIWallMomentDesign["local_checks"]; readonly beam_bearings: WIWallMomentDesign["web_bearing"];
  readonly support_response: {readonly status: string; readonly reasons: readonly string[]; readonly response: unknown } | null;
  readonly support_bolts: readonly FRPSupportBoltCheck[]; readonly support_local_checks: readonly FRPSupportLocalCheck[];
  readonly local_zone: {readonly status: string; readonly required_coverage: readonly string[]; readonly reasons: readonly string[]} | null;
  readonly scope_statuses: readonly (readonly [string,string])[];
}
export interface WIFrpSupportMomentResponse<T> {
  readonly api_transport_schema_version: "4.3-API-RC1"; readonly contract: "4.3-RC1"; readonly request_id: string;
  readonly geometry_status: string; readonly geometry_invalid_reasons: readonly string[]; readonly assembly_status: string;
  readonly ordinary_pass_allowed: false; readonly resistance_evaluated: boolean; readonly design_check_ready: boolean;
  readonly engineering_fingerprint: string; readonly result_fingerprint: string;
  readonly whole_connection_status: "LOCAL_SUPPORT_COMPLETENESS_AND_OVERALL_MEMBER_ANALYSIS_REQUIRED"; readonly result: T;
}
