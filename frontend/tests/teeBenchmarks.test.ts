import { describe, expect, it } from "vitest";

import { loadTeeBenchmark } from "../src/fixtures/teeBenchmarks";

describe("controlled R4 Tee benchmark", () => {
  it("projects the canonical U.S. flat-plate benchmark exactly", () => {
    const request = loadTeeBenchmark("US_CUSTOMARY");

    expect(request.unit_system).toBe("US_CUSTOMARY");
    expect(request.source_length_unit).toBe("in");
    expect(request.connector_dimensions).toEqual({
      connector_length: { value: "8", unit: "in" },
      flange_width: { value: "6", unit: "in" },
      flange_thickness: { value: "0.5", unit: "in" },
      stem_depth: { value: "4", unit: "in" },
      stem_thickness: { value: "0.375", unit: "in" },
    });
    expect(request.connected_member_profile).toMatchObject({
      role: "BRACE",
      profile_family: "FLAT_PLATE",
      selected_profile_surface: "FACE_POS",
      dimensions: {
        width: { value: "8", unit: "in" },
        thickness: { value: "0.375", unit: "in" },
        member_length: { value: "6", unit: "in" },
      },
    });
    expect(request.support_target_id).toBe("W_COLUMN_FLANGE");
    expect(request.support_profile).toMatchObject({
      member_length: { value: "16", unit: "in" },
      depth: { value: "8", unit: "in" },
      flange_width: { value: "8", unit: "in" },
      web_thickness: { value: "0.5", unit: "in" },
      flange_thickness: { value: "0.75", unit: "in" },
    });
    expect(request.interface_a_layout).toEqual(request.interface_b_layout);
    expect(request.interface_a_layout).not.toBe(request.interface_b_layout);
    expect(request.interface_a_layout.pitch).toEqual({ value: "2", unit: "in" });
    expect(request.interface_a_layout.unloaded_end_distance).toEqual({
      value: "1",
      unit: "in",
    });
    expect(request.bolt_diameter).toEqual({ value: "0.5", unit: "in" });
    expect(request.hole_basis).toBe("US_CUSTOMARY_PRINTED");
    expect(request.global_force).toEqual({ x: "0", y: "0", z: "0.1", unit: "kip" });
  });

  it("derives the exact SI fixture and action from the same canonical values", () => {
    const request = loadTeeBenchmark("SI");

    expect(request.unit_system).toBe("SI");
    expect(request.source_length_unit).toBe("mm");
    expect(request.connector_dimensions).toEqual({
      connector_length: { value: "203.2", unit: "mm" },
      flange_width: { value: "152.4", unit: "mm" },
      flange_thickness: { value: "12.7", unit: "mm" },
      stem_depth: { value: "101.6", unit: "mm" },
      stem_thickness: { value: "9.525", unit: "mm" },
    });
    expect(request.connected_member_profile).toMatchObject({
      profile_family: "FLAT_PLATE",
      selected_profile_surface: "FACE_POS",
      dimensions: {
        width: { value: "203.2", unit: "mm" },
        thickness: { value: "9.525", unit: "mm" },
        member_length: { value: "152.4", unit: "mm" },
      },
    });
    expect(request.support_target_id).toBe("W_COLUMN_FLANGE");
    expect(request.support_profile).toMatchObject({
      member_length: { value: "406.4", unit: "mm" },
      depth: { value: "203.2", unit: "mm" },
      flange_width: { value: "203.2", unit: "mm" },
      web_thickness: { value: "12.7", unit: "mm" },
      flange_thickness: { value: "19.05", unit: "mm" },
    });
    expect(request.interface_a_layout).toEqual(request.interface_b_layout);
    expect(request.interface_a_layout.pitch).toEqual({ value: "50.8", unit: "mm" });
    expect(request.interface_a_layout.gauge).toEqual({ value: "50.8", unit: "mm" });
    expect(request.interface_a_layout.unloaded_end_distance).toEqual({
      value: "25.4",
      unit: "mm",
    });
    expect(request.bolt_diameter).toEqual({ value: "12.7", unit: "mm" });
    expect(request.hole_basis).toBe("US_CUSTOMARY_PRINTED");
    expect(request.global_force).toEqual({
      x: "0",
      y: "0",
      z: "0.44482216152605",
      unit: "kN",
    });
    expect(request.global_reference_point).toEqual({
      x: "0",
      y: "0",
      z: "0",
      unit: "mm",
    });
  });

  it("returns fresh mutable request objects without changing benchmark authority", () => {
    const first = loadTeeBenchmark("US_CUSTOMARY");
    const firstWidth = first.connected_member_profile.dimensions.width;
    if (firstWidth === undefined) throw new Error("Flat-plate width is required.");
    firstWidth.value = "99";
    first.interface_a_layout.pitch.value = "99";

    const second = loadTeeBenchmark("US_CUSTOMARY");
    const secondWidth = second.connected_member_profile.dimensions.width;
    if (secondWidth === undefined) throw new Error("Flat-plate width is required.");
    expect(secondWidth.value).toBe("8");
    expect(second.interface_a_layout.pitch.value).toBe("2");
  });
});
