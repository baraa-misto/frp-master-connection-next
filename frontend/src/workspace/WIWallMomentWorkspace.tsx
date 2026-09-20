import { ConnectorBodyMaterialControl, ConnectorBodyMaterialResult } from "./connectorBodyMaterial";
import { useConnectorBodyMaterial } from "./useConnectorBodyMaterial";
import { useEffect, useMemo, useRef, useState } from "react";
import type { MultiRowQuantity } from "../api/multirowContracts";
import { designWIWallMoment } from "../api/wiWallMomentClient";
import type { WIWallMomentDesign, WIWallMomentRequest, WIWallMomentResponse, WallMomentAngle, WallMomentVector, WallMomentWrench } from "../api/wiWallMomentContracts";
import { loadWIWallMomentBenchmark } from "../fixtures/wiWallMomentBenchmarks";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import { buildWIWallMomentScene } from "../visualization/wiWallMomentSceneModel";
import { ConnectionWorkspaceMain, ConnectionWorkspaceShell, ConnectionWorkspaceSidebar, PersistentConnectionViewer, SidebarGroup } from "./ConnectionWorkspaceShell";
import { formatDisplayQuantity, friendlyEnum } from "./presentation";
import { isIntentionalAbort } from "./previewWorkflow";
import { useWIWallMomentPreview } from "./wiWallMomentWorkflow";
import { wallMomentVisibleFailures } from "./wiWallMomentFailures";
import "./wiWallMomentWorkspace.css";

