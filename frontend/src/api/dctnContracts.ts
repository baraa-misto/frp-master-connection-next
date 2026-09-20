import type { MultiRowQuantity } from "./multirowContracts";
import type { Vec3 } from "../visualization/sceneModel";

export type DCTNArrangement = "VERTICAL_ONLY" | "ONE_INCLINED" | "TWO_INCLINED" | "VERTICAL_ONE_INCLINED" | "VERTICAL_TWO_INCLINED";
export type DCTNForm = "RHS" | "SOLID_RECTANGLE" | "W_I";
export type DCTNSlot = "V" | "D1" | "D2";
export interface DCTNSection {
  form: DCTNForm;
  length: MultiRowQuantity;
  depth: MultiRowQuantity;
  width: MultiRowQuantity;
  wall_or_web: MultiRowQuantity;
  flange_thickness: MultiRowQuantity;
}
export interface DCTNMember {
  slot: DCTNSlot;
  section: DCTNSection;
  start: [MultiRowQuantity, MultiRowQuantity, MultiRowQuantity];
  inclination_deg: string;
  axial_force: MultiRowQuantity;
  pattern: { rows: number; across: number; first_from_start: MultiRowQuantity; pitch: MultiRowQuantity; wi_offset: MultiRowQuantity; staggered: boolean };
  material_source_reference: string;
  local_path_source_reference: string;
  material_id: "ICE_LOCKED_PULTRUDED_FRP";
}
export interface DCTNHardware {
  washer_diameter: MultiRowQuantity; washer_thickness: MultiRowQuantity;
  head_across_flats: MultiRowQuantity; head_height: MultiRowQuantity;
  nut_across_flats: MultiRowQuantity; nut_height: MultiRowQuantity;
  end_extension: MultiRowQuantity; geometry_source: string;
}
export interface DCTNRequest {
  request_id: string; contract: "DCTN-2-RC1"; unit_system: "US" | "SI"; length_unit: "in" | "mm";
  arrangement: DCTNArrangement;
  channel: { length: MultiRowQuantity; depth: MultiRowQuantity; flange_width: MultiRowQuantity; web_thickness: MultiRowQuantity; flange_thickness: MultiRowQuantity; material_source_reference: string; material_id: "ICE_LOCKED_PULTRUDED_FRP" };
  members: DCTNMember[];
  fastener: { diameter: MultiRowQuantity; hole_diameter: MultiRowQuantity; hardware: DCTNHardware; source_reference: string; threads_excluded: boolean; snug_tight: boolean; product_id: "ASTM_F593_GROUP2_316" };
  shared_channel_source_reference: string;
}
export interface DCTNRational { readonly numerator: string; readonly denominator: string }
export type DCTNRational3 = readonly [DCTNRational, DCTNRational, DCTNRational];
export interface DCTNFrame { readonly origin: Vec3; readonly x_axis: Vec3; readonly y_axis: Vec3; readonly z_axis: Vec3 }
export interface DCTNPrism { readonly extent: { readonly x_start: number; readonly x_end: number }; readonly rectangle: { readonly min_y: number; readonly max_y: number; readonly min_z: number; readonly max_z: number } }
export interface DCTNPlacement {
  readonly global_frame: DCTNFrame;
  readonly physical_elements: readonly {
    readonly source_element: { readonly id: string; readonly material_region_id: string };
    readonly source_material_region: { readonly orientation: { readonly crosswise_axis: "X" | "Y" | "Z"; readonly through_thickness_axis: "X" | "Y" | "Z"; readonly crosswise_sign: number; readonly through_thickness_sign: number } };
    readonly global_frame: DCTNFrame;
    readonly extrusions: readonly DCTNPrism[];
  }[];
  readonly deferred_features: readonly { readonly source_feature: { readonly id: string }; readonly global_frame: DCTNFrame; readonly extrusion: DCTNPrism | { readonly is_zero_thickness: true } }[];
}
export interface DCTNWrench {
  readonly reference: { readonly x: MultiRowQuantity; readonly y: MultiRowQuantity; readonly z: MultiRowQuantity };
  readonly force: { readonly x: MultiRowQuantity; readonly y: MultiRowQuantity; readonly z: MultiRowQuantity };
  readonly moment: { readonly x: MultiRowQuantity; readonly y: MultiRowQuantity; readonly z: MultiRowQuantity };
}
export interface DCTNPreview {
  readonly input: DCTNRequest; readonly fingerprint: string; readonly connector_body_count: 0;
  readonly geometry: {
    readonly status: string; readonly reasons: readonly string[]; readonly length_unit: "in" | "mm";
    readonly members: readonly { readonly physical_id: string; readonly profile: { readonly family: string }; readonly placement: DCTNPlacement; readonly start: DCTNRational3; readonly u: DCTNRational3; readonly v: DCTNRational3; readonly w: DCTNRational3 }[];
    readonly shafts: readonly { readonly bolt_id: string; readonly member_id: string; readonly row: number; readonly side: string; readonly start: DCTNRational3; readonly end: DCTNRational3; readonly layer_owners: readonly string[]; readonly free_span: string; readonly physical_bolt_count: 1 }[];
    readonly holes: readonly { readonly hole_id: string; readonly owner_id: string; readonly group_id: string; readonly shaft_id: string; readonly center: DCTNRational3; readonly hole_valid: boolean; readonly hardware_footprint_valid: boolean }[];
  };
  readonly response: {
    readonly status: string; readonly reasons: readonly string[]; readonly method: string;
    readonly rows: readonly { readonly member_id: string; readonly row: number; readonly row_fraction: string; readonly side_fraction: string; readonly signed_row_force: MultiRowQuantity; readonly member_force_closes: boolean; readonly member_moment_closes: boolean; readonly negative_at_channel: DCTNWrench; readonly positive_at_channel: DCTNWrench }[];
    readonly channels: readonly { readonly member_id: string; readonly total: DCTNWrench; readonly hole_ids: readonly string[]; readonly group_ids: readonly string[] }[];
  };
  readonly global_chord_design_evaluated: false; readonly global_boundary: string;
}
export interface DCTNDesign {
  readonly checks: readonly { readonly check_id: string; readonly owner_id: string; readonly status: string; readonly demand: MultiRowQuantity | null; readonly resistance: MultiRowQuantity | null; readonly source_reference: string; readonly native_trace: unknown }[];
  readonly blockers: readonly string[]; readonly governing_checks: readonly string[]; readonly whole_connection_status: string; readonly fingerprint: string; readonly global_chord_design_evaluated: false;
}
export interface DCTNResponse {
  readonly api_transport_schema_version: "DCTN-2-API-RC1"; readonly request_id: string; readonly contract: "DCTN-2-RC1";
  readonly geometry_status: string; readonly geometry_invalid_reasons: readonly string[];
  readonly engineering_fingerprint: string; readonly whole_connection_status: string;
  readonly result: { readonly preview: DCTNPreview; readonly design: DCTNDesign | null };
}

