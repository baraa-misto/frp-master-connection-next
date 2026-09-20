import type { MultiRowQuantity } from "../api/multirowContracts";
import type { WIWallMomentDesign } from "../api/wiWallMomentContracts";

export interface WallMomentVisibleFailure {
  readonly checkId: string;
  readonly component: string;
  readonly reason: string;
  readonly utilization: string | null;
  readonly demand: MultiRowQuantity | null;
  readonly resistance: MultiRowQuantity | null;
  readonly nativeRecord: unknown;
}

// Presentation projection only. Never select a governing check, compare a
// utilization, recompute a resistance, or change the backend aggregate status.
export function wallMomentVisibleFailures(value: WIWallMomentDesign): readonly WallMomentVisibleFailure[] {
  const rows: WallMomentVisibleFailure[] = value.native_failed_checks
    .filter(c => c.numerical_comparison === "FAIL")
    .map(c => ({checkId:c.result_id,component:c.result_id.split(":")[1] ?? c.result_id,reason:c.limit_state,
      utilization:c.utilization,demand:c.demand,resistance:c.design_resistance,nativeRecord:c}));
  for (const c of [...value.web_bearing,...value.flange_bearing]) {
    if (c.comparison.numerical_comparison === "FAIL") rows.push({checkId:c.check_id,component:c.layer_id,
      reason:`PIN_BEARING · ${c.material_direction}`,utilization:c.comparison.utilization,demand:c.demand,
      resistance:c.trace.factor_trace.design_resistance,nativeRecord:c});
  }
  for (const p of value.connector_results) {
    const component = value.preview.connectors.find(c => c.core.fingerprint === p.core_fingerprint)?.connector_id ?? p.core_fingerprint;
    const start = rows.length;
    const instep = p.detail?.instep;
    if (instep != null && !instep.passed) rows.push({checkId:instep.method,component,reason:p.reason,
      utilization:instep.utilization,demand:instep.demand,resistance:instep.factors.design_resistance,nativeRecord:instep});
    const body = p.detail?.body;
    if (body?.status === "FAIL") rows.push({checkId:body.method,component,reason:body.interaction_method,
      utilization:body.utilization,demand:null,resistance:null,nativeRecord:body});
    if (p.status === "FAIL" && rows.length === start) rows.push({checkId:"Connector provider",component,reason:p.reason,
      utilization:null,demand:null,resistance:null,nativeRecord:p});
  }
  for (const c of value.attachment_results) {
    if (c.check.status === "FAIL") rows.push({checkId:c.method,component:c.connector_id,reason:c.check.interaction_method,
      utilization:c.check.utilization,demand:null,resistance:null,nativeRecord:c.check});
  }
  for (const c of value.common_web_bolts) {
    if (c.status === "FAIL") rows.push({checkId:c.bolt_id,component:"Common web bolt",reason:c.method,
      utilization:c.governing_utilization,demand:null,resistance:c.per_plane_design_capacity,nativeRecord:c});
  }
  for (const c of value.local_checks) {
    if (c.scope_status === "FAIL") rows.push({checkId:c.connector_id,component:c.layer_id,reason:c.scope_status,
      utilization:null,demand:null,resistance:null,nativeRecord:c});
  }
  if (value.status === "FAIL" && rows.length === 0) rows.push({checkId:"Native aggregate status",component:"Internal connection",
    reason:`${value.status_reason} — no individual failure record returned; inspect the complete native trace.`,
    utilization:null,demand:null,resistance:null,nativeRecord:{status:value.status,status_reason:value.status_reason}});
  return rows;
}
