import { ConnectorBodyMaterialControl, ConnectorBodyMaterialResult } from "./connectorBodyMaterial";
import { useConnectorBodyMaterial } from "./useConnectorBodyMaterial";
import { useEffect, useMemo, useRef, useState } from "react";

import type { BeamConcretePairedAngleDesignResponse, BeamConcretePairedAngleR2Request, WallVector, WallWrench } from "../api/beamConcretePairedAngleContracts";
import { EvaluationTransportError, evaluateBeamConcretePairedAngle } from "../api/client";
import type { ClipAngleBoltLayoutRequest } from "../api/clipAngleContracts";
import type { MultiRowQuantity } from "../api/multirowContracts";
import type { PairedProfileFamily } from "../api/pairedClipAngleContracts";
import type { TeeProfileOrientation, TeeProfileSurface } from "../api/teeContracts";
import { BEAM_CONCRETE_PROFILE_FAMILIES, beamConcreteConnectedProfile, loadBeamConcretePairedAngleBenchmark } from "../fixtures/beamConcretePairedAngleBenchmarks";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { buildBeamConcretePairedAngleSceneModel } from "../visualization/beamConcretePairedAngleSceneModel";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import { useBeamConcretePairedAnglePreview } from "./beamConcretePairedAngleWorkflow";
import { ConnectionWorkspaceMain, ConnectionWorkspaceShell, ConnectionWorkspaceSidebar, PersistentConnectionViewer, SidebarGroup } from "./ConnectionWorkspaceShell";
import { PAIRED_SURFACES } from "./pairedClipAngleOptions";
import { formatDisplayQuantity, friendlyEnum } from "./presentation";
import { PROFILE_SURFACE_LABELS, TEE_PROFILE_DEFINITIONS } from "./teeProfileOptions";

function DecimalField({ label, quantity, onChange }: { readonly label: string; readonly quantity: MultiRowQuantity; readonly onChange: (value: string) => void }) {
  return <label className="field-control"><span>{label}</span><span className="input-with-unit"><input aria-label={label} type="text" inputMode="decimal" value={quantity.value} onChange={(event) => { onChange(event.currentTarget.value); }} /><small>{quantity.unit}</small></span></label>;
}

function LayoutEditor({ layout, onChange }: { readonly layout: ClipAngleBoltLayoutRequest; readonly onChange: (change: (next: ClipAngleBoltLayoutRequest) => void) => void }) {
  const integer = (label: string, key: "row_count" | "bolts_per_row") => <label className="field-control"><span>{label}</span><input aria-label={`Common beam ${label}`} type="number" min="1" step="1" value={layout[key]} onChange={(event) => { const value = Number(event.currentTarget.value); onChange((next) => { next[key] = value; }); }} /></label>;
  const quantity = (label: string, key: "pitch" | "gauge" | "heel_edge_distance" | "free_edge_distance" | "negative_end_distance" | "positive_end_distance") => <DecimalField label={`Common beam ${label}`} quantity={layout[key]} onChange={(value) => { onChange((next) => { next[key].value = value; }); }} />;
  return <div className="field-grid">{integer("rows", "row_count")}{integer("bolts per row", "bolts_per_row")}{quantity("pitch", "pitch")}{quantity("gauge", "gauge")}{quantity("heel edge distance", "heel_edge_distance")}{quantity("free edge distance", "free_edge_distance")}{quantity("negative end distance", "negative_end_distance")}{quantity("positive end distance", "positive_end_distance")}</div>;
}

function WrenchCard({ title, value, system }: { readonly title: string; readonly value: WallWrench; readonly system: "US_CUSTOMARY" | "SI" }) {
  const vector = (item: WallVector) => wallVectorText(item, system);
  return <article className="source-card compact-source-card"><h4>{title}</h4><dl className="diagnostic-list"><div><dt>Reference H/V/N</dt><dd>{vector(value.reference_hvn)}</dd></div><div><dt>Force H/V/N</dt><dd>{vector(value.force_hvn)}</dd></div><div><dt>Eccentricity-induced transfer moment H/V/N</dt><dd>{vector(value.moment_hvn)}</dd></div></dl></article>;
}

