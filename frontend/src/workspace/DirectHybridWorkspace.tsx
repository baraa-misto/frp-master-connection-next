import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { calculateHybrid, downloadHybrid, enteredCase, hybridPost, sourceExample } from "../api/hybridWorkflow";
import type { HybridCase, HybridComparison, HybridInputs, HybridQuantity, HybridResponse } from "../api/hybridWorkflow";
import type { TwoBoltRequest } from "../api/directTwoBolt";
import type { SingleBoltPreviewRequest } from "../api/contracts";
import type { MultiRowConnectionRequest } from "../api/multirowContracts";
import { buildMAT1DesignEnvelope } from "../api/mat1Transport";
import { MAT1MaterialsPanel } from "../features/MAT1MaterialsPanel";
import { defaultFastenerSelection, mat1FamilyKey, observeMAT1, rememberMAT1Preview, setFastenerSelection, useMAT1 } from "../state/mat1Session";
import { FastenerSelector } from "../features/FastenerSelector";
import { loadJ1Benchmark } from "../fixtures/j1Benchmarks";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { buildHybridScene } from "../visualization/hybridSceneModel";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import { DirectBoltAlignment } from "../features/DirectBoltAlignment";
import { ConnectionWorkspaceMain, ConnectionWorkspaceShell, ConnectionWorkspaceSidebar, PersistentConnectionViewer, SidebarGroup } from "./ConnectionWorkspaceShell";
import type { UnityView } from "./unityRatio";
import { formatUnityPercent } from "./unityRatio";
import { formatDecimal, formatUtilization, friendlyEnum } from "./presentation";
import { DirectConnectionInputs } from "./DirectConnectionInputs";
import { calculationLabel } from "./directCalculationLabels";
import { DirectPresetConfirmation } from "./DirectPresetConfirmation";
import "./directHybridWorkspace.css";

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
  return <p><strong>{label}: </strong>{row === null ? "NOT EVALUATED" : `${calculationLabel(row.mechanism)} · ${row.case_id} · UR ${formatUtilization(row.ratio)}`}</p>;
}

function NativeInputs({ value, onChange }: { readonly value: TwoBoltRequest; readonly onChange: (next: TwoBoltRequest) => void }) {
  const physical = value.legacy.physical_connection;
  if (physical === undefined) return <p>The current physical connection is missing. Load a connection preset or restore previous inputs.</p>;
  const change = (nextPhysical: SingleBoltPreviewRequest) => {
    const legacy = { ...value.legacy, physical_connection: nextPhysical };
    onChange({ ...value, legacy, ...(value.material_request === undefined ? {} : { material_request: { ...value.material_request as object, legacy_request: legacy } }) });
  };
  return <>
    {physical.joint_assembly.member_end_actions.map((action, index) => <fieldset key={action.id}><legend>LRFD member-end action</legend><p>Case {action.load_combination_id}; frame {friendlyEnum(action.coordinate_frame_kind)}; reference {friendlyEnum(action.reference_point.kind)}. All six actions are retained.</p>
      {(["force", "moment"] as const).flatMap((kind) => (["x", "y", "z"] as const).map((axis) => <ValueInput key={kind + axis} label={action.id + " " + kind + " " + axis} quantity={{ value: action[kind][axis], unit: action[kind].unit }} onChange={(q) => { change({ ...physical, joint_assembly: { ...physical.joint_assembly, member_end_actions: physical.joint_assembly.member_end_actions.map((item, i) => i === index ? { ...item, [kind]: { ...item[kind], [axis]: q.value } } : item) } }); }} />))}
    </fieldset>)}
  </>;
}

function sourceMaterials(value: HybridInputs, template: TwoBoltRequest): HybridInputs {
  const next = { ...value };
  if (value.geometry === null) return next;
  try {
    const envelope = buildMAT1DesignEnvelope("multi-row", JSON.stringify(template.legacy));
    next.same_connection_lrfd = { assignments: envelope.request.assignments, fastener: envelope.request.fastener ?? defaultFastenerSelection };
  } catch { delete next.same_connection_lrfd; }
  return next;
}

