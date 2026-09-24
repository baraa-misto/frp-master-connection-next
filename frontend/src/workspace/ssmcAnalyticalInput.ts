import type { SSMCAnalyticalRequest, SSMCRequest, SSMCTimeEffectCategory } from "../api/ssmcClient";

export const SSMC_TIME_EFFECT_CATEGORIES = [
  "DEAD_ONLY", "IMPACT", "STORAGE", "LONG_TERM_OPERATING", "OTHER_LIVE",
  "SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE", "WIND_TORNADO_SEISMIC",
] as const satisfies readonly SSMCTimeEffectCategory[];

export type SSMCConfirmation = "" | "YES" | "NO";
export interface SSMCAnalyticalDraft {
  combination_id: string;
  combination_source: string;
  already_factored: SSMCConfirmation;
  time_effect_category: SSMCTimeEffectCategory | "";
  time_effect_reference: string;
  external_actions_at_faying_interface: SSMCConfirmation;
  independent_normal_force: string;
  independent_out_of_plane_moment: string;
  imposed_separation: SSMCConfirmation;
  non_contact_gap: SSMCConfirmation;
  friction_or_preload_credit: SSMCConfirmation;
  miter_bearing_credit: SSMCConfirmation;
}

export const EMPTY_SSMC_ANALYTICAL_DRAFT: Readonly<SSMCAnalyticalDraft> = {
  combination_id: "", combination_source: "", already_factored: "", time_effect_category: "", time_effect_reference: "",
  external_actions_at_faying_interface: "", independent_normal_force: "", independent_out_of_plane_moment: "",
  imposed_separation: "", non_contact_gap: "", friction_or_preload_credit: "", miter_bearing_credit: "",
};

export function isSSMCAnalyticalDraftReady(draft: SSMCAnalyticalDraft): boolean {
  const requiredText = [draft.combination_id, draft.combination_source, draft.time_effect_reference,
    draft.independent_normal_force, draft.independent_out_of_plane_moment];
  const declarations = [draft.external_actions_at_faying_interface, draft.imposed_separation,
    draft.non_contact_gap, draft.friction_or_preload_credit, draft.miter_bearing_credit];
  return requiredText.every(value => value.trim() !== "") &&
    [draft.independent_normal_force, draft.independent_out_of_plane_moment].every(value => Number.isFinite(Number(value))) &&
    draft.already_factored === "YES" && draft.time_effect_category !== "" &&
    declarations.every(value => value !== "");
}

export function buildSSMCAnalyticalRequest(physical: SSMCRequest, draft: SSMCAnalyticalDraft): SSMCAnalyticalRequest {
  if (!isSSMCAnalyticalDraftReady(draft)) throw new Error("Complete the factored load and single-lap declaration before design.");
  return {
    contract: "SSMC-3-ANALYTICAL-RC1",
    physical: { ...physical, source_reference: "", fastener: { ...physical.fastener, source_reference: "" } },
    action: {
      basis: "FACTORED_LRFD", combination_id: draft.combination_id.trim(), combination_source: draft.combination_source.trim(),
      already_factored: true, time_effect_category: draft.time_effect_category as SSMCTimeEffectCategory,
      time_effect_reference: draft.time_effect_reference.trim(),
    },
    single_lap: {
      external_actions_at_faying_interface: draft.external_actions_at_faying_interface === "YES",
      independent_normal_force: { value: draft.independent_normal_force, unit: "N" },
      independent_out_of_plane_moment: { value: draft.independent_out_of_plane_moment, unit: "N-mm" },
      imposed_separation: draft.imposed_separation === "YES", non_contact_gap: draft.non_contact_gap === "YES",
      friction_or_preload_credit: draft.friction_or_preload_credit === "YES", miter_bearing_credit: draft.miter_bearing_credit === "YES",
    },
  };
}
