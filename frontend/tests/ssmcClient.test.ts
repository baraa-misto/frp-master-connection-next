import { afterEach, assert, expect, it, vi } from "vitest";
import { convertSSMC, evaluateSSMC, isSSMCRequest, loadSSMC, type SSMCRequest, type SSMCResponse } from "../src/api/ssmcClient";
import fixture from "./ssmcNativeFixtures.json";

const data = fixture as unknown as { us: { request: SSMCRequest; response: SSMCResponse }; si: { request: SSMCRequest; response: SSMCResponse } };
const signal = () => new AbortController().signal;
const copy = <T,>(v: T): T => structuredClone(v);
function reply(value: unknown, status = 200) { return vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(value), { status })); }
afterEach(() => { vi.restoreAllMocks(); });

it("validates both native unit paths and uses only the new route with request identity", async () => {
  for (const native of [data.us, data.si]) {
    expect(isSSMCRequest(native.request)).toBe(true);
    reply(native.request);
    expect(await loadSSMC(signal())).toEqual(native.request);
    const fetch = reply(native.response);
    expect(await evaluateSSMC(native.request, "preview", signal())).toEqual(native.response);
    expect(fetch).toHaveBeenCalledWith("/api/v1/calculations/stair-stringer-miter/preview", expect.objectContaining({ method: "POST", credentials: "same-origin", body: JSON.stringify(native.request) }));
    reply(native.request);
    expect(await convertSSMC(native.request, native.request.unit_system === "SI", signal())).toEqual(native.request);
  }
});

it.each([null, {}, { ...data.us.request, theta_deg: "NaN" }, { ...data.us.request, contract: "FORGED" }])("rejects malformed defaults %j", async value => {
  reply(value); await expect(loadSSMC(signal())).rejects.toThrow("Invalid SSMC defaults");
});
it("rejects malformed converted input", async () => { reply({}); await expect(convertSSMC(data.us.request, true, signal())).rejects.toThrow("converted-input"); });
it.each(["network", "abort", "json", "422", "500"])("preserves transport failure %s", async kind => {
  if (kind === "network" || kind === "abort") vi.spyOn(globalThis, "fetch").mockRejectedValue(kind === "abort" ? new DOMException("stop", "AbortError") : new Error("offline"));
  else if (kind === "json") vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("not json"));
  else reply({ detail: "test" }, Number(kind));
  await expect(loadSSMC(signal())).rejects.toThrow(kind === "abort" ? "stop" : kind === "network" ? "unavailable" : kind === "json" ? "Unreadable" : "rejected");
});
it.each(["shape", "id", "input_id", "fingerprint", "shaft", "members", "groups"])("rejects %s response mismatch", async kind => {
  const response = copy(data.us.response);
  if (kind === "shape") response.result.complete_moment_capacity_qualified = true as never;
  if (kind === "id") response.request_id = "wrong";
  if (kind === "input_id") response.result.input.request_id = "wrong";
  if (kind === "fingerprint") response.result.engineering_fingerprint = "wrong";
  if (kind === "shaft") { const shaft = response.result.geometry.shafts[0]; assert(shaft); response.result.geometry.shafts.push(shaft); }
  if (kind === "members") response.result.geometry.members.pop();
  if (kind === "groups") response.result.groups.pop();
  reply(response); await expect(evaluateSSMC(data.us.request, "design-check", signal())).rejects.toThrow();
});
it("accepts all supported choices and rejects nonfinite native geometry", async () => {
  const request = copy(data.si.request);
  request.horizontal.form = "W_I"; request.plate.side = "POS_Y";
  request.horizontal_group.rows = 3; request.fastener.threads = "INCLUDED";
  expect(isSSMCRequest(request)).toBe(true);
  const response = copy(data.us.response); response.result.geometry.polygon.area = Number.NaN;
  reply(response); await expect(evaluateSSMC(data.us.request, "preview", signal())).rejects.toThrow("contract");
});
