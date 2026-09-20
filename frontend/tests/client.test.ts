import { afterEach, describe, expect, it, vi } from "vitest";

import {
  EvaluationTransportError,
  DIRECT_SIDE_LAP_CONCRETE_DESIGN_PATH,
  DIRECT_SIDE_LAP_CONCRETE_PREVIEW_PATH,
  MULTIROW_DESIGN_PATH,
  MULTIROW_PREVIEW_PATH,
  SINGLE_BOLT_EVALUATION_PATH,
  SINGLE_BOLT_PREVIEW_PATH,
  TEE_CONNECTOR_DESIGN_PATH,
  TEE_CONNECTOR_PREVIEW_PATH,
  evaluateTeeConnector,
  evaluateDirectSideLapConcrete,
  evaluateSingleBolt,
  evaluateMultiRow,
  previewMultiRow,
  previewSingleBolt,
  previewDirectSideLapConcrete,
  previewTeeConnector,
} from "../src/api/client";
import type { MultiRowConnectionRequest } from "../src/api/multirowContracts";
import { loadJ1Benchmark, loadJ1ViewExtents } from "../src/fixtures/j1Benchmarks";
import { loadDirectSideLapConcreteBenchmark } from "../src/fixtures/directSideLapConcreteBenchmarks";
import { buildSingleBoltPreviewRequest } from "../src/workspace/previewWorkflow";
import { previewResponseFixture, responseFixture } from "./fixtures";
import { minimalTeeRequest, teeDesignFixture, teePreviewFixture } from "./teeFixtures";
import {
  directSideLapDesignFixture,
  directSideLapPreviewFixture,
} from "./directSideLapConcreteFixtures";
import type { FullThroughBoltTrace } from "../src/api/teeContracts";

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("typed same-origin single-bolt API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts the strict request DTO to the same-origin endpoint and accepts engineering HTTP 200", async () => {
    const fetch = vi.fn().mockResolvedValue(response(responseFixture()));
    vi.stubGlobal("fetch", fetch);
    const request = loadJ1Benchmark("US_CUSTOMARY");
    await expect(evaluateSingleBolt(request)).resolves.toMatchObject({
      aggregate_status: "SECTION_2_3_2_QUALIFICATION_REQUIRED",
    });
    expect(fetch).toHaveBeenCalledWith(
      SINGLE_BOLT_EVALUATION_PATH,
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      }),
    );
  });

  it("passes an optional abort signal without adding a production host", async () => {
    const fetch = vi.fn().mockResolvedValue(response(responseFixture()));
    vi.stubGlobal("fetch", fetch);
    const controller = new AbortController();
    await evaluateSingleBolt(loadJ1Benchmark("SI"), controller.signal);
    expect(fetch.mock.calls[0]?.[0]).toBe("/api/v1/calculations/single-bolt/evaluate");
    expect(fetch.mock.calls[0]?.[1]).toMatchObject({ signal: controller.signal });
  });

  it("classifies network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(evaluateSingleBolt(loadJ1Benchmark("US_CUSTOMARY"))).rejects.toMatchObject({
      kind: "NETWORK",
      status: null,
    });
  });

  it.each([
    [422, "VALIDATION"],
    [401, "IDENTITY"],
    [403, "IDENTITY"],
    [503, "HTTP"],
  ] as const)("classifies HTTP %i independently from engineering status", async (status, kind) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: "controlled" }, status)));
    await expect(evaluateSingleBolt(loadJ1Benchmark("US_CUSTOMARY"))).rejects.toMatchObject({
      kind,
      status,
      detail: { detail: "controlled" },
    });
  });

  it("rejects an unsupported successful response contract", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ results: [] })));
    await expect(evaluateSingleBolt(loadJ1Benchmark("US_CUSTOMARY"))).rejects.toMatchObject({
      kind: "RESPONSE",
      status: 200,
    });
  });

  it("handles an unreadable response body without leaking a parser exception", async () => {
    const unreadable = new Response("not json", { status: 422 });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(unreadable));
    try {
      await evaluateSingleBolt(loadJ1Benchmark("US_CUSTOMARY"));
      throw new Error("expected transport failure");
    } catch (error) {
      expect(error).toBeInstanceOf(EvaluationTransportError);
      expect(error).toMatchObject({ kind: "VALIDATION", detail: null });
    }
  });

  it("requires visualization frames and the exact transport schema", async () => {
    const invalid = responseFixture();
    invalid.visualization.frames = [];
    Object.assign(invalid, { api_transport_schema_version: "0.1.0-draft" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(invalid)));
    await expect(evaluateSingleBolt(loadJ1Benchmark("US_CUSTOMARY"))).rejects.toBeInstanceOf(
      EvaluationTransportError,
    );
  });

  it.each([
    null,
    { api_transport_schema_version: "0.3.0-draft", results: [] },
    { api_transport_schema_version: "0.3.0-draft", results: [], visualization: null },
    { api_transport_schema_version: "0.3.0-draft", results: [], visualization: { frames: "invalid" } },
  ])("rejects malformed successful response variant %#", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    await expect(evaluateSingleBolt(loadJ1Benchmark("US_CUSTOMARY"))).rejects.toMatchObject({
      kind: "RESPONSE",
      status: 200,
    });
  });

  it.each([
    "PREVIEW_VALID",
    "PREVIEW_INVALID_GEOMETRY",
    "PREVIEW_INCOMPLETE_INPUT",
    "PREVIEW_UNSUPPORTED",
  ] as const)("posts a strict preview request with AbortSignal and accepts %s", async (status) => {
    const body = previewResponseFixture();
    body.geometry_status = status;
    if (status !== "PREVIEW_VALID") body.visualization = null;
    const fetch = vi.fn().mockResolvedValue(response(body));
    vi.stubGlobal("fetch", fetch);
    const request = buildSingleBoltPreviewRequest(loadJ1Benchmark("US_CUSTOMARY"), loadJ1ViewExtents("US_CUSTOMARY"));
    const controller = new AbortController();

    await expect(previewSingleBolt(request, controller.signal)).resolves.toMatchObject({
      geometry_status: status,
    });
    expect(fetch).toHaveBeenCalledWith(
      SINGLE_BOLT_PREVIEW_PATH,
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal: controller.signal,
      }),
    );
  });

  it("propagates intentional preview and design aborts without transport wrapping", async () => {
    const aborted = new DOMException("aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(aborted));
    const request = loadJ1Benchmark("US_CUSTOMARY");
    const controller = new AbortController();

    await expect(evaluateSingleBolt(request, controller.signal)).rejects.toBe(aborted);
    await expect(
      previewSingleBolt(buildSingleBoltPreviewRequest(request, loadJ1ViewExtents("US_CUSTOMARY")), controller.signal),
    ).rejects.toBe(aborted);
  });

  it("classifies preview network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    const request = buildSingleBoltPreviewRequest(loadJ1Benchmark("US_CUSTOMARY"), loadJ1ViewExtents("US_CUSTOMARY"));

    await expect(previewSingleBolt(request, new AbortController().signal)).rejects.toMatchObject({
      kind: "NETWORK",
      status: null,
    });
  });

  it.each([
    [422, "VALIDATION"],
    [401, "IDENTITY"],
    [403, "IDENTITY"],
    [503, "HTTP"],
  ] as const)("classifies preview HTTP %i as %s", async (status, kind) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: "controlled" }, status)));
    const request = buildSingleBoltPreviewRequest(loadJ1Benchmark("US_CUSTOMARY"), loadJ1ViewExtents("US_CUSTOMARY"));

    await expect(previewSingleBolt(request, new AbortController().signal)).rejects.toMatchObject({
      kind,
      status,
      detail: { detail: "controlled" },
    });
  });

  it("handles an unreadable preview error body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not json", { status: 422 })));
    const request = buildSingleBoltPreviewRequest(loadJ1Benchmark("US_CUSTOMARY"), loadJ1ViewExtents("US_CUSTOMARY"));

    await expect(previewSingleBolt(request, new AbortController().signal)).rejects.toMatchObject({
      kind: "VALIDATION",
      detail: null,
    });
  });

  it.each([
    null,
    "preview",
    { preview_schema_version: "wrong", geometry_status: "PREVIEW_VALID", visualization: null, design_check_ready: true },
    { preview_schema_version: "0.2.0-draft", geometry_status: 1, visualization: null, design_check_ready: true },
    { preview_schema_version: "0.2.0-draft", geometry_status: "NOT_A_STATUS", visualization: null, design_check_ready: true },
    { preview_schema_version: "0.2.0-draft", geometry_status: "PREVIEW_VALID", visualization: "invalid", design_check_ready: true },
    { preview_schema_version: "0.2.0-draft", geometry_status: "PREVIEW_VALID", visualization: null, design_check_ready: "yes" },
  ])("rejects malformed successful preview response variant %#", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    const request = buildSingleBoltPreviewRequest(loadJ1Benchmark("US_CUSTOMARY"), loadJ1ViewExtents("US_CUSTOMARY"));

    await expect(previewSingleBolt(request, new AbortController().signal)).rejects.toMatchObject({
      kind: "RESPONSE",
      status: 200,
    });
  });
});

