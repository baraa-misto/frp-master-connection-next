import { describe, expect, it } from "vitest";

import { interfaceDemand, interfaceHandoff } from "../src/api/teeContracts";
import { teeDesignFixture, teePreviewFixture } from "./teeFixtures";

describe("Stage 3.2 Tee result accessors", () => {
  it("prefers design demand/handoff and retains preview-only fallbacks", () => {
    const preview = teePreviewFixture().result.interface_a;
    const design = teeDesignFixture().result.interface_a;

    expect(interfaceDemand(preview)).toBe(preview.preview.automatic_demand_result);
    expect(interfaceHandoff(preview)).toBeNull();
    expect(interfaceDemand(design)).toBe(design.design?.automatic_demand_result);
    expect(interfaceHandoff(design)).toBe(design.design?.automatic_handoff_results[0]);
  });
});
