import { afterEach, expect, it, vi } from "vitest";
import { calculateHybrid, downloadHybrid, enteredCase, hybridPost, sourceExample } from "../src/api/hybridWorkflow";
import type { HybridInputs } from "../src/api/hybridWorkflow";

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
const base = (): HybridInputs => sourceExample({ contract: "HYB2-D3-P1-LIVE", workspace_id: "real-form", revision: 2 } as HybridInputs);
const reply = (body: unknown, status = 200): Response => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

it("submits current user inputs, credentials and separate case bases; explicit example contains no results", async () => {
  const inputs = base(), fetcher = vi.fn().mockResolvedValue(reply({ contract: inputs.contract, revision: 2, fingerprint: "server", workflow_available: true, scene: null, native_geometry: null }));
  vi.stubGlobal("fetch", fetcher);
  expect(await calculateHybrid("preview", inputs)).toMatchObject({ fingerprint: "server", revision: 2 });
  expect(fetcher).toHaveBeenCalledWith("/api/v1/direct-hybrid/preview", expect.objectContaining({ credentials: "same-origin", body: JSON.stringify(inputs) }));
  expect(inputs).not.toHaveProperty("results");
  expect(inputs.asd_cases[0]?.components[0]).toEqual({ value: ".09155", unit: "kip" });
  expect(enteredCase("independent").components[0]?.value).toBe("0");
});

it.each(["contract", "revision", "fingerprint", "workflow_available", "record", "report_handle"])("rejects mismatched or incomplete %s before presenting current results", async (field) => {
  const inputs = base();
  const data: Record<string, unknown> = { contract: inputs.contract, revision: 2, fingerprint: "server", workflow_available: true, record: {}, report_handle: "opaque" };
  if (field === "contract") data[field] = "WRONG";
  else if (field === "revision") data[field] = 1;
  else if (field === "fingerprint") data[field] = null;
  else if (field === "workflow_available") data[field] = false;
  else data[field] = undefined;
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(data)));
  await expect(calculateHybrid("assess", inputs)).rejects.toThrow(/current revision|signed record/);
});

it.each(["network", "unreadable", "detail", "validation"])("gives actionable %s errors", async (kind) => {
  const fetcher = vi.fn();
  if (kind === "network") fetcher.mockRejectedValue(new TypeError("Failed to fetch"));
  else if (kind === "unreadable") fetcher.mockResolvedValue(new Response("<html>bad gateway</html>"));
  else fetcher.mockResolvedValue(reply({ detail: kind === "detail" ? "Known engineering input error" : [] }, 422));
  vi.stubGlobal("fetch", fetcher);
  await expect(hybridPost("assess", base())).rejects.toThrow(/could not be reached|unreadable|Known engineering input error|Review finite inputs/);
});

it.each([[false, "pdf"], [true, "pdf"], [false, "json"]] as const)("downloads current %s / %s through the authenticated handle and disposes its URL", async (technical, format) => {
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  const create = vi.fn().mockReturnValue("blob:current"), revoke = vi.fn();
  vi.stubGlobal("URL", { createObjectURL: create, revokeObjectURL: revoke });
  const fetcher = vi.fn().mockResolvedValue(new Response("file bytes", { headers: { "Content-Type": format === "json" ? "application/json" : "application/pdf" } }));
  vi.stubGlobal("fetch", fetcher);
  await downloadHybrid("opaque/current", technical, format);
  expect(fetcher).toHaveBeenCalledWith("/api/v1/direct-hybrid/" + (format === "json" ? "records/" : "reports/") + "opaque%2Fcurrent" + (technical ? "?technical=true" : ""), { credentials: "same-origin" });
  expect(click).toHaveBeenCalledOnce(); expect(revoke).toHaveBeenCalledWith("blob:current");
});

it.each(["network", "stale", "wrong-type"])("refuses invalid %s exports", async (kind) => {
  const fetcher = vi.fn();
  if (kind === "network") fetcher.mockRejectedValue(new TypeError("Failed to fetch"));
  else fetcher.mockResolvedValue(new Response("error", { status: kind === "stale" ? 409 : 200 }));
  vi.stubGlobal("fetch", fetcher);
  await expect(downloadHybrid("old", false)).rejects.toThrow(/could not be reached|stale|requested file type/);
});

it("does not download a completed export after its inputs have changed", async () => {
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  vi.stubGlobal("URL", { createObjectURL: vi.fn().mockReturnValue("blob:old"), revokeObjectURL: vi.fn() });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("old PDF", { headers: { "Content-Type": "application/pdf" } })));
  await expect(downloadHybrid("previous-current", false, "pdf", () => false)).rejects.toThrow("Inputs changed during export");
  expect(click).not.toHaveBeenCalled();
});
