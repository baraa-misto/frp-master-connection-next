import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { MAT1CatalogRecord, MAT1Conditions } from "../src/state/mat1Session";
import { loadJ1Benchmark } from "../src/fixtures/j1Benchmarks";

const record: MAT1CatalogRecord = {
  id: "ICE:POLY", revision: "RC0", content_digest: "A".repeat(64), display_name: "ICE", company: "ICE",
  resin: "ISOPHTHALIC_POLYESTER", source_kind: "OWNER", missing: [], qualification: "UNQUALIFIED", properties: [],
};
const conditions: MAT1Conditions = {
  sustained_temperature: { value: "90", unit: "degF" }, maximum_temperature: { value: "90", unit: "degF" },
  glass_transition_temperature: null, moisture: "REFERENCE", chemical: "NONE_DECLARED", load_case_name: "LC-1",
  time_effect_category: "WIND_TORNADO_SEISMIC", source_reference_condition: "UNKNOWN",
  chemical_substance: "", chemical_concentration: "", chemical_contact_form: "", chemical_duration: "",
  uv_weathering: "UNKNOWN", freeze_thaw: "UNKNOWN", protective_measures: "", exposure_notes: "",
  action_provenance: "", live_load_subtype: "", full_amplitude_duration: "", design_period: "", service_period: "", fatigue_cycles: "",
};
type Store = typeof import("../src/state/mat1Session");
type Transport = typeof import("../src/api/mat1Transport");
let store: Store;
let transport: Transport;
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(async () => {
  vi.resetModules();
  fetchMock = vi.fn(() => Promise.resolve(new Response(JSON.stringify({ native_design: { status: "legacy" }, overall_status: "SOURCE_REQUIRED" }), { status: 200 })));
  vi.stubGlobal("fetch", fetchMock);
  store = await import("../src/state/mat1Session");
  transport = await import("../src/api/mat1Transport");
});
afterEach(() => { vi.unstubAllGlobals(); });
function ready(): void {
  store.setMAT1Catalog([record]); store.setMAT1Default(record.id); store.setMAT1Conditions(conditions);
}
const post = (path: string, body: object = { a: 1 }) => transport.mat1Fetch(path, { method: "POST", headers: { Accept: "application/json" }, body: JSON.stringify(body) });

it("forwards only an installed qualification ID for Direct and invalidates its snapshot", async () => {
  ready();
  store.setDirectQualificationRecordId("INSTALLED-Q1");
  await post("/api/v1/calculations/multi-row/design-check", { direct_finalization_contract_version: "SHEAR01-DIRECT-F1", layers: [] });
  const request = JSON.parse((fetchMock.mock.calls.at(-1)?.[1] as RequestInit).body as string) as Record<string, unknown>;
  expect(request.qualification_record_id).toBe("INSTALLED-Q1");
  expect(request).not.toHaveProperty("specimens");
  await post("/api/v1/calculations/multi-row/design-check", { layers: [] });
  const other = JSON.parse((fetchMock.mock.calls.at(-1)?.[1] as RequestInit).body as string) as Record<string, unknown>;
  expect(other).not.toHaveProperty("qualification_record_id");
});

it("keeps preview geometry-only and records its input for currency", async () => {
  await post("/api/v1/calculations/clip-angle/preview", { geometry: 1 });
  expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/calculations/clip-angle/preview");
  expect(store.mat1Snapshot().previewInputs["clip-angle"]).toBe('{"geometry":1}');
  ready();
  await post("/api/v1/calculations/clip-angle/preview", { geometry: 2 });
  expect(store.mat1Snapshot().previewInputs["clip-angle"]).toBe('{"geometry":2}');
});

