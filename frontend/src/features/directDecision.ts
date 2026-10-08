export interface DirectDecision {
  readonly contract: "DIRECT-STATUS-F9";
  readonly final_status: "GREEN" | "RED" | "YELLOW" | "GRAY";
  readonly final_status_reason: string;
  readonly governing_label: string;
  readonly unresolved_requirements: readonly string[];
  readonly qualification_capacity_state: string;
  readonly qualification_record_identity?: { readonly digest: string | null };
  readonly analytical_check_summary: {
    readonly evaluated: number;
    readonly numerical_outcome: string;
    readonly highest_utilization: string | null;
    readonly counts: Readonly<Record<string, number>>;
  };
}

export function currentDirectDecision(trace: unknown, stale: boolean, currentKey: boolean): DirectDecision | undefined {
  if (stale || !currentKey) return undefined;
  const value = (trace as { readonly final_decision?: DirectDecision } | undefined)?.final_decision;
  return value?.contract === "DIRECT-STATUS-F9" ? value : undefined;
}

export function directDecisionHeadline(decision: DirectDecision | undefined, stale: boolean): string {
  return decision === undefined ? stale ? "GRAY — stale; run Design Check" : "GRAY — not calculated / input needed"
    : `${decision.final_status} — ${decision.final_status_reason}`;
}

