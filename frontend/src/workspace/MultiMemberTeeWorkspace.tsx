import { useMemo, useRef, useState } from "react";
import { ConnectorBodyMaterialControl, ConnectorBodyMaterialResult } from "./connectorBodyMaterial";
import { useConnectorBodyMaterial } from "./useConnectorBodyMaterial";

import { EvaluationTransportError, evaluateMultiMemberTee } from "../api/client";
import type {
  ExpandedMultiMemberTeeRequest,
  MultiMemberTeeDesignResponse,
  MultiMemberTeeSlotId,
  NodeBoltGroup,
  NodeExpandedSlot,
  NodeUnitSystem,
} from "../api/multiMemberTeeContracts";
import { sharedSupportLabel } from "../api/sharedSupportContracts";
import {
  initialMultiMemberTeeSupport,
} from "../fixtures/multiMemberTeeBenchmarks";
import { loadMultiMemberTeeWorkspaceDefault } from "../fixtures/connectionWorkspaceDefaults";
import { loadMultiMemberTeeBenchmark } from "../fixtures/multiMemberTeeBenchmarks";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { buildMultiMemberTeeSceneModel } from "../visualization/multiMemberTeeSceneModel";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import {
  ConnectionWorkspaceMain,
  ConnectionWorkspaceShell,
  ConnectionWorkspaceSidebar,
  PersistentConnectionViewer,
  SidebarGroup,
} from "./ConnectionWorkspaceShell";
import { friendlyEnum, friendlyIdentifier } from "./presentation";
import { MultiMemberTeeProfileEditor } from "./MultiMemberTeeProfileEditor";
import { SupportingMemberEditor } from "./SupportingMemberEditor";
import { TEE_PROFILE_DEFINITIONS } from "./teeProfileOptions";
import { useMultiMemberTeePreview } from "./multiMemberTeeWorkflow";

const SLOT_LABELS: Readonly<Record<MultiMemberTeeSlotId, string>> = {
  UPPER_BRACE: "Upper Member",
  MIDDLE_BEAM: "Middle Member (horizontal)",
  LOWER_BRACE: "Lower Member",
};
const SLOT_KEYS = {
  UPPER_BRACE: "upper_brace",
  MIDDLE_BEAM: "middle_beam",
  LOWER_BRACE: "lower_brace",
} as const;
function clone(value: ExpandedMultiMemberTeeRequest): ExpandedMultiMemberTeeRequest {
  return structuredClone(value);
}

function QuantityInput({ label, value, onChange }: { readonly label: string; readonly value: { value: string; unit: string }; readonly onChange: (value: string) => void }) {
  return <label className="field-control"><span>{label}</span><span className="input-with-unit"><input aria-label={label} inputMode="decimal" value={value.value} onChange={(event) => { onChange(event.currentTarget.value); }} /><small>{value.unit}</small></span></label>;
}

function GroupEditor({ title, value, onChange }: { readonly title: string; readonly value: NodeBoltGroup; readonly onChange: (change: (group: NodeBoltGroup) => void) => void }) {
  return <section className="node-group-editor" aria-label={title}><h4>{title}</h4><div className="field-grid">
    <label className="field-control"><span>Rows</span><input aria-label={`${title} rows`} type="number" min="1" value={value.row_count} onChange={(event) => { const count = Number(event.currentTarget.value); onChange((group) => { group.row_count = count; }); }} /></label>
    <label className="field-control"><span>Bolts per row</span><input aria-label={`${title} bolts per row`} type="number" min="1" value={value.bolts_per_row} onChange={(event) => { const count = Number(event.currentTarget.value); onChange((group) => { group.bolts_per_row = count; }); }} /></label>
    <QuantityInput label={`${title} pitch`} value={value.pitch} onChange={(next) => { onChange((group) => { group.pitch.value = next; }); }} />
    <QuantityInput label={`${title} gauge`} value={value.gauge} onChange={(next) => { onChange((group) => { group.gauge.value = next; }); }} />
  </div></section>;
}