it("routes every special design envelope and stores backend source status", async () => {
  ready();
  for (const [family, action, target, contract] of [
    ["single-bolt", "evaluate", "single-bolt", "MAT1-SINGLE-BOLT-RC0"],
    ["multi-row", "design-check", "multi-row", "MAT1-MULTI-ROW-RC0"],
    ["tee-connector", "design-check", "tee-connector", "MAT1-TEE-RC0"],
    ["stair-stringer-miter", "analytical-design-check", "stair-stringer-miter", "MAT1-SSMC-ANALYTICAL-RC0"],
    ["clip-angle", "design-check", "family", "MAT1-FAMILY-RC0"],
  ] as const) {
    const result = await post(`/api/v1/calculations/${family}/${action}`, { action: { time_effect_category: "DEAD_ONLY" }, time_effect_category: "DEAD_ONLY" });
    expect(await result.json()).toEqual({ status: "legacy" });
    const last = fetchMock.mock.calls.at(-1);
    expect(last?.[0]).toContain(`/api/v1/frp-materials/${target}/`);
    const body = JSON.parse((last?.[1] as RequestInit).body as string) as { contract: string; legacy_request: { action: { time_effect_category: string }; time_effect_category: string } };
    expect(body.contract).toBe(contract);
    if (family === "single-bolt" || family === "multi-row") expect(body.legacy_request.time_effect_category).toBe("WIND_TORNADO_SEISMIC");
    if (family === "stair-stringer-miter") expect(body.legacy_request.action.time_effect_category).toBe("WIND_TORNADO_SEISMIC");
    expect(store.mat1Snapshot().designTraces[family]).toMatchObject({ overall_status: "SOURCE_REQUIRED" });
  }
  await transport.mat1Fetch("/api/v1/calculations/clip-angle/design-check", {
    method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: "{}",
  });
  const forwardedHeaders = new Headers((fetchMock.mock.calls.at(-1)?.[1] as RequestInit).headers);
  expect(forwardedHeaders.get("Content-Type")).toBe("application/json");
});

it("binds the selected Direct fastener to the signed design envelope and stales it on change", async () => {
  ready();
  await post("/api/v1/calculations/multi-row/design-check", { direct_finalization_contract_version: "SHEAR01-DIRECT-F1", layers: [] });
  const standard = JSON.parse((fetchMock.mock.calls.at(-1)?.[1] as RequestInit).body as string) as { fastener: unknown };
  expect(standard.fastener).toEqual(store.defaultFastenerSelection);
  const snapshot = structuredClone(loadJ1Benchmark("US_CUSTOMARY").fastener_snapshot);
  snapshot.id = "USER_FASTENER_UI_QA";
  snapshot.locked = false;
  snapshot.fnt = { value: "75", unit: "ksi" };
  snapshot.fnt_source_classification = "USER_DEFINED";
  snapshot.fnt_qualification_status = "DEVELOPMENT_ONLY";
  store.setFastenerSelection("multi-row", {
    kind: "SESSION", contract: "FASTENER-OR1-RC1", revision: "1",
    source_label: "QA session source", fnt_source_basis: "QA-only Fnt", snapshot,
  });
  await post("/api/v1/calculations/multi-row/design-check", { layers: [] });
  const submitted = JSON.parse((fetchMock.mock.calls.at(-1)?.[1] as RequestInit).body as string) as {
    fastener: { kind: string; snapshot: { id: string; fnt: { value: string } } };
  };
  expect(submitted.fastener).toMatchObject({ kind: "SESSION", snapshot: { id: "USER_FASTENER_UI_QA", fnt: { value: "75" } } });
  expect(store.mat1Snapshot().designKeys["multi-row"]).toBe(store.mat1FamilyKey("multi-row"));
  store.setFastenerSelection("multi-row", store.defaultFastenerSelection);
  expect(store.mat1Snapshot().designKeys["multi-row"]).not.toBe(store.mat1FamilyKey("multi-row"));
  await post("/api/v1/calculations/clip-angle/design-check");
  const unrelated = JSON.parse((fetchMock.mock.calls.at(-1)?.[1] as RequestInit).body as string) as Record<string, unknown>;
  expect(unrelated).not.toHaveProperty("fastener");
});

it("blocks missing inputs, unassigned owners and stainless bypasses", async () => {
  ready();
  store.setMAT1Default(null);
  await expect(post("/api/v1/calculations/clip-angle/design-check")).rejects.toThrow("Assign a connection FRP material");
  store.setMAT1Default(record.id);
  store.setMAT1Default("missing");
  await expect(post("/api/v1/calculations/clip-angle/design-check")).rejects.toThrow("Selected FRP material is unavailable");
  store.setMAT1Default(record.id);
  store.setMAT1Conditions({ ...conditions, load_case_name: "" });
  await expect(post("/api/v1/calculations/clip-angle/design-check")).rejects.toThrow("Complete the MAT1 design conditions");
  store.setMAT1Conditions(conditions);
  store.setMAT1Override("clip-angle", "ANGLE", null);
  await expect(post("/api/v1/calculations/clip-angle/design-check")).rejects.toThrow("unassigned");
  store.setMAT1Override("clip-angle", "ANGLE", "missing");
  await expect(post("/api/v1/calculations/clip-angle/design-check")).rejects.toThrow("unavailable material");
  store.setMAT1Override("clip-angle", "ANGLE", undefined);
  await expect(transport.mat1Fetch("/api/v1/calculations/clip-angle/design-check", { method: "POST" })).rejects.toThrow("JSON request body");
  await expect(post("/api/v1/calculations/clip-angle/design-check?connector_body_material=SS316")).rejects.toThrow("MAT1_STAINLESS_MEMBER_ADAPTER_UNAVAILABLE");
  await expect(post("/api/v1/calculations/stair-stringer-miter/design-check")).rejects.toThrow("MAT1_SSMC_REQUIRES_ANALYTICAL_DESIGN_ROUTE");
  expect(fetchMock).not.toHaveBeenCalled();
});