describe("typed same-origin multi-row API client", () => {
  const request = { request_id: "MR" } as MultiRowConnectionRequest;
  const preview = {
    api_transport_schema_version: "0.3.0-draft",
    orchestration_contract_version: "2.5C-RC1",
    resistance_evaluated: false,
    preview_fingerprint: "a".repeat(64),
  };
  const design = {
    api_transport_schema_version: "0.3.0-draft",
    orchestration_contract_version: "2.5C-RC1",
    preview,
  };

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts preview and design to the exact Stage 2.5C operations", async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(response(preview))
      .mockResolvedValueOnce(response(design));
    vi.stubGlobal("fetch", fetch);
    const signal = new AbortController().signal;
    await expect(previewMultiRow(request, signal)).resolves.toMatchObject(preview);
    await expect(evaluateMultiRow(request, signal)).resolves.toMatchObject(design);
    expect(fetch.mock.calls[0]?.[0]).toBe(MULTIROW_PREVIEW_PATH);
    expect(fetch.mock.calls[1]?.[0]).toBe(MULTIROW_DESIGN_PATH);
    expect(fetch.mock.calls[0]?.[1]).toMatchObject({
      body: JSON.stringify(request),
      credentials: "same-origin",
      signal,
    });
  });

  it.each([
    [422, "VALIDATION"],
    [401, "IDENTITY"],
    [500, "HTTP"],
  ] as const)("classifies multi-row HTTP %i as %s", async (status, kind) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: "controlled" }, status)));
    await expect(previewMultiRow(request, new AbortController().signal)).rejects.toMatchObject({
      kind,
      status,
    });
  });

  it("preserves aborts and wraps other multi-row network failures", async () => {
    const abort = new DOMException("cancelled", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(abort).mockRejectedValueOnce(new Error("offline")));
    await expect(previewMultiRow(request, new AbortController().signal)).rejects.toBe(abort);
    await expect(evaluateMultiRow(request, new AbortController().signal)).rejects.toMatchObject({ kind: "NETWORK" });
  });

  it.each([
    null,
    { ...preview, api_transport_schema_version: "wrong" },
    { ...preview, orchestration_contract_version: "wrong" },
    { ...preview, resistance_evaluated: true },
    { ...preview, preview_fingerprint: 1 },
  ])("rejects malformed multi-row preview response %#", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    await expect(previewMultiRow(request, new AbortController().signal)).rejects.toMatchObject({
      kind: "RESPONSE",
    });
  });

  it.each([
    null,
    { ...design, api_transport_schema_version: "wrong" },
    { ...design, orchestration_contract_version: "wrong" },
    { ...design, preview: null },
  ])("rejects malformed multi-row design response %#", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    await expect(evaluateMultiRow(request, new AbortController().signal)).rejects.toMatchObject({
      kind: "RESPONSE",
    });
  });
});

