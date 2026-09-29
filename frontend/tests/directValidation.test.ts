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
