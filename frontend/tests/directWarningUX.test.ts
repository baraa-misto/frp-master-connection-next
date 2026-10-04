import { expect, it } from "vitest";
import { describeDirectWarning } from "../src/workspace/directWarning";

it("separates physical clearance, source, method and information warnings", () => {
  const physical = describeDirectWarning("DIRECT_PHYSICAL_CONTAINMENT:B_R2_L1:member-a:TOP_FLANGE:available=0.625; required=1.25; plane=X. unit=in");
  expect(physical.group).toBe("geometry");
  expect(physical.boltId).toBe("B_R2_L1");
  expect(physical.text).toContain("boundary 0.625 in; required minimum 1.250 in");
  expect(physical.text).toContain("hole radius and washer radius remain separate");
  const metric = describeDirectWarning("DIRECT_PHYSICAL_CONTAINMENT:B_R1_L1:member-a:TOP_FLANGE:available=10; required=20; plane=X. unit=mm");
  expect(metric.text).toContain("boundary 10.000 mm; required minimum 20.000 mm");
  const otherGeometry = describeDirectWarning("DIRECT_PHYSICAL_CONTAINMENT:B_R3_L1:member-a:TOP_FLANGE:outside member");
  expect(otherGeometry).toMatchObject({ group: "geometry", boltId: "B_R3_L1" });
  expect(otherGeometry.text).toContain("outside member");
  expect(describeDirectWarning("F593_TENSILE_SOURCE_DATA_PENDING")).toMatchObject({ group: "source" });
  expect(describeDirectWarning("CONTROLLED_ICE_DEVELOPMENT_MATERIAL")).toMatchObject({ group: "qualification" });
  expect(describeDirectWarning("OUT_OF_PLANE_MOMENT_UNSUPPORTED")).toMatchObject({ group: "method" });
  expect(describeDirectWarning("EXTRA_INFORMATION")).toMatchObject({ group: "information" });
  expect(describeDirectWarning("RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY_USED")).toEqual({ group: "information", text: "Demand distribution / Rational elastic bolt-group method" });
});

it("classifies action and whole-connection qualification independently of geometry", () => {
  expect(describeDirectWarning("DIRECT_INDEPENDENT_MEMBER_END_MOMENT_NOT_SUPPORTED").group).toBe("action");
  expect(describeDirectWarning("DIRECT_BOLT_AXIS_FORCE_UNSUPPORTED").group).toBe("action");
  expect(describeDirectWarning("DIRECT_DEMAND_PLAN_NOT_READY").group).toBe("action");
  expect(describeDirectWarning("SECTION_2_3_2_WHOLE_CONNECTION_QUALIFICATION_REQUIRED").group).toBe("qualification");
  expect(describeDirectWarning("INVALID_PHYSICAL_CONNECTION_GEOMETRY").group).toBe("geometry");
});
