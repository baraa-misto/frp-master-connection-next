/** SAB2 geometry authority is separate from the existing MAT1 design authority. */
import { buildMAT1DesignEnvelope } from "./mat1Transport";
import type { DirectSupportEndAuthority, MultiRowConnectionRequest, MultiRowDesignResponse, MultiRowVisualization } from "./multirowContracts";
import { acceptMAT1Design, mat1FamilyKey } from "../state/mat1Session";
import { acceptReportSnapshot, invalidateReportSnapshot, reportGeneration } from "../state/reportSession";

export const GEOMETRY_BANNER = "GEOMETRY / CONSTRUCTABILITY ONLY — NOT A STRUCTURAL DESIGN APPROVAL";
export type Alignment = "BRACE" | "SUPPORT";
export type FitState = "FIT_FOR_STATED_GEOMETRY" | "CONDITIONAL" | "DOES_NOT_FIT" | "NOT_EVALUATED";
export type Vector = [string, string, string];
export interface TwoBoltOptions {
  alignment: Alignment;
  spacing: string;
  longitudinal: string;
  transverse: string;
  search: boolean;
  searchLimit: string;
  angleRoot: string;
  supportRoot: string;
  geometrySource: string;
  holeDiameter: string;
  cutPolygon: string; cutSource: string;
  neighborBounds: string; neighborSource: string;
  headEnvelope: string; nutEnvelope: string; toolEnvelope: string; envelopeSource: string;
}
export const INITIAL_TWO_BOLT: TwoBoltOptions = {
  alignment: "BRACE", spacing: "", longitudinal: "0", transverse: "0", search: false, searchLimit: "",
  angleRoot: "", supportRoot: "", geometrySource: "",
  holeDiameter: "",
  cutPolygon: "", cutSource: "", neighborBounds: "", neighborSource: "",
  headEnvelope: "", nutEnvelope: "", toolEnvelope: "", envelopeSource: "",
};
export function editedTwoBolt(options: TwoBoltOptions): boolean {
  return options.alignment !== "BRACE" || options.spacing !== "" ||
    options.longitudinal !== "0" || options.transverse !== "0" ||
    options.angleRoot !== "" || options.supportRoot !== "" || options.holeDiameter !== "" ||
    options.cutPolygon !== "" || options.neighborBounds !== "" || options.headEnvelope !== "" ||
    options.nutEnvelope !== "" || options.toolEnvelope !== "";
}
interface Quantity { value: string; unit: "in" | "mm" }
interface Offset { support_longitudinal: Quantity; support_transverse: Quantity }
export interface TwoBoltRequest {
  contract: "SHEAR01-DIRECT-SAB2-GEOMETRY-V1";
  revision: string;
  legacy: MultiRowConnectionRequest;
  material_request?: unknown;
  alignment: Alignment;
  spacing: Quantity;
  hole_diameter?: Quantity;
  offset: Offset;
  angle_root_encroachment?: Quantity;
  support_root_encroachment?: Quantity;
  manufactured_geometry_source?: string;
  midpoint_search?: { minimum: Offset; maximum: Offset };
  end_cuts?: { member_id: string; polygon: Quantity[][]; source: string }[];
  neighbors?: { id: string; support_local_lower: Quantity[]; support_local_upper: Quantity[]; source: string }[];
  hardware?: { kind: "HEAD" | "NUT" | "TOOL"; radius: Quantity; axial_start: Quantity; axial_end: Quantity; source: string }[];
}
export interface GeometryOutcome {
  centers: [Vector, Vector];
  face_points: { station: string; member_id: string; face_id: string; local_center: Vector; global_center: Vector; face_point_global: Vector }[];
  margins: { station: string; owner: string; role: string; boundary: string; source: string; value: string }[];
  hole_state: FitState;
  shaft_state: FitState;
  washer_state: FitState;
  obstruction_state: FitState;
  hardware_state: FitState;
  installation_state: FitState;
  aggregate_state: FitState;
  unknowns: string[];
}
export interface GeometryResponse {
  contract: "SHEAR01-DIRECT-SAB2-GEOMETRY-V1";
  revision: string;
  geometry_fingerprint: string;
  geometry_report_handle: string;
  direct_support_end_authority: DirectSupportEndAuthority;
  geometry: GeometryOutcome;
  pair_input: {
    midpoint: Vector; spacing: string; hole_radius: string; washer_radius: string;
    faces: { id: string; member_id: string; boundaries: { id: string; a: string; b: string; limit: string; role: string }[]; seating_strips: [string, string][] }[];
  };
  visualization: Pick<MultiRowVisualization, "physical_connection" | "physical_bolts" | "connection_demand" | "automatic_bolt_demands">;
  structural_eligible: boolean;
  structural_route: "B_FRESH_LEGACY_COMPATIBLE" | "C_GEOMETRY_ONLY";
  structural_reason: string;
  comparison: { alignment: Alignment; basis: string; geometry: GeometryOutcome };
  midpoint_regions: { assigned_strips: number[]; polygon: [string, string][]; proposed_offset: [string, string]; proposed_request_offset: [string, string]; candidate_geometry: GeometryOutcome; moment_diagnostic: unknown }[];
  moment_diagnostic: unknown;
}

