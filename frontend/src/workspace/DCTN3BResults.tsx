import type { DCTN3BDesign, DCTN3BPreview, DCTNWrench } from "../api/dctnContracts";
import type { MultiRowQuantity } from "../api/multirowContracts";
import { formatDisplayQuantity, friendlyEnum } from "./presentation";

export function DCTN3BResults({ snapshot, result, current }: {
  readonly snapshot: DCTN3BPreview; readonly result: DCTN3BDesign | null; readonly current: boolean;
}) {
  const units = snapshot.input.unit_system === "US" ? "US_CUSTOMARY" : "SI";
  const quantity = (q: MultiRowQuantity | null) => {
    // Same presentation-only moment conversion/precision as the existing
    // wall/column moment workspaces. Never re-author request or trace values.
    const moments: Readonly<Record<string, number>> = { "N-mm": 1, "kN-mm": 1000, "kip-in": 112984.8290276167 };
    const factor = q === null ? undefined : moments[q.unit];
    if (q === null || factor === undefined) return formatDisplayQuantity(q, units);
    const divisor = units === "SI" ? 1000 : 112984.8290276167;
    return Number((Number(q.value) * factor / divisor).toPrecision(7)).toString() + " " + (units === "SI" ? "kN-mm" : "kip-in");
  };
  const wrench = (w: DCTNWrench) => (["reference", "force", "moment"] as const).map(k => <div key={k}><strong>{friendlyEnum(k)} — X / Y / Z</strong><p>{[w[k].x, w[k].y, w[k].z].map(quantity).join(" · ")}</p></div>);
  const native = snapshot.historical_preview;
  const responseMessage = native === null ? "Transverse demand calculated — connection response not yet qualified." : "Historical axial-only response retained.";
  return <>
    <section className="dctn-results" aria-label="DCTN engineering preview">
      <article className="source-card"><h3>{current ? "Current engineering status" : "LAST VALID engineering status — not current"}</h3>
        <dl>{([
          ["Geometry", snapshot.geometry_status], ["Demand", snapshot.demand_status],
          ["Response", native === null ? "NOT QUALIFIED" : snapshot.response_status], ["Qualification", result === null ? snapshot.qualification_status : result.blockers.length ? "REQUIRED_QUALIFICATION_MISSING" : "EVALUATED"],
          ["Design", result?.whole_connection_status ?? snapshot.design_status],
        ] as const).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>
        <h4>Response coverage / missing qualification</h4>
        <p><strong>{responseMessage}</strong></p>
        <p>{native === null ? "No automatic transverse Channel/row sharing, contact, bolt tension, prying or local resistance. Unresolved response is unavailable, not zero." : "Historical axial-only symmetry and row response retained. Response qualification is separate from resistance/source qualification."}</p>
        {(result?.blockers ?? snapshot.blockers).map(b => <p key={b}>{b}</p>)}
        <p>Numerical failures: {result === null ? "Not checked" : result.checks.filter(c => c.status === "FAIL").length}.</p>
        <p>{snapshot.geometry.members.length} primary members · {snapshot.geometry.shafts.length} physical bolts · zero connector bodies</p>
      </article>
      <article className="source-card"><h3>Total demand at node reference</h3>{wrench(snapshot.demand.total_at_node)}<p>Calculated demand, not an allocated Channel response.</p></article>
      {snapshot.demand.members.map(m => {
        const input = snapshot.input.members.find(member => member.slot === m.member_id);
        if (input === undefined) throw new Error("DCTN member demand is missing its input authority.");
        return <article className="source-card" key={m.member_id}><h3>{m.member_id} member-end demand</h3><h4>Local engineering actions</h4><dl><div><dt>Axial P</dt><dd>{quantity(input.P)}</dd></div><div><dt>{m.presentation.Qp_label} (Qp)</dt><dd>{quantity(input.Qp)}</dd></div><div><dt>{m.presentation.Qq_label} (Qq)</dt><dd>{quantity(input.Qq)}</dd></div></dl><h4>Derived global member-end wrench</h4>{wrench(m.at_member_end)}<p>Derived global member-end coordinates are read-only. Placement uses Member Horizontal Location and Member Vertical Location.</p><details><summary>Generated moments at node, actual bolt groups and Channel references</summary>{m.transported.map(t => <div key={t.reference_id}><h4>{t.reference_id}</h4>{wrench(t.wrench)}<p>{t.interpretation}</p></div>)}</details></article>;
      })}
      {native === null ? null : <article className="source-card"><h3>Historical P-only response</h3><p>{native.response.status} · {native.response.method}</p>{native.response.reasons.map(r => <p key={r}>{r}</p>)}<table><thead><tr><th>Member / row</th><th>Row / side fraction</th><th>Signed row P</th><th>Force / moment closure</th></tr></thead><tbody>{native.response.rows.map(r => <tr key={r.member_id + ":" + String(r.row)}><td>{r.member_id} / {r.row}</td><td>{r.row_fraction} / {r.side_fraction}</td><td>{quantity(r.signed_row_force)}</td><td>{r.member_force_closes ? "Exact" : "Unproven"} / {r.member_moment_closes ? "Exact" : "Unproven"}</td></tr>)}</tbody></table></article>}
      {native?.response.channels.map(channel => <article className="source-card" key={channel.member_id}><h3>{channel.member_id} local contribution</h3>{wrench(channel.total)}<p>{channel.hole_ids.length} actual holes in {channel.group_ids.length} groups. Not global chord strength or stability.</p></article>)}
      <article className="qualification-banner"><h3>Local connection scope only</h3><p>Missing product, hardware and local-path qualification is not zero demand and not a PASS. No sleeves, no automatic hardware multiplier, and no global truss redistribution.</p><p>{snapshot.global_boundary}</p></article>
      <details className="source-card"><summary>Status and qualification codes</summary><p>Response: {snapshot.response_status}</p><p>Qualification: {result === null ? snapshot.qualification_status : result.blockers.length ? "REQUIRED_QUALIFICATION_MISSING" : "EVALUATED"}</p>{(result?.blockers ?? snapshot.blockers).map(b => <p key={b}>{b}</p>)}</details>
      <details className="source-card"><summary>Complete current / last-valid native geometry and engineering trace</summary><pre>{JSON.stringify(snapshot, null, 2)}</pre></details>
    </section>
    {result === null ? null : <section className="source-card" aria-label="DCTN design results"><h3>{result.whole_connection_status}</h3><p>Numerical failure outranks unresolved independent qualification.</p><table><thead><tr><th>Owner / check</th><th>Status</th><th>Demand / resistance</th></tr></thead><tbody>{result.checks.map(check => <tr key={check.check_id}><td>{check.owner_id} · {check.check_id}</td><td>{check.status}</td><td>{quantity(check.demand)} / {quantity(check.resistance)}</td></tr>)}</tbody></table><h4>Required unresolved qualification</h4>{result.blockers.map(b => <p key={b}>{b}</p>)}<details><summary>Complete design and source trace</summary><pre>{JSON.stringify(result, null, 2)}</pre></details><p>Global design certified: No.</p></section>}
  </>;
}