it("passes neutral legacy factors once and blocks an imported manual factor", async () => {
  ready();
  const factors = { cm: "1", ct: "1", cch: "1" };
  await post("/api/v1/calculations/single-bolt/evaluate", { end_use_factors: factors });
  let body = JSON.parse((fetchMock.mock.calls.at(-1)?.[1] as RequestInit).body as string) as {
    legacy_request: { end_use_factors: typeof factors };
  };
  expect(body.legacy_request.end_use_factors).toMatchObject(factors);
  expect(body.legacy_request.end_use_factors).toHaveProperty("source_reference", expect.stringContaining("MAT1-adjusted"));
  await post("/api/v1/calculations/multi-row/design-check", { layers: [{ end_use_factors: factors }] });
  body = JSON.parse((fetchMock.mock.calls.at(-1)?.[1] as RequestInit).body as string) as typeof body;
  expect((body.legacy_request as unknown as { layers: { end_use_factors: typeof factors }[] }).layers[0]?.end_use_factors).toMatchObject(factors);
  await post("/api/v1/calculations/multi-row/design-check", { layers: [{}] });
  body = JSON.parse((fetchMock.mock.calls.at(-1)?.[1] as RequestInit).body as string) as typeof body;
  expect((body.legacy_request as unknown as { layers: { end_use_factors: typeof factors }[] }).layers[0]?.end_use_factors).toMatchObject(factors);
  await expect(post("/api/v1/calculations/multi-row/design-check", {
    layers: [{ end_use_factors: { cm: "0.75", ct: "1", cch: "1" } }],
  })).rejects.toThrow("imported design contains manual end-use factors");
  await expect(post("/api/v1/calculations/single-bolt/evaluate", {
    end_use_factors: { cm: "0.75", ct: "1", cch: "1" },
  })).rejects.toThrow("imported design contains manual end-use factors");
});

it("preserves a valid physical override and normalizes Request and URL inputs", async () => {
  ready();
  store.setMAT1Override("clip-angle", "ANGLE", record.id);
  await transport.mat1Fetch(new URL("http://example.test/api/v1/calculations/clip-angle/design-check"), { method: "POST", body: "{}" });
  const body = JSON.parse((fetchMock.mock.calls[0]?.[1] as RequestInit).body as string) as { assignments: { material_overrides: Record<string, unknown> } };
  expect(body.assignments.material_overrides.ANGLE).toMatchObject({ kind: "CATALOG", id: record.id });
  const request = new Request("http://example.test/api/v1/calculations/clip-angle/preview", { method: "POST", body: "{}" });
  await transport.mat1Fetch(request, { method: "POST", body: "{}" });
  expect(store.mat1Snapshot().previewInputs["clip-angle"]).toBe("{}");
});

it("rejects stale responses and preserves backend validation failures", async () => {
  ready();
  fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ client_design: { status: "PASS" }, overall_status: "SOURCE_REQUIRED" }), { status: 200 }));
  const staleRequest = post("/api/v1/calculations/clip-angle/design-check");
  store.setMAT1Conditions({ ...conditions, moisture: "OTHER" });
  await expect(staleRequest).rejects.toMatchObject({ name: "AbortError" });
  expect(store.mat1Snapshot().designTraces["clip-angle"]).toBeUndefined();
  fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ detail: "invalid" }), { status: 422 }));
  expect((await post("/api/v1/calculations/clip-angle/design-check")).status).toBe(422);
  fetchMock.mockResolvedValueOnce(new Response("Renderer unavailable", { status: 503 }));
  expect((await post("/api/v1/calculations/clip-angle/design-check")).status).toBe(503);
  fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ overall_status: "SOURCE_REQUIRED" }), { status: 200 }));
  await expect(post("/api/v1/calculations/clip-angle/design-check")).rejects.toThrow("omitted its public result");
});