function wallVectorText(value: WallVector, system: "US_CUSTOMARY" | "SI"): string {
  return `(${formatDisplayQuantity(value.h, system)}, ${formatDisplayQuantity(value.v, system)}, ${formatDisplayQuantity(value.n, system)})`;
}

function localValidation(request: BeamConcretePairedAngleR2Request): string | null {
  const numeric = [request.wall.width.value, request.wall.height.value, request.wall.thickness.value, request.beam_end_gap.value, request.external_anchor.specified_embedment.value, request.major_shear.value, request.minor_shear.value, request.axial_force.value].map(Number);
  if (numeric.some((value) => !Number.isFinite(value))) return "Wall, gap, embedment, and force fields must be finite decimal values.";
  const [width = Number.NaN, height = Number.NaN, thickness = Number.NaN, gap = Number.NaN, embedment = Number.NaN] = numeric;
  if (width <= 0 || height <= 0 || thickness <= 0) return "Concrete wall dimensions must be positive.";
  if (gap < 0) return "Member end gap must be nonnegative.";
  if (embedment <= 0) return "External anchor embedment must be positive.";
  return null;
}

export function BeamConcretePairedAngleWorkspace() {
  const [request, setRequest] = useState<BeamConcretePairedAngleR2Request>(() => loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY"));
  const [revision, setRevision] = useState(0);
  const [design, setDesign] = useState<BeamConcretePairedAngleDesignResponse | null>(null);
  const [designError, setDesignError] = useState<EvaluationTransportError | null>(null);
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [copyStatus, setCopyStatus] = useState("");
  const [selection, setSelection] = useState<SceneSelection>({ kind: "MEMBER", id: "clip-angle-connected-member" });
  const designController = useRef<AbortController | null>(null);
  useEffect(() => () => { designController.current?.abort(); }, []);
  const validationMessage = localValidation(request);
  const previewInput = useMemo(() => ({ request, revision, immediate: revision === 0, validationMessage }), [request, revision, validationMessage]);
  const preview = useBeamConcretePairedAnglePreview(previewInput);
  const result = preview.response?.result ?? null;
  const model = useMemo(() => result?.visualization === null || result?.visualization === undefined ? null : buildBeamConcretePairedAngleSceneModel(result.visualization, request.beam_profile.profile_family), [request.beam_profile.profile_family, result]);
  const update = (change: (next: BeamConcretePairedAngleR2Request) => void) => {
    designController.current?.abort();
    designController.current = null;
    setLoading(false);
    setRequest((current) => { const next = structuredClone(current); change(next); return next; });
    setRevision((value) => value + 1);
    setStale(design !== null);
    setDesignError(null);
  };
  const loadBenchmark = (system: "US_CUSTOMARY" | "SI") => { setRequest(loadBeamConcretePairedAngleBenchmark(system)); setRevision((value) => value + 1); setStale(design !== null); };
  const bodyMaterial = useConnectorBodyMaterial("beam-concrete-paired-angle", request, revision, () => {
    designController.current?.abort(); designController.current = null; setLoading(false); setDesign(null); setDesignError(null); setStale(true);
  });
  const runDesign = async () => {
    if (bodyMaterial.material === "SS316") { await bodyMaterial.run(); return; }
    designController.current?.abort();
    const controller = new AbortController();
    designController.current = controller;
    setLoading(true);
    try {
      const response = await evaluateBeamConcretePairedAngle(request, controller.signal);
      if (designController.current !== controller) return;
      setDesign(response); setStale(false);
    } catch (caught) {
      if (!controller.signal.aborted) setDesignError(caught instanceof EvaluationTransportError ? caught : new EvaluationTransportError("RESPONSE", null, "Unexpected design-check failure.", caught));
    } finally { if (designController.current === controller) { designController.current = null; setLoading(false); } }
  };
  const copyHandoff = async () => {
    /* v8 ignore next -- the rendered action is disabled until a current backend handoff exists */
    if (result === null) return;
    await navigator.clipboard.writeText(result.external_anchor_handoff_json);
    setCopyStatus("Copied full-precision backend handoff JSON.");
  };
  const downloadHandoff = () => {
    /* v8 ignore next -- the rendered action is disabled until a current backend handoff exists */
    if (result === null) return;
    const url = URL.createObjectURL(new Blob([result.external_anchor_handoff_json], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${request.request_id}-external-anchor-handoff.json`; anchor.click(); URL.revokeObjectURL(url);
  };
  const previewMessage = preview.state === "CURRENT_VALID" ? "Current backend wall/connection geometry" : preview.state === "PREVIEW_PENDING" ? "Preview updating" : preview.state === "CURRENT_INVALID_SHOWING_LAST_VALID" ? "Current geometry invalid — showing last valid preview" : preview.state === "PREVIEW_FAILED_SHOWING_LAST_VALID" ? "Preview unavailable — showing last valid preview" : "No valid backend preview";
  const q = (label: string, target: MultiRowQuantity, set: (next: BeamConcretePairedAngleR2Request, value: string) => void) => <DecimalField label={label} quantity={target} onChange={(value) => { update((next) => { set(next, value); }); }} />;
  const profileDefinition = TEE_PROFILE_DEFINITIONS[request.beam_profile.profile_family];
  const profileField = (key: string, label: string) => {
    const target = request.beam_profile.dimensions[key];
    /* v8 ignore next -- the controlled family definitions and strict profile union share the same dimension keys */
    if (target === undefined) throw new Error(`Missing controlled ${key} profile dimension.`);
    return q(label, target, (next, value) => {
      const quantity = next.beam_profile.dimensions[key];
      /* v8 ignore next -- profile changes replace the entire strict family object before render */
      if (quantity !== undefined) quantity.value = value;
    });
  };
  const shown = design === null || stale ? result : design.result.preview;
  const handoffFingerprint = typeof result?.external_anchor_handoff.handoff_fingerprint === "string" ? result.external_anchor_handoff.handoff_fingerprint : "Pending";
  const anchorDistribution = result?.limitations.some(([name, status]) => name === "WALL_ANCHOR_INTERNAL_FORCE_DISTRIBUTION" && status === "EXTERNAL_DESIGN_REQUIRED") === true ? "EXTERNAL_DESIGN_REQUIRED" : "Nominal coordination trace available";
  const handoffMode = result?.handoff_mode ?? "BRANCH_RESOLVED";
  const userForce = result?.visualization?.user_force_hvn;
  const zeroMoment = result?.visualization?.user_moment_hvn;
  return <ConnectionWorkspaceShell className="clip-angle-workspace paired-clip-angle-workspace beam-concrete-workspace" banner={<section className="workspace-banner"><div><p className="eyebrow">Stage 3.5A-R2 · Shear-category external-anchor handoff</p><h2>Beam connection — Paired clip angles to concrete wall</h2><p>Backend-authoritative FRP connection design with concrete and anchor capacity designed elsewhere.</p></div><div className="benchmark-actions"><button type="button" className="secondary-button" onClick={() => { loadBenchmark("US_CUSTOMARY"); }}>Load R2 U.S.</button><button type="button" className="secondary-button" onClick={() => { loadBenchmark("SI"); }}>Load R2 SI</button></div></section>}>
    <ConnectionWorkspaceSidebar ariaLabel="Beam-to-concrete paired clip-angle engineering properties">
      <ConnectorBodyMaterialControl material={bodyMaterial.material} onChange={bodyMaterial.choose} />
      <SidebarGroup title="General / Case" summary="3.5A-R2-RC1" defaultOpen><dl className="diagnostic-list"><div><dt>Connection</dt><dd>Symmetric paired FRP clip angles</dd></div><div><dt>Anchor design authority</dt><dd>External specialty anchor software</dd></div></dl></SidebarGroup>
      <SidebarGroup title="Connected Member" summary={`${profileDefinition.label} · horizontal`} defaultOpen><label className="field-control"><span>Profile family</span><select aria-label="Concrete-wall connected profile family" value={request.beam_profile.profile_family} onChange={(event) => { const family = event.currentTarget.value as PairedProfileFamily; update((next) => { next.beam_profile = beamConcreteConnectedProfile(next.unit_system, family); }); }}>{BEAM_CONCRETE_PROFILE_FAMILIES.map((family) => <option key={family} value={family}>{TEE_PROFILE_DEFINITIONS[family].label}</option>)}</select></label><div className="field-grid">{profileDefinition.dimensions.map((field) => <span key={field.key}>{profileField(field.key, field.label)}</span>)}{q("Member end gap", request.beam_end_gap, (next, value) => { next.beam_end_gap.value = value; })}</div><label className="field-control"><span>Connected profile surface</span><select aria-label="Concrete-wall connected profile surface" value={request.beam_profile.selected_profile_surface} onChange={(event) => { const surface = event.currentTarget.value as TeeProfileSurface; update((next) => { next.beam_profile.selected_profile_surface = surface; }); }}>{PAIRED_SURFACES[request.beam_profile.profile_family].map((surface) => <option key={surface} value={surface}>{PROFILE_SURFACE_LABELS[surface]}</option>)}</select></label><label className="field-control"><span>Profile roll</span><select aria-label="Concrete-wall connected profile roll" value={request.beam_profile.profile_orientation} onChange={(event) => { const orientation = event.currentTarget.value as TeeProfileOrientation; update((next) => { next.beam_profile.profile_orientation = orientation; }); }}>{(["ROTATION_0", "ROTATION_90", "ROTATION_180", "ROTATION_270"] as const).map((orientation) => <option key={orientation} value={orientation}>{orientation.replace("ROTATION_", "")}°</option>)}</select></label><p className="sidebar-note">The connected member remains horizontal; profile roll changes only the selected physical section orientation.</p></SidebarGroup>
      <SidebarGroup title="Concrete Wall" summary="Finite coordination prism" defaultOpen><div className="field-grid">{q("Wall width", request.wall.width, (next, value) => { next.wall.width.value = value; })}{q("Wall height", request.wall.height, (next, value) => { next.wall.height.value = value; })}{q("Wall thickness", request.wall.thickness, (next, value) => { next.wall.thickness.value = value; })}{q("Connection origin H", request.wall.connection_origin_h, (next, value) => { next.wall.connection_origin_h.value = value; })}{q("Connection origin V", request.wall.connection_origin_v, (next, value) => { next.wall.connection_origin_v.value = value; })}</div><p className="sidebar-note">Concrete has no FRP LW/CW/TT material axes.</p></SidebarGroup>
      <SidebarGroup title="Paired Clip-Angle Connector" summary="Locked identical mirror"><div className="field-grid">{q("Connected-leg width", request.connector_dimensions.connected_leg_width, (next, value) => { next.connector_dimensions.connected_leg_width.value = value; })}{q("Wall-leg width", request.connector_dimensions.support_leg_width, (next, value) => { next.connector_dimensions.support_leg_width.value = value; })}{q("Angle thickness", request.connector_dimensions.thickness, (next, value) => { next.connector_dimensions.thickness.value = value; })}{q("Angle length", request.connector_dimensions.connector_length, (next, value) => { next.connector_dimensions.connector_length.value = value; })}</div></SidebarGroup>
      <SidebarGroup title="Connected Member ↔ Paired Clip Angles" summary="One physical common through-bolt group"><LayoutEditor layout={request.common_beam_layout} onChange={(change) => { update((next) => { change(next.common_beam_layout); }); }} /><div className="field-grid">{q("Common bolt diameter", request.common_bolt_diameter, (next, value) => { next.common_bolt_diameter.value = value; })}{q("Common hole diameter", request.common_hole_diameter, (next, value) => { next.common_hole_diameter.value = value; })}</div></SidebarGroup>
      <SidebarGroup title="Mirrored Wall Anchor Groups" summary="Pattern edited once · exact mirror"><div className="field-grid"><label className="field-control"><span>Rows</span><input aria-label="Wall anchor rows" type="number" min="1" value={request.wall_anchor_pattern.row_count} onChange={(event) => { const value = Number(event.currentTarget.value); update((next) => { next.wall_anchor_pattern.row_count = value; }); }} /></label><label className="field-control"><span>Anchors per row</span><input aria-label="Wall anchors per row" type="number" min="1" value={request.wall_anchor_pattern.anchors_per_row} onChange={(event) => { const value = Number(event.currentTarget.value); update((next) => { next.wall_anchor_pattern.anchors_per_row = value; }); }} /></label>{q("Wall anchor pitch", request.wall_anchor_pattern.pitch, (next, value) => { next.wall_anchor_pattern.pitch.value = value; })}{q("Wall anchor gauge", request.wall_anchor_pattern.gauge, (next, value) => { next.wall_anchor_pattern.gauge.value = value; })}{q("Group centroid ±H", request.wall_anchor_pattern.centroid_offset_h, (next, value) => { next.wall_anchor_pattern.centroid_offset_h.value = value; })}{q("Group centroid V", request.wall_anchor_pattern.centroid_v, (next, value) => { next.wall_anchor_pattern.centroid_v.value = value; })}</div></SidebarGroup>
      <SidebarGroup title="External Anchor Geometry" summary="Capacity designed elsewhere"><div className="field-grid">{q("Anchor diameter", request.external_anchor.nominal_diameter, (next, value) => { next.external_anchor.nominal_diameter.value = value; })}{q("Clip-angle anchor hole", request.external_anchor.hole_diameter, (next, value) => { next.external_anchor.hole_diameter.value = value; })}{q("Specified coordination embedment", request.external_anchor.specified_embedment, (next, value) => { next.external_anchor.specified_embedment.value = value; })}{q("Washer outside diameter", request.external_anchor.washer_outside_diameter, (next, value) => { next.external_anchor.washer_outside_diameter.value = value; })}{q("Washer thickness", request.external_anchor.washer_thickness, (next, value) => { next.external_anchor.washer_thickness.value = value; })}</div><p className="sidebar-note">Exterior nut/washer and blind embedded shank only. No far-side hardware.</p></SidebarGroup>
      <SidebarGroup title="Loads" summary="Three signed wall-frame force components" defaultOpen><div className="field-grid">{q("Major shear", request.major_shear, (next, value) => { next.major_shear.value = value; })}{q("Minor shear", request.minor_shear, (next, value) => { next.minor_shear.value = value; })}{q("Axial force", request.axial_force, (next, value) => { next.axial_force.value = value; })}</div><p className="sidebar-note">Major + is wall vertical +V_W. Minor + is wall horizontal +H_W. Axial + is +N_W, pulling away from the wall. No user-applied moments; eccentricity-induced transfer moments remain in the handoff.</p></SidebarGroup>
      <SidebarGroup title="Wall / Anchor Design Handoff" summary="External design required" defaultOpen><div className="benchmark-actions"><button type="button" disabled={result === null} onClick={() => { void copyHandoff(); }}>Copy JSON</button><button type="button" disabled={result === null} onClick={downloadHandoff}>Download JSON</button></div><p className="sidebar-note" role="status">{copyStatus || "Full-precision backend payload; no frontend wrench calculation."}</p><dl className="diagnostic-list"><div><dt>Handoff mode</dt><dd>{handoffMode === "BRANCH_RESOLVED" ? "Branch-resolved" : "Combined layout — branch allocation NOT_EVALUATED"}</dd></div><div><dt>Handoff fingerprint</dt><dd>{handoffFingerprint}</dd></div><div><dt>Anchor/concrete design</dt><dd>EXTERNAL_DESIGN_REQUIRED</dd></div><div><dt>Internal anchor-force distribution</dt><dd>{anchorDistribution}</dd></div></dl></SidebarGroup>
      <SidebarGroup title="Materials / Fasteners" summary="FRP + F593 + external anchors"><dl className="diagnostic-list"><div><dt>Connected member / angles</dt><dd>ICE locked pultruded FRP · region-embedded axes</dd></div><div><dt>Common bolts</dt><dd>316SS ASTM F593</dd></div><div><dt>Wall anchors</dt><dd>External system classification only</dd></div></dl></SidebarGroup>
      <SidebarGroup title="Geometry / Design Results" summary={design === null ? "No design run" : stale ? "Stale" : friendlyEnum(design.assembly_status)}><dl className="diagnostic-list"><div><dt>Geometry/model</dt><dd>{previewMessage}</dd></div><div><dt>Design status</dt><dd>{design === null ? "Run Design Check" : stale ? "Stale" : friendlyEnum(design.assembly_status)}</dd></div><div><dt>Ordinary PASS</dt><dd>Prohibited</dd></div><div><dt>External design</dt><dd>Required</dd></div><div><dt>Engineering fingerprint</dt><dd>{result?.engineering_fingerprint ?? "Pending"}</dd></div></dl></SidebarGroup>
      <SidebarGroup title="Advanced / Diagnostics" summary="Exact frames and provenance"><dl className="diagnostic-list"><div><dt>Wall frame</dt><dd>H_W × V_W = N_W</dd></div><div><dt>Input force H/V/N</dt><dd>{userForce === undefined ? "Pending" : wallVectorText(userForce, request.unit_system)}</dd></div><div><dt>User moment H/V/N</dt><dd>{zeroMoment === undefined ? "(0, 0, 0)" : wallVectorText(zeroMoment, request.unit_system)}</dd></div><div><dt>Selected profile</dt><dd>{request.beam_profile.profile_family}</dd></div><div><dt>Selected surface</dt><dd>{request.beam_profile.selected_profile_surface}</dd></div><div><dt>Connected-member reference</dt><dd>Backend authoritative</dd></div><div><dt>Preview resistance calls</dt><dd>0</dd></div></dl></SidebarGroup>
      <section className="evaluate-panel sidebar-evaluate"><p>Run Design Check evaluates only accepted beam/FRP checks. Concrete and anchors remain external.</p><button type="button" className="primary-button" disabled={bodyMaterial.busy || loading || validationMessage !== null || preview.state !== "CURRENT_VALID" || result?.design_check_ready !== true} onClick={() => { void runDesign(); }}>{loading ? "Running design check…" : "Run Design Check"}</button>{validationMessage === null ? null : <p className="sidebar-note" role="status">{validationMessage}</p>}</section>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain><ConnectorBodyMaterialResult state={bodyMaterial} /><PersistentConnectionViewer><div className={`tee-preview-state tee-preview-state-${preview.state.toLowerCase()}`} role="status"><strong>{previewMessage}</strong>{preview.invalidDetail === null ? null : <span>{preview.invalidDetail}</span>}</div>{model === null ? <section className="viewer-prompt"><h3>Canonical beam-to-concrete model unavailable</h3><p>{preview.invalidDetail ?? previewMessage}</p></section> : <VisualizationPanel model={model} title="Beam connection — Paired clip angles to concrete wall" contactSelectionLabel="Selected concrete wall/anchor interface" selection={selection} onSelect={setSelection} appliedActionInputValues={{ FX: request.minor_shear.value, FY: request.axial_force.value, FZ: request.major_shear.value, MX: "0", MY: "0", MZ: "0" }} onAppliedActionValueChange={(component, value) => { if (component === "FX" || component === "FY" || component === "FZ") update((next) => { if (component === "FX") next.minor_shear.value = value; else if (component === "FY") next.axial_force.value = value; else next.major_shear.value = value; }); }} actionSourceLabel="Applied wall-frame force" />}</PersistentConnectionViewer>{preview.error === null ? null : <div className="error-banner" role="alert"><strong>{preview.error.message}</strong><button type="button" onClick={preview.retry}>Retry preview</button></div>}{designError === null ? null : <div className="error-banner" role="alert">{designError.message}</div>}{stale ? <div className="stale-banner" role="status">Design results are stale. Run Design Check after the current backend preview is valid.</div> : null}<section className="tee-results-grid" aria-label="Beam-to-concrete wall transfer results">{shown === null ? <p>No current beam-to-concrete result.</p> : <>{shown.positive_wall_group.wrench === null || shown.negative_wall_group.wrench === null ? <article className="source-card compact-source-card"><h4>Paired branch allocation</h4><p>NOT_EVALUATED for nonzero Minor shear. The complete combined wall wrench and both owner-qualified anchor layouts are retained for external design.</p></article> : <><WrenchCard title="Positive wall-anchor group" value={shown.positive_wall_group.wrench} system={request.unit_system} /><WrenchCard title="Negative wall-anchor group" value={shown.negative_wall_group.wrench} system={request.unit_system} /></>}<WrenchCard title="Combined wall-interface handoff" value={shown.combined_wall_wrench} system={request.unit_system} /><article className="qualification-banner tee-body-limitation"><span aria-hidden="true">!</span><div><strong>Concrete and external-anchor capacity · Not calculated</strong><p>Specialized anchor software must independently verify anchor forces, steel strength, concrete limit states, edge and spacing effects, and product qualification.</p></div></article></>}</section></ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
