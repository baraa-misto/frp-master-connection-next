import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { calculateHybrid, downloadHybrid, enteredCase, hybridPost, sourceExample } from "../api/hybridWorkflow";
import type { HybridCase, HybridComparison, HybridGeometry, HybridInputs, HybridQuantity, HybridResponse } from "../api/hybridWorkflow";
import type { TwoBoltRequest } from "../api/directTwoBolt";
import type { SingleBoltPreviewRequest } from "../api/contracts";
import type { MultiRowConnectionRequest } from "../api/multirowContracts";
import { buildMAT1DesignEnvelope } from "../api/mat1Transport";
import { MAT1MaterialsPanel } from "../features/MAT1MaterialsPanel";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { buildMultiRowSceneModel } from "../visualization/sceneModel";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import { DirectBoltAlignment } from "../features/DirectBoltAlignment";
import { ConnectionWorkspaceMain, ConnectionWorkspaceShell, ConnectionWorkspaceSidebar, PersistentConnectionViewer, SidebarGroup } from "./ConnectionWorkspaceShell";
import type { UnityView } from "./unityRatio";
import { formatUnityPercent } from "./unityRatio";
import "./directHybridWorkspace.css";

const GEOMETRY_LABELS: Record<Exclude<keyof HybridGeometry, "phi">, string> = { vertical_bolt_pitch: "Actual bolt spacing", xb: "Brace end Xb", xc: "Receiving flange Xc", brace_near_v_edge_distance: "Near B1 transverse distance", brace_leg: "Equal Angle leg width", column_flange: "Receiving I flange width", brace_thickness: "Angle thickness", column_thickness: "I flange thickness", diameter: "Bolt diameter", hole: "Declared hole diameter" };
const COMPONENTS = ["P / Fx", "Sketch V / Fy", "Out-of-plane Fz", "Moment Mx", "Moment My", "Moment Mz"];
function ValueInput({ label, quantity, onChange }: { readonly label: string; readonly quantity: HybridQuantity; readonly onChange: (q: HybridQuantity) => void }) {
  return <label className="field-control"><span>{label}</span><div className="hybrid-quantity"><input aria-label={label} inputMode="decimal" value={quantity.value} onChange={(event) => { onChange({ ...quantity, value: event.currentTarget.value }); }} /><span>{quantity.unit}</span></div></label>;
}
function CaseEditor({ value, basis, onChange, onRemove }: { readonly value: HybridCase; readonly basis: string; readonly onChange: (c: HybridCase) => void; readonly onRemove: () => void }) {
  const labels = value.frame === "GLOBAL" ? ["Global Fx", "Global Fy", "Global Fz", "Global Mx", "Global My", "Global Mz"] : COMPONENTS;
  return <fieldset className="hybrid-case"><legend>{basis} case</legend>
    <label className="field-control">Case ID<input aria-label={basis + " case ID"} value={value.case_id} onChange={(e) => { onChange({ ...value, case_id: e.currentTarget.value }); }} /></label>
    <label className="field-control">Action frame<select aria-label={basis + " action frame"} value={value.frame} onChange={(e) => { onChange({ ...value, frame: e.currentTarget.value as HybridCase["frame"] }); }}><option value="DIRECT_P_SKETCH_V_CENTROID">P / sketch V=-n at centroid</option><option value="DIRECT_P_POSITIVE_N_CENTROID">P / backend +n at centroid</option><option value="GLOBAL">Global (RHM evaluation unavailable)</option></select></label>
    <div className="field-grid">{value.components.map((q, i) => <ValueInput key={COMPONENTS[i]} label={basis + " " + (value.frame === "DIRECT_P_POSITIVE_N_CENTROID" && i === 1 ? "Transverse +n / Fy" : String(labels[i]))} quantity={q ?? { value: "", unit: i < 3 ? "kip" : "kip-in" }} onChange={(next) => { const components = [...value.components] as HybridCase["components"]; components[i] = next.value === "" ? null : next; onChange({ ...value, components }); }} />)}</div>
    <details><summary>Action reference point</summary>{value.reference.map((q, i) => <ValueInput key={i} label={basis + " reference " + String(i + 1)} quantity={q} onChange={(next) => { const reference = [...value.reference] as HybridCase["reference"]; reference[i] = next; onChange({ ...value, reference }); }} />)}</details>
    <button type="button" onClick={onRemove}>Remove {basis} case</button>
  </fieldset>;
}
function Governing({ label, row }: { readonly label: string; readonly row: HybridComparison | null }) {
  return <p><strong>{label}: </strong>{row === null ? "NOT EVALUATED" : `${row.mechanism} · ${row.case_id} · UR ${String(row.ratio)}`}</p>;
}

