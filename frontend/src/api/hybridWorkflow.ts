import type { TwoBoltRequest, GeometryResponse } from "./directTwoBolt";
import type { SingleBoltSceneModel } from "../visualization/sceneModel";
export interface HybridQuantity { value: string; unit: string }
export type HybridGeometry = Record<"vertical_bolt_pitch" | "xb" | "xc" | "brace_near_v_edge_distance" | "brace_leg" | "column_flange" | "brace_thickness" | "column_thickness" | "diameter" | "hole", HybridQuantity> & { phi: string };
export interface HybridCase {
  case_id: string; frame: "DIRECT_P_SKETCH_V_CENTROID" | "DIRECT_P_POSITIVE_N_CENTROID" | "GLOBAL";
  reference: [HybridQuantity, HybridQuantity, HybridQuantity];
  components: [HybridQuantity | null, HybridQuantity | null, HybridQuantity | null, HybridQuantity | null, HybridQuantity | null, HybridQuantity | null];
}
export interface HybridInputs {
  // These are physical boundary representations of the one current connection,
  // never calculation-basis modes. The backend rejects simultaneous native/R3
  // inputs and retains layout-specific applicability for every fresh execution.
  contract: "HYB2-D3-P1-LIVE"; workspace_id: string; revision: number;
  connection: "RHM_R3" | "CURRENT_NATIVE"; alignment: "BRACE" | "SUPPORT";
  geometry: HybridGeometry | null; native_request: TwoBoltRequest | null;
  include_native_lrfd: boolean; asd_cases: HybridCase[]; lrfd_cases: HybridCase[];
  source_profile: "RHM_POLYESTER_100F_SF4" | "UNMATCHED";
  bearing_face: "UNKNOWN" | "DECLARED_STRAIGHT_FREE_EDGE";
  washer_od: HybridQuantity | null; native_edge_distance: HybridQuantity | null;
}
export interface HybridComparison { mechanism: string; case_id: string; basis: "LRFD" | "ASD"; ratio: string | null; outcome: string; evidence_scope: string; equation: string; resistance_trace: string }
export interface HybridRecord {
  revision: number; fingerprint: string; field_use_note: string; coverage_summary: string; data_provenance: string;
  requested_computation: { rhm_comparisons_executed: number; rhm_comparisons_requested: number; native_checks_executed: number; native_run_completed: boolean };
  withheld: [string, string][];
  detailing_failures: { check_kind: string; actual_distance: string; required_distance: string; unit: string; boundary_label: string; source_rule: string }[];
  assessment: {
    evaluated_outcome: "PASS" | "FAIL" | "NOT_EVALUATED"; tone: "green" | "red" | "neutral";
    coverage_state: string; source_domain: string; qualification: string; native_status: string;
    comparisons: HybridComparison[]; governing_asd: HybridComparison | null; governing_lrfd: HybridComparison | null;
    fit: { state: string; action: string; unknowns: string[]; actual_overhang_in: string | null };
  };
}
export interface HybridResponse {
  contract: "HYB2-D3-P1-LIVE"; revision: number; fingerprint: string; workflow_available: true;
  scene: SingleBoltSceneModel | null; native_geometry: GeometryResponse | null;
  record?: HybridRecord; report_handle?: string;
}
const BASE = "/api/v1/direct-hybrid/";
export async function hybridPost<T>(path: string, body: unknown): Promise<T> {
  let response: Response;
  try { response = await fetch(BASE + path, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); }
  catch { throw new Error("Hybrid calculation service could not be reached. Check the isolated backend and Retry."); }
  let data: { detail?: unknown };
  try { data = await response.json() as { detail?: unknown }; }
  catch { throw new Error("Hybrid service returned an unreadable response. Check the backend and Retry."); }
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Review finite inputs, units and the supported calculation scope, then Retry.");
  return data as T;
}
export async function calculateHybrid(path: "preview" | "assess", inputs: HybridInputs): Promise<HybridResponse> {
  const data = await hybridPost<Omit<HybridResponse, "contract" | "workflow_available"> & { contract: string; workflow_available: boolean }>(path, inputs);
  if (data.contract !== inputs.contract || data.revision !== inputs.revision || typeof data.fingerprint !== "string" || !data.workflow_available) throw new Error("Hybrid response does not match the current revision. Retry.");
  if (path === "assess" && (data.record === undefined || data.report_handle === undefined)) throw new Error("Hybrid calculation omitted its current signed record. Retry.");
  return { ...data, contract: inputs.contract, workflow_available: true };
}
export async function downloadHybrid(handle: string, technical: boolean, format: "pdf" | "json" = "pdf", isCurrent: () => boolean = () => true): Promise<void> {
  let response: Response;
  try { response = await fetch(BASE + (format === "json" ? "records/" : "reports/") + encodeURIComponent(handle) + (technical ? "?technical=true" : ""), { credentials: "same-origin" }); }
  catch { throw new Error("Hybrid export service could not be reached. Check the isolated backend and Retry."); }
  if (!response.ok) throw new Error("This hybrid report is stale, expired or unavailable for this account. Recalculate current inputs.");
  const blob = await response.blob();
  if (!isCurrent()) throw new Error("Inputs changed during export. Recalculate current inputs.");
  if (blob.type !== (format === "json" ? "application/json" : "application/pdf")) throw new Error("Hybrid export did not return the requested file type. Retry.");
  const url = URL.createObjectURL(blob), anchor = document.createElement("a");
  anchor.href = url; anchor.download = format === "json" ? "hybrid-calculation-record.json" : technical ? "hybrid-technical-audit.pdf" : "hybrid-connection-calculation.pdf";
  anchor.click(); URL.revokeObjectURL(url);
}
export function enteredCase(id: string, force = "0", shear = "0"): HybridCase {
  const q = (value: string, unit: string): HybridQuantity => ({ value, unit });
  return { case_id: id, frame: "DIRECT_P_SKETCH_V_CENTROID", reference: [q("0", "in"), q("0", "in"), q("0", "in")], components: [q(force, "kip"), q(shear, "kip"), q("0", "kip"), q("0", "kip-in"), q("0", "kip-in"), q("0", "kip-in")] };
}
export function sourceExample(current: HybridInputs): HybridInputs {
  // Inputs-only sample preset. The common workspace confirms replacement and
  // retains an undo snapshot; calculation results are never transferred here.
  const q = (value: string): HybridQuantity => ({ value, unit: "in" });
  return { ...current, connection: "RHM_R3", native_request: null, alignment: "SUPPORT", include_native_lrfd: false,
    geometry: { vertical_bolt_pitch: q("2"), phi: "30.9", xb: q(".4375"), xc: q("1"), brace_near_v_edge_distance: q("1"), brace_leg: q("4"), column_flange: q("4"), brace_thickness: q(".5"), column_thickness: q(".375"), diameter: q(".5"), hole: q(".563") },
    asd_cases: [enteredCase("RHM-source-ASD-example", ".09155", ".0134")], lrfd_cases: [], source_profile: "RHM_POLYESTER_100F_SF4", bearing_face: "UNKNOWN", washer_od: null, native_edge_distance: null };
}
