import { describe, expect, it } from "vitest";

import { loadJ1Benchmark, loadJ1ViewExtents } from "../src/fixtures/j1Benchmarks";

describe("committed J1 benchmark input loaders", () => {
  function verifyTemplateJ1(unitSystem: "US_CUSTOMARY" | "SI") {
    const request = loadJ1Benchmark(unitSystem);
    expect(request.geometry).toBeUndefined();
    expect(request.geometry_template).toMatchObject({
      kind: "BRACE_TO_COLUMN_FLANGE",
      brace_to_column_directed_angle_deg: "45",
      column_flange_connection_side: "EXTERIOR",
      angle_connected_leg: "LEG_1",
      outstanding_leg_side: "POSITIVE_INTERFACE_Z",
    });
    expect(Number(request.geometry_template?.bolt_to_brace_end_distance.value)).toBeGreaterThan(0);
    expect(request.explicit_resolved_demand?.in_plane_force_vector.x).not.toBe("0");
  }

  it("returns independent exact U.S. input snapshots", () => {
    const first = loadJ1Benchmark("US_CUSTOMARY");
    const second = loadJ1Benchmark("US_CUSTOMARY");
    expect(first).not.toBe(second);
    expect(first.joint_assembly.unit_system).toBe("US_CUSTOMARY");
    expect(first.bolt_diameter).toEqual({ value: "0.5", unit: "in" });
    first.bolt_diameter.value = "changed";
    expect(second.bolt_diameter.value).toBe("0.5");
  });

  it("returns the exact separately authored SI profile without live conversion", () => {
    const request = loadJ1Benchmark("SI");
    expect(request.joint_assembly.unit_system).toBe("SI");
    expect(request.bolt_diameter).toEqual({ value: "12.7", unit: "mm" });
    expect(request.geometry_template?.hole_diameter).toEqual({
      value: "14.3002",
      unit: "mm",
    });
    expect(request.joint_assembly.member_end_actions[0]?.force.unit).toBe("kN");
  });

  it("contains request inputs only and no production expected results", () => {
    for (const unit of ["US_CUSTOMARY", "SI"] as const) {
      const serialized = JSON.stringify(loadJ1Benchmark(unit)).toLowerCase();
      expect(serialized).not.toContain("expected_capacity");
      expect(serialized).not.toContain("expected_utilization");
      expect(serialized).not.toContain("governing_check_ids");
      expect(serialized).not.toContain("calculation_fingerprint");
    }
  });

  it("uses physically equivalent backend-owned geometry parameters in U.S. and SI", () => {
    verifyTemplateJ1("US_CUSTOMARY");
    verifyTemplateJ1("SI");
    const us = loadJ1Benchmark("US_CUSTOMARY").geometry_template;
    const si = loadJ1Benchmark("SI").geometry_template;
    expect(Number(si?.bolt_to_brace_end_distance.value) / 25.4).toBeCloseTo(
      Number(us?.bolt_to_brace_end_distance.value),
      12,
    );
    const usView = loadJ1ViewExtents("US_CUSTOMARY");
    const siView = loadJ1ViewExtents("SI");
    expect(Number(siView.column_view_extent_below.value) / 25.4).toBeCloseTo(
      Number(usView.column_view_extent_below.value),
      12,
    );
    expect(Number(siView.column_view_extent_above.value) / 25.4).toBeCloseTo(
      Number(usView.column_view_extent_above.value),
      12,
    );
    expect(Number(siView.brace_view_length.value) / 25.4).toBeCloseTo(
      Number(usView.brace_view_length.value),
      12,
    );
  });
});
