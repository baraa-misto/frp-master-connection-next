import type { WIWallMomentDesign, WIWallMomentPreview, WIWallMomentResponse } from "../src/api/wiWallMomentContracts";
import wire from "./fixtures/wiWallMomentWire.json";
import pureShearWire from "./fixtures/wiWallMomentPureShearWire.json";

// Reduced view of a real backend default response. Engineering numerics come
// from the backend fixture, not a second mechanics implementation in tests.
export function wallDesignFixture(): WIWallMomentResponse<WIWallMomentDesign> {
  return structuredClone(wire) as unknown as WIWallMomentResponse<WIWallMomentDesign>;
}
export function wallPureShearDesignFixture(): WIWallMomentResponse<WIWallMomentDesign> {
  return structuredClone(pureShearWire) as unknown as WIWallMomentResponse<WIWallMomentDesign>;
}
export function wallPreviewFixture(valid = true): WIWallMomentResponse<WIWallMomentPreview> {
  const design = wallDesignFixture();
  const preview = design.result.preview;
  return { ...design, resistance_evaluated: false, assembly_status: "NOT_EVALUATED",
    geometry_status: valid ? "VALID" : "INVALID_GEOMETRY",
    geometry_invalid_reasons: valid ? [] : ["POSITIVE_BEAM_WALL_GAP_REQUIRED"],
    design_check_ready: valid, result: valid ? preview : { ...preview,
      geometry: { ...preview.geometry, status:"INVALID_GEOMETRY", reasons:["POSITIVE_BEAM_WALL_GAP_REQUIRED"] },
      connectors: [], wall_handoff:null, wall_reaction:null, equilibrium:null,
    },
  };
}
