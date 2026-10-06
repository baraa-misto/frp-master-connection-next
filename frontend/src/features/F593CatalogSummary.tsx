/** Current server catalog resolution only; no local strength or resistance calculator. */
import { useEffect, useState } from "react";
import type { FastenerSelection } from "../state/mat1Session";
import { formatEditableDecimal } from "../workspace/presentation";

type Selection = Extract<FastenerSelection, { kind: "CATALOG" }>;
export interface F593Resolution {
  readonly contract: string;
  readonly fnt_state: string;
  readonly fnt: { readonly value: string; readonly unit: string } | null;
  readonly display_fnt: { readonly value: string; readonly unit: string } | null;
  readonly condition: string;
  readonly marking: string | null;
  readonly source_requirement: string;
  readonly specification_note: string;
  readonly catalog_record_id: string;
  readonly catalog_revision: string;
  readonly catalog_digest: string;
  readonly source_classification: string;
  readonly owner_approval: string;
  readonly selected_row: { readonly tensile_min: string; readonly tensile_max: string;
    readonly diameter_min: string; readonly diameter_max: string; readonly hardness_basis: string } | null;
  readonly shear_planes: readonly { readonly plane_id: string; readonly thread_status: string;
    readonly fnv_rule: string; readonly fnv: { readonly value: string; readonly unit: string } | null;
    readonly display_fnv: { readonly value: string; readonly unit: string } | null }[];
}
export function F593CatalogSummary({ selection, diameter, onSelect }: {
  readonly selection: Selection;
  readonly diameter: { readonly value: string; readonly unit: string };
  readonly onSelect: (selection: FastenerSelection) => void;
}) {
  const key = JSON.stringify({ selection, diameter });
  const [resolved, setResolved] = useState<({ readonly key: string; readonly data: F593Resolution } | { readonly key: string; readonly error: string }) | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch("/api/v1/fasteners/resolve", {
          method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
          body: key, signal: controller.signal,
        });
        if (!response.ok) throw new Error("Catalog resolution request failed.");
        const data = await response.json() as F593Resolution;
        if (data.contract !== "FASTENER-F4-RC1") throw new Error("Unexpected catalog response.");
        if (!controller.signal.aborted) setResolved({ key, data });
      } catch {
        if (!controller.signal.aborted) setResolved({ key,
          error: "Fastener catalog could not be resolved. Check the diameter and local backend service, then retry." });
      }
    })();
    return () => { controller.abort(); };
  }, [key]);
  const current = resolved?.key === key ? resolved : null;
  return <section aria-label="F593 controlled catalog">
    {current === null ? <p role="status">Resolving current fastener catalog row…</p>
      : "error" in current ? <p role="alert">{current.error}</p>
      : <ResolvedRecord data={current.data} diameter={diameter} />}
    <details><summary>Predefined alloy and condition selection</summary>
      <label>F593 alloy <select value={selection.alloy} onChange={(event) => { onSelect({ ...selection, alloy: event.currentTarget.value as Selection["alloy"] }); }}><option value="316">316</option><option value="316L">316L</option></select></label>
      <label>F593 condition <select value={selection.condition} onChange={(event) => { onSelect({ ...selection, condition: event.currentTarget.value as Selection["condition"] }); }}>
        <option value="COLD_WORKED">Cold worked — automatic CW1/CW2 by diameter</option><option value="AF">AF / F593E</option><option value="A">A / F593F</option><option value="CW1">CW1 / F593G — explicit</option><option value="CW2">CW2 / F593H — explicit</option>
      </select></label>
      <p>The catalog supplies tensile strength; thread location is recorded under Bolts. It does not establish thread length or qualify the whole connection.</p>
    </details>
  </section>;
}

function ResolvedRecord({data, diameter}: {
  readonly data: F593Resolution;
  readonly diameter: {readonly value: string; readonly unit: string};
}) {
  return <>
        <p><strong>{data.fnt_state === "CATALOG_SOURCE_RESOLVED" ? "Catalog source resolved" : "Source required"}</strong></p>
        {data.fnt === null ? <p role="alert">{data.source_requirement}</p> : <>
          <p>Resolved condition: <strong>{data.condition} / {data.marking}</strong></p>
          <p>Nominal diameter: {diameter.value} {diameter.unit}</p>
          <p>Design Fnt: <strong>{data.display_fnt === null ? "Unavailable" : `${formatEditableDecimal(data.display_fnt.value)} ${data.display_fnt.unit}`}</strong> — lower specified tensile bound</p>
          {data.shear_planes.map((plane) => <p key={plane.plane_id}>Bolt shear basis: {plane.fnv === null
            ? "Thread location unresolved — bolt shear unevaluated"
            : plane.display_fnv === null ? "Unavailable" : `${formatEditableDecimal(plane.display_fnv.value)} ${plane.display_fnv.unit}`} · {plane.thread_status.toLowerCase().replaceAll("_", " ")} ({plane.fnv_rule})</p>)}
        </>}
        <section className="information-status" aria-label="Fastener specification / procurement notes"><h4>Specification / procurement notes</h4><p>{data.specification_note}</p></section>
        <details><summary>Controlled F593 catalog technical record</summary>
          <p>{data.catalog_record_id} · {data.catalog_revision}</p>
          {data.selected_row === null ? null : <><p>Applicable nominal diameter: {data.selected_row.diameter_min}–{data.selected_row.diameter_max} in inclusive</p>
            <p>Specified tensile range: {data.selected_row.tensile_min}–{data.selected_row.tensile_max} ksi; design uses the minimum.</p><p>Hardness: {data.selected_row.hardness_basis}</p></>}
          <p>{data.source_classification}</p><p>{data.owner_approval}</p><p>Catalog SHA-256: {data.catalog_digest}</p>
        </details>
      </>;
}