function NativeInputs({ value, onChange }: { readonly value: TwoBoltRequest; readonly onChange: (next: TwoBoltRequest) => void }) {
  const physical = value.legacy.physical_connection;
  if (physical === undefined) return <p>The current physical connection is missing. Return to native inputs to define it.</p>;
  const publish = (legacy: MultiRowConnectionRequest, extra: Partial<TwoBoltRequest> = {}) => {
    onChange({ ...value, ...extra, legacy, ...(value.material_request === undefined ? {} : { material_request: { ...value.material_request as object, legacy_request: legacy } }) });
  };
  const change = (nextPhysical: SingleBoltPreviewRequest, layers = value.legacy.layers) => {
    const legacy = { ...value.legacy, physical_connection: nextPhysical, layers };
    publish(legacy);
  };
  const template = physical.geometry_template;
  return <><p>Current native MAT1/F593 settings are retained. Native geometry and actions below are freshly submitted; source SUPPORT data is not substituted.</p>
    {(["bolt_diameter", "pitch", "loaded_boundary_to_row_1_distance", "negative_side_distance", "positive_side_distance"] as const).map((key) => <ValueInput key={key} label={"Native " + key.replaceAll("_", " ")} quantity={value.legacy[key]} onChange={(next) => {
      publish({ ...value.legacy, [key]: next, ...(key === "bolt_diameter" ? { physical_connection: { ...physical, bolt_diameter: next } } : {}) }, key === "pitch" ? { spacing: { value: next.value, unit: next.unit as "in" | "mm" } } : {});
    }} />)}
    {template === undefined ? null : <><ValueInput label="Native brace end distance e1" quantity={template.bolt_to_brace_end_distance} onChange={(q) => {
      publish({ ...value.legacy, unloaded_end_e1: q, physical_connection: { ...physical, geometry_template: { ...template, bolt_to_brace_end_distance: q } } });
    }} /><ValueInput label="Native brace to column angle" quantity={{ value: template.brace_to_column_directed_angle_deg, unit: "deg" }} onChange={(q) => { change({ ...physical, geometry_template: { ...template, brace_to_column_directed_angle_deg: q.value } }); }} /><ValueInput label="Native declared hole diameter" quantity={value.hole_diameter ?? template.hole_diameter} onChange={(q) => { publish(value.legacy, { hole_diameter: { value: q.value, unit: q.unit as "in" | "mm" } }); }} /></>}
    {physical.joint_assembly.members.map((member, index) => <fieldset key={member.id}><legend>{member.label}</legend>{Object.entries(member.section).filter(([, q]) => typeof q === "object").map(([name, q]) => <ValueInput key={name} label={member.label + " " + name.replaceAll("_", " ")} quantity={q as HybridQuantity} onChange={(nextQ) => { change({ ...physical, joint_assembly: { ...physical.joint_assembly, members: physical.joint_assembly.members.map((item, i) => i === index ? { ...item, section: { ...item.section, [name]: nextQ } } : item) } }, name === "thickness" || name === "flange_thickness" ? value.legacy.layers.map((layer) => layer.component_id === member.id ? { ...layer, thickness: nextQ } : layer) : value.legacy.layers); }} />)}</fieldset>)}
    {physical.joint_assembly.member_end_actions.map((action, index) => <fieldset key={action.id}><legend>LRFD member-end action</legend><p>Case {action.load_combination_id}; frame {action.coordinate_frame_kind}; reference {action.reference_point.kind}. All six actions are retained.</p>
      {(["force", "moment"] as const).flatMap((kind) => (["x", "y", "z"] as const).map((axis) => <ValueInput key={kind + axis} label={action.id + " " + kind + " " + axis} quantity={{ value: action[kind][axis], unit: action[kind].unit }} onChange={(q) => { change({ ...physical, joint_assembly: { ...physical.joint_assembly, member_end_actions: physical.joint_assembly.member_end_actions.map((item, i) => i === index ? { ...item, [kind]: { ...item[kind], [axis]: q.value } } : item) } }); }} />))}
    </fieldset>)}
  </>;
}

