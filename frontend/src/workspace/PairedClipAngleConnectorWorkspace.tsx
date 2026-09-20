import { ConnectorBodyMaterialControl, ConnectorBodyMaterialResult } from "./connectorBodyMaterial";
import { useConnectorBodyMaterial } from "./useConnectorBodyMaterial";
import { useEffect, useMemo, useRef, useState } from "react";

import { EvaluationTransportError, evaluatePairedClipAngle } from "../api/client";
import type { ClipAngleBoltLayoutRequest } from "../api/clipAngleContracts";
import type { MultiRowQuantity } from "../api/multirowContracts";
import type {
  PairedBoltGroupResult,
  PairedClipAngleDesignResponse,
  PairedClipAngleRequest,
  PairedProfileFamily,
} from "../api/pairedClipAngleContracts";
import type { TeeProfileSurface } from "../api/teeContracts";
import {
  initialSharedSupport,
  sharedSupportLabel,
} from "../api/sharedSupportContracts";
import { loadPairedClipAngleWorkspaceDefault } from "../fixtures/connectionWorkspaceDefaults";
import { loadPairedClipAngleBenchmark } from "../fixtures/pairedClipAngleBenchmarks";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { buildPairedClipAngleSceneModel } from "../visualization/pairedClipAngleSceneModel";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import {
  ConnectionWorkspaceMain,
  ConnectionWorkspaceShell,
  ConnectionWorkspaceSidebar,
  PersistentConnectionViewer,
  SidebarGroup,
} from "./ConnectionWorkspaceShell";
import { pairedClipAngleValidationMessage } from "./pairedClipAngleValidation";
import { PAIRED_PROFILE_FAMILIES, PAIRED_SURFACES } from "./pairedClipAngleOptions";
import { usePairedClipAnglePreview } from "./pairedClipAngleWorkflow";
import { SupportingMemberEditor } from "./SupportingMemberEditor";
import { formatDisplayQuantity, friendlyEnum, friendlyIdentifier } from "./presentation";
import {
  initialConnectedMemberProfile,
  PROFILE_SURFACE_LABELS,
  TEE_PROFILE_DEFINITIONS,
} from "./teeProfileOptions";

function pairedProfile(
  unit: "in" | "mm",
  family: PairedProfileFamily,
): PairedClipAngleRequest["connected_member_profile"] {
  const source = initialConnectedMemberProfile(unit, family);
  return {
    profile_id: "paired-clip-angle-connected-member-profile",
    role: "BRACE",
    profile_family: family,
    size_basis: "CUSTOM_DIMENSIONS",
    dimensions: source.dimensions,
    profile_orientation: source.profile_orientation,
    selected_profile_surface: PAIRED_SURFACES[family].slice(0, 1).join("") as TeeProfileSurface,
  };
}

function DecimalField({ label, quantity, onChange }: {
  readonly label: string;
  readonly quantity: MultiRowQuantity;
  readonly onChange: (value: string) => void;
}) {
  return <label className="field-control"><span>{label}</span><span className="input-with-unit"><input aria-label={label} type="text" inputMode="decimal" value={quantity.value} onChange={(event) => { onChange(event.currentTarget.value); }} /><small>{quantity.unit}</small></span></label>;
}

function BoltGroupEditor({ title, layout, onChange }: {
  readonly title: string;
  readonly layout: ClipAngleBoltLayoutRequest;
  readonly onChange: (change: (next: ClipAngleBoltLayoutRequest) => void) => void;
}) {
  const numeric = (label: string, key: "row_count" | "bolts_per_row") => (
    <label className="field-control"><span>{label}</span><input aria-label={`${title} ${label}`} type="number" min="1" step="1" value={layout[key]} onChange={(event) => { const value = Number(event.currentTarget.value); onChange((next) => { next[key] = value; }); }} /></label>
  );
  const quantity = (label: string, key: "pitch" | "gauge" | "heel_edge_distance" | "free_edge_distance" | "negative_end_distance" | "positive_end_distance") => (
    <DecimalField label={`${title} ${label}`} quantity={layout[key]} onChange={(value) => { onChange((next) => { next[key].value = value; }); }} />
  );
  return <div className="field-grid">{numeric("Rows", "row_count")}{numeric("Bolts per row", "bolts_per_row")}{quantity("Pitch", "pitch")}{quantity("Gauge", "gauge")}{quantity("Heel edge distance", "heel_edge_distance")}{quantity("Free edge distance", "free_edge_distance")}{quantity("Negative end distance", "negative_end_distance")}{quantity("Positive end distance", "positive_end_distance")}</div>;
}

