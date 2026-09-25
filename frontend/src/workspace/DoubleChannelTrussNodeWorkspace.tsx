import { viewerUnity } from "./unityRatio";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { DCTNArrangement, DCTNForm, DCTN3BMember as DCTNMember, DCTN3BRequest as DCTNRequest, DCTN3BResponse as DCTNResponse, DCTNShearPresentation } from "../api/dctnContracts";
import { convertDCTN3BUnits as convertDCTNUnits, loadDCTN3BDefaults as loadDCTNDefaults, requestDCTN3B as requestDCTN } from "../api/dctn3bClient";
import type { MultiRowQuantity } from "../api/multirowContracts";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { buildDCTN3BScene as buildDCTNScene } from "../visualization/dctnSceneModel";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import { ConnectionWorkspaceMain, ConnectionWorkspaceShell, ConnectionWorkspaceSidebar, PersistentConnectionViewer, SidebarGroup } from "./ConnectionWorkspaceShell";
import { clearDCTNQualification, dctnKey, editDCTNMember, useDCTN3BPreview as useDCTNPreview } from "./dctnWorkflow";
import { DCTN3BResults } from "./DCTN3BResults";
import { friendlyEnum } from "./presentation";
import { isIntentionalAbort } from "./previewWorkflow";
import "./dctnWorkspace.css";

const arrangements: readonly DCTNArrangement[] = ["VERTICAL_ONLY", "ONE_INCLINED", "TWO_INCLINED", "VERTICAL_ONE_INCLINED", "VERTICAL_TWO_INCLINED"];
type Update = (change: (request: DCTNRequest) => void, sourceOnly?: boolean) => void;

