import { afterEach, assert, expect, it, vi } from "vitest";
import { convertSSMC, evaluateSSMC, evaluateSSMCAnalytical, isSSMCRequest, loadSSMC, type SSMCAnalyticalResponse, type SSMCDesignStatus, type SSMCRequest, type SSMCResponse } from "../src/api/ssmcClient";
import { buildSSMCAnalyticalRequest, type SSMCAnalyticalDraft } from "../src/workspace/ssmcAnalyticalInput";
import fixture from "./ssmcNativeFixtures.json";

const data = fixture as unknown as { us: { request: SSMCRequest; response: SSMCResponse }; si: { request: SSMCRequest; response: SSMCResponse } };
const signal = () => new AbortController().signal;
const copy = <T,>(v: T): T => structuredClone(v);
function reply(value: unknown, status = 200) { return vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(value), { status })); }
const draft: SSMCAnalyticalDraft = {
  combination_id: "COMBO", combination_source: "ISSUED", already_factored: "YES", time_effect_category: "OTHER_LIVE", time_effect_reference: "TIME SOURCE",
  external_actions_at_faying_interface: "YES", independent_normal_force: "0", independent_out_of_plane_moment: "0", imposed_separation: "NO", non_contact_gap: "NO", friction_or_preload_credit: "NO", miter_bearing_credit: "NO",
};
const analyticalRequest = buildSSMCAnalyticalRequest(data.us.request, draft);
function analyticalResponse(status: SSMCDesignStatus): SSMCAnalyticalResponse {
  return {
    contract: "SSMC-3-ANALYTICAL-RC1", method: "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1", whole_connection_status: status,
    result: {
      contract: "SSMC-3-ANALYTICAL-RC1", method: "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1", whole_connection_status: status,
      request: analyticalRequest, existing_demand: data.us.response.result, applicability_status: "ELIGIBLE", applicability_reasons: [],
      checks: [{ owner: "MITER_WEB_PLATE", path_id: "P1", mode: "PIN_BEARING", status, reason: "SERVER_REASON", demand_N: 1, source_id: "SOURCE", qualification_id: null }],
      blockers: ["SERVER_BLOCKER"], numerical_failures: [], action_reaction: [], member_cut_demands: [], cuts: { cuts: [], finite_coverage_proven: false, status: "ENGINEERING_REVIEW_REQUIRED" },
    },
  };
}
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
it.each(["PASS", "FAIL", "ENGINEERING_REVIEW_REQUIRED", "SOURCE_REQUIRED", "NOT_APPLICABLE"] as const)("posts exact analytical request and preserves server %s", async status => {
  const response = analyticalResponse(status);
  const check = response.result.checks[0]; assert(check); check.qualification_id = "QUALIFIED";
  response.result.applicability_status = status === "ENGINEERING_REVIEW_REQUIRED" ? "ENGINEERING_REVIEW_REQUIRED" : "ELIGIBLE";
  response.result.action_reaction = [{ group_id: "HORIZONTAL_WEB_GROUP" }];
  response.result.member_cut_demands = [{ member: "HORIZONTAL_STRINGER" }];
  response.result.cuts.cuts = [{ cut_id: "CUT_1" }];
  const fetch = reply(response);
  expect(await evaluateSSMCAnalytical(analyticalRequest, signal())).toEqual(response);
  expect(fetch).toHaveBeenCalledWith("/api/v1/calculations/stair-stringer-miter/analytical-design-check", expect.objectContaining({ method: "POST", credentials: "same-origin", body: JSON.stringify(analyticalRequest) }));
});
it.each(["contract", "method", "child_status", "source", "request_id", "demand_id", "status_mismatch"] as const)("rejects malformed analytical %s without inferring PASS", async kind => {
  const response = copy(analyticalResponse("ENGINEERING_REVIEW_REQUIRED"));
  const check = response.result.checks[0]; assert(check);
  if (kind === "contract") response.contract = "FORGED" as never;
  if (kind === "method") response.result.method = "FORGED" as never;
  if (kind === "child_status") check.status = "FORGED" as never;
  if (kind === "source") check.source_id = 1 as never;
  if (kind === "request_id") response.result.request.physical.request_id = "WRONG";
  if (kind === "demand_id") response.result.existing_demand.input.request_id = "WRONG";
  if (kind === "status_mismatch") response.result.whole_connection_status = "PASS";
  reply(response);
  await expect(evaluateSSMCAnalytical(analyticalRequest, signal())).rejects.toThrow("SSMC analytical response");
});
