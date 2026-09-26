import { afterEach, describe, expect, it, vi } from "vitest";
import { mat1Fetch } from "../src/api/mat1Transport";
import {
  acceptReportSnapshot,
  currentReportSnapshot,
  invalidateReportSnapshot,
  reportGeneration,
} from "../src/state/reportSession";

describe("report snapshot freshness", () => {
  afterEach(() => { vi.unstubAllGlobals(); });

  it("rejects a response that arrives after an input edit", () => {
    const family = "report-test-stale";
    const pending = reportGeneration(family);
    invalidateReportSnapshot(family);
    acceptReportSnapshot(family, "old-design", "design", pending);
    expect(currentReportSnapshot(family).token).toBeNull();
    expect(currentReportSnapshot(family).dirty).toBe(true);
    acceptReportSnapshot(family, "new-design", "design", reportGeneration(family));
    expect(currentReportSnapshot(family)).toEqual({
      token: "new-design", kind: "design", dirty: false,
    });
  });

  it("keeps an explicit design result when a late preview returns", () => {
    const family = "report-test-preview";
    const generation = reportGeneration(family);
    acceptReportSnapshot(family, "design", "design", generation);
    acceptReportSnapshot(family, "preview", "input_only", generation);
    expect(currentReportSnapshot(family).token).toBe("design");
  });

  it("retains a server-sealed input-only handle for a rejected preview", async () => {
    const family = "report-invalid-preview";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{\"detail\":[]}", {
      status: 422,
      headers: { "X-Report-Handle": "invalid-preview-handle", "X-Report-Kind": "input_only" },
    })));
    const response = await mat1Fetch(`/api/v1/calculations/${family}/preview`, {
      method: "POST", body: "{}", headers: { "Content-Type": "application/json" },
    });
    expect(response.status).toBe(422);
    expect(currentReportSnapshot(family)).toEqual({
      token: "invalid-preview-handle", kind: "input_only", dirty: false,
    });
  });

  it("invalidates an old design when a new calculation starts and ignores its late response", async () => {
    const family = "report-concurrent-preview";
    acceptReportSnapshot(family, "old-design", "design", reportGeneration(family));
    const completions: ((response: Response) => void)[] = [];
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(resolve => { completions.push(resolve); })));
    const options = { method: "POST", body: "{}", headers: { "Content-Type": "application/json" } };
    const older = mat1Fetch(`/api/v1/calculations/${family}/preview`, options);
    expect(currentReportSnapshot(family).dirty).toBe(true);
    const newer = mat1Fetch(`/api/v1/calculations/${family}/preview`, options);
    completions[1]?.(new Response("{}", { status: 200, headers: { "X-Report-Handle": "new-preview" } }));
    await newer;
    completions[0]?.(new Response("{}", { status: 200, headers: { "X-Report-Handle": "old-preview" } }));
    await older;
    expect(currentReportSnapshot(family)).toEqual({ token: "new-preview", kind: "input_only", dirty: false });
  });
});