function QuantityField({ label, value, onChange, disabled = false }: { readonly label: string; readonly value: MultiRowQuantity; readonly onChange: (value: string) => void; readonly disabled?: boolean }) {
  return <label className="field-control"><span>{label}</span><span className="input-with-unit"><input aria-label={label} inputMode="decimal" disabled={disabled} value={value.value} onChange={e => { onChange(e.currentTarget.value); }}/><small>{disabled ? "N/A" : value.unit}</small></span></label>;
}
function MemberFields({ member, update, linked, presentation, selected, onSelect }: { readonly member: DCTNMember; readonly update: Update; readonly linked: boolean; readonly presentation: DCTNShearPresentation | undefined; readonly selected: boolean; readonly onSelect: () => void }) {
  const edit = (change: (member: DCTNMember) => void) => { update(next => { editDCTNMember(next, member.slot, change, linked); }); };
  const q = (label: string, value: MultiRowQuantity, change: (m: DCTNMember, raw: string) => void, disabled = false) => <QuantityField label={member.slot + " " + label} value={value} disabled={disabled} onChange={raw => { edit(m => { change(m, raw); }); }}/>;
  const sectionFields = (["length", "depth", "width", ...(member.section.form === "SOLID_RECTANGLE" ? [] : ["wall_or_web"]), ...(member.section.form === "W_I" ? ["flange_thickness"] : [])] as (keyof Omit<DCTNMember["section"], "form">)[]);
  const sectionLabel = (key: string) => key === "depth" ? (member.section.form === "W_I" ? "Depth" : "Gap depth") : key === "width" && member.section.form === "W_I" ? "Flange width" : key === "wall_or_web" ? (member.section.form === "RHS" ? "Wall thickness" : "Web thickness") : friendlyEnum(key);
  return <SidebarGroup title={member.slot + " incoming member"} summary={linked ? "D1/D2 section linked; placement and P/Qp/Qq independent" : "FRP primary member"} defaultOpen selected={selected} onSelect={onSelect}>
    <label className="field-control"><span>Section form</span><select aria-label={member.slot + " section form"} value={member.section.form} onChange={e => { const form = e.currentTarget.value as DCTNForm; edit(m => { m.section.form = form; }); }}><option value="RHS">Hollow rectangle</option><option value="SOLID_RECTANGLE">Solid rectangle</option><option value="W_I">W/I</option></select></label>
    <div className="field-grid">{sectionFields.map(k => <span key={k}>{q(sectionLabel(k), member.section[k], (m, raw) => { m.section[k].value = raw; })}</span>)}
      {q("Member Horizontal Location", member.chord_station, (m, raw) => { m.chord_station.value = raw; })}
      {q("Member Vertical Location", member.end_center_above_lower_web, (m, raw) => { m.end_center_above_lower_web.value = raw; })}
      {member.slot === "V" ? <p>Vertical direction: +Z (90°), fixed</p> : <label className="field-control"><span>Inclination angle (deg)</span><span className="input-with-unit"><input aria-label={member.slot + " Inclination angle (deg)"} inputMode="decimal" value={member.inclination_deg} onChange={e => { const raw = e.currentTarget.value; edit(m => { m.inclination_deg = raw; }); }}/><small>deg</small></span></label>}
      {q("Axial P", member.P, (m, raw) => { m.P.value = raw; })}
      {q(presentation?.Qp_label ?? "Shear p (Qp)", member.Qp, (m, raw) => { m.Qp.value = raw; })}
      {q(presentation?.Qq_label ?? "Shear q (Qq)", member.Qq, (m, raw) => { m.Qq.value = raw; })}
    </div>
    <p className="sidebar-note">X: horizontal chord · Y: cross-gap · Z: vertical. Inclination: 0° = +X, 90° = +Z, 180° = −X. P positive: tension along physical START → END. Cross-gap eccentricity is not automatically qualified. No hidden trim or placement repair.</p>
    {member.section.form === "W_I" ? <p className="sidebar-note">W/I mapping: Major shear → Qq; Minor shear → Qp.</p> : presentation?.major_component === null ? <p className="sidebar-note">Equal axes: use Shear p / Shear q; no unique major/minor axis.</p> : null}
    <label className="field-control"><span>Bolt rows along member axis</span><select aria-label={member.slot + " Bolt rows along member axis"} value={member.pattern.rows} onChange={e => { const count = Number(e.currentTarget.value); edit(m => { m.pattern.rows = count; }); }}>{[1, 2, 3].map(n => <option key={n} value={n}>{n}</option>)}</select></label>
    <div className="field-grid">{q("First bolt row from member end", member.pattern.first_from_start, (m, raw) => { m.pattern.first_from_start.value = raw; })}{q("Row pitch", member.pattern.pitch, (m, raw) => { m.pattern.pitch.value = raw; }, member.pattern.rows === 1)}{member.section.form === "W_I" ? q("W/I transverse offset magnitude", member.pattern.wi_offset, (m, raw) => { m.pattern.wi_offset.value = raw; }) : null}</div>
    <p className="sidebar-note">One physical position across each row. W/I uses two independent centro-symmetric side bolts; RHS/SRS use one common shaft per row.</p>
  </SidebarGroup>;
}

function MemberQualificationFields({ request, update }: { readonly request: DCTNRequest; readonly update: Update }) {
  return <>{request.members.flatMap(member => (["material_source_reference", "local_path_source_reference"] as const).map(field => <label className="field-control" key={member.slot + field}><span>{member.slot + " " + friendlyEnum(field)}</span><input aria-label={member.slot + " " + field} value={member[field]} onChange={e => { const raw = e.currentTarget.value; update(n => { editDCTNMember(n, member.slot, m => { m[field] = raw; }, false); }, true); }}/></label>))}</>;
}