function SlotEditor({ slot, unitSystem, onChange }: { readonly slot: NodeExpandedSlot; readonly unitSystem: NodeUnitSystem; readonly onChange: (change: (slot: NodeExpandedSlot) => void) => void }) {
  const isMiddle = slot.slot_id === "MIDDLE_BEAM";
  const actionFields = (["force_hvn", "moment_hvn", "reference_hvn"] as const).flatMap((kind) => (["x", "y", "z"] as const).map((axis) => ({ kind, axis })));
  return <>
    <div className="field-grid">
      <QuantityInput label={`${SLOT_LABELS[slot.slot_id]} anchor H`} value={slot.anchor_h} onChange={(value) => { onChange((next) => { next.anchor_h.value = value; }); }} />
      <QuantityInput label={`${SLOT_LABELS[slot.slot_id]} anchor V`} value={slot.anchor_v} onChange={(value) => { onChange((next) => { next.anchor_v.value = value; next.action.reference_hvn.y = value; }); }} />
      <label className="field-control"><span>Inclination</span><span className="input-with-unit"><input aria-label={`${SLOT_LABELS[slot.slot_id]} inclination`} disabled={isMiddle} value={slot.inclination_degrees} onChange={(event) => { const value = event.currentTarget.value; onChange((next) => { next.inclination_degrees = value; }); }} /><small>deg</small></span></label>
    </div>
    <MultiMemberTeeProfileEditor label={SLOT_LABELS[slot.slot_id]} unitSystem={unitSystem} profile={slot.profile} onChange={(profile) => { onChange((next) => { next.profile = profile; next.profile_roll_degrees = profile.profile_orientation.replace("ROTATION_", ""); }); }} />
    <label className="field-control tee-checkbox-control"><span>Independent member-end trim</span><input aria-label={`${SLOT_LABELS[slot.slot_id]} trim`} type="checkbox" checked={slot.trim_enabled} onChange={(event) => { const enabled = event.currentTarget.checked; onChange((next) => { next.trim_enabled = enabled; next.trim_clearance = enabled ? { value: "0", unit: next.profile.dimensions.member_length.unit } : null; }); }} /></label>
    {slot.trim_clearance === null ? null : <QuantityInput label={`${SLOT_LABELS[slot.slot_id]} trim clearance`} value={slot.trim_clearance} onChange={(value) => { onChange((next) => { Object.assign(next.trim_clearance as { value: string }, { value }); }); }} />}
    <GroupEditor title={`${SLOT_LABELS[slot.slot_id]} bolt group`} value={slot.bolt_group} onChange={(change) => { onChange((next) => { change(next.bolt_group); }); }} />
    <h4>Complete member-end wrench</h4><div className="field-grid">{actionFields.map(({ kind, axis }) => <label className="field-control" key={`${kind}-${axis}`}><span>{friendlyEnum(kind)} {axis.toUpperCase()}</span><span className="input-with-unit"><input aria-label={`${SLOT_LABELS[slot.slot_id]} ${kind} ${axis}`} value={slot.action[kind][axis]} onChange={(event) => { const value = event.currentTarget.value; onChange((next) => { next.action[kind][axis] = value; }); }} /><small>{slot.action[kind].unit}</small></span></label>)}</div>
  </>;
}

