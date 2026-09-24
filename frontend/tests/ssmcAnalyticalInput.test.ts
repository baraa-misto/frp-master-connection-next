import { expect, it } from "vitest";
import type { SSMCRequest } from "../src/api/ssmcClient";
import { buildSSMCAnalyticalRequest, EMPTY_SSMC_ANALYTICAL_DRAFT, isSSMCAnalyticalDraftReady, SSMC_TIME_EFFECT_CATEGORIES, type SSMCAnalyticalDraft } from "../src/workspace/ssmcAnalyticalInput";
import fixture from "./ssmcNativeFixtures.json";

const physical = (fixture as unknown as { us: { request: SSMCRequest } }).us.request;
const complete: SSMCAnalyticalDraft = {
  combination_id: " COMBO-1 ", combination_source: " Issued schedule ", already_factored: "YES",
  time_effect_category: "OTHER_LIVE", time_effect_reference: " Published time basis ",
  external_actions_at_faying_interface: "YES", independent_normal_force: "0", independent_out_of_plane_moment: "0",
  imposed_separation: "NO", non_contact_gap: "NO", friction_or_preload_credit: "NO", miter_bearing_credit: "NO",
};

it("requires explicit factored provenance and every single-lap declaration before design", () => {
  expect(isSSMCAnalyticalDraftReady({ ...EMPTY_SSMC_ANALYTICAL_DRAFT })).toBe(false);
  expect(() => buildSSMCAnalyticalRequest(physical, { ...EMPTY_SSMC_ANALYTICAL_DRAFT })).toThrow("Complete the factored load");
  expect(isSSMCAnalyticalDraftReady(complete)).toBe(true);
  for (const draft of [
    { ...complete, combination_id: " " }, { ...complete, combination_source: "" }, { ...complete, time_effect_reference: "" },
    { ...complete, independent_normal_force: "" }, { ...complete, independent_out_of_plane_moment: "" },
    { ...complete, independent_normal_force: "NaN" }, { ...complete, independent_out_of_plane_moment: "Infinity" },
    { ...complete, already_factored: "NO" as const }, { ...complete, time_effect_category: "" as const },
    { ...complete, external_actions_at_faying_interface: "" as const }, { ...complete, imposed_separation: "" as const },
    { ...complete, non_contact_gap: "" as const }, { ...complete, friction_or_preload_credit: "" as const }, { ...complete, miter_bearing_credit: "" as const },
  ]) expect(isSSMCAnalyticalDraftReady(draft)).toBe(false);
});

it("maps only the accepted public LRFD and single-lap fields, retaining signed physical actions and no source override", () => {
  const changed = structuredClone(physical);
  changed.N.value = "-8"; changed.V.value = "4"; changed.M.value = "-20";
  changed.source_reference = "UNTRUSTED"; changed.fastener.source_reference = "UNTRUSTED_HARDWARE";
  const request = buildSSMCAnalyticalRequest(changed, complete);
  expect(request.contract).toBe("SSMC-3-ANALYTICAL-RC1");
  expect(request.physical).toEqual({ ...changed, source_reference: "", fastener: { ...changed.fastener, source_reference: "" } });
  expect([request.physical.N.value, request.physical.V.value, request.physical.M.value]).toEqual(["-8", "4", "-20"]);
  expect(request.action).toEqual({ basis: "FACTORED_LRFD", combination_id: "COMBO-1", combination_source: "Issued schedule", already_factored: true, time_effect_category: "OTHER_LIVE", time_effect_reference: "Published time basis" });
  expect(request.single_lap).toEqual({ external_actions_at_faying_interface: true, independent_normal_force: { value: "0", unit: "N" }, independent_out_of_plane_moment: { value: "0", unit: "N-mm" }, imposed_separation: false, non_contact_gap: false, friction_or_preload_credit: false, miter_bearing_credit: false });
  const review = buildSSMCAnalyticalRequest(physical, { ...complete, external_actions_at_faying_interface: "NO", imposed_separation: "YES", non_contact_gap: "YES", friction_or_preload_credit: "YES", miter_bearing_credit: "YES", independent_normal_force: "5", independent_out_of_plane_moment: "10" });
  expect(review.single_lap).toMatchObject({ external_actions_at_faying_interface: false, imposed_separation: true, non_contact_gap: true, friction_or_preload_credit: true, miter_bearing_credit: true, independent_normal_force: { value: "5", unit: "N" }, independent_out_of_plane_moment: { value: "10", unit: "N-mm" } });
  expect(SSMC_TIME_EFFECT_CATEGORIES).toEqual(["DEAD_ONLY", "IMPACT", "STORAGE", "LONG_TERM_OPERATING", "OTHER_LIVE", "SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE", "WIND_TORNADO_SEISMIC"]);
});
