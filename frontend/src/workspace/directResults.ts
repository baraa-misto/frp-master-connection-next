import type { AutomaticGroupModeIntegrationResult, MultiRowCheckResult } from "../api/multirowContracts";

/** Presentation only: consume final authorized results, not the earlier partial handoff. */
export function finalDirectChecks(integration: AutomaticGroupModeIntegrationResult): MultiRowCheckResult[] {
  return Array.from(new Map([
    ...integration.scenario_results.flatMap((scenario) => scenario.supported_results),
    ...(integration.direct_angle_block_results ?? []).flatMap((block) => block.supported_results),
  ]
    .map((check) => [JSON.stringify(check), check])).values());
}
