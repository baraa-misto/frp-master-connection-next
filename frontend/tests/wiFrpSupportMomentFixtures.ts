import type { SupportMode, WIFrpSupportMomentDesign, WIFrpSupportMomentPreview, WIFrpSupportMomentResponse } from "../src/api/wiFrpSupportMomentContracts";
import flange from "./fixtures/wiFrpSupportMoment_WI_FLANGE.json";
import web from "./fixtures/wiFrpSupportMoment_WI_WEB.json";
import hollow from "./fixtures/wiFrpSupportMoment_HOLLOW_SQUARE.json";
import solid from "./fixtures/wiFrpSupportMoment_SOLID_SQUARE.json";
import channel from "./fixtures/wiFrpSupportMoment_CHANNEL_WEB.json";

// Reduced views of real Stage 4.3 backend outputs. Omitted deep native traces
// are tested in Python; no values retained here are recomputed in the frontend.
const fixtures = { WI_FLANGE: flange, WI_WEB: web, HOLLOW_SQUARE: hollow, SOLID_SQUARE: solid, CHANNEL_WEB: channel };
export function frpDesignFixture(mode: SupportMode = "WI_FLANGE"): WIFrpSupportMomentResponse<WIFrpSupportMomentDesign> {
  const value = structuredClone(fixtures[mode]) as unknown as WIFrpSupportMomentResponse<WIFrpSupportMomentDesign>;
  return { ...value, request_id: `stage-4.3-${mode}-US_CUSTOMARY` };
}
export function frpPreviewFixture(mode: SupportMode = "WI_FLANGE", valid = true): WIFrpSupportMomentResponse<WIFrpSupportMomentPreview> {
  const value = frpDesignFixture(mode), p = value.result.preview;
  return { ...value, resistance_evaluated: false, assembly_status: "NOT_EVALUATED", design_check_ready: valid,
    geometry_status: valid ? "VALID" : "INVALID_GEOMETRY", geometry_invalid_reasons: valid ? [] : ["INVALID_GAP"],
    result: valid ? p : { ...p, geometry: { ...p.geometry, status: "INVALID_GEOMETRY", reasons: ["INVALID_GAP"] }, connectors: [], support_contribution: null, support_reaction: null, equilibrium: null },
  };
}
