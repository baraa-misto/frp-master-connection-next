/** Browser view of the same packaged contract served by the authenticated API. */
import raw from "../../../backend/src/frp_master_connection/data/workspace_capabilities.json";

export type CapabilityState = "SUPPORTED" | "DEFERRED" | "NOT_APPLICABLE";
export type CapabilityFeature =
  | "frp_material_selection" | "shared_design_conditions" | "bolted_metallic_hardware"
  | "automatic_physical_demand" | "externally_resolved_demand" | "force_only_shear"
  | "independent_moment_input" | "bolt_axis_prying_input" | "multirow_physical_layout"
  | "custom_material" | "custom_fastener" | "report_engineer" | "report_audit";

export interface WorkspaceCapability {
  readonly route_id: string;
  readonly template_id: string;
  readonly material_assignment_mode: "LINKED" | "PER_COMPONENT";
  readonly features: Readonly<Record<CapabilityFeature, CapabilityState>>;
}

export const WORKSPACE_CAPABILITY_CONTRACT = raw.contract;

function resolveCapability(row: (typeof raw.families)[number]): WorkspaceCapability {
  const profile = raw.profiles[row.profile as keyof typeof raw.profiles];
  return {
    route_id: row.route_id,
    template_id: row.template_id,
    material_assignment_mode: row.material_assignment_mode as WorkspaceCapability["material_assignment_mode"],
    features: { ...raw.common, ...profile } as WorkspaceCapability["features"],
  };
}

export const WORKSPACE_CAPABILITIES: Readonly<Record<string, WorkspaceCapability>> = Object.fromEntries(
  raw.families.map((row) => [row.route_id, resolveCapability(row)]),
);

export function workspaceCapability(routeId: string): WorkspaceCapability | undefined {
  return WORKSPACE_CAPABILITIES[routeId];
}

export function workspaceSupports(routeId: string, feature: CapabilityFeature): boolean {
  return workspaceCapability(routeId)?.features[feature] === "SUPPORTED";
}
