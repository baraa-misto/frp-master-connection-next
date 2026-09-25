import { viewerUnity } from "./unityRatio";
import { useEffect, useMemo, useRef, useState } from "react";

import type {
  DirectSideLapConcreteRequest,
  DirectSideLapDesignResponse,
  DirectSideLapProfileFamily,
  SideLapVector,
  SideLapWrench,
} from "../api/directSideLapConcreteContracts";
import { EvaluationTransportError, evaluateDirectSideLapConcrete } from "../api/client";
import type { MultiRowQuantity } from "../api/multirowContracts";
import {
  directSideLapProfile,
  loadDirectSideLapConcreteBenchmark,
} from "../fixtures/directSideLapConcreteBenchmarks";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { buildDirectSideLapConcreteSceneModel } from "../visualization/directSideLapConcreteSceneModel";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import {
  ConnectionWorkspaceMain,
  ConnectionWorkspaceShell,
  ConnectionWorkspaceSidebar,
  PersistentConnectionViewer,
  SidebarGroup,
} from "./ConnectionWorkspaceShell";
import { useDirectSideLapConcretePreview } from "./directSideLapConcreteWorkflow";
import { formatDisplayQuantity } from "./presentation";
import { PROFILE_SURFACE_LABELS, TEE_PROFILE_DEFINITIONS } from "./teeProfileOptions";

function DecimalField(props: {
  readonly label: string;
  readonly quantity: MultiRowQuantity;
  readonly onChange: (value: string) => void;
}) {
  return <label className="field-control"><span>{props.label}</span><span className="input-with-unit"><input aria-label={props.label} type="text" inputMode="decimal" value={props.quantity.value} onChange={(event) => { props.onChange(event.currentTarget.value); }} /><small>{props.quantity.unit}</small></span></label>;
}

function vectorText(value: SideLapVector, system: "US_CUSTOMARY" | "SI"): string {
  return `(${formatDisplayQuantity(value.l, system)}, ${formatDisplayQuantity(value.s, system)}, ${formatDisplayQuantity(value.n, system)})`;
}

function WrenchCard(props: { readonly value: SideLapWrench; readonly system: "US_CUSTOMARY" | "SI" }) {
  return <article className="source-card compact-source-card"><h4>Direct wall anchor-group transfer</h4><dl className="diagnostic-list"><div><dt>Reference L/S/N</dt><dd>{vectorText(props.value.reference_lsn, props.system)}</dd></div><div><dt>Force L/S/N</dt><dd>{vectorText(props.value.force_lsn, props.system)}</dd></div><div><dt>Generated moment L/S/N</dt><dd>{vectorText(props.value.moment_lsn, props.system)}</dd></div></dl></article>;
}

function localValidation(request: DirectSideLapConcreteRequest): string | null {
  const positive = [request.wall.run_length, request.wall.transverse_width, request.wall.thickness, request.side_lap_length, request.member_projection_beyond_wall, request.anchor_pattern.pitch, request.anchor_pattern.gauge, request.anchor_pattern.centroid_distance_behind_free_end, request.external_anchor.nominal_diameter, request.external_anchor.hole_diameter, request.external_anchor.specified_embedment].map((item) => Number(item.value));
  if (positive.some((value) => !Number.isFinite(value))) return "Geometry and anchor fields must be finite decimal values.";
  if (positive.some((value) => value <= 0)) return "Wall, overlap, member, and anchor dimensions must be positive.";
  if (request.anchor_pattern.row_count < 1 || request.anchor_pattern.anchors_per_row < 1) return "Anchor rows and anchors per row must be positive integers.";
  return null;
}

