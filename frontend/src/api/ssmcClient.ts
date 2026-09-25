import { mat1Fetch } from "./mat1Transport";
import { EvaluationTransportError } from "./client";
import { dctnTransport as t } from "./dctnClient";
import type { MultiRowQuantity as Q } from "./multirowContracts";
import type { Vec3 } from "../visualization/sceneModel";

export interface SSMCSection { form: "CHANNEL" | "W_I"; length: Q; depth: Q; width: Q; web_thickness: Q; flange_thickness: Q }
export interface SSMCGroup { rows: number; first_from_cut: Q; pitch: Q; gauge: Q; transverse_offset: Q; ordinary_snug_tight: boolean; slots: boolean; equal_translational_stiffness: boolean }
export interface SSMCHardware { washer_diameter: Q; washer_thickness: Q; head_across_flats: Q; head_height: Q; nut_across_flats: Q; nut_height: Q; end_extension: Q; geometry_source: string }
export interface SSMCRequest {
  request_id: string; contract: "SSMC-2-RC1"; unit_system: "US" | "SI";
  horizontal: SSMCSection; inclined: SSMCSection; theta_deg: string;
  plate: { side: "NEG_Y" | "POS_Y"; thickness: Q; horizontal_overlap: Q; inclined_overlap: Q; horizontal_depth: Q; inclined_depth: Q; normal_gap: Q; corner_radius: Q; chamfer: Q };
  horizontal_group: SSMCGroup; inclined_group: SSMCGroup;
  fastener: { diameter: Q; hole_diameter: Q; hardware: SSMCHardware; threads: "INCLUDED" | "EXCLUDED"; source_reference: string };
  N: Q; V: Q; M: Q; source_reference: string;
}
export interface SSMCWrench { reference: { x: Q; y: Q; z: Q }; force: { x: Q; y: Q; z: Q }; moment: { x: Q; y: Q; z: Q } }
export interface SSMCResponse {
  request_id: string; contract: "SSMC-2-RC1"; geometry_status: "VALID"; engineering_fingerprint: string; whole_connection_status: string;
  result: {
    input: SSMCRequest; engineering_fingerprint: string; whole_connection_status: string;
    geometry: {
      length_unit: "in" | "mm"; plate_y_interval: [number, number]; plate_side: string;
      polygon: { boundary: [number, number][]; edge_ids: string[]; gross_neck_width: number; area: number };
      polygon_paths: { holes: { center: [number, number]; radius: number; shaft_id: string }[] };
      members: { owner: string; end_reference: Vec3; material_longitudinal: Vec3; material_depth: Vec3; trimmed: { solids: { physical_element_id: string; material_region_id: string; faces: { vertices: Vec3[] }[] }[] } }[];
      shafts: { id: string; group: string; row: number; line: number; start: Vec3; end: Vec3; layer_owners: string[] }[];
    };
    groups: { group_id: string; member_end_wrench: SSMCWrench; plate_wrench: SSMCWrench; planar_status: string }[];
    statuses: [string, string][]; blockers: string[]; evaluated_failures: string[];
    complete_moment_capacity_qualified: false; plate_policy: string;
  };
}
export type SSMCDesignStatus = "PASS" | "FAIL" | "ENGINEERING_REVIEW_REQUIRED" | "SOURCE_REQUIRED" | "NOT_APPLICABLE";
export type SSMCTimeEffectCategory = "DEAD_ONLY" | "IMPACT" | "STORAGE" | "LONG_TERM_OPERATING" | "OTHER_LIVE" | "SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE" | "WIND_TORNADO_SEISMIC";
export interface SSMCAnalyticalRequest {
  physical: SSMCRequest;
  action: {
    basis: "FACTORED_LRFD"; combination_id: string; combination_source: string;
    already_factored: boolean; time_effect_category: SSMCTimeEffectCategory; time_effect_reference: string;
  };
  single_lap: {
    external_actions_at_faying_interface: boolean; independent_normal_force: Q; independent_out_of_plane_moment: Q;
    imposed_separation: boolean; non_contact_gap: boolean; friction_or_preload_credit: boolean; miter_bearing_credit: boolean;
  };
  contract: "SSMC-3-ANALYTICAL-RC1";
}
export interface SSMCAnalyticalCheck {
  owner: string; path_id: string; mode: string; status: SSMCDesignStatus; reason: string;
  demand_N: number; source_id: string | null; qualification_id: string | null;
}
export interface SSMCAnalyticalResponse {
  contract: "SSMC-3-ANALYTICAL-RC1"; method: "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1"; whole_connection_status: SSMCDesignStatus;
  result: {
    contract: "SSMC-3-ANALYTICAL-RC1"; method: "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1";
    whole_connection_status: SSMCDesignStatus; request: SSMCAnalyticalRequest;
    existing_demand: SSMCResponse["result"];
    applicability_status: "ELIGIBLE" | "ENGINEERING_REVIEW_REQUIRED"; applicability_reasons: string[];
    checks: SSMCAnalyticalCheck[]; blockers: string[]; numerical_failures: string[];
    action_reaction: unknown[]; member_cut_demands: unknown[]; cuts: { cuts: unknown[]; finite_coverage_proven: boolean; status: string };
  };
}
const q = t.q, text = t.text, arr = t.array, shape = t.shape;
const number = (v: unknown) => typeof v === "number" && Number.isFinite(v);
const bool = (v: unknown) => typeof v === "boolean";
const vec = shape({ x: number, y: number, z: number });
const pair = (v: unknown) => Array.isArray(v) && v.length === 2 && v.every(number);
const quantities = (keys: string[]) => Object.fromEntries(keys.map(k => [k, q]));
const section = shape({ form: v => v === "CHANNEL" || v === "W_I", ...quantities(["length", "depth", "width", "web_thickness", "flange_thickness"]) });
const group = shape({ rows: v => v === 2 || v === 3, ...quantities(["first_from_cut", "pitch", "gauge", "transverse_offset"]), ordinary_snug_tight: bool, slots: bool, equal_translational_stiffness: bool });
export const isSSMCRequest = (v: unknown): v is SSMCRequest => shape({
  request_id: text, contract: x => x === "SSMC-2-RC1", unit_system: x => x === "US" || x === "SI", theta_deg: t.decimal,
  horizontal: section, inclined: section, horizontal_group: group, inclined_group: group,
  plate: shape({ side: x => x === "NEG_Y" || x === "POS_Y", ...quantities(["thickness", "horizontal_overlap", "inclined_overlap", "horizontal_depth", "inclined_depth", "normal_gap", "corner_radius", "chamfer"]) }),
  fastener: shape({ diameter: q, hole_diameter: q, threads: x => x === "INCLUDED" || x === "EXCLUDED", source_reference: text, hardware: shape({ ...quantities(["washer_diameter", "washer_thickness", "head_across_flats", "head_height", "nut_across_flats", "nut_height", "end_extension"]), geometry_source: text }) }),
  N: q, V: q, M: q, source_reference: text,
})(v);
const responseShape = shape({
  request_id: text, contract: v => v === "SSMC-2-RC1", geometry_status: v => v === "VALID", engineering_fingerprint: text, whole_connection_status: text,
  result: shape({ input: isSSMCRequest, engineering_fingerprint: text, whole_connection_status: text, plate_policy: v => v === "MITER_PLATE_CW_BASIS_UNKNOWN_CUT", complete_moment_capacity_qualified: v => v === false,
    statuses: arr(v => Array.isArray(v) && v.length === 2 && v.every(text)), blockers: arr(text), evaluated_failures: arr(text),
    groups: arr(shape({ group_id: text, member_end_wrench: t.wrench, plate_wrench: t.wrench, planar_status: text })),
    geometry: shape({ length_unit: v => v === "in" || v === "mm", plate_y_interval: pair, plate_side: text,
      polygon: shape({ boundary: v => Array.isArray(v) && v.length >= 3 && v.every(pair), edge_ids: arr(text), gross_neck_width: number, area: number }),
      polygon_paths: shape({ holes: arr(shape({ center: pair, radius: number, shaft_id: text })) }),
      members: arr(shape({ owner: text, end_reference: vec, material_longitudinal: vec, material_depth: vec, trimmed: shape({ solids: arr(shape({ physical_element_id: text, material_region_id: text, faces: arr(shape({ vertices: v => Array.isArray(v) && v.length >= 3 && v.every(vec) })) })) }) })),
      shafts: arr(shape({ id: text, group: text, row: number, line: number, start: vec, end: vec, layer_owners: arr(text) })),
    }),
  }),
});
const designStatus = (v: unknown): v is SSMCDesignStatus => v === "PASS" || v === "FAIL" || v === "ENGINEERING_REVIEW_REQUIRED" || v === "SOURCE_REQUIRED" || v === "NOT_APPLICABLE";
const analyticalResponseShape = shape({
  contract: v => v === "SSMC-3-ANALYTICAL-RC1", method: v => v === "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1", whole_connection_status: designStatus,
  result: shape({
    contract: v => v === "SSMC-3-ANALYTICAL-RC1", method: v => v === "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1", whole_connection_status: designStatus,
    request: shape({ physical: isSSMCRequest }), existing_demand: shape({ input: isSSMCRequest, engineering_fingerprint: text }),
    applicability_status: v => v === "ELIGIBLE" || v === "ENGINEERING_REVIEW_REQUIRED", applicability_reasons: arr(text),
    checks: arr(shape({ owner: text, path_id: text, mode: text, status: designStatus, reason: text, demand_N: number, source_id: v => v === null || text(v), qualification_id: v => v === null || text(v) })),
    blockers: arr(text), numerical_failures: arr(text), action_reaction: arr(() => true), member_cut_demands: arr(() => true),
    cuts: shape({ cuts: arr(() => true), finite_coverage_proven: bool, status: text }),
  }),
});
const endpoint = "/api/v1/calculations/stair-stringer-miter";
async function exchange(path: string, signal: AbortSignal, request?: SSMCRequest | SSMCAnalyticalRequest): Promise<unknown> {
  let response: Response;
  try { response = await mat1Fetch(endpoint + path, { method: request === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, credentials: "same-origin", signal, ...(request === undefined ? {} : { body: JSON.stringify(request) }) }); }
  catch (error) { if (error instanceof DOMException && error.name === "AbortError") throw error; throw new EvaluationTransportError("NETWORK", null, "SSMC service unavailable.", error); }
  let value: unknown;
  try { value = await response.json(); } catch (error) { throw new EvaluationTransportError("RESPONSE", response.status, "Unreadable SSMC response.", error); }
  if (!response.ok) throw new EvaluationTransportError(response.status === 422 ? "VALIDATION" : "HTTP", response.status, "SSMC request rejected: " + JSON.stringify(value), value);
  return value;
}
export async function loadSSMC(signal: AbortSignal): Promise<SSMCRequest> {
  const value = await exchange("/defaults", signal);
  if (!isSSMCRequest(value)) throw new Error("Invalid SSMC defaults contract.");
  return value;
}
export async function convertSSMC(request: SSMCRequest, si: boolean, signal: AbortSignal): Promise<SSMCRequest> {
  const value = await exchange("/convert-units?unit_system=" + (si ? "SI" : "US"), signal, request);
  if (!isSSMCRequest(value)) throw new Error("Invalid SSMC converted-input contract.");
  return value;
}
export async function evaluateSSMC(request: SSMCRequest, kind: "preview" | "design-check", signal: AbortSignal): Promise<SSMCResponse> {
  const value = await exchange("/" + kind, signal, request);
  if (!responseShape(value)) throw new Error("Invalid SSMC response contract.");
  const response = value as SSMCResponse;
  if (response.request_id !== request.request_id || response.result.input.request_id !== request.request_id || response.engineering_fingerprint !== response.result.engineering_fingerprint) throw new Error("SSMC response identity mismatch.");
  const shafts = response.result.geometry.shafts;
  if (new Set(shafts.map(s => s.id)).size !== shafts.length || response.result.geometry.members.length !== 2 || response.result.groups.length !== 2) throw new Error("SSMC physical ownership mismatch.");
  return response;
}
export async function evaluateSSMCAnalytical(request: SSMCAnalyticalRequest, signal: AbortSignal): Promise<SSMCAnalyticalResponse> {
  const value = await exchange("/analytical-design-check", signal, request);
  if (!analyticalResponseShape(value)) throw new Error("Invalid SSMC analytical response contract.");
  const response = value as SSMCAnalyticalResponse;
  if (response.whole_connection_status !== response.result.whole_connection_status ||
    response.result.request.physical.request_id !== request.physical.request_id ||
    response.result.existing_demand.input.request_id !== request.physical.request_id) throw new Error("SSMC analytical response identity mismatch.");
  return response;
}
