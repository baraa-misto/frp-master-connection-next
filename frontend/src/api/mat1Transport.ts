/** Versioned material request envelope around the existing explicit design actions. */
import { acceptMAT1Design, mat1FamilyKey, mat1Snapshot, materialSelection, rememberMAT1Preview } from "../state/mat1Session";

interface MAT1TransportResponse {
  readonly overall_status?: string;
  readonly material_ledgers?: unknown[];
  readonly material_issues?: string[];
  readonly native_design?: unknown;
  readonly client_design?: unknown;
}

const routePattern = /^\/api\/v1\/calculations\/([^/?]+)\/(design-check|analytical-design-check|evaluate)(?:\?.*)?$/;
const previewPattern = /^\/api\/v1\/calculations\/([^/?]+)\/preview(?:\?.*)?$/;

function mat1Endpoint(family: string): { readonly path: string; readonly contract: string } {
  if (family === "single-bolt") return { path: "/api/v1/frp-materials/single-bolt/design-check", contract: "MAT1-SINGLE-BOLT-RC0" };
  if (family === "multi-row") return { path: "/api/v1/frp-materials/multi-row/design-check", contract: "MAT1-MULTI-ROW-RC0" };
  if (family === "tee-connector") return { path: "/api/v1/frp-materials/tee-connector/design-check", contract: "MAT1-TEE-RC0" };
  if (family === "stair-stringer-miter") return { path: "/api/v1/frp-materials/stair-stringer-miter/analytical-design-check", contract: "MAT1-SSMC-ANALYTICAL-RC0" };
  return { path: "/api/v1/frp-materials/family/design-check", contract: "MAT1-FAMILY-RC0" };
}

export async function mat1Fetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const state = mat1Snapshot();
  const address = input instanceof URL
    ? input : new URL(typeof input === "string" ? input : input.url, window.location.origin);
  const url = address.pathname + address.search;
  const preview = previewPattern.exec(url);
  if (preview?.[1] !== undefined && init?.method?.toUpperCase() === "POST" && typeof init.body === "string") {
    rememberMAT1Preview(preview[1], init.body);
  }
  const match = routePattern.exec(url);
  if (!state.active || match === null || init?.method?.toUpperCase() !== "POST") return fetch(input, init);
  if (url.includes("connector_body_material=SS316")) throw new Error("MAT1_STAINLESS_MEMBER_ADAPTER_UNAVAILABLE");
  const family = String(match[1]); // The route pattern captures one nonempty family segment.
  if (family === "stair-stringer-miter" && match[2] === "design-check") throw new Error("MAT1_SSMC_REQUIRES_ANALYTICAL_DESIGN_ROUTE");
  if (state.defaultId === null) throw new Error("Assign a connection FRP material before Run Design Check.");
  const selected = materialSelection(state.defaultId);
  if (selected === null) throw new Error("Selected FRP material is unavailable.");
  const conditions = state.conditions;
  if (conditions.sustained_temperature.value === "" || conditions.maximum_temperature.value === "" || conditions.load_case_name.trim() === "" || conditions.time_effect_category === "") throw new Error("Complete the MAT1 design conditions before Run Design Check.");
  const overrides: Record<string, object> = {};
  for (const [owner, id] of Object.entries(state.overrides[family] ?? {})) {
    if (id === null) throw new Error(`FRP component ${owner} is unassigned.`);
    const resolved = materialSelection(id);
    if (resolved === null) throw new Error(`FRP component ${owner} has an unavailable material.`);
    overrides[owner] = resolved;
  }
  if (typeof init.body !== "string") throw new Error("MAT1 design transport requires a JSON request body.");
  const legacy = JSON.parse(init.body) as Record<string, unknown>;
  if (family === "single-bolt" || family === "multi-row") legacy.time_effect_category = conditions.time_effect_category;
  if (family === "stair-stringer-miter" && typeof legacy.action === "object" && legacy.action !== null) {
    legacy.action = { ...legacy.action, time_effect_category: conditions.time_effect_category };
  }
  const endpoint = mat1Endpoint(family);
  const key = mat1FamilyKey(family);
  const request = {
    contract: endpoint.contract,
    ...(endpoint.contract === "MAT1-FAMILY-RC0" ? { family_id: family } : {}),
    legacy_request: legacy,
    assignments: {
      default_material: selected, material_overrides: overrides,
      default_conditions: conditions, condition_overrides: state.conditionOverrides[family] ?? {},
    },
  };
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const response = await fetch(endpoint.path, {
    ...init, headers,
    body: JSON.stringify(request),
  });
  if (!response.ok) return response;
  const body = await response.json() as MAT1TransportResponse;
  if (!acceptMAT1Design(family, key, body)) throw new DOMException("Superseded MAT1 design response.", "AbortError");
  const client = body.client_design ?? body.native_design;
  if (client === undefined) throw new Error("MAT1 design response omitted its public result.");
  return new Response(JSON.stringify(client), { status: response.status, headers: { "Content-Type": "application/json" } });
}