export function DirectHybridWorkspace({ initialNative, onNative }: { readonly initialNative: TwoBoltRequest; readonly onNative: () => void }) {
  const materials = useMAT1();
  const priorMaterialKey = useRef(mat1FamilyKey("multi-row", false));
  const [draft, setDraft] = useState<HybridInputs>(() => ({ contract: "HYB2-D3-P1-LIVE", workspace_id: "live-" + crypto.randomUUID(), revision: 0, connection: "CURRENT_NATIVE", alignment: initialNative.alignment, native_request: initialNative, geometry: null, include_native_lrfd: true, asd_cases: [], lrfd_cases: [], source_profile: "UNMATCHED", bearing_face: "UNKNOWN", washer_od: null, native_edge_distance: null }));
  const [preset, setPreset] = useState<"SOURCE" | "NATIVE" | "RESTORE" | null>(null);
  const [savedInputs, setSavedInputs] = useState<HybridInputs | null>(null);
  const [presetName, setPresetName] = useState("Current Direct connection");
  const nativeExample = useRef(structuredClone(initialNative));
  const current = useRef(0), live = useRef(true);
  const latestRevision = useCallback(() => current.current, []);
  const [preview, setPreview] = useState<HybridResponse | null>(null);
  const [result, setResult] = useState<HybridResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [selection, setSelection] = useState<SceneSelection>({ kind: "MEMBER", id: "member-a" });
  const [materialAxesVisible, setMaterialAxesVisible] = useState(false);
  useEffect(() => { live.current = true; return () => { live.current = false; queueMicrotask(() => { if (!live.current) void hybridPost("invalidate", { workspace_id: draft.workspace_id, revision: latestRevision() + 1 }).catch(() => { /* Account/revision checks also protect every export. */ }); }); }; }, [draft.workspace_id, latestRevision]);
  useEffect(() => {
    const revision = draft.revision;
    if (draft.native_request !== null) rememberMAT1Preview("multi-row", JSON.stringify(draft.native_request.legacy));
    void calculateHybrid("preview", draft).then((value) => { if (live.current && current.current === revision) { setPreview(value); } }).catch((e: unknown) => { if (live.current && current.current === revision) setError((e as Error).message); });
  }, [draft]);
  const edit = useCallback((next: HybridInputs) => {
    const revision = ++current.current;
    setResult(null);
    if (JSON.stringify([next.connection, next.alignment, next.geometry, next.native_request]) !== JSON.stringify([draft.connection, draft.alignment, draft.geometry, draft.native_request])) setPreview(null);
    setBusy(false); setError("");
    setDraft({ ...next, workspace_id: draft.workspace_id, revision });
    void hybridPost("invalidate", { workspace_id: draft.workspace_id, revision }).catch(() => { /* Assess also checks server revision; current export is already disabled locally. */ });
  }, [draft]);
  useEffect(() => observeMAT1(() => {
    const materialKey = mat1FamilyKey("multi-row", false);
    if (priorMaterialKey.current === materialKey) return;
    priorMaterialKey.current = materialKey;
    if (draft.native_request === null) { edit(sourceMaterials(draft, nativeExample.current)); return; }
    const native = { ...draft.native_request };
    try {
      const envelope = buildMAT1DesignEnvelope("multi-row", JSON.stringify(native.legacy));
      native.legacy = envelope.request.legacy_request as unknown as MultiRowConnectionRequest;
      native.material_request = envelope.request;
    } catch { delete native.material_request; }
    edit({ ...draft, native_request: native });
  }), [draft, edit]);
  const applyPreset = () => {
    const previous = structuredClone(draft);
    const next = structuredClone(preset === "SOURCE" ? sourceExample(draft) : preset === "RESTORE" && savedInputs !== null ? savedInputs : { ...draft, connection: "CURRENT_NATIVE" as const, native_request: structuredClone(nativeExample.current), geometry: null, alignment: nativeExample.current.alignment, include_native_lrfd: true, asd_cases: [], lrfd_cases: [], source_profile: "UNMATCHED" as const, washer_od: null, native_edge_distance: null, bearing_face: "UNKNOWN" as const });
    if (preset === "SOURCE") { delete next.same_connection_lrfd; Object.assign(next, sourceMaterials(next, nativeExample.current)); }
    if (next.connection === "CURRENT_NATIVE") delete next.same_connection_lrfd;
    if (preset === "NATIVE" && materials.active && next.native_request !== null) {
      try {
        const envelope = buildMAT1DesignEnvelope("multi-row", JSON.stringify(next.native_request.legacy));
        next.native_request = { ...next.native_request, legacy: envelope.request.legacy_request as unknown as MultiRowConnectionRequest, material_request: envelope.request };
      } catch { delete next.native_request.material_request; }
    }
    setSavedInputs(previous);
    setPresetName(preset === "SOURCE" ? "RHM source sample preset — editable reference inputs" : preset === "RESTORE" ? "Restored previous Direct inputs" : "Native ASCE example preset — editable inputs");
    edit(next); setPreset(null);
  };
  const run = async () => {
    if (materials.active && draft.include_native_lrfd && draft.native_request !== null && draft.native_request.material_request === undefined) {
      setResult(null); setError("Complete the selected FRP material and actual project conditions before calculating ASCE LRFD checks."); return;
    }
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
  const model = useMemo(() => buildHybridScene(preview), [preview]);
  const reportHandle = result?.report_handle;
  const record = result?.record, a = record?.assessment;
  const governing = record?.numerical_governing ?? a?.governing_asd ?? a?.governing_lrfd ?? null;
  const unity: UnityView = { tone: a?.tone === "neutral" || a === undefined ? "gray" : a.tone, ratio: governing?.ratio === null || governing?.ratio === undefined ? null : Number(governing.ratio), ratioText: governing?.ratio === null || governing?.ratio === undefined ? "—" : formatUnityPercent(Number(governing.ratio)), status: a === undefined ? "Ready to calculate" : "Evaluated checks: " + a.evaluated_outcome + " (scoped)", governing: governing === null ? null : governing.basis + " / " + governing.case_id + " / " + calculationLabel(governing.mechanism), explanation: "Calculated methods only; analytical coverage and qualification are not established." };
  const changeAlignment = (alignment: "BRACE" | "SUPPORT") => { edit({ ...draft, alignment, native_request: draft.native_request === null ? null : { ...draft.native_request, alignment } }); };
  const geometry = draft.geometry, nativeRequest = draft.native_request;
  const units = geometry?.vertical_bolt_pitch.unit ?? "in";
  const exportControls = (<div className="hybrid-exports"><button type="button" disabled={result?.report_handle === undefined} onClick={() => { void exportPDF(String(reportHandle), false); }}>Hybrid Calculation Report</button><button type="button" disabled={result?.report_handle === undefined} onClick={() => { void exportPDF(String(reportHandle), true); }}>Technical Audit</button><button type="button" disabled={result?.report_handle === undefined} onClick={() => { void exportPDF(String(reportHandle), false, "json"); }}>Calculation JSON</button></div>);
  const summary = record === undefined ? <p className="hybrid-ready" role="status">Enter the connection inputs, choose independent calculation bases and run calculations. No calculation has been requested for these inputs.</p> : (<section className={"hybrid-summary hybrid-" + unity.tone} aria-label="Hybrid calculation summary" aria-live="polite"><h3>{unity.status}</h3>
    <p><strong>Calculated checks only.</strong> Analytical coverage: {friendlyEnum(record.assessment.coverage_state)}.</p>
    <p>{record.coverage_summary}</p>
    {record.requested_computation.rhm_comparisons_executed === 0 ? null : <p>RHM ASD reference comparisons use the listed source properties and source conditions. Applicability to actual project materials and conditions is not established.</p>}
    <p>{record.requested_computation.rhm_comparisons_executed}/{record.requested_computation.rhm_comparisons_requested} requested RHM comparisons and {record.requested_computation.native_checks_executed} {record.same_connection_lrfd === undefined ? "native" : "ASCE component"} numerical checks executed.</p>
    <Governing label="Governing LRFD" row={a?.governing_lrfd ?? null} /><Governing label="Governing RHM ASD" row={a?.governing_asd ?? null} />
    <p className={record.assessment.fit.state === "NOT_FIT" ? "hybrid-detail-failure" : "hybrid-detail-state"}>Physical fit: {friendlyEnum(record.assessment.fit.state)}. {record.assessment.fit.action}</p>
    {record.detailing_failures.map((check, i) => <p key={i} className="hybrid-detail-failure">{calculationLabel(check.check_kind)}{check.bolt_id === undefined ? "" : " — " + check.bolt_id}{check.case_id === undefined ? "" : " / " + check.case_id}: {formatDecimal(check.actual_distance)} {check.unit}; required {formatDecimal(check.required_distance)} {check.unit}. {check.boundary_label}. {check.source_rule} Revise the actual detailing.</p>)}

  </section>);
  return <ConnectionWorkspaceShell className="hybrid-workspace" banner={<><section className="workspace-banner"><div><p className="eyebrow">Shear · Direct</p><h2>Direct connection — ASCE LRFD + RHM ASD</h2><p>Engineer-assisted calculations with separate LRFD/ASD bases.</p></div><button type="button" onClick={onNative}>Other bolt arrangements</button></section>{summary}{exportControls}</>}>
    <ConnectionWorkspaceSidebar ariaLabel="Hybrid connection inputs">
      <div className="hybrid-example"><p><strong>{presetName}</strong></p><button type="button" onClick={() => { setPreset("SOURCE"); }}>Load RHM source example</button><button type="button" onClick={() => { setPreset("NATIVE"); }}>Load native ASCE example</button><button type="button" disabled={savedInputs === null} onClick={() => { setPreset("RESTORE"); }}>Restore previous inputs</button><p>Presets replace the common connection inputs after confirmation. They are examples, not project design recommendations.</p></div>
      {preset === null ? null : <DirectPresetConfirmation onConfirm={applyPreset} onCancel={() => { setPreset(null); }} />}
      {geometry === null ? null : <label className="field-control">Input unit system<select aria-label="Hybrid unit system" value={units} onChange={(e) => { const requested = e.currentTarget.value; const revision = current.current; void hybridPost<HybridInputs>("units", { inputs: draft, system: requested }).then((converted) => { if (live.current && revision === current.current) edit(converted); }).catch((e: unknown) => { if (live.current && revision === current.current) setError((e as Error).message); }); }}><option value="in">in / kip</option><option value="mm">mm / N</option></select></label>}
      <DirectBoltAlignment alignment={draft.alignment} onChange={changeAlignment} calculationScope="Native ASCE checks require the existing supported geometry contract. Executable RHM reference/conditional calculations are reported separately." />
      <SidebarGroup title="Connection geometry" summary="One editable Angle / I connection" defaultOpen><DirectConnectionInputs value={draft} onChange={edit} /></SidebarGroup>
      <p className="sidebar-note">User-declared inputs. No certificate, review hash or liability checkbox is required to calculate.</p>
      <SidebarGroup title="Materials and project conditions" summary="Separate LRFD and source ASD property authorities" defaultOpen>
        {nativeRequest === null ? <><p>ASCE LRFD uses the selected MAT1 characteristic/specification properties and actual project conditions on this same geometry. RHM ASD retains its separate listed polyester/100°F reference basis; no factor or property blending.</p><MAT1MaterialsPanel family="multi-row" />{draft.same_connection_lrfd === undefined ? <p>Complete current material and project conditions to enable applicable ASCE components. Independent RHM reference calculations remain available.</p> : null}</> : <div onChange={() => { try { const envelope = buildMAT1DesignEnvelope("multi-row", JSON.stringify(nativeRequest.legacy)); edit({ ...draft, native_request: { ...nativeRequest, legacy: envelope.request.legacy_request as unknown as MultiRowConnectionRequest, material_request: envelope.request } }); } catch (e) { const unresolved = { ...nativeRequest }; delete unresolved.material_request; edit({ ...draft, native_request: unresolved }); setError((e as Error).message); } }}><MAT1MaterialsPanel family="multi-row" /></div>}
      </SidebarGroup>
      <SidebarGroup title="Fastener" summary="ASCE hardware source and selection"><FastenerSelector defaultSnapshot={loadJ1Benchmark(nativeRequest?.legacy.physical_connection?.joint_assembly.unit_system ?? "US_CUSTOMARY").fastener_snapshot} diameter={nativeRequest?.legacy.bolt_diameter ?? geometry?.diameter ?? { value: ".5", unit: "in" }} selection={materials.fastenerSelections["multi-row"] ?? defaultFastenerSelection} onSelect={(selection) => { setFastenerSelection("multi-row", selection); }} /></SidebarGroup>
      <SidebarGroup title="RHM supplemental properties" summary="Separate source-specific ASD basis"><label className="field-control">RHM property profile<select aria-label="RHM property profile" value={draft.source_profile} onChange={(e) => { edit({ ...draft, source_profile: e.currentTarget.value as HybridInputs["source_profile"] }); }}><option value="UNMATCHED">No matching source profile</option><option value="RHM_POLYESTER_100F_SF4">RHM polyester 100°F · listed/SF4</option></select></label><p>Ts=.85; repeated Ts in D31/D221. Source 316SS included-thread allowance 12.75 ksi. These are worksheet properties, not the native MAT1/F593 selector. Moisture/duration/chemical and product-statistical applicability remain explicit limitations.</p></SidebarGroup>
      <SidebarGroup title="Loads and calculation bases" summary="Independent LRFD and ASD actions" defaultOpen>
        <label className="checkbox-control"><input type="checkbox" checked={draft.include_native_lrfd} onChange={(e) => { edit({ ...draft, include_native_lrfd: e.currentTarget.checked }); }} />Evaluate applicable ASCE LRFD checks</label>
        {nativeRequest === null ? <p>Applicable ASCE bolt/bearing components use this R3 pair, current MAT1 properties and independent entered LRFD cases. No BRACE-reference result is borrowed and no LRFD case is inferred from ASD.</p> : <NativeInputs value={nativeRequest} onChange={(native_request) => { edit({ ...draft, native_request }); }} />}
        <p>P follows the brace; source sketch V=-n. Nonzero/unknown unsupported components and transported moments remain supplied and are withheld, never zeroed.</p>
        {(["asd_cases", "lrfd_cases"] as const).map((key) => <div key={key}>{key === "lrfd_cases" && draft.connection === "CURRENT_NATIVE" ? null : <><button type="button" disabled={draft[key].length >= 8} onClick={() => { edit({ ...draft, [key]: [...draft[key], enteredCase((key === "asd_cases" ? "ASD-" : "LRFD-") + String(draft[key].length + 1))] }); }}>Add {key === "asd_cases" ? "ASD" : "LRFD"} case</button>{draft[key].map((value, i) => <CaseEditor key={i} basis={key === "asd_cases" ? "ASD" : "LRFD"} value={value} onChange={(next) => { edit({ ...draft, [key]: draft[key].map((c, j) => i === j ? next : c) }); }} onRemove={() => { edit({ ...draft, [key]: draft[key].filter((_, j) => j !== i) }); }} />)}</>}</div>)}
        <p>No entered case list is automatically declared a complete project envelope. The executed-check list identifies each calculation and its basis.</p>
      </SidebarGroup>
      <SidebarGroup title="Washer and detailing" summary="Declared footprint; separate from strength" defaultOpen><label className="field-control">Bearing-face definition<select aria-label="Bearing-face definition" value={draft.bearing_face} onChange={(e) => { edit({ ...draft, bearing_face: e.currentTarget.value as HybridInputs["bearing_face"] }); }}><option value="UNKNOWN">Unknown / conditional screen</option><option value="DECLARED_STRAIGHT_FREE_EDGE">User-declared straight free edge</option></select></label><label className="field-control">Washer outside diameter<div className="hybrid-quantity"><input aria-label="Washer outside diameter" inputMode="decimal" value={draft.washer_od?.value ?? ""} placeholder="Unknown" onChange={(e) => { edit({ ...draft, washer_od: e.currentTarget.value === "" ? null : { value: e.currentTarget.value, unit: units } }); }} /><span>{units}</span></div></label>{draft.connection === "CURRENT_NATIVE" ? <label className="field-control">Declared straight-edge distance<input aria-label="Declared straight-edge distance" value={draft.native_edge_distance?.value ?? ""} onChange={(e) => { edit({ ...draft, native_edge_distance: e.currentTarget.value === "" ? null : { value: e.currentTarget.value, unit: units } }); }} />{units}</label> : <p>The declared free-edge screen uses the same current Xb as the physical R3 model. User declaration is not a verified survey.</p>}</SidebarGroup>
      <button className="primary-button" type="button" disabled={busy} onClick={() => { void run(); }}>{busy ? "Running Hybrid Calculations…" : "Run Hybrid Calculations"}</button>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain>

      {error === "" ? null : <div className="transport-error" role="alert">{error}</div>}
      <PersistentConnectionViewer {...(a === undefined ? {} : { unity })}>{model === null ? <p role="status">Current geometry is pending or invalid. No earlier model or result is represented as current.</p> : <VisualizationPanel model={model} selection={selection} onSelect={setSelection} title="Current Direct connection geometry" materialAxesQuickAccess initialMaterialAxes={materialAxesVisible} onMaterialAxesChange={setMaterialAxesVisible} />}</PersistentConnectionViewer>
      <p>Source-model far caps are display crops, not engineering end cuts. Fillet and complete hardware/tool fit remain unknown.</p>
      {record === undefined ? null : <><section aria-label="Current hybrid check results"><h3>Executed checks — separate bases</h3><div className="hybrid-table-scroll"><table><thead><tr><th>Basis / case</th><th>Calculated check</th><th>Utilization</th><th>Outcome / scope</th></tr></thead><tbody>{a?.comparisons.map((row) => <tr key={row.basis + row.case_id + row.mechanism}><td>{row.basis} / {row.case_id}</td><td>{calculationLabel(row.mechanism)}</td><td>{formatUtilization(row.ratio)}</td><td>{friendlyEnum(row.outcome)} / {calculationLabel(row.evidence_scope)}</td></tr>)}</tbody></table></div>{record.withheld.map(([id, reason], i) => <p key={i}>Not evaluated — {calculationLabel(id)}: {reason}</p>)}</section><details><summary>Method notes and technical provenance</summary><p>{record.data_provenance}</p><p>{record.field_use_note}</p><p>Native completeness authority: {a?.native_status}. {record.coverage_summary}</p><p>Fingerprint: {record.fingerprint}; revision {record.revision}. Qualified engineering adoption and Section 2.3.2 evidence remain separate.</p><p>Exact equations, operands, registry and native traces are retained in the Technical Audit and current backend record.</p></details></>}
      {record?.physical_mechanisms === undefined ? null : <section aria-label="Physical mechanism coverage"><h3>Physical mechanism coverage</h3>{record.physical_mechanisms.map((item) => <details key={item.mechanism}><summary>{item.mechanism} — {item.executed_comparisons.length === 0 ? "evidence required" : "scoped calculations available"}</summary><p>{item.evidence}</p><p>{item.remaining_evidence}</p></details>)}{record.same_connection_lrfd?.assumptions.map((note) => <p key={note}>{note}</p>)}</section>}
    </ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