export function twoBoltRequest(legacy: MultiRowConnectionRequest, options: TwoBoltOptions, revision: string): TwoBoltRequest {
  const quantity = (value: string): Quantity => ({ value, unit: "in" });
  const numbers = (text: string, count: number, label: string) => {
    const values = text.trim().split(/[\s,]+/);
    if (values.length !== count || values.some((v) => !Number.isFinite(Number(v)))) throw new Error(label + ": enter " + String(count) + " finite values in inches.");
    return values.map(quantity);
  };
  const hardware: NonNullable<TwoBoltRequest["hardware"]> = [];
  for (const [kind, text] of [["HEAD", options.headEnvelope], ["NUT", options.nutEnvelope], ["TOOL", options.toolEnvelope]] as const) {
    if (text === "") continue;
    const [radius, axial_start, axial_end] = numbers(text, 3, kind + " envelope") as [Quantity, Quantity, Quantity];
    hardware.push({ kind, radius, axial_start, axial_end, source: options.envelopeSource });
  }
  const neighbor = options.neighborBounds === "" ? null : numbers(options.neighborBounds, 6, "Neighbor bounds");
  const cut = options.cutPolygon === "" ? null : options.cutPolygon.split(";").map((p) => numbers(p, 2, "Angle cut vertex"));
  let material: { request: { legacy_request: Record<string, unknown> } } | undefined;
  try { material = buildMAT1DesignEnvelope("multi-row", JSON.stringify(legacy)); } catch { /* Incomplete conditions remain explicit; geometry does not require them. */ }
  const currentLegacy = material === undefined ? legacy : material.request.legacy_request as unknown as MultiRowConnectionRequest;
  const cutMember = currentLegacy.physical_connection?.joint_assembly.members.find((m) => m.section.kind === "ANGLE")?.id;
  const endCuts: NonNullable<TwoBoltRequest["end_cuts"]> = [];
  if (cut !== null) {
    if (cutMember === undefined) throw new Error("An Angle cut requires the current physical Angle member.");
    endCuts.push({ member_id: cutMember, polygon: cut, source: options.cutSource });
  }
  const spacing = options.spacing === "" ? legacy.pitch : quantity(options.spacing);
  return {
    contract: "SHEAR01-DIRECT-SAB2-GEOMETRY-V1", revision, legacy: currentLegacy,
    ...(material === undefined ? {} : { material_request: material.request }),
    alignment: options.alignment,
    spacing: { value: spacing.value, unit: spacing.unit as "in" | "mm" },
    ...(options.holeDiameter === "" ? {} : { hole_diameter: quantity(options.holeDiameter) }),
    offset: { support_longitudinal: quantity(options.longitudinal), support_transverse: quantity(options.transverse) },
    ...(options.angleRoot === "" ? {} : { angle_root_encroachment: quantity(options.angleRoot) }),
    ...(options.supportRoot === "" ? {} : { support_root_encroachment: quantity(options.supportRoot) }),
    ...(options.geometrySource === "" ? {} : { manufactured_geometry_source: options.geometrySource }),
    ...(endCuts.length === 0 ? {} : { end_cuts: endCuts }),
    ...(neighbor === null ? {} : { neighbors: [{ id: "DECLARED-NEIGHBOR", support_local_lower: neighbor.slice(0, 3), support_local_upper: neighbor.slice(3), source: options.neighborSource }] }),
    ...(hardware.length === 0 ? {} : { hardware }),
    ...(options.search ? { midpoint_search: {
      minimum: { support_longitudinal: quantity(String(-Number(options.searchLimit))), support_transverse: quantity(String(-Number(options.searchLimit))) },
      maximum: { support_longitudinal: quantity(options.searchLimit), support_transverse: quantity(options.searchLimit) },
    } } : {}),
  };
}

async function post(path: string, body: unknown, signal?: AbortSignal): Promise<Response> {
  let response: Response;
  try {
    response = await fetch("/api/v1/direct-two-bolt/" + path, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      ...(signal === undefined ? {} : { signal }),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error("Connection geometry service could not be reached. Check the local backend, then Retry.");
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: "Geometry service returned an unreadable error. Retry." })) as { detail?: unknown };
    const detail = typeof data.detail === "string" ? data.detail :
      typeof data.detail === "object" && data.detail !== null && "message" in data.detail ? String(data.detail.message) : "Review the geometry inputs, then Retry.";
    throw new Error(detail);
  }
  return response;
}

export async function previewTwoBolt(request: TwoBoltRequest, signal: AbortSignal): Promise<GeometryResponse> {
  const data = await (await post("preview", request, signal)).json() as (Omit<GeometryResponse, "contract"> & { contract: string }) | null;
  if (data?.contract !== request.contract || data.revision !== request.revision || typeof data.geometry_fingerprint !== "string") {
    throw new Error("Geometry service returned an incompatible preview. Retry the current inputs.");
  }
  return data as GeometryResponse;
}

export async function designTwoBolt(request: TwoBoltRequest, signal: AbortSignal, isCurrent: () => boolean): Promise<MultiRowDesignResponse> {
  invalidateReportSnapshot("multi-row");
  const generation = reportGeneration("multi-row");
  const key = mat1FamilyKey("multi-row");
  const data = await (await post("design-check", request, signal)).json() as {
    result: { client_design?: MultiRowDesignResponse; native_design?: MultiRowDesignResponse }; report_handle: string;
  };
  if (signal.aborted || !isCurrent()) throw new DOMException("Superseded geometry design.", "AbortError");
  if (!acceptMAT1Design("multi-row", key, data.result)) throw new DOMException("Superseded material design.", "AbortError");
  acceptReportSnapshot("multi-row", data.report_handle, "design", generation);
  const result = data.result.client_design ?? data.result.native_design;
  if (result === undefined) throw new Error("Design service omitted its current result.");
  return result;
}

export async function exportGeometry(request: TwoBoltRequest, preview: GeometryResponse): Promise<Blob> {
  return (await post("geometry-review", { report_handle: preview.geometry_report_handle, current_request: request })).blob();
}