export function MultiMemberTeeWorkspace() {
  const [request, setRequest] = useState<ExpandedMultiMemberTeeRequest>(() => loadMultiMemberTeeWorkspaceDefault("US_CUSTOMARY"));
  const [revision, setRevision] = useState(0);
  const [selection, setSelection] = useState<SceneSelection>({ kind: "MEMBER", id: "tee-connector" });
  const [design, setDesign] = useState<MultiMemberTeeDesignResponse | null>(null);
  const [designRevision, setDesignRevision] = useState<number | null>(null);
  const [designError, setDesignError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const preview = useMultiMemberTeePreview(request, revision);
  const mutate = (change: (next: ExpandedMultiMemberTeeRequest) => void) => {
    setRequest((current) => { const next = clone(current); change(next); return next; });
    setRevision((value) => value + 1);
  };
  const load = (system: NodeUnitSystem) => { setRequest(loadMultiMemberTeeBenchmark(system)); setRevision((value) => value + 1); setDesign(null); setDesignRevision(null); };
  const toggle = (id: MultiMemberTeeSlotId, enabled: boolean) => {
    mutate((next) => {
      const key = SLOT_KEYS[id];
      if (enabled) {
        const source = loadMultiMemberTeeBenchmark(next.unit_system)[key];
        Object.assign(next, { [key]: source });
      } else {
        if (id === "UPPER_BRACE") delete next.upper_brace;
        else if (id === "MIDDLE_BEAM") delete next.middle_beam;
        else delete next.lower_brace;
      }
    });
  };
  const changeSlot = (id: MultiMemberTeeSlotId, slot: NodeExpandedSlot, change: (slot: NodeExpandedSlot) => void) => {
    const updated = structuredClone(slot);
    change(updated);
    mutate((next) => { Object.assign(next, { [SLOT_KEYS[id]]: updated }); });
  };
  const result = preview.response?.result ?? null;
  const model = useMemo(() => result?.visualization === null || result?.visualization === undefined ? null : buildMultiMemberTeeSceneModel(result.visualization), [result]);
  const designStale = design !== null && designRevision !== revision;
  const materialEpoch = useRef(0);
  const bodyMaterial = useConnectorBodyMaterial("multi-member-tee", request, revision, () => {
    materialEpoch.current += 1; setDesign(null); setDesignRevision(null); setDesignError(null); setLoading(false);
  });
  const runDesign = async () => {
    if (bodyMaterial.material === "SS316") { await bodyMaterial.run(); return; }
    const epoch = materialEpoch.current;
    setLoading(true); setDesignError(null); const controller = new AbortController();
    try { const next = await evaluateMultiMemberTee(request, controller.signal); if (epoch === materialEpoch.current) { setDesign(next); setDesignRevision(revision); } }
    catch (caught) { if (epoch === materialEpoch.current) setDesignError(caught instanceof EvaluationTransportError ? caught.message : "Design check failed."); }
    finally { if (epoch === materialEpoch.current) setLoading(false); }
  };
  const activeCount = ([request.upper_brace, request.middle_beam, request.lower_brace]).filter(Boolean).length;
  const activeProfileLabels: string[] = [];
  if (request.upper_brace !== undefined) activeProfileLabels.push(`Upper: ${TEE_PROFILE_DEFINITIONS[request.upper_brace.profile.profile_family].label}`);
  if (request.middle_beam !== undefined) activeProfileLabels.push(`Middle: ${TEE_PROFILE_DEFINITIONS[request.middle_beam.profile.profile_family].label}`);
  if (request.lower_brace !== undefined) activeProfileLabels.push(`Lower: ${TEE_PROFILE_DEFINITIONS[request.lower_brace.profile.profile_family].label}`);
  const connectionTitle = `${activeProfileLabels.join(" · ")} → ${sharedSupportLabel(request.support_target_id)}`;
  return <ConnectionWorkspaceShell className="multi-member-tee-workspace" banner={<section className="workspace-banner"><div><p className="eyebrow">Stage 3.4B · Expanded profile/support matrix</p><h2>{connectionTitle}</h2><p>Independent connected-member groups with one exact backend-assembled support transfer wrench.</p></div><div className="benchmark-actions"><button type="button" onClick={() => { load("US_CUSTOMARY"); }}>Load expanded U.S.</button><button type="button" onClick={() => { load("SI"); }}>Load expanded SI</button></div></section>}>
    <ConnectionWorkspaceSidebar ariaLabel="Multi-Member Tee engineering inputs">
      <ConnectorBodyMaterialControl material={bodyMaterial.material} onChange={bodyMaterial.choose} />
      <SidebarGroup title="General / Case" summary={`${request.unit_system} · ${String(activeCount)} active`} defaultOpen><p className="sidebar-note">Session only · no persistence</p></SidebarGroup>
      <SidebarGroup title="Connection" summary={`Multiple members → Tee → ${sharedSupportLabel(request.support_target_id)}`} defaultOpen><p className="demand-boundary-note">The Multi-Member Tee is a separate contract. It does not route through or replace the frozen single-member Tee workspace.</p></SidebarGroup>
      {(["UPPER_BRACE", "MIDDLE_BEAM", "LOWER_BRACE"] as const).map((id) => { const slot = request[SLOT_KEYS[id]]; return <SidebarGroup key={id} title={SLOT_LABELS[id]} summary={slot === undefined ? "Disabled / absent" : `${slot.inclination_degrees}° · ${String(slot.bolt_group.row_count)}×${String(slot.bolt_group.bolts_per_row)}`} selected={selection.kind === "MEMBER" && selection.id === `multi-member-tee:${id.toLowerCase()}`} onSelect={() => { if (slot !== undefined) setSelection({ kind: "MEMBER", id: `multi-member-tee:${id.toLowerCase()}` }); }} defaultOpen={id === "UPPER_BRACE"}>
        <label className="field-control tee-checkbox-control"><span>Enable {SLOT_LABELS[id]}</span><input aria-label={`Enable ${SLOT_LABELS[id]}`} type="checkbox" checked={slot !== undefined} disabled={slot !== undefined && activeCount === 1} onChange={(event) => { toggle(id, event.currentTarget.checked); }} /></label>
        {slot === undefined ? <p className="sidebar-note">No hidden request, geometry, bolt group, action, result, or fingerprint is emitted.</p> : <SlotEditor slot={slot} unitSystem={request.unit_system} onChange={(change) => { changeSlot(id, slot, change); }} />}
      </SidebarGroup>; })}
      <SidebarGroup title="Supporting Member" summary={sharedSupportLabel(request.support_target_id)} selected={selection.kind === "MEMBER" && selection.id === "tee-support"} onSelect={() => { setSelection({ kind: "MEMBER", id: "tee-support" }); }}><SupportingMemberEditor targetId={request.support_target_id} profile={request.support_profile} onTargetChange={(target) => { mutate((next) => { next.support_target_id = target; next.support_profile = initialMultiMemberTeeSupport(target, next.unit_system); }); }} onProfileChange={(change) => { mutate((next) => { change(next.support_profile); }); }} /></SidebarGroup>
      <SidebarGroup title="Connector" summary="Pultruded FRP Tee" selected={selection.kind === "MEMBER" && selection.id === "tee-connector"} onSelect={() => { setSelection({ kind: "MEMBER", id: "tee-connector" }); }}><div className="field-grid">{Object.entries(request.connector_dimensions).map(([key, value]) => <QuantityInput key={key} label={`Tee ${friendlyEnum(key)}`} value={value} onChange={(nextValue) => { mutate((next) => { next.connector_dimensions[key as keyof typeof next.connector_dimensions].value = nextValue; }); }} />)}</div></SidebarGroup>
      <SidebarGroup title="Support Bolt Group" summary={`${String(request.support_group.row_count)}×${String(request.support_group.bolts_per_row)}`}><GroupEditor title="Tee Flange to Support" value={request.support_group} onChange={(change) => { mutate((next) => { change(next.support_group); }); }} /></SidebarGroup>
      <SidebarGroup title="Materials / Fasteners" summary="ICE FRP · F593 316"><dl className="diagnostic-list"><div><dt>Members / Tee / support</dt><dd>Pultruded FRP material records</dd></div><div><dt>Fastener</dt><dd>ASTM F593 Group 2 · 316/316L</dd></div></dl><QuantityInput label="Bolt diameter" value={request.bolt_diameter} onChange={(value) => { mutate((next) => { next.bolt_diameter.value = value; }); }} /></SidebarGroup>
      <SidebarGroup title="Joint Equilibrium" summary={result === null ? "Awaiting preview" : "Backend authored"} defaultOpen>{result === null ? <p>Awaiting current backend preview.</p> : <><dl className="diagnostic-list"><div><dt>ΣF (H,V,N)</dt><dd>{result.support_wrench.force.h.value}, {result.support_wrench.force.v.value}, {result.support_wrench.force.n.value} {result.support_wrench.force.h.unit}</dd></div><div><dt>ΣM (H,V,N)</dt><dd>{result.support_wrench.moment.h.value}, {result.support_wrench.moment.v.value}, {result.support_wrench.moment.n.value} {result.support_wrench.moment.h.unit}</dd></div><div><dt>Support reference</dt><dd>{result.support_wrench.reference_point.h.value}, {result.support_wrench.reference_point.v.value}, {result.support_wrench.reference_point.n.value} {result.support_wrench.reference_point.h.unit}</dd></div><div><dt>Wrench fingerprint</dt><dd>{result.support_wrench.wrench_fingerprint}</dd></div><div><dt>Application provenance</dt><dd>{result.support_wrench.application_provenance_fingerprint}</dd></div></dl>{result.support_wrench.contributions.map((item) => <p className="sidebar-note" key={item.slot_id}>{SLOT_LABELS[item.slot_id]} shifted M: ({item.shifted_moment.h.value}, {item.shifted_moment.v.value}, {item.shifted_moment.n.value})</p>)}</>}</SidebarGroup>
      <SidebarGroup title="Model / Geometry Status" summary={friendlyEnum(preview.state)} defaultOpen><strong>{result?.assembly_status ?? "Preview pending"}</strong>{preview.detail === null ? null : <p className="sidebar-note">{preview.detail}</p>}</SidebarGroup>
      <SidebarGroup title="Design Results" summary={design === null ? "No design run" : designStale ? "Stale" : friendlyEnum(design.assembly_status)} defaultOpen><p className="sidebar-note">{design === null ? "Preview executes zero resistance equations." : designStale ? "Prior design is stale after an engineering edit." : `Explicit result: ${friendlyEnum(design.assembly_status)}`}</p>{(design?.result.required_limitations ?? result?.required_limitations ?? []).map((item) => <article className="qualification-banner tee-body-limitation" key={item}><span aria-hidden="true">!</span><div><strong>{friendlyIdentifier(item)}</strong><p>Not evaluated; ordinary whole-connection PASS is prohibited.</p></div></article>)}</SidebarGroup>
      <section className="evaluate-panel sidebar-evaluate"><p>Only this explicit action requests supported resistance handoffs.</p><button type="button" className="primary-button" disabled={bodyMaterial.busy || loading || preview.acceptedRevision !== revision || preview.response?.design_check_ready === false} onClick={() => { void runDesign(); }}>{loading ? "Running design check…" : "Run Design Check"}</button></section>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain><ConnectorBodyMaterialResult state={bodyMaterial} /><PersistentConnectionViewer>{preview.state === "CURRENT_VALID" ? null : <div className="tee-preview-state" role="status"><strong>{friendlyEnum(preview.state)}</strong><span>{preview.detail}</span></div>}{model === null ? <section className="viewer-prompt"><h3>Canonical Multi-Member Tee model unavailable</h3><p>{preview.detail ?? "Waiting for the backend-authoritative preview."}</p></section> : <VisualizationPanel model={model} title="Multi-Member Tee Node" contactSelectionLabel="Selected node member or interface" selection={selection} onSelect={setSelection} actionSourceLabel="Independent backend-resolved slot actions" />}</PersistentConnectionViewer>{designError === null ? null : <div className="error-banner" role="alert">{designError}</div>}{designStale ? <div className="stale-banner" role="status">Design results are stale. Run Design Check after the current preview settles.</div> : null}</ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
