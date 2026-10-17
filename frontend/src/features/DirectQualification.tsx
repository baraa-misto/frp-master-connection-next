import { useEffect, useState } from "react";
import { mat1FamilyKey, setDirectQualificationRecordId, useMAT1 } from "../state/mat1Session";
import { currentDirectDecision } from "./directDecision";

interface Evaluation {
  readonly record_digest: string | null;
  readonly selected_record_id: string | null;
  readonly record_revision: number | null;
  readonly scope_match_state: string;
  readonly capacity_state: string;
  readonly covered_response_ids: readonly string[];
  readonly mismatch_reasons: readonly string[];
  readonly synthetic: boolean;
  readonly laboratory?: string;
  readonly rdp_approval?: string;
  readonly statistics?: { readonly accepted_n: number; readonly Ro: string | null; readonly phi_p: string | null; readonly VR?: string | null };
  readonly Rd_q: { readonly value: string; readonly unit: string } | null;
  readonly Ru?: { readonly value: string; readonly unit: string } | null;
  readonly utilization?: string | null;
}

export function DirectQualification({ stale, onSelectionChange }: {
  readonly stale: boolean;
  readonly onSelectionChange: () => void;
}) {
  const mat1 = useMAT1();
  const [records, setRecords] = useState<readonly string[]>([]);
  const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/v1/frp-materials/direct-qualification/records", {
      credentials: "same-origin", signal: controller.signal,
    }).then(async (response) => {
      if (!response.ok) throw new Error("Catalog unavailable");
      const body = await response.json() as { readonly available_record_ids?: unknown };
      if (!Array.isArray(body.available_record_ids) || body.available_record_ids.some((id: unknown) => typeof id !== "string")) throw new Error("Catalog invalid");
      if (!controller.signal.aborted) setRecords(body.available_record_ids as string[]);
    }).catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => { controller.abort(); };
  }, []);
  const trace = mat1.designTraces["multi-row"] as { readonly qualification_evaluation?: Evaluation } | undefined;
  const evaluation = stale || mat1.designKeys["multi-row"] !== mat1FamilyKey("multi-row") ? undefined : trace?.qualification_evaluation;
  const decision = currentDirectDecision(trace, stale, mat1.designKeys["multi-row"] === mat1FamilyKey("multi-row"));
  return <section aria-label="Connection qualification">
    <h3>Connection qualification</h3>
    <p><strong>{decision?.qualification_capacity_state === "CAPACITY_PASS" ? "APPROVED CAPACITY — PASS" : decision?.qualification_capacity_state === "CAPACITY_FAIL" ? "APPROVED CAPACITY — FAIL" : "QUALIFICATION REQUIRED"}</strong></p>
    {error ? <p role="status">Qualification catalog could not be reached. Check the local backend and reload the application.</p> : null}
    {records.length > 0 ? <label className="field-control"><span>Approved qualification record</span>
      <select value={mat1.directQualificationRecordId ?? ""} onChange={(event) => {
        setDirectQualificationRecordId(event.currentTarget.value || null); onSelectionChange();
      }}><option value="">Select installed record</option>{records.map((id) => <option key={id} value={id}>{id}</option>)}</select>
    </label> : null}
    {evaluation?.record_digest == null ? <>
      <p>No approved Section 2.3.2 qualification record matches this Direct connection.</p>
      <p className="sidebar-note">Select an approved qualification record installed by the engineering administrator.</p>
      {stale ? <p role="status">Run Design Check to evaluate qualification for the current inputs.</p> : null}
    </> : <>
      {evaluation.synthetic ? <p className="qualification-banner">SYNTHETIC QA — CANNOT QUALIFY PRODUCTION DESIGN</p> : null}
      <dl>
        <dt>Record / revision</dt><dd>{evaluation.selected_record_id} / {evaluation.record_revision}</dd>
        <dt>Laboratory / RDP</dt><dd>{evaluation.laboratory} / {evaluation.rdp_approval}</dd>
        <dt>Accepted specimens</dt><dd>{evaluation.statistics?.accepted_n ?? "Unevaluated"}</dd>
        <dt>Reference strength</dt><dd>{evaluation.statistics?.Ro == null ? "Unevaluated" : `${Number(evaluation.statistics.Ro).toPrecision(5)} N`}</dd>
        <dt>phi_p</dt><dd>{evaluation.statistics?.phi_p == null ? "Unevaluated" : Number(evaluation.statistics.phi_p).toPrecision(4)}</dd>
        <dt>COV</dt><dd>{evaluation.statistics?.VR == null ? "Unevaluated" : Number(evaluation.statistics.VR).toPrecision(5)}</dd>
        <dt>Qualified design strength</dt><dd>{evaluation.Rd_q === null ? "Unevaluated" : `${Number(evaluation.Rd_q.value).toPrecision(5)} ${evaluation.Rd_q.unit}`}</dd>
        <dt>Required strength</dt><dd>{evaluation.Ru == null ? "Unevaluated" : `${Number(evaluation.Ru.value).toPrecision(5)} ${evaluation.Ru.unit}`}</dd>
        <dt>Utilization</dt><dd>{evaluation.utilization == null ? "Unevaluated" : Number(evaluation.utilization).toPrecision(6)}</dd>
        <dt>Scope / capacity</dt><dd>{evaluation.scope_match_state} / {evaluation.capacity_state}</dd>
        <dt>Covered responses</dt><dd>{evaluation.covered_response_ids.length} of 5</dd>
      </dl>
      {decision === undefined ? null : <ul>{decision.unresolved_requirements.map((reason) => <li key={reason}>{reason}</li>)}</ul>}
      {evaluation.mismatch_reasons.length > 0 ? <details><summary>Advanced qualification diagnostics</summary><ul>{evaluation.mismatch_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></details> : null}
    </>}
  </section>;
}
