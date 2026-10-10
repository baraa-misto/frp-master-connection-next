import { useEffect, useState } from "react";
import { inspectMAT1Factors } from "../api/mat1Service";
import type { MAT1CatalogRecord, MAT1Conditions } from "../state/mat1Session";
import { materialConditionIssues } from "./materialConditionValidation";

export function ASCEShapeBasisSummary({ record, conditions, compact = false }: {
  readonly record: MAT1CatalogRecord;
  readonly conditions: MAT1Conditions;
  readonly compact?: boolean;
}) {
  const [response, setResponse] = useState<{ key: string; value: Awaited<ReturnType<typeof inspectMAT1Factors>> } | null>(null);
  const [error, setError] = useState<{ key: string; value: string } | null>(null);
  const key = JSON.stringify([record.id, record.revision, record.content_digest, conditions]);
  useEffect(() => {
    if (Object.keys(materialConditionIssues(conditions)).length > 0) return;
    const controller = new AbortController();
    void inspectMAT1Factors({ material: { kind: "CATALOG", id: record.id, revision: record.revision, content_digest: record.content_digest },
      conditions, component_id: "DIRECT_MATERIAL_BASIS", property_ids: ["tensile_strength_L", "tensile_modulus_L"] }, controller.signal)
      .then((value) => { if (!controller.signal.aborted) setResponse({ key, value }); })
      .catch((cause: unknown) => { if (!controller.signal.aborted) setError({ key, value: cause instanceof Error ? cause.message : "Material requirements could not be resolved. Check project conditions and try again." }); });
    return () => { controller.abort(); };
  }, [key, record.id, record.revision, record.content_digest, conditions]);
  const current = response?.key === key ? response.value : null;
  const thermal = current?.condition_basis;
  const issues = Array.from(new Set((current?.ledgers ?? []).flatMap((ledger) => (ledger as { issues: string[] }).issues)));
  return <section className="information-status" aria-label="ASCE shape material design basis">
    <h4>{compact ? "Required Tg · specification" : "Design-property basis"}</h4>
    {compact ? null : <>
    <p>ASCE/SEI 74-23 Table 1-2 minimum characteristic properties for pultruded shapes.</p>
    <p>ASCE minimum characteristic design basis; project-specified ICE resin selection. Reference condition resolves automatically from Section 2.4.2. Moduli are characteristic values for strength and stability; no manufacturer mean-modulus authority is supplied.</p>
    <p>Project FRP shall conform to the selected resin system and the applicable ASCE/SEI 74-23 minimum physical, mechanical, and durability requirements.</p></>}
    <p aria-label="Tg requirement"><strong>Tg requirement: {thermal === undefined ? "Complete project temperatures and load classification to resolve the requirement." : `>= ${thermal.required_tg.value} °F (${Number(thermal.required_tg_degC).toFixed(3)} °C)`}</strong></p>
    <p>Furnished-product conformance is procurement/project QA responsibility. This is a specification requirement; the software has not measured actual product Tg.</p>
    {compact ? <p>Resistance time-effect factor λ: <output>{current === null ? "Pending explicit conditions and classification" : (current.ledgers[0] as { lambda_factor?: string }).lambda_factor ?? "Not resolved"}</output></p> : null}
    {issues.length === 0 ? null : <section aria-label="Project material condition requirements"><ul>{issues.map((issue) => <li key={issue}>{issue.replaceAll("_", " ").toLowerCase()}</li>)}</ul></section>}
    {error?.key === key && current === null ? <p role="alert">{error.value}</p> : null}
  </section>;
}
