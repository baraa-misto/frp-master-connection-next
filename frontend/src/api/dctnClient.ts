import type { DCTN3BRequest, DCTNArrangement, DCTNRequest, DCTNResponse } from "./dctnContracts";
import { EvaluationTransportError } from "./client";

type Validator = (value: unknown) => boolean;
const record = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === "object" && !Array.isArray(v);
const text: Validator = v => typeof v === "string";
const number: Validator = v => typeof v === "number" && Number.isFinite(v);
const decimal: Validator = v => typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v));
const bool: Validator = v => typeof v === "boolean";
const array = (f: Validator): Validator => v => Array.isArray(v) && v.every(f);
const shape = (s: Readonly<Record<string, Validator>>): Validator => v => record(v) && Object.entries(s).every(([k, f]) => f(v[k]));
const q = shape({ value: decimal, unit: text });
const vec = shape({ x: number, y: number, z: number });
const qvec = shape({ x: q, y: q, z: q });
const rational = shape({ numerator: decimal, denominator: v => decimal(v) && Number(v) !== 0 });
const triple = (f: Validator): Validator => v => Array.isArray(v) && v.length === 3 && v.every(f);
const frame = shape({ origin: vec, x_axis: vec, y_axis: vec, z_axis: vec });
const wrench = shape({ reference: qvec, force: qvec, moment: qvec });
const section = shape({ form: v => ["RHS", "SOLID_RECTANGLE", "W_I"].includes(String(v)), length: q, depth: q, width: q, wall_or_web: q, flange_thickness: q });
const member = shape({ slot: v => ["V", "D1", "D2"].includes(String(v)), section, start: triple(q), inclination_deg: decimal, axial_force: q, pattern: shape({ rows: number, across: number, first_from_start: q, pitch: q, wi_offset: q, staggered: bool }), material_source_reference: text, local_path_source_reference: text, material_id: v => v === "ICE_LOCKED_PULTRUDED_FRP" });
const hardware = shape({ washer_diameter: q, washer_thickness: q, head_across_flats: q, head_height: q, nut_across_flats: q, nut_height: q, end_extension: q, geometry_source: text });
const requestShape = shape({
  request_id: text, contract: v => v === "DCTN-2-RC1", unit_system: v => v === "US" || v === "SI", length_unit: v => v === "in" || v === "mm",
  arrangement: v => ["VERTICAL_ONLY", "ONE_INCLINED", "TWO_INCLINED", "VERTICAL_ONE_INCLINED", "VERTICAL_TWO_INCLINED"].includes(String(v)),
  channel: shape({ length: q, depth: q, flange_width: q, web_thickness: q, flange_thickness: q, material_source_reference: text, material_id: v => v === "ICE_LOCKED_PULTRUDED_FRP" }),
  members: array(member), fastener: shape({ diameter: q, hole_diameter: q, hardware, source_reference: text, threads_excluded: bool, snug_tight: bool, product_id: v => v === "ASTM_F593_GROUP2_316" }), shared_channel_source_reference: text,
});
export function isDCTNRequest(v: unknown): v is DCTNRequest { return requestShape(v); }
const orientation = shape({ crosswise_axis: v => ["X", "Y", "Z"].includes(String(v)), through_thickness_axis: v => ["X", "Y", "Z"].includes(String(v)), crosswise_sign: number, through_thickness_sign: number });
const prism = shape({ extent: shape({ x_start: number, x_end: number }), rectangle: shape({ min_y: number, max_y: number, min_z: number, max_z: number }) });
const placement = shape({ global_frame: frame, physical_elements: array(shape({ source_element: shape({ id: text, material_region_id: text }), source_material_region: shape({ orientation }), global_frame: frame, extrusions: array(prism) })), deferred_features: array(shape({ source_feature: shape({ id: text }), global_frame: frame, extrusion: v => prism(v) || shape({ is_zero_thickness: v => v === true })(v) })) });
const geometry = shape({ status: text, reasons: array(text), length_unit: v => v === "in" || v === "mm",
    members: array(shape({ physical_id: text, profile: shape({ family: text }), placement, start: triple(rational), u: triple(rational), v: triple(rational), w: triple(rational) })),
    shafts: array(shape({ bolt_id: text, member_id: text, row: number, side: text, start: triple(rational), end: triple(rational), layer_owners: array(text), free_span: decimal, physical_bolt_count: v => v === 1 })),
    holes: array(shape({ hole_id: text, owner_id: text, group_id: text, shaft_id: text, center: triple(rational), hole_valid: bool, hardware_footprint_valid: bool })),
  });
