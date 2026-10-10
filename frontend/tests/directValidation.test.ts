import { expect, it, vi } from "vitest";
import * as benchmarks from "../src/fixtures/j1Benchmarks";
import {
  buildMultirowRequest, designValidationMessage, directStartingExample,
  initialBoltGroupState, multirowValidationMessage,
} from "../src/workspace/SingleBoltEngineeringWorkspace";

it("blocks incomplete factors and externally resolved Direct demand before a design request", () => {
  const request = benchmarks.loadJ1Benchmark("US_CUSTOMARY");
  const group = { ...initialBoltGroupState("US_CUSTOMARY", true) };
  expect(designValidationMessage(request)).toBeNull();
  request.end_use_factors.cm = "";
  expect(designValidationMessage(request)).toContain("finite CM, CT, and CCH");
  expect(multirowValidationMessage(request, group, "AUTOMATIC_MEMBER_END_FORCE")).toContain("finite CM");
  request.end_use_factors.cm = "1";
  request.explicit_resolved_demand = null;
  expect(multirowValidationMessage(request, group, "EXPLICIT_RESOLVED_CONNECTION_DEMAND")).toContain("Explicit externally resolved");
  const built = buildMultirowRequest(
    request, benchmarks.loadJ1ViewExtents("US_CUSTOMARY"), group,
    "EXPLICIT_RESOLVED_CONNECTION_DEMAND",
  );
  expect(built.force_reference).toBeUndefined();
  expect(built.provenance.reference_point).toBeNull();
  request.explicit_resolved_demand = benchmarks.loadJ1Benchmark("US_CUSTOMARY").explicit_resolved_demand;
  if (request.explicit_resolved_demand === null) throw new Error("Fixture explicit demand required");
  request.explicit_resolved_demand.in_plane_force_vector.x = "0";
  request.explicit_resolved_demand.in_plane_force_vector.y = "0";
  expect(multirowValidationMessage(request, group, "EXPLICIT_RESOLVED_CONNECTION_DEMAND")).toContain("finite and nonzero");
});

it("rejects a malformed Direct starter instead of displaying a mismatched physical stack", () => {
  const malformed = benchmarks.loadJ1Benchmark("US_CUSTOMARY");
  const brace = malformed.joint_assembly.members[0];
  if (brace === undefined) throw new Error("Fixture brace required");
  (brace.section as { kind: string }).kind = "WIDE_FLANGE";
  const source = vi.spyOn(benchmarks, "loadJ1Benchmark").mockReturnValue(malformed);
  try {
    expect(() => directStartingExample("US_CUSTOMARY")).toThrow("requires an angle and W column");
  } finally {
    source.mockRestore();
  }
});

it.each([
  ["US_CUSTOMARY", "4", "8", "3", "3", "in"],
  ["SI", "101.6", "203.2", "76.2", "76.2", "mm"],
] as const)("builds a contained %s Direct starter without modifying historical J1", (unit, leg, flange, end, boundary, lengthUnit) => {
  const legacyBefore = JSON.stringify(benchmarks.loadJ1Benchmark(unit));
  const starter = directStartingExample(unit);
  const built = buildMultirowRequest(starter, benchmarks.loadJ1ViewExtents(unit), initialBoltGroupState(unit, true), "AUTOMATIC_MEMBER_END_FORCE");
  const scale = unit === "SI" ? 25.4 : 1;
  expect(starter.joint_assembly.member_end_actions[0]?.force.x).toBe(unit === "SI" ? "3.11375513068235" : "0.7");
  const brace = built.physical_connection?.joint_assembly.members[0]?.section;
  const support = built.physical_connection?.joint_assembly.members[1]?.section;
  expect(Number(brace?.leg_z?.value)).toBe(4 * scale);
  expect(Number(brace?.thickness.value)).toBe(0.5 * scale);
  expect(Number(support?.overall_depth?.value)).toBe(8 * scale);
  expect(Number(support?.web_thickness?.value)).toBe(0.5 * scale);
  expect(Number(support?.flange_thickness?.value)).toBe(0.5 * scale);
  expect(built.hole_basis).toBe("US_CUSTOMARY_PRINTED");
  expect(Number(built.physical_connection?.geometry_template?.hole_diameter.value)).toBeCloseTo(0.563 * scale, 12);
  expect(Number(starter.fastener_snapshot.washer_geometry?.outside_diameter.value)).toBe(1 * scale);
  expect(Number(starter.fastener_snapshot.washer_geometry?.thickness.value)).toBeCloseTo(0.051 * scale, 12);
  expect(Number(built.pitch.value)).toBe(2 * scale);
  expect(Number(built.gauge.value)).toBe(2 * scale);
  expect(Number(built.negative_side_distance.value)).toBe(1 * scale);
  expect(Number(built.positive_side_distance.value)).toBe(1 * scale);
  expect(built.lap_configuration).toBe("SINGLE_LAP");
  expect(built.physical_connection?.geometry_template).toMatchObject({ angle_connected_leg: "LEG_1", outstanding_leg_side: "POSITIVE_INTERFACE_Z", column_flange_connection_side: "EXTERIOR" });
  expect(built.direct_finalization_contract_version).toBe("SHEAR01-DIRECT-F1");
  expect(built.row_count).toBe(2);
  expect(built.bolts_per_row).toBe(1);
  expect(built.source_length_unit).toBe(lengthUnit);
  expect(built.physical_connection?.joint_assembly.members[0]?.section.leg_y?.value).toBe(leg);
  expect(built.physical_connection?.joint_assembly.members[1]?.section.flange_width?.value).toBe(flange);
  expect(built.unloaded_end_e1.value).toBe(end);
  expect(built.loaded_boundary_to_row_1_distance.value).toBe(boundary);
  expect(JSON.stringify(benchmarks.loadJ1Benchmark(unit))).toBe(legacyBefore);
  expect(starter.geometry_template?.brace_to_column_directed_angle_deg).toBe("135");
});