export function DirectSideLapConcreteWorkspace() {
  const [request, setRequest] = useState<DirectSideLapConcreteRequest>(() => loadDirectSideLapConcreteBenchmark("US_CUSTOMARY"));
  const [revision, setRevision] = useState(0);
  const [design, setDesign] = useState<DirectSideLapDesignResponse | null>(null);
  const [designError, setDesignError] = useState<EvaluationTransportError | null>(null);
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [copyStatus, setCopyStatus] = useState("");
  const [selection, setSelection] = useState<SceneSelection>({ kind: "MEMBER", id: "direct-side-lap-connected-member" });
  const designController = useRef<AbortController | null>(null);
  useEffect(() => () => { designController.current?.abort(); }, []);
  const validationMessage = localValidation(request);
  const preview = useDirectSideLapConcretePreview(useMemo(() => ({ request, revision, immediate: revision === 0, validationMessage }), [request, revision, validationMessage]));
  const result = preview.response?.result ?? null;
  const model = useMemo(() => result?.visualization === null || result?.visualization === undefined ? null : buildDirectSideLapConcreteSceneModel(result.visualization), [result]);
  const update = (change: (next: DirectSideLapConcreteRequest) => void) => {
    designController.current?.abort(); designController.current = null; setLoading(false);
    setRequest((current) => { const next = structuredClone(current); change(next); return next; });
    setRevision((value) => value + 1); setStale(design !== null); setDesignError(null);
  };
  const loadBenchmark = (system: "US_CUSTOMARY" | "SI") => {
    setRequest(loadDirectSideLapConcreteBenchmark(system)); setRevision((value) => value + 1); setStale(design !== null);
  };
  const runDesign = async () => {
    designController.current?.abort();
    const controller = new AbortController(); designController.current = controller; setLoading(true);
    try {
      const response = await evaluateDirectSideLapConcrete(request, controller.signal);
      if (designController.current !== controller) return;
      setDesign(response); setStale(false);
    } catch (caught) {
      if (!controller.signal.aborted) setDesignError(caught instanceof EvaluationTransportError ? caught : new EvaluationTransportError("RESPONSE", null, "Unexpected direct side-lap design failure.", caught));
    } finally { if (designController.current === controller) { designController.current = null; setLoading(false); } }
  };
  const q = (label: string, target: MultiRowQuantity, set: (next: DirectSideLapConcreteRequest, value: string) => void) => <DecimalField label={label} quantity={target} onChange={(value) => { update((next) => { set(next, value); }); }} />;
  const profileDefinition = TEE_PROFILE_DEFINITIONS[request.connected_profile.profile_family];
  const profileField = (key: string, label: string) => {
    const target = request.connected_profile.dimensions[key];
    /* v8 ignore next -- controlled family definitions and strict profile dimensions share the same keys */
    if (target === undefined) throw new Error(`Missing controlled ${key} profile dimension.`);
    return q(label, target, (next, value) => { const quantity = next.connected_profile.dimensions[key]; /* v8 ignore next -- rendered controls retain their declared profile dimension */ if (quantity !== undefined) quantity.value = value; });
  };
  const centerAnchorGroup = () => {
    const centered = Number(request.side_lap_length.value) / 2;
    if (Number.isFinite(centered)) update((next) => { next.anchor_pattern.centroid_distance_behind_free_end.value = String(centered); });
  };
  const copyHandoff = async () => { /* v8 ignore next -- the rendered action is disabled until a current backend handoff exists */ if (result === null) return; await navigator.clipboard.writeText(result.external_anchor_handoff_json); setCopyStatus("Copied full-precision external anchor handoff JSON."); };
  const downloadHandoff = () => {
    /* v8 ignore next -- the rendered action is disabled until a current backend handoff exists */
    if (result === null) return;
    const url = URL.createObjectURL(new Blob([result.external_anchor_handoff_json], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${request.request_id}-direct-side-lap-anchor-handoff.json`; anchor.click(); URL.revokeObjectURL(url);
  };
  const shown = design === null || stale ? result : design.result.preview;
  const previewMessage = preview.state === "CURRENT_VALID" ? "Current backend finite-wall / overlap geometry" : preview.state === "PREVIEW_PENDING" ? "Preview updating" : preview.state === "CURRENT_INVALID_SHOWING_LAST_VALID" ? "Current geometry invalid — showing last valid preview" : preview.state === "PREVIEW_FAILED_SHOWING_LAST_VALID" ? "Preview unavailable — showing last valid preview" : "No valid backend preview";
  return <ConnectionWorkspaceShell family="direct-side-lap-concrete" className="clip-angle-workspace beam-concrete-workspace direct-side-lap-workspace" banner={<section className="workspace-banner"><div><p className="eyebrow">Stage 3.5B · Direct side-lap external-anchor handoff</p><h2>Brace/beam connection — Direct side-lap Angle/Channel to concrete wall</h2><p>Finite wall free end, physical overlap, and exact transferred wrench; concrete and anchor capacity remain external.</p></div><div className="benchmark-actions"><button type="button" className="secondary-button" onClick={() => { loadBenchmark("US_CUSTOMARY"); }}>Load 3.5B U.S.</button><button type="button" className="secondary-button" onClick={() => { loadBenchmark("SI"); }}>Load 3.5B SI</button></div></section>}>
    <ConnectionWorkspaceSidebar ariaLabel="Direct side-lap concrete-wall engineering properties">
      <SidebarGroup title="General / Case" summary="3.5B-RC1" defaultOpen><dl className="diagnostic-list"><div><dt>Connection</dt><dd>Direct FRP Angle/Channel side lap</dd></div><div><dt>Anchor design</dt><dd>External specialty anchor software</dd></div></dl></SidebarGroup>
      <SidebarGroup title="Connected Member" summary={`${profileDefinition.label} · side lap`} defaultOpen><label className="field-control"><span>Profile family</span><select aria-label="Direct side-lap profile family" value={request.connected_profile.profile_family} onChange={(event) => { const family = event.currentTarget.value as DirectSideLapProfileFamily; update((next) => { next.connected_profile = directSideLapProfile(next.unit_system, family); }); }}><option value="CHANNEL">Channel</option><option value="ANGLE">Angle</option></select></label><div className="field-grid">{profileDefinition.dimensions.filter((field) => field.key !== "member_length").map((field) => <span key={field.key}>{profileField(field.key, field.label)}</span>)}{q("Side-lap length", request.side_lap_length, (next, value) => { next.side_lap_length.value = value; })}{q("Member projection beyond wall", request.member_projection_beyond_wall, (next, value) => { next.member_projection_beyond_wall.value = value; })}</div>{request.connected_profile.profile_family === "ANGLE" ? <label className="field-control"><span>Selected Angle leg to wall</span><select aria-label="Selected Angle leg to wall" value={request.connected_profile.selected_profile_surface} onChange={(event) => { const surface = event.currentTarget.value as "LEG_Y_OUTER" | "LEG_Z_OUTER"; update((next) => { next.connected_profile.selected_profile_surface = surface; }); }}><option value="LEG_Y_OUTER">{PROFILE_SURFACE_LABELS.LEG_Y_OUTER}</option><option value="LEG_Z_OUTER">{PROFILE_SURFACE_LABELS.LEG_Z_OUTER}</option></select></label> : <p className="sidebar-note">Channel contact is locked to the web. Flange-to-wall placement is rejected.</p>}</SidebarGroup>
      <SidebarGroup title="Concrete Wall / Free End" summary="Finite L ≤ 0" defaultOpen><div className="field-grid">{q("Wall run behind free end", request.wall.run_length, (next, value) => { next.wall.run_length.value = value; })}{q("Wall transverse width", request.wall.transverse_width, (next, value) => { next.wall.transverse_width.value = value; })}{q("Wall thickness", request.wall.thickness, (next, value) => { next.wall.thickness.value = value; })}</div><p className="sidebar-note">The authoritative wall free-end plane is L = 0. The member continues into L &gt; 0 while concrete stops.</p></SidebarGroup>
      <SidebarGroup title="Direct Wall Anchor Group" summary="Fixed unless explicitly centered" defaultOpen><div className="field-grid"><label className="field-control"><span>Rows</span><input aria-label="Direct anchor rows" type="number" min="1" value={request.anchor_pattern.row_count} onChange={(event) => { const value = Number(event.currentTarget.value); update((next) => { next.anchor_pattern.row_count = value; }); }} /></label><label className="field-control"><span>Anchors per row</span><input aria-label="Direct anchors per row" type="number" min="1" value={request.anchor_pattern.anchors_per_row} onChange={(event) => { const value = Number(event.currentTarget.value); update((next) => { next.anchor_pattern.anchors_per_row = value; }); }} /></label>{q("Anchor pitch", request.anchor_pattern.pitch, (next, value) => { next.anchor_pattern.pitch.value = value; })}{q("Anchor gauge", request.anchor_pattern.gauge, (next, value) => { next.anchor_pattern.gauge.value = value; })}{q("Anchor group distance behind wall free end", request.anchor_pattern.centroid_distance_behind_free_end, (next, value) => { next.anchor_pattern.centroid_distance_behind_free_end.value = value; })}{q("Anchor group transverse offset", request.anchor_pattern.transverse_offset, (next, value) => { next.anchor_pattern.transverse_offset.value = value; })}</div><button type="button" className="secondary-button" onClick={centerAnchorGroup}>Center anchor group in overlap</button><p className="sidebar-note">Changing side-lap length never moves anchors. Centering occurs only from this explicit action.</p></SidebarGroup>
      <SidebarGroup title="External Anchor Geometry" summary="Capacity designed elsewhere"><div className="field-grid">{q("Anchor diameter", request.external_anchor.nominal_diameter, (next, value) => { next.external_anchor.nominal_diameter.value = value; })}{q("FRP anchor hole", request.external_anchor.hole_diameter, (next, value) => { next.external_anchor.hole_diameter.value = value; })}{q("Specified embedment", request.external_anchor.specified_embedment, (next, value) => { next.external_anchor.specified_embedment.value = value; })}{q("Washer outside diameter", request.external_anchor.washer_outside_diameter, (next, value) => { next.external_anchor.washer_outside_diameter.value = value; })}{q("Washer thickness", request.external_anchor.washer_thickness, (next, value) => { next.external_anchor.washer_thickness.value = value; })}</div></SidebarGroup>
      <SidebarGroup title="Applied Forces" summary="Axial / Major / Minor · zero user moments" defaultOpen><div className="field-grid">{q("Axial force (+L)", request.axial_force, (next, value) => { next.axial_force.value = value; })}{q("Major shear (+S)", request.major_shear, (next, value) => { next.major_shear.value = value; })}{q("Minor shear (+N)", request.minor_shear, (next, value) => { next.minor_shear.value = value; })}</div><p className="sidebar-note">User-applied moments are not accepted. Every eccentricity-induced anchor-group moment is retained.</p></SidebarGroup>
      <SidebarGroup title="External Handoff" summary="Full precision"><div className="benchmark-actions"><button type="button" className="secondary-button" disabled={result === null} onClick={() => { void copyHandoff(); }}>Copy handoff JSON</button><button type="button" className="secondary-button" disabled={result === null} onClick={downloadHandoff}>Download handoff JSON</button></div>{copyStatus === "" ? null : <p role="status">{copyStatus}</p>}</SidebarGroup>
      <section className="evaluate-connection-action"><button type="button" className="primary-action" disabled={loading || preview.state !== "CURRENT_VALID"} onClick={() => { void runDesign(); }}>{loading ? "Running design check…" : "Run Design Check"}</button>{validationMessage === null ? null : <p className="sidebar-note" role="status">{validationMessage}</p>}</section>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain><PersistentConnectionViewer unity={viewerUnity("direct-side-lap", design, { stale, checking: loading, error: designError, previewState: preview.state })}><div className={`tee-preview-state tee-preview-state-${preview.state.toLowerCase()}`} role="status"><strong>{previewMessage}</strong>{preview.invalidDetail === null ? null : <span>{preview.invalidDetail}</span>}</div>{model === null ? <section className="viewer-prompt"><h3>Canonical direct side-lap model unavailable</h3><p>{preview.invalidDetail ?? previewMessage}</p></section> : <VisualizationPanel model={model} title="Direct side-lap Angle/Channel to concrete wall" contactSelectionLabel="Selected FRP/contact face and finite wall free end" selection={selection} onSelect={setSelection} appliedActionInputValues={{ FX: request.axial_force.value, FY: request.minor_shear.value, FZ: request.major_shear.value, MX: "0", MY: "0", MZ: "0" }} onAppliedActionValueChange={(component, value) => { if (component === "FX" || component === "FY" || component === "FZ") update((next) => { if (component === "FX") next.axial_force.value = value; else if (component === "FY") next.minor_shear.value = value; else next.major_shear.value = value; }); }} actionSourceLabel="Applied side-lap-frame force" />}</PersistentConnectionViewer>{preview.error === null ? null : <div className="error-banner" role="alert"><strong>{preview.error.message}</strong><button type="button" onClick={preview.retry}>Retry preview</button></div>}{designError === null ? null : <div className="error-banner" role="alert">{designError.message}</div>}{stale ? <div className="stale-banner" role="status">Design results are stale. Run Design Check after the current backend preview is valid.</div> : null}<section className="tee-results-grid" aria-label="Direct side-lap transfer results">{shown === null ? <p>No current direct side-lap result.</p> : <><WrenchCard value={shown.anchor_group_wrench} system={request.unit_system} /><article className="qualification-banner tee-body-limitation"><span aria-hidden="true">!</span><div><strong>Concrete, anchors, pull-through, and unsupported response · Not calculated</strong><p>The exact complete group wrench is exported for external anchor design. No ordinary whole-connection PASS is issued.</p></div></article></>}</section></ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
