import type { DCTN3BRequest, DCTN3BResponse, DCTNArrangement } from "./dctnContracts";
import { EvaluationTransportError } from "./client";
import { dctnTransport as t, isDCTNRequest } from "./dctnClient";

export function isDCTN3BRequest(v: unknown): v is DCTN3BRequest {
  if (!t.record(v) || v.contract !== "DCTN-3B-RC1" || v.placement_datum !== "CHANNEL_PAIR_LOWER_CLEAR_WEB" || !Array.isArray(v.members) || v.members.length === 0) return false;
  const members = [];
  for (const m of v.members) {
    if (!t.record(m) || "start" in m || "axial_force" in m || !t.shape({ chord_station: t.q, end_center_above_lower_web: t.q, P: t.q, Qp: t.q, Qq: t.q })(m)) return false;
    members.push({ ...m, start: [m.chord_station, m.chord_station, m.chord_station], axial_force: m.P });
  }
  // Reuse validation of unchanged section, pattern and independent hardware.
  return isDCTNRequest({ ...v, contract: "DCTN-2-RC1", members });
}
const component = (v: unknown) => v === null || v === "Qp" || v === "Qq";
const preview = t.shape({
  input: isDCTN3BRequest, geometry: t.geometry, fingerprint: t.text,
  connector_body_count: v => v === 0, global_chord_design_evaluated: v => v === false, global_boundary: t.text,
  geometry_status: t.text, demand_status: t.text, response_status: t.text, qualification_status: t.text, design_status: t.text, blockers: t.array(t.text),
  historical_preview: v => v === null || t.preview(v),
  trusted_response: v => v === null || t.shape({ status: t.text, reasons: t.array(t.text) })(v),
  demand: t.shape({ status: t.text, fingerprint: t.text, total_at_node: t.wrench, members: t.array(t.shape({
    member_id: t.text, u: t.triple(t.rational), p: t.triple(t.rational), q: t.triple(t.rational),
    presentation: t.shape({ Qp_label: t.text, Qq_label: t.text, major_component: component, minor_component: component }),
    at_member_end: t.wrench, transported: t.array(t.shape({ reference_id: t.text, wrench: t.wrench, interpretation: v => v === "WHOLE_MEMBER_DEMAND_AT_REFERENCE_NOT_ALLOCATED_RESPONSE" })),
  })) }),
});
const design = (v: unknown) => t.record(v) && t.design({ ...v, global_chord_design_evaluated: false }) && (v.historical_design === null || t.design(v.historical_design));

export async function loadDCTN3BDefaults(arrangement: DCTNArrangement, si: boolean, signal: AbortSignal): Promise<DCTN3BRequest> {
  const value = await t.exchange(t.endpoint + "/defaults?arrangement=" + arrangement + "&unit_system=" + (si ? "SI" : "US"), signal);
  if (!isDCTN3BRequest(value)) throw new EvaluationTransportError("RESPONSE", 200, "Invalid DCTN-3B defaults.", value);
  return value;
}
export async function convertDCTN3BUnits(request: DCTN3BRequest, si: boolean, signal: AbortSignal): Promise<DCTN3BRequest> {
  const value = await t.exchange(t.endpoint + "/convert-units?unit_system=" + (si ? "SI" : "US"), signal, request);
  if (!isDCTN3BRequest(value)) throw new EvaluationTransportError("RESPONSE", 200, "Invalid DCTN-3B unit conversion.", value);
  return value;
}
export async function requestDCTN3B(kind: "preview" | "design-check", request: DCTN3BRequest, signal: AbortSignal): Promise<DCTN3BResponse> {
  const value = await t.exchange(t.endpoint + "/" + kind, signal, request);
  if (!t.record(value) || value.api_transport_schema_version !== "DCTN-3B-API-RC1" || value.contract !== request.contract || value.request_id !== request.request_id ||
      !t.shape({ geometry_status: t.text, geometry_invalid_reasons: t.array(t.text), engineering_fingerprint: t.text, whole_connection_status: t.text,
        demand_status: t.text, response_status: t.text, qualification_status: t.text, design_status: t.text })(value) ||
      !t.record(value.result) || !preview(value.result.preview) || !(kind === "preview" ? value.result.design === null : design(value.result.design))) {
    throw new EvaluationTransportError("RESPONSE", 200, "Unsupported DCTN-3B response contract.", value);
  }
  const result = value as unknown as DCTN3BResponse;
  const p = result.result.preview, shafts = new Set(p.geometry.shafts.map(s => s.bolt_id));
  const members = p.demand.members.map(m => m.member_id);
  if (shafts.size !== p.geometry.shafts.length || p.geometry.holes.some(h => !shafts.has(h.shaft_id)) ||
      new Set(members).size !== members.length || members.length !== request.members.length || request.members.some(m => !members.includes(m.slot))) {
    throw new EvaluationTransportError("RESPONSE", 200, "DCTN-3B physical/action identity is incomplete or duplicated.", value);
  }
  return result;
}
