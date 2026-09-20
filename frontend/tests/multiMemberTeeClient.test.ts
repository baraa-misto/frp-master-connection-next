import { afterEach, describe, expect, it, vi } from "vitest";

import {
  MULTI_MEMBER_TEE_DESIGN_PATH,
  MULTI_MEMBER_TEE_PREVIEW_PATH,
  evaluateMultiMemberTee,
  previewMultiMemberTee,
} from "../src/api/client";
import { loadMultiMemberTeeBenchmark } from "../src/fixtures/multiMemberTeeBenchmarks";
import { multiMemberTeeDesign, multiMemberTeePreview } from "./multiMemberTeeFixtures";

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("Multi-Member Tee stateless API client", () => {
  afterEach(() => { vi.unstubAllGlobals(); });

  it("posts strict preview and design routes with the caller AbortSignal", async () => {
    const request = loadMultiMemberTeeBenchmark("US_CUSTOMARY");
    const controller = new AbortController();
    const fetch = vi.fn()
      .mockResolvedValueOnce(response(multiMemberTeePreview()))
      .mockResolvedValueOnce(response(multiMemberTeeDesign()));
    vi.stubGlobal("fetch", fetch);
    await expect(previewMultiMemberTee(request, controller.signal)).resolves.toMatchObject({ assembly_status: "NOT_EVALUATED" });
    await expect(evaluateMultiMemberTee(request, controller.signal)).resolves.toMatchObject({ ordinary_pass_allowed: false });
    expect(fetch.mock.calls[0]?.[0]).toBe(MULTI_MEMBER_TEE_PREVIEW_PATH);
    expect(fetch.mock.calls[1]?.[0]).toBe(MULTI_MEMBER_TEE_DESIGN_PATH);
    expect(fetch.mock.calls[0]?.[1]).toMatchObject({ method: "POST", credentials: "same-origin", signal: controller.signal });
  });

  it.each([[422, "VALIDATION"], [503, "HTTP"]] as const)("classifies HTTP %i as %s", async (status, kind) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: "controlled" }, status)));
    await expect(previewMultiMemberTee(loadMultiMemberTeeBenchmark("US_CUSTOMARY"), new AbortController().signal)).rejects.toMatchObject({ kind, status });
  });

  it("preserves aborts and rejects network and malformed contracts", async () => {
    const request = loadMultiMemberTeeBenchmark("US_CUSTOMARY");
    const signal = new AbortController().signal;
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(previewMultiMemberTee(request, signal)).rejects.toMatchObject({ kind: "NETWORK" });
    await expect(evaluateMultiMemberTee(request, signal)).rejects.toMatchObject({ kind: "NETWORK" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(null)));
    await expect(previewMultiMemberTee(request, signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    await expect(evaluateMultiMemberTee(request, signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ api_transport_schema_version: "0.1.0-draft" })));
    await expect(evaluateMultiMemberTee(request, signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    const aborted = new DOMException("aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(aborted));
    await expect(previewMultiMemberTee(request, signal)).rejects.toBe(aborted);
  });

  it("accepts the backend slot visualization wrapper and rejects the obsolete wrapper fail-closed", async () => {
    const request = loadMultiMemberTeeBenchmark("US_CUSTOMARY");
    const signal = new AbortController().signal;
    const current = multiMemberTeePreview();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(current)));
    await expect(previewMultiMemberTee(request, signal)).resolves.toEqual(current);

    const obsolete = structuredClone(current) as unknown as Record<string, unknown>;
    const result = obsolete.result as Record<string, unknown>;
    const visualization = result.visualization as Record<string, unknown>;
    const slots = visualization.slots as Record<string, unknown>[];
    const first = slots[0];
    if (first === undefined) throw new Error("fixture invariant");
    first.tee_visualization = first.visualization;
    delete first.visualization;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(obsolete)));
    await expect(previewMultiMemberTee(request, signal)).rejects.toMatchObject({ kind: "RESPONSE", status: 200 });

    const unsupportedVisualization = structuredClone(current) as unknown as Record<string, unknown>;
    const unsupportedResult = unsupportedVisualization.result as Record<string, unknown>;
    unsupportedResult.visualization = { schema_version: "future", slots: [] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(unsupportedVisualization)));
    await expect(previewMultiMemberTee(request, signal)).rejects.toMatchObject({ kind: "RESPONSE", status: 200 });

    const incompleteResult = structuredClone(current) as unknown as Record<string, unknown>;
    delete (incompleteResult.result as Record<string, unknown>).active_slot_ids;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(incompleteResult)));
    await expect(previewMultiMemberTee(request, signal)).rejects.toMatchObject({ kind: "RESPONSE", status: 200 });
  });

  it("accepts both controlled orchestration response versions and rejects future versions", async () => {
    const request = loadMultiMemberTeeBenchmark("US_CUSTOMARY");
    const signal = new AbortController().signal;
    const historical = structuredClone(multiMemberTeePreview());
    historical.orchestration_contract_version = "3.4A-RC1";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(response(historical)));
    await expect(previewMultiMemberTee(request, signal)).resolves.toEqual(historical);
    const future = { ...multiMemberTeePreview(), orchestration_contract_version: "3.4C-RC1" };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(response(future)));
    await expect(previewMultiMemberTee(request, signal)).rejects.toMatchObject({ kind: "RESPONSE" });
  });
});
