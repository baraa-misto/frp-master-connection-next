/** Current signed Direct decision presentation. Never selects or envelopes scenarios. */
import { currentDirectDecision, type DirectDecision } from "./directDecision";
import { unityPhase, type UnityPhase, type UnityView } from "../workspace/unityRatio";
import type { ReportSnapshotState } from "../state/reportSession";

export const currentSignedDirectReport = (state: ReportSnapshotState): boolean => state.kind === "design" && state.token !== null && !state.dirty;

export interface DirectViewerCurrency {
  readonly currentKey: boolean;
  readonly signedCurrent: boolean;
  readonly stale: boolean;
  readonly checking: boolean;
  readonly error: unknown;
  readonly invalid: boolean;
  readonly previewCurrent: boolean;
}

const pending: Record<Exclude<UnityPhase, "current">, string> = {
  "checking": "Checking current inputs",
  "request-error": "Design check unavailable",
  "invalid": "Inputs need correction",
  "stale": "Recalculation needed",
  "not-checked": "Not calculated",
};
const gray = (status: string, explanation: string): UnityView => ({
  tone: "gray", ratio: null, ratioText: "—", status, governing: null, explanation,
});

export function directViewerUnity(trace: unknown, design: unknown, currency: DirectViewerCurrency): UnityView {
  const phase = unityPhase({ design, ...currency });
  if (phase !== "current") return gray(pending[phase], "Run Design Check when the current inputs and model are ready.");
  const decision = currentDirectDecision(trace, currency.stale, currency.currentKey);
  const native = (trace as { client_design?: unknown; native_design?: unknown } | undefined)?.client_design
    ?? (trace as { native_design?: unknown } | undefined)?.native_design;
  if (!currency.signedCurrent || decision === undefined || native === undefined
    || JSON.stringify(native) !== JSON.stringify(design)
    || !/^[a-fA-F0-9]{64}$/.test(decision.current_snapshot_digest ?? "")
    || !["GREEN", "RED", "YELLOW"].includes(decision.final_status)) {
    return gray("Current design evidence unavailable", "The viewer requires the current signed Direct result and its matching decision trace.");
  }
  const summary = (decision as Partial<DirectDecision>).analytical_check_summary;
  const raw = summary?.highest_utilization;
  const rows: NonNullable<DirectDecision["schedule"]> = Array.isArray(decision.schedule) ? decision.schedule as NonNullable<DirectDecision["schedule"]> : [];
  const matched = rows.filter(row => row.check_id === summary?.highest_analytical_check && row.category === "ANALYTICALLY_EVALUATED");
  const check = matched.length === 1 ? matched[0] : undefined;
  if (summary === undefined || !Number.isSafeInteger(summary.evaluated) || summary.evaluated <= 0 || typeof raw !== "string"
    || !/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(raw)
    || !Number.isFinite(Number(raw)) || (Number(raw) === 0 && !/^0*(?:\.0*)?(?:[eE][+-]?\d+)?$/.test(raw))
    || check?.utilization !== raw || typeof check.label !== "string" || check.label.trim() === ""
    || !["PASS", "FAIL"].includes(check.outcome)) {
    return gray("Evaluated utilization unavailable", "No unambiguous evaluated analytical maximum is available in the current backend decision. See the complete decision inventory.");
  }
  const independentBolts = rows.filter(row => row.category === "ANALYTICALLY_EVALUATED").every(row => row.check_id.startsWith("BOLT_SHEAR:"));
  return {
    tone: decision.final_status.toLowerCase() as UnityView["tone"],
    ratio: Number(raw),
    ratioText: `UR (${independentBolts ? "bolt checks" : "evaluated"}): ${Number(raw).toPrecision(6)}`,
    status: `Whole connection: ${decision.final_status} — ${decision.final_status_reason.replaceAll("_", " ").toLowerCase()}`,
    governing: `${check.label} · ${check.outcome}`,
    explanation: `${String(summary.evaluated)} analytical checks evaluated; ${String(summary.counts.REQUIRED_UNRESOLVED)} required items unresolved. ${independentBolts ? "Independent bolt checks only; FRP resistances remain unevaluated. " : ""}Whole-connection qualification: ${decision.qualification_capacity_state.replaceAll("_", " ").toLowerCase()}. Exact analytical utilization: ${raw}. Snapshot: ${String(decision.current_snapshot_digest)}.`,
  };
}