function GroupResultCard({ value }: { readonly value: PairedBoltGroupResult }) {
  const perBolt = value.demand?.scenarios[0]?.per_bolt[0]?.total_force_magnitude;
  const handoff = value.resistance?.automatic_handoff_results[0] ?? null;
  return <article className="source-card compact-source-card"><div className="card-title"><div><p className="eyebrow">{friendlyIdentifier(value.group_id)}</p><h4>{value.physical_name}</h4></div><span className="locked-badge">{handoff === null ? "PREVIEW" : friendlyEnum(handoff.overall_disposition)}</span></div><dl className="property-grid"><div><dt>Physical bolts</dt><dd>{value.placement.bolts.length}</dd></div><div><dt>Per-bolt demand</dt><dd>{perBolt === undefined ? "Unavailable" : formatDisplayQuantity(perBolt, perBolt.unit === "kip" ? "US_CUSTOMARY" : "SI")}</dd></div><div><dt>Layer allocations</dt><dd>{value.layer_demands.length}</dd></div><div><dt>Minimum clearance</dt><dd>{formatDisplayQuantity(value.placement.clearances.minimum, value.placement.clearances.minimum.unit === "in" ? "US_CUSTOMARY" : "SI")}</dd></div></dl></article>;
}

export function PairedClipAngleConnectorWorkspace() {
  const [request, setRequest] = useState<PairedClipAngleRequest>(() => loadPairedClipAngleWorkspaceDefault("US_CUSTOMARY"));
  const [revision, setRevision] = useState(0);
  const [design, setDesign] = useState<PairedClipAngleDesignResponse | null>(null);
  const [designError, setDesignError] = useState<EvaluationTransportError | null>(null);
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [selection, setSelection] = useState<SceneSelection>({ kind: "MEMBER", id: "SYMMETRIC_PAIRED_CLIP_ANGLES" });
  const designController = useRef<AbortController | null>(null);
  useEffect(() => () => { designController.current?.abort(); }, []);

  const validation = pairedClipAngleValidationMessage(request);
  const previewInput = useMemo(() => ({ request, revision, immediate: revision === 0, validationMessage: validation }), [request, revision, validation]);
  const preview = usePairedClipAnglePreview(previewInput);
  const result = preview.response?.result ?? null;
  const model = useMemo(() => {
    const visualization = preview.response?.result.visualization;
    return visualization === null || visualization === undefined ? null : buildPairedClipAngleSceneModel(visualization);
  }, [preview.response]);

  const cancelDesign = () => {
    designController.current?.abort();
    designController.current = null;
    setLoading(false);
  };
  const update = (change: (next: PairedClipAngleRequest) => void) => {
    cancelDesign();
    setRequest((current) => { const next = structuredClone(current); change(next); return next; });
    setRevision((value) => value + 1);
    if (design !== null) setStale(true);
    setDesignError(null);
  };
  const loadBenchmark = (system: "US_CUSTOMARY" | "SI") => {
    cancelDesign();
    setRequest(loadPairedClipAngleBenchmark(system));
    setRevision((value) => value + 1);
    setStale(design !== null);
    setDesignError(null);
  };
  const bodyMaterial = useConnectorBodyMaterial("paired-clip-angle", request, revision, () => {
    cancelDesign(); setDesign(null); setDesignError(null); setStale(true);
  });
  const runDesign = async () => {
    if (bodyMaterial.material === "SS316") { await bodyMaterial.run(); return; }
    cancelDesign();
    const controller = new AbortController();
    designController.current = controller;
    setLoading(true);
    try {
      const response = await evaluatePairedClipAngle(request, controller.signal);
      if (designController.current !== controller) return;
      setDesign(response);
      setStale(false);
    } catch (caught) {
      if (controller.signal.aborted) return;
      setDesignError(caught instanceof EvaluationTransportError ? caught : new EvaluationTransportError("RESPONSE", null, "Unexpected paired clip-angle design failure.", caught));
    } finally {
      if (designController.current === controller) {
        designController.current = null;
        setLoading(false);
      }
    }
  };
  const quantityField = (label: string, group: "connector_dimensions", key: string) => {
    const quantity = (request[group] as unknown as Record<string, MultiRowQuantity>)[key];
    /* v8 ignore next -- fixed declared controls retain their dimension key */
    if (quantity === undefined) throw new Error(`Missing paired clip-angle dimension ${key}.`);
    return <DecimalField label={label} quantity={quantity} onChange={(value) => { update((next) => { const target = (next[group] as unknown as Record<string, MultiRowQuantity>)[key]; /* v8 ignore next -- fixed declared controls retain their target */ if (target !== undefined) target.value = value; }); }} />;
  };
  const profileDefinition = TEE_PROFILE_DEFINITIONS[request.connected_member_profile.profile_family];
  const profileField = (key: string, label: string) => {
    const quantity = request.connected_member_profile.dimensions[key];
    /* v8 ignore next -- registry dimension definitions and request data are paired */
    if (quantity === undefined) throw new Error(`Missing paired connected-profile dimension ${key}.`);
    return <DecimalField label={label} quantity={quantity} onChange={(value) => { update((next) => { const target = next.connected_member_profile.dimensions[key]; /* v8 ignore next -- registry and request remain paired */ if (target !== undefined) target.value = value; }); }} />;
  };
  const changeLayout = (key: "common_member_layout" | "mirrored_support_layout", change: (next: ClipAngleBoltLayoutRequest) => void) => { update((next) => { change(next[key]); }); };
  const previewMessage = preview.state === "CURRENT_VALID" ? "Current backend paired geometry" : preview.state === "PREVIEW_PENDING" ? "Preview updating" : preview.state === "CURRENT_INVALID_SHOWING_LAST_VALID" ? "Current geometry invalid — showing last valid preview" : preview.state === "PREVIEW_FAILED_SHOWING_LAST_VALID" ? "Preview unavailable — showing last valid preview" : "No valid backend preview";
  const designReady = validation === null && preview.state === "CURRENT_VALID" && result?.design_check_ready === true;
  const shown = design === null || stale ? result : design.result.preview;
  const title = `${profileDefinition.label} Brace → Symmetric Paired FRP Clip Angles → ${sharedSupportLabel(request.support_target_id)}`;

  return <ConnectionWorkspaceShell className="clip-angle-workspace paired-clip-angle-workspace" banner={<section className="workspace-banner"><div><p className="eyebrow">Stage 3.3C3 · Symmetric Paired FRP Clip Angles</p><h2>{title}</h2><p>One backend-authoritative mirrored pair with a common member through-bolt group.</p></div><div className="benchmark-actions"><button type="button" className="secondary-button" onClick={() => { loadBenchmark("US_CUSTOMARY"); }}>Load G1 U.S.</button><button type="button" className="secondary-button" onClick={() => { loadBenchmark("SI"); }}>Load G1 SI</button></div></section>}>
    <ConnectionWorkspaceSidebar ariaLabel="Symmetric paired clip-angle engineering properties">
      <ConnectorBodyMaterialControl material={bodyMaterial.material} onChange={bodyMaterial.choose} />
      <SidebarGroup title="Connection" summary="One locked identical mirror pair" defaultOpen><dl className="diagnostic-list"><div><dt>Assembly</dt><dd>Symmetric paired clip angles</dd></div><div><dt>Pair frame</dt><dd>S/P/L · symmetry plane S = 0</dd></div><div><dt>Distribution</dt><dd>Equal sharing only after proof</dd></div></dl></SidebarGroup>
      <SidebarGroup title="Connected Member" summary={`${profileDefinition.label} Brace`} defaultOpen><label className="field-control"><span>Profile family</span><select aria-label="Paired connected profile family" value={request.connected_member_profile.profile_family} onChange={(event) => { const family = event.currentTarget.value as PairedProfileFamily; update((next) => { next.connected_member_profile = pairedProfile(next.source_length_unit, family); }); }}>{PAIRED_PROFILE_FAMILIES.map((family) => <option key={family} value={family}>{TEE_PROFILE_DEFINITIONS[family].label}</option>)}</select></label><div className="field-grid">{profileDefinition.dimensions.map((field) => <span key={field.key}>{profileField(field.key, field.label)}</span>)}</div><label className="field-control"><span>Paired contact surfaces</span><select aria-label="Paired connected profile surface" value={request.connected_member_profile.selected_profile_surface} onChange={(event) => { const surface = event.currentTarget.value as TeeProfileSurface; update((next) => { next.connected_member_profile.selected_profile_surface = surface; }); }}>{PAIRED_SURFACES[request.connected_member_profile.profile_family].map((surface) => <option key={surface} value={surface}>{PROFILE_SURFACE_LABELS[surface]}</option>)}</select></label><DecimalField label="Connected-member inclination" quantity={{ value: request.connected_member_inclination_degrees, unit: "deg" }} onChange={(value) => { update((next) => { next.connected_member_inclination_degrees = value; }); }} /><label className="field-control tee-checkbox-control"><span>Apply end trim clearance</span><input aria-label="Apply paired end trim clearance" type="checkbox" checked={request.connected_member_end_trim_enabled} onChange={(event) => { const enabled = event.currentTarget.checked; update((next) => { next.connected_member_end_trim_enabled = enabled; next.connected_member_end_clearance = enabled ? { value: "0", unit: next.source_length_unit } : null; }); }} /></label>{request.connected_member_end_clearance === null ? null : <DecimalField label="End clearance to paired clip-angle support legs" quantity={request.connected_member_end_clearance} onChange={(value) => { update((next) => { /* v8 ignore next -- visible trim field owns non-null clearance */ if (next.connected_member_end_clearance !== null) next.connected_member_end_clearance.value = value; }); }} />}</SidebarGroup>
      <SidebarGroup title="Supporting Member" summary={sharedSupportLabel(request.support_target_id)}><SupportingMemberEditor targetId={request.support_target_id} profile={request.support_profile} onTargetChange={(target) => { update((next) => { next.support_target_id = target; next.support_profile = initialSharedSupport(target, next.source_length_unit, "paired-clip-angle-support"); }); }} onProfileChange={(change) => { update((next) => { change(next.support_profile); }); }} /></SidebarGroup>
      <SidebarGroup title="Connector Pair" summary="Positive + negative identical FRP angles" defaultOpen><div className="field-grid">{quantityField("Connected-leg width", "connector_dimensions", "connected_leg_width")}{quantityField("Support-leg width", "connector_dimensions", "support_leg_width")}{quantityField("Angle thickness", "connector_dimensions", "thickness")}{quantityField("Pair length", "connector_dimensions", "connector_length")}</div><DecimalField label="Pair longitudinal position" quantity={request.connector_length_anchor_position} onChange={(value) => { update((next) => { next.connector_length_anchor_position.value = value; }); }} /></SidebarGroup>
      <SidebarGroup title="Common Member Bolt Group" summary="One physical three-layer through-bolt group"><BoltGroupEditor title="Common member group" layout={request.common_member_layout} onChange={(change) => { changeLayout("common_member_layout", change); }} /></SidebarGroup>
      <SidebarGroup title="Mirrored Support Bolt Groups" summary="One group per physical angle"><BoltGroupEditor title="Mirrored support groups" layout={request.mirrored_support_layout} onChange={(change) => { changeLayout("mirrored_support_layout", change); }} /></SidebarGroup>
      <SidebarGroup title="Materials" summary="Four independent angle-leg regions"><dl className="diagnostic-list"><div><dt>Positive angle</dt><dd>Connected + support leg LW/CW/TT</dd></div><div><dt>Negative angle</dt><dd>Exact mirrored region bases</dd></div><div><dt>Connected profile</dt><dd>Backend-authored embedded axes</dd></div></dl></SidebarGroup>
      <SidebarGroup title="Fasteners" summary="316SS · ASTM F593"><div className="field-grid"><DecimalField label="Common bolt diameter" quantity={request.bolt_diameter} onChange={(value) => { update((next) => { next.bolt_diameter.value = value; }); }} /><DecimalField label="Hole diameter" quantity={request.hole_diameter} onChange={(value) => { update((next) => { next.hole_diameter.value = value; }); }} /></div><p className="sidebar-note">Common bolts span positive angle, connected member, and negative angle. No internal hardware.</p></SidebarGroup>
      <SidebarGroup title="Loads" summary="Pure reaction shear symmetry gate" defaultOpen><div className="field-grid">{(["x", "y", "z"] as const).map((axis) => <DecimalField key={`paired-force-${axis}`} label={`Force ${axis.toUpperCase()}`} quantity={{ value: request.global_force[axis], unit: request.global_force.unit }} onChange={(value) => { update((next) => { next.global_force[axis] = value; }); }} />)}{(["x", "y", "z"] as const).map((axis) => <DecimalField key={`paired-moment-${axis}`} label={`Moment ${axis.toUpperCase()}`} quantity={{ value: request.global_moment[axis], unit: request.global_moment.unit }} onChange={(value) => { update((next) => { next.global_moment[axis] = value; }); }} />)}{(["x", "y", "z"] as const).map((axis) => <DecimalField key={`paired-reference-${axis}`} label={`Reference ${axis.toUpperCase()}`} quantity={{ value: request.global_reference_point[axis], unit: request.global_reference_point.unit }} onChange={(value) => { update((next) => { next.global_reference_point[axis] = value; }); }} />)}</div></SidebarGroup>
      <SidebarGroup title="Results / Diagnostics" summary={design === null ? "No design run" : stale ? "Stale" : friendlyEnum(design.assembly_status)}><dl className="diagnostic-list"><div><dt>Geometry/model</dt><dd>{previewMessage}</dd></div><div><dt>Geometry symmetry</dt><dd>{result?.symmetry_proof.geometry_proven === true ? "Proven" : "Not proven"}</dd></div><div><dt>Action symmetry</dt><dd>{result?.symmetry_proof.action_proven === true ? "Proven" : "Not proven"}</dd></div><div><dt>Equal sharing</dt><dd>{result?.symmetry_proof.equal_sharing_eligible === true ? "Eligible" : "Not proven"}</dd></div><div><dt>Design status</dt><dd>{design === null ? "Run Design Check" : stale ? "Stale" : friendlyEnum(design.assembly_status)}</dd></div><div><dt>Required limitations</dt><dd>Not evaluated</dd></div><div><dt>Engineering fingerprint</dt><dd>{result?.engineering_fingerprint ?? "Pending"}</dd></div><div><dt>Result fingerprint</dt><dd>{design?.result_fingerprint ?? "Pending"}</dd></div></dl></SidebarGroup>
      <section className="evaluate-panel sidebar-evaluate" aria-label="Paired clip-angle design-check controls"><p>Preview resolves geometry, symmetry, actions, and demand only. Resistance runs only on explicit request.</p><button type="button" className="primary-button" disabled={bodyMaterial.busy || loading || !designReady} onClick={() => { void runDesign(); }}>{loading ? "Running design check…" : "Run Design Check"}</button>{validation === null ? null : <p className="sidebar-note" role="status">{validation}</p>}</section>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain><ConnectorBodyMaterialResult state={bodyMaterial} /><PersistentConnectionViewer><div className={`tee-preview-state tee-preview-state-${preview.state.toLowerCase()}`} role="status" aria-live="polite"><strong>{previewMessage}</strong>{preview.invalidDetail === null ? null : <span>{preview.invalidDetail}</span>}</div>{model === null ? <section className="viewer-prompt"><h3>Canonical paired clip-angle model unavailable</h3><p>{preview.invalidDetail ?? previewMessage}</p></section> : <VisualizationPanel model={model} title={title} contactSelectionLabel="Selected paired clip-angle contact surface" selection={selection} onSelect={setSelection} appliedActionInputValues={{ FX: request.global_force.x, FY: request.global_force.y, FZ: request.global_force.z, MX: request.global_moment.x, MY: request.global_moment.y, MZ: request.global_moment.z }} onAppliedActionValueChange={(component, value) => { const key = component.slice(1).toLowerCase() as "x" | "y" | "z"; update((next) => { if (component.startsWith("F")) next.global_force[key] = value; else next.global_moment[key] = value; }); }} actionSourceLabel="Canonical symmetric-pair parent action" />}</PersistentConnectionViewer>{preview.error === null ? null : <div className="error-banner" role="alert"><strong>{preview.invalidDetail ?? preview.error.message}</strong><button type="button" onClick={preview.retry}>Retry preview</button></div>}{designError === null ? null : <div className="error-banner" role="alert">{designError.message}</div>}{stale ? <div className="stale-banner" role="status">Design results are stale. Run Design Check after the current backend preview is valid.</div> : null}<section className="tee-results-grid" aria-label="Symmetric paired clip-angle grouped results">{shown === null ? <p>No current paired clip-angle result.</p> : <><GroupResultCard value={shown.common_member_group} /><GroupResultCard value={shown.positive_support_group} /><GroupResultCard value={shown.negative_support_group} /><article className="qualification-banner tee-body-limitation"><span aria-hidden="true">!</span><div><strong>Paired connector body and common double shear · Not evaluated</strong><p>Supported numerical interface failures govern FAIL. Paired body, common metallic double-shear, branch compatibility, and whole-system qualification prohibit ordinary PASS in RC1.</p></div></article></>}</section></ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
