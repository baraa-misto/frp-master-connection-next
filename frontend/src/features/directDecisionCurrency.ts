import { currentReportSnapshot, invalidateReportSnapshot } from "../state/reportSession";

/** Checks the sealed server handle; browser JSON cannot grant qualification. */
export async function validateDirectDecisionCurrency(signal: AbortSignal): Promise<boolean> {
  const authority = currentReportSnapshot("multi-row");
  if (authority.dirty || authority.kind !== "design" || authority.token === null) return false;
  try {
    const response = await fetch("/api/v1/reports/direct-decision-current", {
      method: "POST", credentials: "same-origin", signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ report_handle: authority.token }),
    });
    if (!response.ok) return false;
    const body = await response.json() as { readonly current?: unknown };
    return body.current === true;
  } catch { return false; }
}

export function invalidateDirectDecision(): void {
  invalidateReportSnapshot("multi-row");
}