export function DoubleChannelTrussNodeWorkspace() {
  const [initial, setInitial] = useState<DCTNRequest | null>(null), [error, setError] = useState<string | null>(null), [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); let disposed = false;
    void loadDCTNDefaults("VERTICAL_ONLY", false, controller.signal).then(value => { if (!disposed) { setInitial(value); setError(null); } }).catch((e: unknown) => { if (!disposed && !isIntentionalAbort(e)) setError(e instanceof Error ? e.message : "DCTN defaults unavailable."); });
    return () => { disposed = true; controller.abort(); };
  }, [retry]);
  if (initial === null) return <section className="source-card"><h2>Double-Channel Truss Node</h2>{error === null ? <p role="status">Loading backend defaults…</p> : <div role="alert">{error}<button onClick={() => { setRetry(v => v + 1); }}>Retry defaults</button></div>}</section>;
  return <DCTNEditor initial={initial}/>;
}

function DCTNEditor({ initial }: { readonly initial: DCTNRequest }) {
  const [request, setRequest] = useState(initial), [revision, setRevision] = useState(0);
  const [design, setDesign] = useState<{ key: string; response: DCTNResponse } | null>(null);
  const [error, setError] = useState<string | null>(null), [busy, setBusy] = useState(false), [loading, setLoading] = useState(false);
  const [selection, setSelection] = useState<SceneSelection>({ kind: "MEMBER", id: "V" });
  const [allMemberActions, setAllMemberActions] = useState(false);
  const sequence = useRef(0), active = useRef<AbortController | null>(null);
  useEffect(() => () => { sequence.current += 1; active.current?.abort(); }, []);
  const update: Update = useCallback((change, sourceOnly = false) => {
    sequence.current += 1; active.current?.abort(); setBusy(false); setLoading(false);
    setRequest(previous => { const next = structuredClone(previous); change(next); if (!sourceOnly) clearDCTNQualification(next); return next; });
    setRevision(v => v + 1); setError(null);
  }, []);
  const preview = useDCTNPreview(request, revision);
  const current = preview.current && !loading;
  const snapshot = preview.response?.result.preview ?? null;
  const scene = useMemo(() => {
    if (snapshot === null) return null;
    const model = buildDCTNScene(snapshot);
    if (!current) return { ...model, appliedArrows: [], positiveArrows: [] };
    if (allMemberActions) return model;
    const selectedMember = selection.kind === "MEMBER" ? selection.id : null;
    return { ...model, appliedArrows: model.appliedArrows.filter(arrow => selectedMember !== null && arrow.referencePointId === selectedMember + ":START") };
  }, [snapshot, current, allMemberActions, selection]);
  const key = dctnKey(request);
  const stale = design !== null && (design.key !== key || !current);
  const result = !stale ? design?.response.result.design ?? null : null;
  const reviseConfiguration = async (arrangement: DCTNArrangement | null, si: boolean) => {
    const serial = ++sequence.current; active.current?.abort(); const controller = new AbortController(); active.current = controller;
    setLoading(true); setBusy(false); setError(null);
    try {
      let next: DCTNRequest;
      if (arrangement === null) next = await convertDCTNUnits(request, si, controller.signal);
      else {
        const defaults = await loadDCTNDefaults(arrangement, si, controller.signal);
        next = { ...structuredClone(request), arrangement, members: defaults.members.map(m => structuredClone(request.members.find(old => old.slot === m.slot) ?? m)) };
        const d1 = next.members.find(m => m.slot === "D1");
        if (d1 !== undefined && !request.members.some(m => m.slot === "D2")) next.members = next.members.map(m => m.slot === "D2" ? { ...m, section: { ...structuredClone(d1.section), length: m.section.length } } : m);
        clearDCTNQualification(next);
      }
      if (serial === sequence.current) {
        setRequest(next);
        setSelection(currentSelection => currentSelection.kind === "MEMBER" && next.members.some(member => member.slot === currentSelection.id) ? currentSelection : { kind: "MEMBER", id: next.members[0]?.slot ?? "V" });
        setRevision(v => v + 1);
      }
    } catch (e) { if (serial === sequence.current && !isIntentionalAbort(e)) setError(e instanceof Error ? e.message : "Configuration unavailable."); }
    finally { if (serial === sequence.current) setLoading(false); }
  };
  const run = async () => {
    const serial = ++sequence.current; active.current?.abort(); const controller = new AbortController(); active.current = controller; setBusy(true); setError(null);
    try { const response = await requestDCTN("design-check", request, controller.signal); if (serial === sequence.current) setDesign({ key, response }); }
    catch (e) { if (serial === sequence.current && !isIntentionalAbort(e)) setError(e instanceof Error ? e.message : "Design unavailable."); }
    finally { if (serial === sequence.current) setBusy(false); }
  };
  return <ConnectionWorkspaceShell className="dctn-workspace" banner={<section className="stage-banner"><h2>Double-Channel Truss Node</h2><p>DCTN-3B-RC1 · primary FRP members · independent hardware · no connector body</p></section>}>
    <ConnectionWorkspaceSidebar ariaLabel="DCTN inputs">
      <SidebarGroup title="Arrangement / units" summary="Five arrangements, one derived gap" defaultOpen>
        <label className="field-control"><span>Unit system</span><select aria-label="DCTN unit system" disabled={loading} value={request.unit_system} onChange={e => { void reviseConfiguration(null, e.currentTarget.value === "SI"); }}><option value="US">U.S. Units</option><option value="SI">S.I. Units</option></select></label>
        <label className="field-control"><span>Arrangement</span><select aria-label="DCTN arrangement" disabled={loading} value={request.arrangement} onChange={e => { void reviseConfiguration(e.currentTarget.value as DCTNArrangement, request.unit_system === "SI"); }}>{arrangements.map(a => <option key={a} value={a}>{friendlyEnum(a)}</option>)}</select></label>
        <div className="sidebar-note"><strong>Member local axes / actions</strong><p>P = axial along local u · Qp = in-plane shear along local p · Qq = cross-gap shear along local q. Major/minor names follow the current backend section-axis authority; stored Qp/Qq never swap.</p><p><strong>Member Horizontal Location:</strong> along the Channel/chord axis from the DCTN node datum. <strong>Member Vertical Location:</strong> section-center height relative to the lower usable Channel-web line.</p></div>
      </SidebarGroup>
      <SidebarGroup title="Mirrored Channel chord pair" summary="One common profile / source" defaultOpen><div className="field-grid">{(["length", "depth", "flange_width", "web_thickness", "flange_thickness"] as const).map(k => <QuantityField key={k} label={"Channel " + friendlyEnum(k)} value={request.channel[k]} onChange={raw => { update(n => { n.channel[k].value = raw; }); }}/>)}</div></SidebarGroup>
      {request.members.map(m => <MemberFields key={m.slot} member={m} update={update} linked={m.slot !== "V" && request.members.filter(v => v.slot !== "V").length === 2} presentation={JSON.stringify(m.section) === JSON.stringify(snapshot?.input.members.find(item => item.slot === m.slot)?.section) ? snapshot?.demand.members.find(item => item.member_id === m.slot)?.presentation : undefined} selected={selection.kind === "MEMBER" && selection.id === m.slot} onSelect={() => { setSelection({ kind: "MEMBER", id: m.slot }); }}/>)}
      <SidebarGroup title="Common hardware" summary="Geometry is not strength qualification" defaultOpen><div className="field-grid">{(["diameter", "hole_diameter"] as const).map(k => <QuantityField key={k} label={"Bolt " + friendlyEnum(k)} value={request.fastener[k]} onChange={raw => { update(n => { n.fastener[k].value = raw; }); }}/>)}</div>
        <details><summary>Head, nut and exterior washers</summary><div className="field-grid">{(["washer_diameter", "washer_thickness", "head_across_flats", "head_height", "nut_across_flats", "nut_height", "end_extension"] as const).map(k => <QuantityField key={k} label={"Hardware " + friendlyEnum(k)} value={request.fastener.hardware[k]} onChange={raw => { update(n => { n.fastener.hardware[k].value = raw; }); }}/>)}</div></details>
        <label className="field-control"><span>Thread location</span><select aria-label="DCTN thread location" value={request.fastener.threads_excluded ? "EXCLUDED" : "INCLUDED"} onChange={e => { const excluded = e.currentTarget.value === "EXCLUDED"; update(n => { n.fastener.threads_excluded = excluded; }); }}><option value="EXCLUDED">Threads excluded</option><option value="INCLUDED">Threads included</option></select></label>
        <label><input type="checkbox" checked={request.fastener.snug_tight} onChange={e => { const checked = e.currentTarget.checked; update(n => { n.fastener.snug_tight = checked; }); }}/>Snug-tight installation</label>
      </SidebarGroup>
      <SidebarGroup title="Advanced" summary="Source text does not grant qualification">
        <details><summary>Engineering qualification / source authority</summary>
          <label className="field-control"><span>Channel material source reference</span><input aria-label="Channel material source reference" value={request.channel.material_source_reference} onChange={e => { const raw = e.currentTarget.value; update(n => { n.channel.material_source_reference = raw; }, true); }}/></label>
          <label className="field-control"><span>Shared Channel local-path source reference</span><input aria-label="Shared Channel local-path source reference" value={request.shared_channel_source_reference} onChange={e => { const raw = e.currentTarget.value; update(n => { n.shared_channel_source_reference = raw; }, true); }}/></label>
          <label className="field-control"><span>Hardware strength / installation source</span><input aria-label="Hardware source reference" value={request.fastener.source_reference} onChange={e => { const raw = e.currentTarget.value; update(n => { n.fastener.source_reference = raw; }, true); }}/></label>
          <MemberQualificationFields request={request} update={update}/>
          <p>Complete transverse response production registry: empty. Typed references cannot activate sharing, contact, tension, prying or resistance.</p>
        </details>
      </SidebarGroup>
      <SidebarGroup title="Model / design status" summary={result?.whole_connection_status ?? "Not checked"} defaultOpen><p>{current ? "Current backend preview" : "Current inputs unverified"}</p><p>Global Channel/member/truss design is outside this local connection.</p><button className="primary-button" disabled={!current || busy || loading} onClick={() => { void run(); }}>{busy ? "Checking…" : "Run Design Check"}</button></SidebarGroup>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain><PersistentConnectionViewer unity={viewerUnity("dctn", design?.response.result.design, { stale, checking: busy, error, previewCurrent: current })}><section className="viewer-card" data-engineering-fingerprint={snapshot?.fingerprint ?? ""}><div role="status"><strong>{current ? "CURRENT BACKEND PREVIEW" : scene === null ? "WAITING FOR VALID GEOMETRY" : "LAST VALID PREVIEW — CURRENT INPUTS UNVERIFIED"}</strong>{!current && scene !== null ? <p>Previous action arrows are hidden. This is not the current edited geometry.</p> : null}</div>{preview.error !== null ? <p role="alert">{preview.error}</p> : null}{scene === null ? <p>No valid backend geometry yet.</p> : <><label className="scene-toggle dctn-action-overlay"><input type="checkbox" aria-label="All member actions" checked={allMemberActions} onChange={event => { setAllMemberActions(event.currentTarget.checked); }}/><span>All member actions</span></label><VisualizationPanel title="Double-Channel Truss Node" model={scene} selection={selection} onSelect={setSelection} actionSourceLabel=""/></>}</section></PersistentConnectionViewer>
      {error !== null ? <p role="alert">{error}</p> : null}{stale ? <p role="status">Design is stale; previous-case resistance checks are hidden.</p> : null}
      {snapshot === null ? null : <DCTN3BResults snapshot={snapshot} result={result} current={current}/>}
    </ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
