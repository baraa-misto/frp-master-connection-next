import { useEffect } from "react";
import { mat1FamilyKey, useMAT1 } from "../state/mat1Session";
import { invalidateDirectDecision, validateDirectDecisionCurrency } from "./directDecisionCurrency";

import { currentDirectDecision, directDecisionHeadline } from "./directDecision";

export function DirectDesignStatus({ stale, onCurrencyInvalid }: { readonly stale: boolean; readonly onCurrencyInvalid: () => void }) {
  const mat1 = useMAT1();
  const decision = currentDirectDecision(mat1.designTraces["multi-row"], stale,
    mat1.designKeys["multi-row"] === mat1FamilyKey("multi-row"));
  const recordDigest = decision?.qualification_record_identity?.digest;
  useEffect(() => {
    if (recordDigest == null || stale) return;
    const controller = new AbortController();
    const revalidate = () => {
      void validateDirectDecisionCurrency(controller.signal).then((valid) => {
        if (!valid && !controller.signal.aborted) {
          invalidateDirectDecision(); onCurrencyInvalid();
        }
      });
    };
    revalidate();
    window.addEventListener("focus", revalidate);
    const timer = window.setInterval(revalidate, 60_000);
    return () => { controller.abort(); window.clearInterval(timer); window.removeEventListener("focus", revalidate); };
  }, [recordDigest, stale, onCurrencyInvalid]);
  return <section className={`direct-final-status status-${decision?.final_status.toLowerCase() ?? "gray"}`} aria-label="Direct final design status" role="status">
    <h3>{directDecisionHeadline(decision, stale)}</h3>
    {decision === undefined ? <p>Run Design Check for the current engineering inputs.</p> : <>
      <p><strong>Governing result:</strong> {decision.governing_label}</p>
      <p><strong>Numerical checks:</strong> {decision.analytical_check_summary.evaluated} evaluated — {decision.analytical_check_summary.numerical_outcome}</p>
      <p><strong>Highest analytical utilization:</strong> {decision.analytical_check_summary.highest_utilization === null ? "Unevaluated" : Number(decision.analytical_check_summary.highest_utilization).toPrecision(6)}</p>
      <p><strong>Qualification:</strong> {decision.qualification_capacity_state === "UNEVALUATED" ? "Required / not currently applicable" : decision.qualification_capacity_state.replaceAll("_", " ")}</p>
      <p><strong>Required checks/evidence items unresolved:</strong> {decision.analytical_check_summary.counts.REQUIRED_UNRESOLVED}</p>
      <details><summary>Remaining actions and decision diagnostics</summary>
        <ul>{decision.unresolved_requirements.map((item) => <li key={item}>{item}</li>)}</ul>
      </details>
    </>}
  </section>;
}
