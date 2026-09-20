import { describe, expect, it } from "vitest";

import {
  directSideLapProfile,
  loadDirectSideLapConcreteBenchmark,
} from "../src/fixtures/directSideLapConcreteBenchmarks";

describe("Stage 3.5B exact U.S./SI benchmark loaders", () => {
  it("loads exact U.S. and SI fixtures and both strict profile families", () => {
    const us = loadDirectSideLapConcreteBenchmark("US_CUSTOMARY");
    const si = loadDirectSideLapConcreteBenchmark("SI");
    expect(us.side_lap_length).toEqual({ value: "12", unit: "in" });
    expect(si.side_lap_length).toEqual({ value: "304.8", unit: "mm" });
    expect(si.major_shear).toEqual({ value: "-17.792886461042", unit: "kN" });
    expect(directSideLapProfile("US_CUSTOMARY", "ANGLE")).toMatchObject({
      profile_family: "ANGLE",
      selected_profile_surface: "LEG_Y_OUTER",
    });
    expect(directSideLapProfile("SI", "CHANNEL")).toMatchObject({
      profile_family: "CHANNEL",
      selected_profile_surface: "WEB_OUTER",
      dimensions: { depth: { value: "203.2", unit: "mm" } },
    });
  });
});