export interface DCTN3BMember extends Omit<DCTNMember, "start" | "axial_force"> {
  chord_station: MultiRowQuantity;
  end_center_above_lower_web: MultiRowQuantity;
  P: MultiRowQuantity;
  Qp: MultiRowQuantity;
  Qq: MultiRowQuantity;
}
export interface DCTN3BRequest extends Omit<DCTNRequest, "contract" | "members"> {
  contract: "DCTN-3B-RC1";
  placement_datum: "CHANNEL_PAIR_LOWER_CLEAR_WEB";
  members: DCTN3BMember[];
}
export interface DCTNShearPresentation {
  readonly Qp_label: string;
  readonly Qq_label: string;
  readonly major_component: "Qp" | "Qq" | null;
  readonly minor_component: "Qp" | "Qq" | null;
}
export interface DCTN3BPreview {
  readonly input: DCTN3BRequest;
  readonly geometry: DCTNPreview["geometry"];
  readonly demand: {
    readonly status: string;
    readonly fingerprint: string;
    readonly total_at_node: DCTNWrench;
    readonly members: readonly {
      readonly member_id: DCTNSlot;
      readonly u: DCTNRational3; readonly p: DCTNRational3; readonly q: DCTNRational3;
      readonly presentation: DCTNShearPresentation;
      readonly at_member_end: DCTNWrench;
      readonly transported: readonly { readonly reference_id: string; readonly wrench: DCTNWrench; readonly interpretation: string }[];
    }[];
  };
  readonly historical_preview: DCTNPreview | null;
  readonly trusted_response: { readonly status: string; readonly reasons: readonly string[]; readonly response: unknown } | null;
  readonly geometry_status: string; readonly demand_status: string; readonly response_status: string;
  readonly qualification_status: string; readonly design_status: string;
  readonly blockers: readonly string[]; readonly fingerprint: string;
  readonly connector_body_count: 0; readonly global_chord_design_evaluated: false; readonly global_boundary: string;
}
export interface DCTN3BDesign extends Omit<DCTNDesign, "global_chord_design_evaluated"> {
  readonly historical_design: DCTNDesign | null;
}
export interface DCTN3BResponse extends Omit<DCTNResponse, "contract" | "api_transport_schema_version" | "result"> {
  readonly contract: "DCTN-3B-RC1";
  readonly api_transport_schema_version: "DCTN-3B-API-RC1";
  readonly demand_status: string; readonly response_status: string;
  readonly qualification_status: string; readonly design_status: string;
  readonly result: { readonly preview: DCTN3BPreview; readonly design: DCTN3BDesign | null };
}