describe("typed same-origin Tee connector API client", () => {
  afterEach(() => { vi.unstubAllGlobals(); });

  it("posts preview and design requests to the two exact stateless routes", async () => {
    const preview = teePreviewFixture();
    const design = teeDesignFixture();
    const fetch = vi.fn()
      .mockResolvedValueOnce(response(preview))
      .mockResolvedValueOnce(response(design));
    vi.stubGlobal("fetch", fetch);
    const request = minimalTeeRequest();
    const signal = new AbortController().signal;

    await expect(previewTeeConnector(request, signal)).resolves.toEqual(preview);
    await expect(evaluateTeeConnector(request, signal)).resolves.toEqual(design);
    expect(fetch.mock.calls[0]?.[0]).toBe(TEE_CONNECTOR_PREVIEW_PATH);
    expect(fetch.mock.calls[1]?.[0]).toBe(TEE_CONNECTOR_DESIGN_PATH);
    expect(fetch.mock.calls[0]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify(request),
      credentials: "same-origin",
      signal,
    });
  });

  it("requires finite decimal-string physical endpoints for every full-through path", async () => {
    const validTrace: FullThroughBoltTrace = {
      path: {
        bolt_id: "A_B_R1_L1",
        segments: [{ kind: "MATERIAL_LAYER", identity: "TEE_STEM", length: "0.5" }],
      },
      hardware: {
        bolt_id: "A_B_R1_L1",
        shank_length: "6.5",
        head_location: "EXTERIOR_NEAR_SIDE",
        nut_location: "EXTERIOR_FAR_SIDE",
        washer_locations: ["EXTERIOR_NEAR_SIDE", "EXTERIOR_FAR_SIDE"],
        physical_bolt_count: 1,
        continuous_shank_count: 1,
        internal_hardware_count: 0,
      },
      physical_start_point: { x: "3.5", y: "-0.25", z: "-3" },
      physical_end_point: { x: "3.5", y: "6.25", z: "-3" },
      geometry_valid: true,
      path_fingerprint: "physical-endpoint-contract",
    };
    const accepted = teePreviewFixture();
    accepted.result.rectangular_full_through_paths = [validTrace];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(accepted)));
    await expect(
      previewTeeConnector(minimalTeeRequest(), new AbortController().signal),
    ).resolves.toEqual(accepted);

    for (const invalidPoint of [null, { x: 3.5, y: "6.25", z: "-3" }, {
      x: "3.5",
      y: "not-finite",
      z: "-3",
    }, { x: " ", y: "6.25", z: "-3" }]) {
      const rejected = structuredClone(accepted) as unknown as Record<string, unknown>;
      const result = rejected.result as Record<string, unknown>;
      const paths = result.rectangular_full_through_paths as Record<string, unknown>[];
      if (paths[0] !== undefined) paths[0].physical_end_point = invalidPoint;
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(rejected)));
      await expect(
        previewTeeConnector(minimalTeeRequest(), new AbortController().signal),
      ).rejects.toMatchObject({ kind: "RESPONSE", status: 200 });
    }
    for (const invalidTrace of [null, "not-a-through-bolt-trace"]) {
      const rejected = structuredClone(accepted) as unknown as Record<string, unknown>;
      const result = rejected.result as Record<string, unknown>;
      result.rectangular_full_through_paths = [invalidTrace];
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(rejected)));
      await expect(
        previewTeeConnector(minimalTeeRequest(), new AbortController().signal),
      ).rejects.toMatchObject({ kind: "RESPONSE", status: 200 });
    }
  });

  it("propagates intentional abort and classifies other network failures", async () => {
    const request = minimalTeeRequest();
    const signal = new AbortController().signal;
    const abort = new DOMException("cancel", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));
    await expect(previewTeeConnector(request, signal)).rejects.toBe(abort);

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(evaluateTeeConnector(request, signal)).rejects.toMatchObject({
      kind: "NETWORK",
      status: null,
    });
  });

  it.each([
    [422, "VALIDATION"],
    [401, "IDENTITY"],
    [403, "IDENTITY"],
    [500, "HTTP"],
  ] as const)("classifies Tee HTTP %i as %s", async (status, kind) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: "controlled" }, status)));
    await expect(
      previewTeeConnector(minimalTeeRequest(), new AbortController().signal),
    ).rejects.toMatchObject({ kind, status, detail: { detail: "controlled" } });
  });

  it("uses the Tee-specific HTTP design error and tolerates unreadable error JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not-json", { status: 503 })));
    await expect(
      evaluateTeeConnector(minimalTeeRequest(), new AbortController().signal),
    ).rejects.toMatchObject({ kind: "HTTP", status: 503, detail: null });
  });

  it.each([
    null,
    {},
    { ...teePreviewFixture(), api_transport_schema_version: "wrong" },
    { ...teePreviewFixture(), orchestration_contract_version: "wrong" },
    { ...teePreviewFixture(), preview_schema_version: "wrong" },
    { ...teePreviewFixture(), resistance_evaluated: true },
    { ...teePreviewFixture(), engineering_fingerprint: 1 },
    {
      ...teePreviewFixture(),
      result: { ...teePreviewFixture().result, preview_schema_version: "wrong" },
    },
  ])("rejects malformed Tee preview response %#", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    await expect(
      previewTeeConnector(minimalTeeRequest(), new AbortController().signal),
    ).rejects.toMatchObject({ kind: "RESPONSE", status: 200 });
  });

  it.each([
    null,
    {},
    { ...teeDesignFixture(), api_transport_schema_version: "wrong" },
    { ...teeDesignFixture(), orchestration_contract_version: "wrong" },
    { ...teeDesignFixture(), ordinary_pass_allowed: true },
    { ...teeDesignFixture(), result_fingerprint: 1 },
    {
      ...teeDesignFixture(),
      result: {
        ...teeDesignFixture().result,
        preview: { ...teeDesignFixture().result.preview, preview_schema_version: "wrong" },
      },
    },
  ])("rejects malformed Tee design response %#", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    await expect(
      evaluateTeeConnector(minimalTeeRequest(), new AbortController().signal),
    ).rejects.toMatchObject({ kind: "RESPONSE", status: 200 });
  });
});