const preview = shape({
  input: requestShape, fingerprint: text, connector_body_count: v => v === 0, global_chord_design_evaluated: v => v === false, global_boundary: text,
  geometry,
  response: shape({ status: text, reasons: array(text), method: text, rows: array(shape({ member_id: text, row: number, row_fraction: decimal, side_fraction: decimal, signed_row_force: q, member_force_closes: bool, member_moment_closes: bool, negative_at_channel: wrench, positive_at_channel: wrench })), channels: array(shape({ member_id: text, total: wrench, hole_ids: array(text), group_ids: array(text) })) }),
});
const nullableQ: Validator = v => v === null || q(v);
const design = shape({ checks: array(shape({ check_id: text, owner_id: text, status: text, demand: nullableQ, resistance: nullableQ, source_reference: text })), blockers: array(text), governing_checks: array(text), whole_connection_status: text, fingerprint: text, global_chord_design_evaluated: v => v === false });
const endpoint = "/api/v1/calculations/double-channel-truss-node";
async function exchange(url: string, signal: AbortSignal, request?: DCTNRequest | DCTN3BRequest): Promise<unknown> {
  let response: Response;
  try { response = await fetch(url, { method: request === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, credentials: "same-origin", signal, ...(request === undefined ? {} : { body: JSON.stringify(request) }) }); }
  catch (error) { if (error instanceof DOMException && error.name === "AbortError") throw error; throw new EvaluationTransportError("NETWORK", null, "DCTN service could not be reached.", error); }
  let value: unknown;
  try { value = await response.json(); } catch (error) { throw new EvaluationTransportError("RESPONSE", response.status, "Unreadable DCTN response.", error); }
  if (!response.ok) throw new EvaluationTransportError(response.status === 422 ? "VALIDATION" : "HTTP", response.status, "DCTN request rejected: " + JSON.stringify(value), value);
  return value;
}
export async function loadDCTNDefaults(arrangement: DCTNArrangement, si: boolean, signal: AbortSignal): Promise<DCTNRequest> {
  const value = await exchange(endpoint + "/defaults?contract=DCTN-2-RC1&arrangement=" + arrangement + "&unit_system=" + (si ? "SI" : "US"), signal);
  if (!isDCTNRequest(value)) throw new EvaluationTransportError("RESPONSE", 200, "Invalid DCTN defaults.", value);
  return value;
}
export async function convertDCTNUnits(request: DCTNRequest, si: boolean, signal: AbortSignal): Promise<DCTNRequest> {
  const value = await exchange(endpoint + "/convert-units?unit_system=" + (si ? "SI" : "US"), signal, request);
  if (!isDCTNRequest(value)) throw new EvaluationTransportError("RESPONSE", 200, "Invalid DCTN unit conversion.", value);
  return value;
}
export async function requestDCTN(kind: "preview" | "design-check", request: DCTNRequest, signal: AbortSignal): Promise<DCTNResponse> {
  const value = await exchange(endpoint + "/" + kind, signal, request);
  if (!record(value) || value.api_transport_schema_version !== "DCTN-2-API-RC1" || value.contract !== "DCTN-2-RC1" || value.request_id !== request.request_id || !shape({ geometry_status: text, geometry_invalid_reasons: array(text), engineering_fingerprint: text, whole_connection_status: text })(value) || !record(value.result) || !preview(value.result.preview) || !(kind === "preview" ? value.result.design === null : design(value.result.design))) throw new EvaluationTransportError("RESPONSE", 200, "Unsupported DCTN response contract.", value);
  const result = value as unknown as DCTNResponse;
  const geometry = result.result.preview.geometry;
  const shafts = new Set(geometry.shafts.map(s => s.bolt_id));
  if (shafts.size !== geometry.shafts.length || geometry.holes.some(h => !shafts.has(h.shaft_id))) throw new EvaluationTransportError("RESPONSE", 200, "DCTN physical shaft identity is incomplete or duplicated.", value);
  return result;
}

// Shared transport validation only; no engineering or version reinterpretation.
export const dctnTransport = { record, text, decimal, array, shape, q, triple, rational, wrench, geometry, preview, design, exchange, endpoint };
