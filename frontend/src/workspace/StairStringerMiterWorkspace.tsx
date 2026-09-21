import { useEffect, useMemo, useRef, useState } from "react";
import { convertSSMC, evaluateSSMC, isSSMCRequest, loadSSMC, type SSMCRequest, type SSMCResponse, type SSMCWrench } from "../api/ssmcClient";
import type { MultiRowQuantity as Q } from "../api/multirowContracts";
import { buildSSMCScene } from "../visualization/ssmcScene";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { ConnectionWorkspaceMain, ConnectionWorkspaceShell, ConnectionWorkspaceSidebar, PersistentConnectionViewer, SidebarGroup } from "./ConnectionWorkspaceShell";
import { friendlyEnum } from "./presentation";
import { isIntentionalAbort, PREVIEW_DEBOUNCE_MS } from "./previewWorkflow";
import "./dctnWorkspace.css";

const keyOf = (r: SSMCRequest) => JSON.stringify({ ...r, request_id: "" });
function Field({ label, value, change }: { readonly label: string; readonly value: Q; readonly change: (raw: string) => void }) {
  return <label className="field-control"><span>{label}</span><span className="input-with-unit"><input aria-label={label} inputMode="decimal" value={value.value} onChange={e => { change(e.currentTarget.value); }}/><small>{value.unit}</small></span></label>;
}
function formatSSMCQuantity(q: Q, si: boolean): string {
  const mapping: Record<string, [number, string]> = si ? {
    N: [0.001, "kN"], "N-mm": [0.001, "kN-mm"], kip: [4.4482216152605, "kN"], "kip-in": [112.9848290276167, "kN-mm"], in: [25.4, "mm"],
  } : { N: [1 / 4448.2216152605, "kip"], "N-mm": [1 / 112984.8290276167, "kip-in"], kN: [1 / 4.4482216152605, "kip"], "kN-mm": [1 / 112.9848290276167, "kip-in"], mm: [1 / 25.4, "in"] };
  const conversion = mapping[q.unit] ?? [1, q.unit];
  return Number((Number(q.value) * conversion[0]).toPrecision(7)).toString() + " " + conversion[1];
}
function WrenchCard({ title, wrench, si }: { readonly title: string; readonly wrench: SSMCWrench; readonly si: boolean }) {
  return <section className="source-card"><h3>{title}</h3>{(["force", "moment"] as const).map(k => <p key={k}>{friendlyEnum(k)} X / Y / Z: {(["x", "y", "z"] as const).map(a => formatSSMCQuantity(wrench[k][a], si)).join(" · ")}</p>)}<p>Reference X / Y / Z: {(["x", "y", "z"] as const).map(a => formatSSMCQuantity(wrench.reference[a], si)).join(" · ")}</p></section>;
}
export function StairStringerMiterWorkspace() {
  const [initial, setInitial] = useState<SSMCRequest | null>(null), [failure, setFailure] = useState<string | null>(null), [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); let disposed = false;
    void loadSSMC(controller.signal).then(r => { if (!disposed) { setInitial(r); setFailure(null); } }).catch((e: unknown) => { if (!disposed && !isIntentionalAbort(e)) setFailure(String(e)); });
    return () => { disposed = true; controller.abort(); };
  }, [retry]);
  return initial === null ? <section className="source-card"><h2>Stair Stringer Miter Connection</h2>{failure === null ? <p role="status">Loading illustrative, unqualified inputs…</p> : <p role="alert">{failure}<button onClick={() => { setRetry(n => n + 1); }}>Retry</button></p>}</section> : <Editor initial={initial}/>;
}
function Editor({ initial }: { readonly initial: SSMCRequest }) {
  const [request, setRequest] = useState(initial), [revision, setRevision] = useState(0);
  const [accepted, setAccepted] = useState<{ key: string; response: SSMCResponse } | null>(null);
  const [failure, setFailure] = useState<{ key: string; text: string } | null>(null);
  const [design, setDesign] = useState<{ key: string; response: SSMCResponse } | null>(null);
  const [busy, setBusy] = useState(false), [operationError, setOperationError] = useState<string | null>(null);
  const [selection, setSelection] = useState<SceneSelection>({ kind: "MEMBER", id: "MITER_WEB_PLATE" });
  const operation = useRef(0), active = useRef<AbortController | null>(null);
  const key = keyOf(request), finite = isSSMCRequest(request);
  useEffect(() => () => { operation.current += 1; active.current?.abort(); }, []);
  useEffect(() => {
    let disposed = false; const controller = new AbortController();
    const execute = async () => {
      try { const response = await evaluateSSMC(request, "preview", controller.signal); if (!disposed) { setAccepted({ key, response }); setFailure(null); } }
      catch (e) { if (!disposed && !isIntentionalAbort(e)) setFailure({ key, text: String(e) }); }
    };
    const timer = finite ? setTimeout(() => { void execute(); }, revision === 0 ? 0 : PREVIEW_DEBOUNCE_MS) : undefined;
    return () => { disposed = true; clearTimeout(timer); controller.abort(); };
  }, [request, revision, key, finite]);
  const current = finite && accepted?.key === key && !busy && failure?.key !== key;
  const snapshot = accepted?.response.result ?? null;
  const scene = useMemo(() => snapshot === null ? null : buildSSMCScene(snapshot, current), [snapshot, current]);
  const change = (fn: (r: SSMCRequest) => void, sourceOnly = false) => {
    operation.current += 1; active.current?.abort(); setBusy(false); setOperationError(null);
    setRequest(old => { const next = structuredClone(old); fn(next); next.request_id = "SSMC:" + String(operation.current); if (!sourceOnly) { next.source_reference = ""; next.fastener.source_reference = ""; } return next; });
    setRevision(n => n + 1);
  };
  const operate = async (kind: "design" | "US" | "SI") => {
    const serial = ++operation.current; active.current?.abort(); const controller = new AbortController(); active.current = controller; setBusy(true); setOperationError(null);
    try {
      if (kind === "design") { const response = await evaluateSSMC(request, "design-check", controller.signal); if (serial === operation.current) setDesign({ key, response }); }
      else { const converted = await convertSSMC(request, kind === "SI", controller.signal); if (serial === operation.current) { setRequest(converted); setRevision(n => n + 1); } }
    } catch (e) { if (serial === operation.current && !isIntentionalAbort(e)) setOperationError(String(e)); }
    finally { if (serial === operation.current) setBusy(false); }
  };
  const field = (label: string, value: Q, fn: (r: SSMCRequest, raw: string) => void) => <Field label={label} value={value} change={raw => { change(r => { fn(r, raw); }); }}/>;
  const si = request.unit_system === "SI";
  return <ConnectionWorkspaceShell className="dctn-workspace" banner={<section className="stage-banner"><h2>Stair Stringer Miter Connection</h2><p>Illustrative unqualified geometry · one FRP plate · CW basis — unknown cut · independent hardware</p><p>Geometry and demand workflow only. Complete moment capacity is not qualified.</p></section>}>
    <ConnectionWorkspaceSidebar ariaLabel="SSMC inputs">
      <SidebarGroup title="Units and inclination" summary="X horizontal · Y out of stair plane · Z vertical" defaultOpen>
        <label className="field-control">Unit system<select aria-label="SSMC unit system" value={request.unit_system} disabled={busy} onChange={e => { void operate(e.currentTarget.value as "US" | "SI"); }}><option value="US">U.S. Units</option><option value="SI">S.I. Units</option></select></label>
        <label className="field-control">Signed inclination (deg)<input aria-label="Signed inclination (deg)" value={request.theta_deg} onChange={e => { const raw = e.currentTarget.value; change(r => { r.theta_deg = raw; }); }}/></label><p>30°–45° in either direction. Horizontal member remains horizontal; no fit repair.</p>
      </SidebarGroup>
      {(["horizontal", "inclined"] as const).map(owner => <SidebarGroup key={owner} title={friendlyEnum(owner) + " stringer"} summary="FRP · CUSTOM_DIMENSIONS" defaultOpen>
        <label className="field-control">Section form<select aria-label={owner + " section form"} value={request[owner].form} onChange={e => { const form = e.currentTarget.value as "CHANNEL" | "W_I"; change(r => { r[owner].form = form; }); }}><option value="CHANNEL">Channel</option><option value="W_I">W/I</option></select></label>
        <div className="field-grid">{(["length", "depth", "width", "web_thickness", "flange_thickness"] as const).map(k => <span key={k}>{field(friendlyEnum(owner) + " " + friendlyEnum(k), request[owner][k], (r, raw) => { r[owner][k].value = raw; })}</span>)}</div>
      </SidebarGroup>)}
      <SidebarGroup title="One-piece miter web plate" summary="FRP only — no stainless activation" defaultOpen>
        <label className="field-control">Plate side<select aria-label="Plate side" value={request.plate.side} onChange={e => { const side = e.currentTarget.value as "NEG_Y" | "POS_Y"; change(r => { r.plate.side = side; }); }}><option value="NEG_Y">Negative Y</option><option value="POS_Y">Positive Y</option></select></label>
        <div className="field-grid">{(["thickness", "horizontal_overlap", "inclined_overlap", "horizontal_depth", "inclined_depth", "normal_gap"] as const).map(k => <span key={k}>{field("Plate " + friendlyEnum(k), request.plate[k], (r, raw) => { r.plate[k].value = raw; })}</span>)}</div>
        <p>Gross neck: {current && snapshot !== null ? String(Number(snapshot.geometry.polygon.gross_neck_width.toPrecision(7))) + " " + snapshot.geometry.length_unit : "Current geometry not verified"}. Derived geometry only, not resistance.</p>
        <details><summary>Manufactured corner treatment</summary>{(["corner_radius", "chamfer"] as const).map(k => <span key={k}>{field("Plate " + friendlyEnum(k), request.plate[k], (r, raw) => { r.plate[k].value = raw; })}</span>)}<p>Nonzero treatment is rejected when the native kernel cannot represent it authoritatively.</p></details>
      </SidebarGroup>
      {(["horizontal_group", "inclined_group"] as const).map(owner => <SidebarGroup key={owner} title={friendlyEnum(owner)} summary="Serial group — full action, not half" defaultOpen>
        <label className="field-control">Bolt stations along member<select aria-label={owner + " rows"} value={request[owner].rows} onChange={e => { const rows = Number(e.currentTarget.value); change(r => { r[owner].rows = rows; }); }}><option value={2}>2 × 2</option><option value={3}>3 × 2</option></select></label>
        <div className="field-grid">{(["first_from_cut", "pitch", "gauge", "transverse_offset"] as const).map(k => <span key={k}>{field(friendlyEnum(owner) + " " + friendlyEnum(k), request[owner][k], (r, raw) => { r[owner][k].value = raw; })}</span>)}</div>
        <details><summary>Planar response assumptions</summary>{(["ordinary_snug_tight", "slots", "equal_translational_stiffness"] as const).map(k => <label key={k}><input type="checkbox" aria-label={owner + " " + k} checked={request[owner][k]} onChange={e => { const checked = e.currentTarget.checked; change(r => { r[owner][k] = checked; }); }}/>{friendlyEnum(k)}</label>)}</details>
      </SidebarGroup>)}
      <SidebarGroup title="Independent hardware" summary="Geometry is not strength qualification" defaultOpen><div className="field-grid">{(["diameter", "hole_diameter"] as const).map(k => <span key={k}>{field("Bolt " + friendlyEnum(k), request.fastener[k], (r, raw) => { r.fastener[k].value = raw; })}</span>)}</div>
        <details><summary>Head, nut, washers and thread installation</summary>{(["washer_diameter", "washer_thickness", "head_across_flats", "head_height", "nut_across_flats", "nut_height", "end_extension"] as const).map(k => <span key={k}>{field("Hardware " + friendlyEnum(k), request.fastener.hardware[k], (r, raw) => { r.fastener.hardware[k].value = raw; })}</span>)}<select aria-label="Thread location" value={request.fastener.threads} onChange={e => { const value = e.currentTarget.value as "INCLUDED" | "EXCLUDED"; change(r => { r.fastener.threads = value; }); }}><option value="EXCLUDED">Threads excluded</option><option value="INCLUDED">Threads included</option></select></details>
      </SidebarGroup>
      <SidebarGroup title="Inclined connected-end actions" summary="Signed local N / V / M" defaultOpen><div className="field-grid">{(["N", "V", "M"] as const).map(k => <span key={k}>{field(k, request[k], (r, raw) => { r[k].value = raw; })}</span>)}</div><p>u follows the incline; p is in-plane normal; q = −Y. M is about q. The horizontal counter-wrench is derived by equilibrium.</p></SidebarGroup>
      <SidebarGroup title="Advanced qualification" summary="Typed references do not activate authority"><label className="field-control">Response / material source reference<input aria-label="SSMC source reference" value={request.source_reference} onChange={e => { const v = e.currentTarget.value; change(r => { r.source_reference = v; }, true); }}/></label><label className="field-control">Hardware source reference<input aria-label="SSMC hardware source reference" value={request.fastener.source_reference} onChange={e => { const v = e.currentTarget.value; change(r => { r.fastener.source_reference = v; }, true); }}/></label><p>Production trusted registries are empty. No LW fallback, fictitious isotropy or automatic double shear.</p></SidebarGroup>
      <SidebarGroup title="Design status" summary={current && snapshot !== null ? snapshot.whole_connection_status : "Current inputs unverified"} defaultOpen><button className="primary-button" disabled={!current || busy} onClick={() => { void operate("design"); }}>Run Design Check</button></SidebarGroup>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain><PersistentConnectionViewer><section className="viewer-card" data-engineering-fingerprint={snapshot?.engineering_fingerprint ?? ""}><strong role="status">{current ? "CURRENT BACKEND PREVIEW" : scene === null ? "WAITING FOR VALID GEOMETRY" : "LAST VALID PREVIEW — CURRENT INPUTS UNVERIFIED"}</strong>{!current && scene !== null ? <p>Previous action arrows are hidden. This is not current edited geometry or demand.</p> : null}{!finite ? <p role="alert">Enter finite numeric values.</p> : failure?.key === key ? <p role="alert">{failure.text}</p> : null}{scene === null ? <p>No valid geometry yet.</p> : <VisualizationPanel title="Stair Stringer Miter Connection" model={scene} selection={selection} onSelect={setSelection}/>}</section></PersistentConnectionViewer>
      {operationError !== null ? <p role="alert">{operationError}</p> : null}{design !== null ? <p role="status">{design.key === key && current ? "Current design check: " + design.response.whole_connection_status : "Design is stale; previous-case design is not current."}</p> : null}
      {snapshot === null ? null : <section aria-label="SSMC results"><h3>{current ? "Current demand / qualification" : "LAST VALID demand / qualification — not current"}</h3><p>Local N / V / M: {(["N", "V", "M"] as const).map(k => formatSSMCQuantity(snapshot.input[k], si)).join(" · ")}</p><p>Demand calculated — complete single-sided response and local resistance are not yet qualified.</p>
        <dl>{snapshot.statuses.map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{friendlyEnum(value)}</dd></div>)}</dl>
        <h3>Required missing coverage / failures</h3><ul>{[...snapshot.blockers, ...snapshot.evaluated_failures].map(code => <li key={code}>{friendlyEnum(code.replace(/^SSMC_/u, ""))}</li>)}</ul>
        {snapshot.groups.map(g => <WrenchCard key={g.group_id} title={friendlyEnum(g.group_id) + " — plate reference"} wrench={g.plate_wrench} si={si}/>)}
        <details><summary>Exact engineering trace / references / machine codes</summary><pre>{JSON.stringify(snapshot, null, 2)}</pre></details>
      </section>}
    </ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