describe("typed same-origin direct side-lap concrete API client", () => {
  const request = loadDirectSideLapConcreteBenchmark("US_CUSTOMARY");
  afterEach(() => { vi.unstubAllGlobals(); });

  it("posts preview and design to the exact strict operations", async () => {
    const preview = directSideLapPreviewFixture();
    const design = directSideLapDesignFixture();
    const fetch = vi.fn().mockResolvedValueOnce(response(preview)).mockResolvedValueOnce(response(design));
    vi.stubGlobal("fetch", fetch);
    const signal = new AbortController().signal;
    await expect(previewDirectSideLapConcrete(request, signal)).resolves.toEqual(preview);
    await expect(evaluateDirectSideLapConcrete(request, signal)).resolves.toEqual(design);
    expect(fetch.mock.calls[0]?.[0]).toBe(DIRECT_SIDE_LAP_CONCRETE_PREVIEW_PATH);
    expect(fetch.mock.calls[1]?.[0]).toBe(DIRECT_SIDE_LAP_CONCRETE_DESIGN_PATH);
    expect(fetch.mock.calls[0]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify(request),
      credentials: "same-origin",
      signal,
    });
  });

  it.each([
    [422, "VALIDATION"],
    [503, "HTTP"],
  ] as const)("classifies direct side-lap HTTP %i as %s", async (status, kind) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: "controlled" }, status)));
    await expect(
      previewDirectSideLapConcrete(request, new AbortController().signal),
    ).rejects.toMatchObject({ kind, status });
  });

  it("preserves aborts and wraps other direct side-lap network failures", async () => {
    const abort = new DOMException("cancel", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(abort).mockRejectedValueOnce(new Error("offline")));
    await expect(
      previewDirectSideLapConcrete(request, new AbortController().signal),
    ).rejects.toBe(abort);
    await expect(
      evaluateDirectSideLapConcrete(request, new AbortController().signal),
    ).rejects.toMatchObject({ kind: "NETWORK", status: null });
  });

  it.each([
    null,
    { ...directSideLapPreviewFixture(), api_transport_schema_version: "wrong" },
    { ...directSideLapPreviewFixture(), orchestration_contract_version: "wrong" },
    { ...directSideLapPreviewFixture(), preview_schema_version: "wrong" },
    { ...directSideLapPreviewFixture(), resistance_evaluated: true },
    { ...directSideLapPreviewFixture(), external_design_required: false },
    { ...directSideLapPreviewFixture(), engineering_fingerprint: 1 },
    { ...directSideLapPreviewFixture(), result: null },
  ])("rejects malformed direct side-lap preview response %#", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    await expect(
      previewDirectSideLapConcrete(request, new AbortController().signal),
    ).rejects.toMatchObject({ kind: "RESPONSE", status: 200 });
  });

  it.each([
    null,
    { ...directSideLapDesignFixture(), api_transport_schema_version: "wrong" },
    { ...directSideLapDesignFixture(), orchestration_contract_version: "wrong" },
    { ...directSideLapDesignFixture(), required_check_status: "PASS" },
    { ...directSideLapDesignFixture(), ordinary_pass_allowed: true },
    { ...directSideLapDesignFixture(), external_design_required: false },
    { ...directSideLapDesignFixture(), result_fingerprint: 1 },
    { ...directSideLapDesignFixture(), result: null },
  ])("rejects malformed direct side-lap design response %#", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
    await expect(
      evaluateDirectSideLapConcrete(request, new AbortController().signal),
    ).rejects.toMatchObject({ kind: "RESPONSE", status: 200 });
  });
});
