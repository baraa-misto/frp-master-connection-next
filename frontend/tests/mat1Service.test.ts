import { afterEach, expect, it, vi } from "vitest";
import { inspectMAT1Factors, loadMAT1Catalog, loadMAT1Owners } from "../src/api/mat1Service";
import type { FactorInspectionRequest } from "../src/api/mat1Service";

const signal = new AbortController().signal;
const response = (body: unknown, status = 200): Response => new Response(JSON.stringify(body), { status });
const catalog = { contract: "MAT1-CATALOG-RC0", records: [{
  id: "ICE", revision: "RC0", content_digest: "digest", display_name: "ICE", properties: [],
}] };
const owners = { contract: "MAT1-OWNER-PREVIEW-RC0", family_id: "multi-row", owners: ["A"], design_check_performed: false };
const factors = { contract: "MAT1-FACTOR-RC0", record_id: "ICE", ledgers: [], design_check_performed: false };
const request = { material: { kind: "CATALOG", id: "ICE", revision: "RC0", content_digest: "digest" },
  conditions: {} as FactorInspectionRequest["conditions"], component_id: "A", property_ids: ["Ft,L"] } satisfies FactorInspectionRequest;

afterEach(() => { vi.unstubAllGlobals(); });

it("uses same-origin typed catalog, owner and factor service requests", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(response(catalog))
    .mockResolvedValueOnce(response(owners))
    .mockResolvedValueOnce(response(factors));
  vi.stubGlobal("fetch", fetchMock);
  expect(await loadMAT1Catalog(signal)).toEqual(catalog.records);
  expect(await loadMAT1Owners("multi-row", { legacy: true }, signal)).toEqual(["A"]);
  expect(await inspectMAT1Factors(request, signal)).toEqual(factors);
  expect(fetchMock.mock.calls.map((call: unknown[]) => call[0])).toEqual([
    "/api/v1/frp-materials/catalog", "/api/v1/frp-materials/family/owners", "/api/v1/frp-materials/factor-candidates",
  ]);
  expect(fetchMock.mock.calls.every((call: unknown[]) => (call[1] as RequestInit).credentials === "same-origin")).toBe(true);
});

it("fails closed for every malformed catalog record contract", async () => {
  for (const body of [null, [], {}, { ...catalog, contract: "wrong" }, { ...catalog, records: null },
    ...[null, [], {}, { id: 1 }, { id: "x", revision: 1 }, { id: "x", revision: "1", content_digest: 1 },
      { id: "x", revision: "1", content_digest: "d", display_name: 1 },
      { id: "x", revision: "1", content_digest: "d", display_name: "x", properties: null }]
      .map((record) => ({ ...catalog, records: [record] }))]) {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    await expect(loadMAT1Catalog(signal)).rejects.toThrow("MAT1 catalog contract is invalid.");
  }
});

it("rejects malformed owner and factor replies", async () => {
  for (const body of [null, [], {}, { ...owners, contract: "wrong" }, { ...owners, family_id: "other" },
    { ...owners, design_check_performed: true }, { ...owners, owners: null }, { ...owners, owners: [1] }]) {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    await expect(loadMAT1Owners("multi-row", {}, signal)).rejects.toThrow("MAT1 owner preview contract is invalid.");
  }
  for (const body of [null, [], {}, { ...factors, contract: "wrong" },
    { ...factors, design_check_performed: true }, { ...factors, record_id: null }, { ...factors, ledgers: null }]) {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    await expect(inspectMAT1Factors(request, signal)).rejects.toThrow("MAT1 factor response contract is invalid.");
  }
});

it("distinguishes HTTP, invalid JSON, network and cancellation failures", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({}, 503)));
  await expect(loadMAT1Catalog(signal)).rejects.toThrow("MAT1 service HTTP 503");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{broken", { status: 200 })));
  await expect(loadMAT1Catalog(signal)).rejects.toThrow("MAT1 service returned invalid JSON.");
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  await expect(loadMAT1Catalog(signal)).rejects.toThrow("MAT1 service could not be reached.");
  const controller = new AbortController();
  controller.abort();
  const aborted = new Error("aborted");
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(aborted));
  await expect(loadMAT1Catalog(controller.signal)).rejects.toBe(aborted);
});