export function DirectHybridWorkspace({ initialNative, onNative }: { readonly initialNative: TwoBoltRequest; readonly onNative: () => void }) {
  const [draft, setDraft] = useState<HybridInputs>(() => ({ contract: "HYB2-D3-P1-LIVE", workspace_id: "live-" + crypto.randomUUID(), revision: 0, connection: "CURRENT_NATIVE", alignment: initialNative.alignment, native_request: initialNative, geometry: null, include_native_lrfd: true, asd_cases: [], lrfd_cases: [], source_profile: "UNMATCHED", bearing_face: "UNKNOWN", washer_od: null, native_edge_distance: null }));
  const current = useRef(0), live = useRef(true);
  const latestRevision = useCallback(() => current.current, []);
  const [preview, setPreview] = useState<HybridResponse | null>(null);
  const [result, setResult] = useState<HybridResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [selection, setSelection] = useState<SceneSelection>({ kind: "MEMBER", id: "member-a" });
  useEffect(() => { live.current = true; return () => { live.current = false; queueMicrotask(() => { if (!live.current) void hybridPost("invalidate", { workspace_id: draft.workspace_id, revision: latestRevision() + 1 }).catch(() => { /* Account/revision checks also protect every export. */ }); }); }; }, [draft.workspace_id, latestRevision]);
  useEffect(() => {
    const revision = draft.revision;
    void calculateHybrid("preview", draft).then((value) => { if (live.current && current.current === revision) { setPreview(value); } }).catch((e: unknown) => { if (live.current && current.current === revision) setError((e as Error).message); });
  }, [draft]);
  const edit = (next: HybridInputs) => {
    const revision = ++current.current;
    setResult(null); setPreview(null); setBusy(false); setError("");
    setDraft({ ...next, revision });
    void hybridPost("invalidate", { workspace_id: draft.workspace_id, revision }).catch(() => { /* Assess also checks server revision; current export is already disabled locally. */ });
  };
  const run = async () => {
    const revision = current.current; setBusy(true); setResult(null); setError("");
    try { const value = await calculateHybrid("assess", draft); if (live.current && current.current === revision) { setResult(value); setPreview(value); } }
    catch (e) { if (live.current && current.current === revision) setError((e as Error).message); }
    finally { if (live.current && current.current === revision) setBusy(false); }
  };
  const exportPDF = async (handle: string, technical: boolean, format: "pdf" | "json" = "pdf") => {
    const revision = current.current;
    try { await downloadHybrid(handle, technical, format, () => live.current && current.current === revision); }
    catch (e) { if (live.current && current.current === revision) { setResult(null); setError((e as Error).message); } }
  };
  const model = useMemo(() => preview?.scene ?? (preview?.native_geometry === null || preview?.native_geometry === undefined ? null : buildMultiRowSceneModel(preview.native_geometry.visualization, preview.native_geometry.direct_support_end_authority)), [preview]);
  const reportHandle = result?.report_handle;
  const record = result?.record, a = record?.assessment;
  const governing = a?.governing_asd ?? a?.governing_lrfd;
  const unity: UnityView = { tone: a?.tone === "neutral" || a === undefined ? "gray" : a.tone, ratio: governing?.ratio === null || governing?.ratio === undefined ? null : Number(governing.ratio), ratioText: governing?.ratio === null || governing?.ratio === undefined ? "—" : formatUnityPercent(Number(governing.ratio)), status: a === undefined ? "No current hybrid calculation" : "Evaluated checks: " + a.evaluated_outcome + " (scoped)", governing: governing === null || governing === undefined ? null : governing.basis + " / " + governing.case_id + " / " + governing.mechanism, explanation: "Calculated methods only; analytical coverage and qualification are not established." };
  const changeAlignment = (alignment: "BRACE" | "SUPPORT") => { edit({ ...draft, alignment, native_request: draft.native_request === null ? null : { ...draft.native_request, alignment } }); };
  const geometry = draft.geometry, nativeRequest = draft.native_request;
  const units = geometry?.vertical_bolt_pitch.unit ?? "in";
  const summary = (<section className={"hybrid-summary hybrid-" + unity.tone} aria-label="Hybrid calculation summary" aria-live="polite"><h3>{unity.status}</h3><p><strong>Scope: evaluated native LRFD and/or RHM reference/conditional method calculations only.</strong> Method applicability and complete structural coverage are not established.</p><p>Analytical coverage: {a?.coverage_state ?? "Not calculated"}. Qualification: {a?.qualification ?? "NOT ESTABLISHED"}. Complete connection verification is not established.</p>{record === undefined ? <p>Enter current inputs and run calculations. Previous results have no current export authority after edits.</p> : <><p>{record.requested_computation.rhm_comparisons_executed}/{record.requested_computation.rhm_comparisons_requested} requested RHM comparisons and {record.requested_computation.native_checks_executed} native numerical checks executed. This does not mean all structural mechanisms are checked.</p><Governing label="Governing LRFD" row={a?.governing_lrfd ?? null} /><Governing label="Governing RHM ASD" row={a?.governing_asd ?? null} /><p>Native F8/F9: {a?.native_status} (unchanged).</p><p>{record.coverage_summary}</p><p className={a?.fit.state === "NOT_FIT" ? "hybrid-detail-failure" : "hybrid-detail-state"}>Physical fit: {a?.fit.state}. {a?.fit.action}</p>{record.detailing_failures.map((check, i) => <p key={i} className="hybrid-detail-failure">{check.check_kind}: {check.actual_distance} {check.unit}; required {check.required_distance} {check.unit}. {check.boundary_label}. {check.source_rule}. Revise the actual detailing.</p>)}<p>{record.field_use_note}</p></>}
        <p>Owner-reported installed and successful field use is not physical load testing or formal qualification.</p>
        <div className="hybrid-exports"><button type="button" disabled={result?.report_handle === undefined} onClick={() => { void exportPDF(String(reportHandle), false); }}>Hybrid Calculation Report</button><button type="button" disabled={result?.report_handle === undefined} onClick={() => { void exportPDF(String(reportHandle), true); }}>Technical Audit</button><button type="button" disabled={result?.report_handle === undefined} onClick={() => { void exportPDF(String(reportHandle), false, "json"); }}>Calculation JSON</button></div>
      </section>);
  return <ConnectionWorkspaceShell className="hybrid-workspace" banner={<><section className="workspace-banner"><div><p className="eyebrow">Shear · Direct</p><h2>Hybrid — ASCE + RHM</h2><p>Engineer-assisted calculations with separate LRFD/ASD bases.</p></div><button type="button" onClick={onNative}>Return to native ASCE inputs</button></section>{summary}</>}>
    <ConnectionWorkspaceSidebar ariaLabel="Hybrid connection inputs">
      <div className="hybrid-example"><button type="button" onClick={() => { edit(sourceExample(draft)); }}>Load RHM source example</button><p>Explicit worked example, not a recommended project load envelope.</p></div>
      <DirectBoltAlignment alignment={draft.alignment} onChange={changeAlignment} calculationScope="Native ASCE checks require the existing supported geometry contract. Executable RHM reference/conditional calculations are reported separately." />
      <p className="sidebar-note">User-declared inputs. No certificate, review hash or liability checkbox is required to calculate.</p>
      {geometry === null ? <SidebarGroup title="Current native connection" summary="Actual current workspace inputs" defaultOpen>{nativeRequest === null ? <p>Define a current native connection.</p> : <NativeInputs value={nativeRequest} onChange={(native_request) => { edit({ ...draft, native_request }); }} />}<div onChange={() => { if (draft.native_request === null) return; try { const envelope = buildMAT1DesignEnvelope("multi-row", JSON.stringify(draft.native_request.legacy)); edit({ ...draft, native_request: { ...draft.native_request, legacy: envelope.request.legacy_request as unknown as MultiRowConnectionRequest, material_request: envelope.request } }); } catch (e) { const unresolved = { ...draft.native_request }; delete unresolved.material_request; edit({ ...draft, native_request: unresolved }); setError((e as Error).message); } }}><MAT1MaterialsPanel family="multi-row" /></div><label className="checkbox-control"><input type="checkbox" checked={draft.include_native_lrfd} onChange={(e) => { edit({ ...draft, include_native_lrfd: e.currentTarget.checked }); }} />Evaluate original native LRFD case</label><details><summary>Current native inputs and source trace</summary><pre>{JSON.stringify(draft.native_request, null, 2)}</pre></details></SidebarGroup> : <>
        <label className="field-control">Input unit system<select aria-label="Hybrid unit system" value={units} onChange={(e) => { const requested = e.currentTarget.value; const revision = current.current; void hybridPost<HybridInputs>("units", { inputs: draft, system: requested }).then((converted) => { if (live.current && revision === current.current) edit(converted); }).catch((e: unknown) => { if (live.current && revision === current.current) setError((e as Error).message); }); }}><option value="in">in / kip</option><option value="mm">mm / N</option></select></label>
        <SidebarGroup title="Current connection geometry" summary="One shared Angle / I bolt pair" defaultOpen>
          <label className="field-control">Brace angle phi<input aria-label="Brace angle phi" inputMode="decimal" value={geometry.phi} onChange={(e) => { edit({ ...draft, geometry: { ...geometry, phi: e.currentTarget.value } }); }} />degrees</label>
          {(Object.keys(GEOMETRY_LABELS) as (Exclude<keyof HybridGeometry, "phi">)[]).map((key) => <ValueInput key={key} label={GEOMETRY_LABELS[key]} quantity={geometry[key]} onChange={(q) => { edit({ ...draft, geometry: { ...geometry, [key]: q } }); }} />)}
          <details><summary>Geometry and constructability details</summary><p>Xc and the near-B1 anchor are inherited nominal source inputs. Hole size is declared review input. View caps, root fillets, true fabrication ends and tool access are not verified. Altered geometry is freshly calculated as a parametric/reference extension, not a newly adopted design domain.</p></details>
        </SidebarGroup>
      </>}
      <SidebarGroup title="Supplemental properties" summary="Separate source-specific RHM basis" defaultOpen><label className="field-control">RHM property profile<select aria-label="RHM property profile" value={draft.source_profile} onChange={(e) => { edit({ ...draft, source_profile: e.currentTarget.value as HybridInputs["source_profile"] }); }}><option value="UNMATCHED">No matching source profile</option><option value="RHM_POLYESTER_100F_SF4">RHM polyester 100°F · listed/SF4</option></select></label><p>Ts=.85; repeated Ts in D31/D221. Source 316SS included-thread allowance 12.75 ksi. These are worksheet properties, not the native MAT1/F593 selector. Moisture/duration/chemical and product-statistical applicability remain explicit limitations.</p></SidebarGroup>
      <SidebarGroup title="Independent actions" summary="Separate bases; no conversion" defaultOpen>
        <p>P follows the brace; source sketch V=-n. Nonzero/unknown unsupported components and transported moments remain supplied and are withheld, never zeroed.</p>
        {(["asd_cases", "lrfd_cases"] as const).map((key) => <div key={key}>{key === "lrfd_cases" && draft.connection === "CURRENT_NATIVE" ? null : <><button type="button" disabled={draft[key].length >= 8} onClick={() => { edit({ ...draft, [key]: [...draft[key], enteredCase((key === "asd_cases" ? "ASD-" : "LRFD-") + String(draft[key].length + 1))] }); }}>Add {key === "asd_cases" ? "ASD" : "LRFD"} case</button>{draft[key].map((value, i) => <CaseEditor key={i} basis={key === "asd_cases" ? "ASD" : "LRFD"} value={value} onChange={(next) => { edit({ ...draft, [key]: draft[key].map((c, j) => i === j ? next : c) }); }} onRemove={() => { edit({ ...draft, [key]: draft[key].filter((_, j) => j !== i) }); }} />)}</>}</div>)}
        <p>No entered case list is automatically declared a complete project envelope. Source SUPPORT geometry does not imply native ASCE checks ran.</p>
      </SidebarGroup>
      <SidebarGroup title="Washer and detailing" summary="Declared footprint; separate from strength" defaultOpen><label className="field-control">Bearing-face definition<select aria-label="Bearing-face definition" value={draft.bearing_face} onChange={(e) => { edit({ ...draft, bearing_face: e.currentTarget.value as HybridInputs["bearing_face"] }); }}><option value="UNKNOWN">Unknown / conditional screen</option><option value="DECLARED_STRAIGHT_FREE_EDGE">User-declared straight free edge</option></select></label><label className="field-control">Washer outside diameter<div className="hybrid-quantity"><input aria-label="Washer outside diameter" inputMode="decimal" value={draft.washer_od?.value ?? ""} placeholder="Unknown" onChange={(e) => { edit({ ...draft, washer_od: e.currentTarget.value === "" ? null : { value: e.currentTarget.value, unit: units } }); }} /><span>{units}</span></div></label>{draft.connection === "CURRENT_NATIVE" ? <label className="field-control">Declared straight-edge distance<input aria-label="Declared straight-edge distance" value={draft.native_edge_distance?.value ?? ""} onChange={(e) => { edit({ ...draft, native_edge_distance: e.currentTarget.value === "" ? null : { value: e.currentTarget.value, unit: units } }); }} />{units}</label> : <p>The declared free-edge screen uses the same current Xb as the physical R3 model. User declaration is not a verified survey.</p>}</SidebarGroup>
      <button className="primary-button" type="button" disabled={busy} onClick={() => { void run(); }}>{busy ? "Running Hybrid Calculations…" : "Run Hybrid Calculations"}</button>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain>

      {error === "" ? null : <div className="transport-error" role="alert">{error}</div>}
      <PersistentConnectionViewer unity={unity}>{model === null ? <p role="status">Current geometry is pending or invalid. No earlier model or result is represented as current.</p> : <VisualizationPanel model={model} selection={selection} onSelect={setSelection} title="Current hybrid connection geometry" />}</PersistentConnectionViewer>
      <p>Source-model far caps are display crops, not engineering end cuts. Fillet and complete hardware/tool fit remain unknown.</p>
      {record === undefined ? null : <><section aria-label="Current hybrid check results"><h3>Executed checks — separate bases</h3><div className="hybrid-table-scroll"><table><thead><tr><th>Basis / case</th><th>Calculated check</th><th>Utilization</th><th>Outcome / scope</th></tr></thead><tbody>{a?.comparisons.map((row) => <tr key={row.basis + row.case_id + row.mechanism}><td>{row.basis} / {row.case_id}</td><td>{row.mechanism}</td><td>{row.ratio ?? "Not evaluated"}</td><td>{row.outcome} / {row.evidence_scope}</td></tr>)}</tbody></table></div>{record.withheld.map(([id, reason], i) => <p key={i}>NOT EVALUATED — {id}: {reason}</p>)}</section><details><summary>Method notes and technical provenance</summary><p>{record.data_provenance}</p><p>Fingerprint: {record.fingerprint}; revision {record.revision}. Qualified engineering adoption and Section 2.3.2 evidence remain separate.</p><p>Exact equations, operands, registry and native traces are retained in the Technical Audit and current backend record.</p></details></>}
    </ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
