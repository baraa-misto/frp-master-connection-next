import type { MultiRowQuantity } from "./multirowContracts";
import type { WIMomentSpliceFastener, WIMomentSpliceRequest, WIMomentSpliceVector } from "./wiMomentSpliceContracts";

export interface WallMomentPattern { across: number; along: number; gauge: MultiRowQuantity; pitch: MultiRowQuantity; center: MultiRowQuantity }
export interface WallMomentAngle {
  geometry: { length: MultiRowQuantity; member_leg: MultiRowQuantity; support_leg: MultiRowQuantity; thickness: MultiRowQuantity; inside_radius: MultiRowQuantity; heel_end_reliefs: [MultiRowQuantity, MultiRowQuantity] };
  member_pattern: WallMomentPattern;
  support_pattern: WallMomentPattern;
  fastener: WIMomentSpliceFastener;
  anchors: { nominal_diameter: MultiRowQuantity; hole_diameter: MultiRowQuantity; specified_embedment: MultiRowQuantity; washer_outside_diameter: MultiRowQuantity; washer_thickness: MultiRowQuantity };
  connector_source_reference: string;
  attachment_source_reference: string;
  material_id: "ICE_LOCKED_PULTRUDED_FRP";
  provider_id: "FRP";
}
export interface WIWallMomentRequest {
  contract: "4.2-RC1";
  request_id: string;
  unit_system: "US_CUSTOMARY" | "SI";
  source_length_unit: "in" | "mm";
  beam: WIMomentSpliceRequest["beam"];
  gap: MultiRowQuantity;
  wall: { width: MultiRowQuantity; height: MultiRowQuantity; thickness: MultiRowQuantity; connection_origin_h: MultiRowQuantity; connection_origin_v: MultiRowQuantity };
  top: WallMomentAngle; bottom: WallMomentAngle; positive_web: WallMomentAngle; negative_web: WallMomentAngle;
  actions: { axial: MultiRowQuantity; major_shear: MultiRowQuantity; structural_major_moment: MultiRowQuantity };
}
export interface WallMomentVector { readonly x: MultiRowQuantity; readonly y: MultiRowQuantity; readonly z: MultiRowQuantity }
export interface WallMomentWrench { readonly reference: WallMomentVector; readonly force: WallMomentVector; readonly moment: WallMomentVector }
export interface WallMomentHardware {
  readonly hardware_id: string; readonly group_id: string; readonly start: WallMomentVector; readonly end: WallMomentVector;
  readonly diameter: MultiRowQuantity; readonly hole_diameter: MultiRowQuantity; readonly layers: readonly string[]; readonly blind: boolean;
}
export interface WallMomentPart {
  readonly part_id: string;
  readonly box: { readonly component_id: string; readonly role: string; readonly center_l_v_t: WIMomentSpliceVector; readonly size_l_v_t: WIMomentSpliceVector };
  readonly material_region: { readonly component_id: string; readonly region_id: string; readonly lw_axis: readonly [string,string,string]; readonly cw_axis: readonly [string,string,string]; readonly tt_axis: readonly [string,string,string] } | null;
}
export interface WIWallMomentPreview {
  readonly applied_actions: WIWallMomentRequest["actions"];
  readonly source_plans?: readonly unknown[];
  readonly product_id: string; readonly contract: "4.2-RC1";
  readonly geometry: { readonly status: string; readonly reasons: readonly string[]; readonly parts: readonly WallMomentPart[]; readonly member_bolts: readonly WallMomentHardware[]; readonly wall_anchors: readonly WallMomentHardware[]; readonly angles: readonly { readonly connector_id: string; readonly heel: WallMomentVector; readonly member_reference_global: WallMomentVector; readonly support_reference_global: WallMomentVector }[] };
  readonly connectors: readonly { readonly connector_id: string; readonly instep_plan_status: string; readonly core: { readonly request: { readonly member_action: WallMomentWrench }; readonly heel: WallMomentWrench; readonly connector_on_support: WallMomentWrench; readonly fingerprint: string }; readonly support_global: WallMomentWrench; readonly support_at_wall: WallMomentWrench; readonly flange_demand: unknown; readonly web_demand: unknown }[];
  readonly slice5: { readonly components: readonly { readonly region_id: string; readonly wrench: { readonly force_lvt: WIMomentSpliceVector; readonly moment_lvt: WIMomentSpliceVector } }[] };
  readonly joint_right_hand_action: WallMomentWrench;
  readonly wall_handoff: WallMomentWrench | null; readonly wall_reaction: WallMomentWrench | null;
  readonly equilibrium: { readonly proof_passed: boolean; readonly serialized_force_diagnostic: WallMomentVector; readonly serialized_moment_diagnostic: WallMomentVector; readonly structural_major_moment: MultiRowQuantity } | null;
  readonly engineering_fingerprint: string; readonly disclaimer: string; readonly disclaimer_id: string; readonly sign_method: string;
  readonly whole_connection_status: "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED";
}
export interface WallMomentFailedCheck { readonly result_id: string; readonly limit_state: string; readonly utilization: string | null; readonly design_resistance: MultiRowQuantity | null; readonly demand: MultiRowQuantity | null; readonly numerical_comparison: string }
export interface WallMomentQualifiedCheck {
  readonly status: string; readonly utilization: string | null; readonly method: string; readonly interaction_method: string;
  readonly terms: readonly { readonly component: string; readonly signed_demand: MultiRowQuantity; readonly selected_design_strength: MultiRowQuantity | null; readonly utilization: string }[];
}
export interface WallMomentBearing {
  readonly check_id: string; readonly layer_id: string; readonly demand: MultiRowQuantity; readonly material_direction: string;
  readonly comparison: { readonly numerical_comparison: string; readonly utilization: string | null };
  readonly trace: { readonly factor_trace: { readonly design_resistance: MultiRowQuantity } };
}
export interface WIWallMomentDesign {
  readonly preview: WIWallMomentPreview; readonly status: string; readonly status_reason: string;
  readonly native_governing_check_ids: readonly string[]; readonly native_failed_checks: readonly WallMomentFailedCheck[];
  readonly missing_sources: readonly string[];
  readonly connector_results: readonly { readonly core_fingerprint: string; readonly status: string; readonly reason: string; readonly detail: { readonly body: WallMomentQualifiedCheck; readonly instep: { readonly method: string; readonly utilization: string; readonly passed: boolean; readonly demand: MultiRowQuantity; readonly factors: { readonly design_resistance: MultiRowQuantity } } | null } | null }[];
  readonly attachment_results: readonly { readonly connector_id: string; readonly method: string; readonly check: WallMomentQualifiedCheck }[];
  readonly local_checks: readonly { readonly connector_id: string; readonly layer_id: string; readonly scope_status: string }[];
  readonly web_bearing: readonly WallMomentBearing[];
  readonly flange_bearing: readonly WallMomentBearing[];
  readonly common_web_bolts: readonly { readonly bolt_id: string; readonly status: string; readonly method: string; readonly governing_utilization: string | null; readonly source_required_reason: string | null; readonly per_plane_design_capacity: MultiRowQuantity | null }[];
}
export interface WIWallMomentResponse<T> {
  readonly api_transport_schema_version: "4.2-API-RC1"; readonly contract: "4.2-RC1"; readonly request_id: string;
  readonly geometry_status: string; readonly geometry_invalid_reasons: readonly string[]; readonly assembly_status: string;
  readonly ordinary_pass_allowed: false; readonly resistance_evaluated: boolean; readonly design_check_ready: boolean;
  readonly engineering_fingerprint: string; readonly result_fingerprint: string;
  readonly whole_connection_status: "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"; readonly result: T;
}
