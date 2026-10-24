import { expect, it } from "vitest";
import {
  WORKSPACE_CAPABILITIES,
  WORKSPACE_CAPABILITY_CONTRACT,
  workspaceCapability,
  workspaceSupports,
} from "../src/domain/workspaceCapabilities";

it("uses the packaged 18-family capability contract for Direct and moment UI boundaries", () => {
  expect(WORKSPACE_CAPABILITY_CONTRACT).toBe("WORKSPACE-CAPABILITIES-OR1-RC1");
  expect(Object.keys(WORKSPACE_CAPABILITIES)).toHaveLength(18);
  expect(workspaceCapability("multi-row")).toMatchObject({
    template_id: "DIRECT_REFERENCE", material_assignment_mode: "LINKED",
    features: {
      force_only_shear: "SUPPORTED", automatic_physical_demand: "SUPPORTED",
      independent_moment_input: "NOT_APPLICABLE", custom_fastener: "SUPPORTED",
    },
  });
  expect(workspaceSupports("multi-row", "custom_fastener")).toBe(true);
  expect(workspaceSupports("wi-major-axis-moment-splice", "independent_moment_input")).toBe(true);
  expect(workspaceSupports("wi-major-axis-moment-splice", "custom_fastener")).toBe(false);
  expect(workspaceCapability("unknown")).toBeUndefined();
});