function validate(value: unknown): boolean {
  if (value !== null && typeof value === "object") {
    if ("value" in value) return typeof value.value === "string" && value.value.trim() !== "" && Number.isFinite(Number(value.value));
    return Object.values(value).every(validate);
  }
  return true;
}
// Presentation only: native quantities and fingerprints remain unchanged.
function display(value: MultiRowQuantity, system: "US_CUSTOMARY" | "SI"): string {
  const momentFactor: Readonly<Record<string, number>> = { "N-mm": 1, "kN-mm": 1000, "kip-in": 112984.8290276167 };
  const factor = momentFactor[value.unit];
  if (factor === undefined) return formatDisplayQuantity(value,system);
  const divisor = system === "US_CUSTOMARY" ? 112984.8290276167 : 1000;
  return `${Number((Number(value.value)*factor/divisor).toPrecision(7)).toString()} ${system === "US_CUSTOMARY" ? "kip-in" : "kN-mm"}`;
}
function Wrench({ title, value, system }: { readonly title: string; readonly value: WallMomentWrench; readonly system: "US_CUSTOMARY" | "SI" }) {
  const text = (v: WallMomentVector) => [v.x,v.y,v.z].map(q => display(q,system)).join(" · ");
  return <dl className="diagnostic-list"><div><dt>{title} — reference</dt><dd>{text(value.reference)}</dd></div><div><dt>Force (three signed components)</dt><dd>{text(value.force)}</dd></div><div><dt>Moment (three signed components)</dt><dd>{text(value.moment)}</dd></div></dl>;
}
export function WIWallMomentWorkspace() {
  const [request,setRequest] = useState(() => loadWIWallMomentBenchmark("US_CUSTOMARY"));
  const [revision,setRevision] = useState(0);
  const [immediate,setImmediate] = useState(true);
  const [design,setDesign] = useState<{ revision: number; value: WIWallMomentResponse<WIWallMomentDesign> } | null>(null);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState<string | null>(null);
  const [selection,setSelection] = useState<SceneSelection>({ kind: "MEMBER",id:"TOP_FLANGE_ANGLE" });
  const sequence = useRef(0);
  const abort = useRef<AbortController | null>(null);
  useEffect(() => () => { sequence.current += 1; abort.current?.abort(); },[]);
  const update = (change: (next: WIWallMomentRequest) => void) => { sequence.current += 1; abort.current?.abort(); setBusy(false); setRequest(old => { const next = structuredClone(old); change(next); return next; }); setRevision(r => r+1); setImmediate(false); };
  const load = (system: "US_CUSTOMARY" | "SI") => { update(next => Object.assign(next,loadWIWallMomentBenchmark(system))); setImmediate(true); setDesign(null); setError(null); };
  const invalid = validate(request) ? null : "Enter finite decimal values before previewing.";
  const preview = useWIWallMomentPreview(request,revision,immediate,invalid);
  const result = preview.response?.result ?? null;
  const model = useMemo(() => result === null ? null : buildWIWallMomentScene(result),[result]);
  const stale = design !== null && design.revision !== revision;
  const current = design === null || stale ? null : design.value.result;
  const failures = current === null ? [] : wallMomentVisibleFailures(current);
  const governing = current === null ? "Not current" : current.native_governing_check_ids.length === 0 ? "None selected by the native group-mode engine; see evaluated failures below." : current.native_governing_check_ids.join(", ");
  const bodyMaterial = useConnectorBodyMaterial("wi-beam-concrete-wall-moment", request, revision, () => {
    sequence.current += 1; abort.current?.abort(); setBusy(false); setDesign(null); setError(null);
  });
  const run = async () => {
    if (bodyMaterial.material === "SS316") { await bodyMaterial.run(); return; }
    const serial = ++sequence.current;
    abort.current?.abort(); const controller = new AbortController(); abort.current = controller;
    setBusy(true); setError(null);
    try { const value = await designWIWallMoment(request,controller.signal); if (serial === sequence.current) setDesign({revision,value}); }
    catch (caught) { if (serial === sequence.current && !isIntentionalAbort(caught)) setError(caught instanceof Error ? caught.message : "Design request failed."); }
    finally { if (serial === sequence.current) setBusy(false); }
  };
  const field = (title: string, quantity: MultiRowQuantity, change: (next: WIWallMomentRequest, value: string) => void) => <label className="field-control"><span>{title}</span><span className="input-with-unit"><input aria-label={title} inputMode="decimal" value={quantity.value} onChange={e => { const value=e.currentTarget.value; update(next => { change(next,value); }); }} /><small>{quantity.unit}</small></span></label>;
  const family = (key: "top" | "positive_web", title: string) => {
    const partner = key === "top" ? "bottom" : "negative_web";
    const angle = request[key];
    const set = (change: (next: WallMomentAngle) => void) => { update(next => { change(next[key]); next[partner] = structuredClone(next[key]); }); };
    const length = (label: string, quantity: MultiRowQuantity, change: (next: WallMomentAngle, raw: string) => void) => <label className="field-control"><span>{label}</span><span className="input-with-unit"><input aria-label={`${title} ${label}`} inputMode="decimal" value={quantity.value} onChange={e => { const raw=e.currentTarget.value; set(next => { change(next,raw); }); }} /><small>{quantity.unit}</small></span></label>;
    const pattern = (k: "member_pattern" | "support_pattern", group: string) => <>{(["across","along"] as const).map(count => <label className="field-control" key={count}><span>{friendlyEnum(count)} count</span><input aria-label={`${title} ${group} ${count} count`} type="number" min="1" step="1" value={angle[k][count]} onChange={e => { const raw=Number(e.currentTarget.value); set(next => { next[k][count]=raw; }); }} /></label>)}{(["gauge","pitch","center"] as const).map(dim => <span key={dim}>{length(`${group} ${dim === "center" ? "centroid distance" : dim}`,angle[k][dim],(next,raw) => { next[k][dim].value=raw; })}</span>)}</>;
    return <SidebarGroup title={title} summary="Locked symmetric pair" defaultOpen>
      <div className="field-grid">{(Object.keys(angle.geometry) as (keyof WallMomentAngle["geometry"])[]).filter(k => k !== "heel_end_reliefs").map(k => <span key={k}>{length(friendlyEnum(k),angle.geometry[k],(next,raw) => { (next.geometry[k]).value=raw; })}</span>)}</div>
      <fieldset className="wall-moment-input-group"><legend>Member bolts</legend><div className="field-grid">
        {pattern("member_pattern","Member bolts")}
        {length("Bolt diameter",angle.fastener.bolt_diameter,(next,raw) => { next.fastener.bolt_diameter.value=raw; })}
        {length("Hole diameter",angle.fastener.hole_diameter,(next,raw) => { next.fastener.hole_diameter.value=raw; })}
        <label className="field-control wall-moment-full-width"><span>Thread condition</span><select aria-label={`${title} Thread condition`} value={angle.fastener.thread_condition} onChange={e => { const v=e.currentTarget.value as "INCLUDED" | "EXCLUDED"; set(next => {next.fastener.thread_condition=v;}); }}><option value="EXCLUDED">Threads excluded</option><option value="INCLUDED">Threads included</option></select></label>
      </div></fieldset>
      <fieldset className="wall-moment-input-group"><legend>Wall anchors</legend><div className="field-grid">
        {pattern("support_pattern","Wall anchors")}
        {length("Anchor diameter",angle.anchors.nominal_diameter,(next,raw) => { next.anchors.nominal_diameter.value=raw; })}
        {length("Anchor hole diameter",angle.anchors.hole_diameter,(next,raw) => { next.anchors.hole_diameter.value=raw; })}
        {length("Anchor embedment",angle.anchors.specified_embedment,(next,raw) => { next.anchors.specified_embedment.value=raw; })}
      </div></fieldset>
      {(["connector_source_reference","attachment_source_reference"] as const).map(k => {
        const label = k === "connector_source_reference" ? "Qualified connector source reference" : "Qualified member-attachment source reference";
        return <label className="field-control wall-moment-source-field" key={k}><span>{label}</span><input aria-label={`${title} ${label}`} value={angle[k]} onChange={e => {const v=e.currentTarget.value;set(next => {next[k]=v;});}} /></label>;
      })}
      <p className="sidebar-note">FRP only · Locked ICE material. F593 numerical strength remains source-pending. Source references must resolve to exact server-controlled qualified packages; no test source is available here.</p>
    </SidebarGroup>;
  };
  return <ConnectionWorkspaceShell className="wi-wall-moment-workspace" banner={<section className="workspace-banner"><div><p className="eyebrow">Stage 4.2 · RC1-R7</p><h2>W/I Beam to Concrete Wall Moment Connection</h2><p>Complete component wrenches · Four FRP angles · External anchor/concrete design required</p></div><div className="benchmark-actions"><button onClick={() => {load("US_CUSTOMARY");}}>Load 4.2 U.S.</button><button onClick={() => {load("SI");}}>Load 4.2 SI</button></div></section>}>
    <ConnectionWorkspaceSidebar ariaLabel="W/I wall-moment engineering properties">
      <ConnectorBodyMaterialControl material={bodyMaterial.material} onChange={bodyMaterial.choose} />
      <SidebarGroup title="Beam / Wall" summary="One W/I beam · finite wall" defaultOpen><div className="field-grid">{(["depth","flange_width","web_thickness","flange_thickness","display_length_each_side"] as const).map(k => <span key={k}>{field(`Beam ${friendlyEnum(k)}`,request.beam[k],(next,v) => {next.beam[k].value=v;})}</span>)}{field("Beam-wall gap",request.gap,(next,v) => {next.gap.value=v;})}{(Object.keys(request.wall) as (keyof WIWallMomentRequest["wall"])[]).map(k => <span key={k}>{field(`Wall ${friendlyEnum(k)}`,request.wall[k],(next,v) => {next.wall[k].value=v;})}</span>)}</div></SidebarGroup>
      <SidebarGroup title="Joint actions" summary="Signed P / V / structural M" defaultOpen><div className="field-grid">{field("Axial force P_L",request.actions.axial,(next,v) => {next.actions.axial.value=v;})}{field("Major shear V_V",request.actions.major_shear,(next,v) => {next.actions.major_shear.value=v;})}{field("Structural major moment M_T",request.actions.structural_major_moment,(next,v) => {next.actions.structural_major_moment.value=v;})}</div><p className="sidebar-note">At the negative beam end, physical right-hand moment = − structural moment. All component/local moments remain in the trace. No minor shear, minor moment or user torsion.</p></SidebarGroup>
      {family("top","Flange angles")}{family("positive_web","Web clip angles")}
      <SidebarGroup title="Model / design status" summary={current?.status ?? (stale ? "Stale" : "Not checked")} defaultOpen><p role="status">{preview.state}</p><p>Internal design: {current?.status ?? (stale ? "Stale — Run Design Check" : "Not checked")}</p><p>Governing native group: {governing}</p><p>Whole connection: External anchor/concrete design required</p><button className="primary-button" disabled={bodyMaterial.busy || busy || !preview.current || preview.response?.design_check_ready !== true} onClick={() => {void run();}}>{busy ? "Running design check…" : "Run Design Check"}</button></SidebarGroup>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain><ConnectorBodyMaterialResult state={bodyMaterial} /><div className="stage42-viewer-region"><PersistentConnectionViewer>{model === null ? <p>No valid canonical model yet.</p> : <VisualizationPanel model={model} title="W/I beam to concrete wall moment connection" selection={selection} onSelect={setSelection} contactSelectionLabel="Selected Stage 4.2 component" actionSourceLabel="Beam-end structural action" appliedActionInputValues={{FX:request.actions.axial.value,FY:"0",FZ:request.actions.major_shear.value,MX:"0",MY:request.actions.structural_major_moment.value,MZ:"0"}} onAppliedActionValueChange={(component,v) => {if (component === "FX" || component === "FZ" || component === "MY") update(next => {next.actions[component === "FX" ? "axial" : component === "FZ" ? "major_shear" : "structural_major_moment"].value=v;});}} />}</PersistentConnectionViewer></div>
      {preview.error === null ? null : <div className="error-banner" role="alert">{preview.error}<button onClick={preview.retry}>Retry preview</button></div>}{error === null ? null : <div role="alert">{error}</div>}{stale ? <div className="stale-banner" role="status">Design results are stale. Current inputs need an explicit Run Design Check.</div> : null}
      {result === null ? null : <section className="tee-results-grid" aria-label="Stage 4.2 engineering trace"><article className="source-card"><h3>Whole-wall handoff / reaction</h3>{result.wall_handoff === null ? null : <Wrench title="Connector on wall" value={result.wall_handoff} system={request.unit_system} />}{result.wall_reaction === null ? null : <Wrench title="Wall on connection" value={result.wall_reaction} system={request.unit_system} />}<p>Inherited algebraic and native core/group equilibrium proofs: {result.equilibrium?.proof_passed ? "Passed" : "Unavailable"}</p><p>No anchor forces or capacities are fabricated.</p><p>Structural wall moment: {result.equilibrium === null ? "Unavailable" : display(result.equilibrium.structural_major_moment,request.unit_system)}</p><details><summary>Slice 5 complete component resultants</summary><pre>{JSON.stringify(result.slice5,null,2)}</pre></details><details><summary>Qualified source binding plans — no resistance in preview</summary><pre>{JSON.stringify(result.source_plans,null,2)}</pre></details></article>{result.connectors.map((c,i) => <article className="source-card" key={c.connector_id}><h3>{friendlyEnum(c.connector_id)}</h3><Wrench title="Member interface — A/B/C" value={c.core.request.member_action} system={request.unit_system}/><details><summary>Heel, wall group and demand trace</summary><Wrench title="Heel — A/B/C" value={c.core.heel} system={request.unit_system}/><Wrench title="Wall group — L/V/T" value={c.support_global} system={request.unit_system}/><pre>{JSON.stringify(c.web_demand ?? c.flange_demand,null,2)}</pre></details><p>Connector source: {current?.connector_results[i]?.status ?? "Not checked"}</p><p>Member-attachment source: {current?.attachment_results[i]?.check.status ?? "Not checked"}</p><p>Instep check plan: {c.instep_plan_status}</p><p>Core fingerprint: {c.core.fingerprint}</p></article>)}<article className="qualification-banner"><div><h3>Engineering review / qualification required</h3><p>{result.disclaimer}</p><p>Stiffness, rotation capacity and full-strength classification: not evaluated.</p><p>Engineering fingerprint: {result.engineering_fingerprint}</p></div></article></section>}
      {current === null ? null : <section aria-label="Design-check trace">
        <h3>Required evaluated failures</h3><p>{current.status_reason}</p>
        <p>These native records support the returned status. This display does not reselect the governing check.</p>
        <p className="wall-moment-result-identity">Design input fingerprint: {design?.value.engineering_fingerprint}<br/>Design result fingerprint: {design?.value.result_fingerprint}</p>
        {failures.length === 0 ? <p>No evaluated failures returned for this design.</p> : <div className="wall-moment-failure-table"><table><thead><tr><th>Native check / component</th><th>Status / native reason</th><th>Utilization</th><th>Demand / resistance</th></tr></thead><tbody>{failures.map((c,i) => <tr key={`${c.checkId}:${c.component}:${String(i)}`}><td>{c.checkId}<br/><small>{friendlyEnum(c.component)}</small></td><td>FAIL<br/>{c.reason}</td><td>{c.utilization === null ? "—" : Number(c.utilization).toPrecision(6)}</td><td>{c.demand === null ? "—" : formatDisplayQuantity(c.demand,request.unit_system)} / {c.resistance === null ? "—" : formatDisplayQuantity(c.resistance,request.unit_system)}<details className="wall-moment-native-record"><summary>Exact native record</summary><pre>{JSON.stringify(c.nativeRecord,null,2)}</pre></details></td></tr>)}</tbody></table></div>}
        <h3>Missing sources remain visible</h3>{current.missing_sources.map(s => <p key={s}>{s}</p>)}<details><summary>Complete native calculation / source / applicability trace</summary><pre>{JSON.stringify(current,null,2)}</pre></details>
      </section>}
    </ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
