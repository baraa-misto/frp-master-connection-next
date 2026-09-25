import { EvaluationTransportError } from "./client";
import { mat1Snapshot } from "../state/mat1Session";

export const ACTIVATION_AUTHORITY = "CME_3_316SS_PUBLIC_CONNECTOR_BODY_ACTIVATION_RC1";
export const BODY_ROUTES = [
  "beam-web-splice", "wi-major-axis-moment-splice", "channel-major-axis-moment-splice",
  "clip-angle", "paired-clip-angle", "beam-concrete-paired-angle", "column-base-web-angles",
  "wi-beam-concrete-wall-moment", "wi-beam-frp-support-moment", "angle-column-two-leg-moment-base",
  "wi-rhs-srs-column-moment-base", "tee-connector", "multi-member-tee",
] as const;
export type BodyRoute = typeof BODY_ROUTES[number];
export type ConnectorBodyMaterial = "FRP" | "SS316";
export interface ActivatedBody {
  readonly body_id: string;
  readonly body_form: "PLATE" | "ANGLE" | "TEE";
  readonly material: "SS316";
  readonly activation: "ACTIVE_CONDITIONAL";
  readonly fingerprint: string;
  readonly blockers: readonly string[];
  readonly provider_fingerprints: readonly string[];
  readonly frp_body_resistance_used: false;
}
export interface StainlessActivationResponse {
  readonly activation_authority: typeof ACTIVATION_AUTHORITY;
  readonly route_id: BodyRoute;
  readonly connector_body_material: "SS316";
  readonly status: "PASS" | "FAIL" | "ENGINEERING_REVIEW_REQUIRED";
  readonly fingerprint: string;
  readonly bodies: readonly ActivatedBody[];
  readonly blockers: readonly string[];
  readonly native_non_body_checks: readonly unknown[];
  readonly trace: unknown;
}

const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
const texts = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item: unknown) => typeof item === "string");
const fingerprint = (value: unknown): value is string =>
  typeof value === "string" && /^[0-9a-f]{64}$/.test(value);

export function parseStainlessActivation(value: unknown, route: BodyRoute): StainlessActivationResponse {
  if (!record(value) || value.activation_authority !== ACTIVATION_AUTHORITY
    || value.route_id !== route || value.connector_body_material !== "SS316"
    || !["PASS", "FAIL", "ENGINEERING_REVIEW_REQUIRED"].includes(String(value.status))
    || !fingerprint(value.fingerprint) || !texts(value.blockers)
    || !Array.isArray(value.native_non_body_checks) || !Array.isArray(value.bodies)
    || value.bodies.length === 0 || !("trace" in value)) {
    throw new Error("Invalid conditional stainless activation response");
  }
  const identities = new Set<string>();
  for (const item of value.bodies as unknown[]) {
    if (!record(item) || typeof item.body_id !== "string" || item.body_id.length === 0
      || identities.has(item.body_id) || !["PLATE", "ANGLE", "TEE"].includes(String(item.body_form))
      || item.material !== "SS316" || item.activation !== "ACTIVE_CONDITIONAL"
      || item.frp_body_resistance_used !== false || !fingerprint(item.fingerprint)
      || !texts(item.blockers) || !texts(item.provider_fingerprints)
      || !item.provider_fingerprints.every(fingerprint)) {
      throw new Error("Invalid conditional stainless body record");
    }
    identities.add(item.body_id);
  }
  if (value.status === "PASS" && (value.blockers.length !== 0
    || (value.bodies as ActivatedBody[]).some(body => body.blockers.length !== 0))) {
    throw new Error("Incomplete stainless qualification cannot report PASS");
  }
  return value as unknown as StainlessActivationResponse;
}

export async function evaluateStainlessActivation(
  route: BodyRoute, request: object, signal: AbortSignal,
): Promise<StainlessActivationResponse> {
  if (mat1Snapshot().active) {
    throw new Error("MAT1 stainless-body member material routing is unavailable; no legacy FRP material design was run.");
  }
  if (!(BODY_ROUTES as readonly string[]).includes(route)) {
    throw new Error("CONNECTOR_BODY_MATERIAL_NOT_APPLICABLE_TO_ROUTE");
  }
  let response: Response;
  try {
    response = await fetch(`/api/v1/calculations/${route}/design-check?connector_body_material=SS316`, {
      method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request), signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError("NETWORK", null, "The stainless design service could not be reached.", error);
  }
  let payload: unknown;
  try { payload = await response.json(); }
  catch { throw new EvaluationTransportError("RESPONSE", response.status, "Invalid stainless design response JSON."); }
  if (!response.ok) {
    const kind = response.status === 422 ? "VALIDATION" : response.status === 401 || response.status === 403 ? "IDENTITY" : "HTTP";
    throw new EvaluationTransportError(kind, response.status, `Stainless design returned HTTP ${String(response.status)}.`, payload);
  }
  try { return parseStainlessActivation(payload, route); }
  catch (error) { throw new EvaluationTransportError("RESPONSE", response.status, "The server did not return a bound stainless design result.", error); }
}
