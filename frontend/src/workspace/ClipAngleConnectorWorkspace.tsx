import { viewerUnity } from "./unityRatio";
import { ConnectorBodyMaterialControl, ConnectorBodyMaterialResult } from "./connectorBodyMaterial";
import { useConnectorBodyMaterial } from "./useConnectorBodyMaterial";
import { useEffect, useMemo, useRef, useState } from "react";

import { evaluateClipAngle, EvaluationTransportError } from "../api/client";
import type {
  ClipAngleBoltLayoutRequest,
  ClipAngleDesignResponse,
  ClipAngleInterfaceResult,
  ClipAngleRequest,
} from "../api/clipAngleContracts";
import type { MultiRowQuantity } from "../api/multirowContracts";
import type { TeeProfileFamily, TeeProfileSurface } from "../api/teeContracts";
import {
  initialSharedSupport,
  sharedSupportLabel,
  type SharedSupportTargetId,
} from "../api/sharedSupportContracts";
import { loadClipAngleWorkspaceDefault } from "../fixtures/connectionWorkspaceDefaults";
import { loadClipAngleC2Benchmark } from "../fixtures/clipAngleBenchmarks";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { buildClipAngleSceneModel } from "../visualization/clipAngleSceneModel";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import {
  ConnectionWorkspaceMain,
  ConnectionWorkspaceShell,
  ConnectionWorkspaceSidebar,
  PersistentConnectionViewer,
  SidebarGroup,
} from "./ConnectionWorkspaceShell";
import { clipAngleValidationMessage } from "./clipAngleValidation";
import { useClipAnglePreview } from "./clipAngleWorkflow";
import { SupportingMemberEditor } from "./SupportingMemberEditor";
import { formatDisplayQuantity, friendlyEnum, friendlyIdentifier } from "./presentation";
import {
  initialConnectedMemberProfile,
  PROFILE_SURFACE_LABELS,
  TEE_PROFILE_DEFINITIONS,
  TEE_PROFILE_FAMILIES,
} from "./teeProfileOptions";

const CLIP_PROFILE_FAMILIES = TEE_PROFILE_FAMILIES.filter(
  (family): family is Exclude<TeeProfileFamily, "ROUND_HOLLOW_SECTION"> => (
    family !== "ROUND_HOLLOW_SECTION"
  ),
);

function connectedProfile(
  unit: "in" | "mm",
  family: Exclude<TeeProfileFamily, "ROUND_HOLLOW_SECTION"> = "FLAT_PLATE",
): ClipAngleRequest["connected_member_profile"] {
  const source = initialConnectedMemberProfile(unit, family);
  return {
    profile_id: "clip-angle-connected-member-profile",
    role: "BRACE",
    profile_family: family,
    size_basis: "CUSTOM_DIMENSIONS",
    dimensions: source.dimensions,
    profile_orientation: source.profile_orientation,
    selected_profile_surface: source.selected_profile_surface,
  };
}

function initialRequest(): ClipAngleRequest {
  return loadClipAngleWorkspaceDefault("US_CUSTOMARY");
}

function DecimalField({ label, quantity, onChange }: {
  readonly label: string;
  readonly quantity: MultiRowQuantity;
  readonly onChange: (value: string) => void;
}) {
  return (
    <label className="field-control">
      <span>{label}</span>
      <span className="input-with-unit">
        <input
          aria-label={label}
          type="text"
          inputMode="decimal"
          value={quantity.value}
          onChange={(event) => { onChange(event.currentTarget.value); }}
        />
        <small>{quantity.unit}</small>
      </span>
    </label>
  );
}

function BoltGroupEditor({
  title,
  value,
  result,
  onChange,
}: {
  readonly title: string;
  readonly value: ClipAngleBoltLayoutRequest;
  readonly result: ClipAngleInterfaceResult | null;
  readonly onChange: (change: (layout: ClipAngleBoltLayoutRequest) => void) => void;
}) {
  const offsetMode = value.placement_mode === "GROUP_OFFSET_CONTROLLED";
  const lengthOffset = value.length_offset ?? null;
  const widthOffset = value.width_offset ?? null;
  const quantityField = (
    label: string,
    key: "pitch" | "gauge" | "heel_edge_distance" | "free_edge_distance" | "negative_end_distance" | "positive_end_distance",
  ) => (
    <DecimalField
      label={`${title} ${label}`}
      quantity={value[key]}
      onChange={(next) => { onChange((layout) => { layout[key].value = next; }); }}
    />
  );
  return (
    <SidebarGroup title={title} summary={`${String(value.row_count)} × ${String(value.bolts_per_row)}`} defaultOpen>
      <section className="tee-placement-section" aria-label={`${title} bolt pattern`}>
        <h4>Bolt Pattern</h4>
        <div className="field-grid">
          <label className="field-control"><span>Rows</span><input aria-label={`${title} rows`} type="number" min="1" value={value.row_count} onChange={(event) => { const count = Number(event.currentTarget.value); onChange((layout) => { layout.row_count = count; }); }} /></label>
          <label className="field-control"><span>Bolts per row</span><input aria-label={`${title} bolts per row`} type="number" min="1" value={value.bolts_per_row} onChange={(event) => { const count = Number(event.currentTarget.value); onChange((layout) => { layout.bolts_per_row = count; }); }} /></label>
          {quantityField("Pitch", "pitch")}
          {quantityField("Gauge", "gauge")}
        </div>
      </section>
      <section className="tee-placement-section" aria-label={`${title} bolt group position`}>
        <h4>Bolt Group Position</h4>
        {offsetMode && lengthOffset !== null && widthOffset !== null
          ? <div className="field-grid"><DecimalField label={`${title} length offset`} quantity={lengthOffset} onChange={(next) => { onChange((layout) => { const target = layout.length_offset; /* v8 ignore next -- rendered offset mode owns both exact offsets */ if (target !== null && target !== undefined) target.value = next; }); }} /><DecimalField label={`${title} width offset`} quantity={widthOffset} onChange={(next) => { onChange((layout) => { const target = layout.width_offset; /* v8 ignore next -- rendered offset mode owns both exact offsets */ if (target !== null && target !== undefined) target.value = next; }); }} /></div>
          : <p className="sidebar-note">Positioning: edge-distance controlled</p>}
        <button type="button" className="secondary-button center-bolt-group" onClick={() => { onChange((layout) => { layout.placement_mode = "GROUP_OFFSET_CONTROLLED"; layout.length_offset = { value: "0", unit: layout.pitch.unit }; layout.width_offset = { value: "0", unit: layout.gauge.unit }; }); }}>Center bolt group</button>
      </section>
      <section className="tee-placement-section" aria-label={`${title} computed clearances`}>
        <h4>Computed Clearances</h4>
        {result === null ? <p className="sidebar-note">Awaiting backend-authoritative clearances.</p> : <dl className="diagnostic-list"><div><dt>Heel</dt><dd>{formatDisplayQuantity(result.placement.clearances.heel, result.placement.clearances.heel.unit === "in" ? "US_CUSTOMARY" : "SI")}</dd></div><div><dt>Free edge</dt><dd>{formatDisplayQuantity(result.placement.clearances.free_edge, result.placement.clearances.free_edge.unit === "in" ? "US_CUSTOMARY" : "SI")}</dd></div><div><dt>+L end</dt><dd>{formatDisplayQuantity(result.placement.clearances.positive_length_end, result.placement.clearances.positive_length_end.unit === "in" ? "US_CUSTOMARY" : "SI")}</dd></div><div><dt>−L end</dt><dd>{formatDisplayQuantity(result.placement.clearances.negative_length_end, result.placement.clearances.negative_length_end.unit === "in" ? "US_CUSTOMARY" : "SI")}</dd></div><div><dt>Governing</dt><dd>{friendlyIdentifier(result.placement.clearances.governing_boundary_id)}</dd></div></dl>}
      </section>
      <details className="tee-advanced-placement">
        <summary>Advanced Placement</summary>
        <div className="tee-advanced-placement-body">
          <label className="field-control"><span>Placement method</span><select aria-label={`${title} placement method`} value={offsetMode ? "GROUP_OFFSET_CONTROLLED" : "EDGE_DISTANCE_CONTROLLED"} onChange={(event) => { const mode = event.currentTarget.value as "EDGE_DISTANCE_CONTROLLED" | "GROUP_OFFSET_CONTROLLED"; onChange((layout) => { layout.placement_mode = mode; if (mode === "GROUP_OFFSET_CONTROLLED") { layout.length_offset = { value: "0", unit: layout.pitch.unit }; layout.width_offset = { value: "0", unit: layout.gauge.unit }; } else { layout.length_offset = null; layout.width_offset = null; } }); }}><option value="EDGE_DISTANCE_CONTROLLED">Edge-distance controlled</option><option value="GROUP_OFFSET_CONTROLLED">Bolt-group offsets</option></select></label>
          {offsetMode ? null : <div className="field-grid">{quantityField("Heel edge distance", "heel_edge_distance")}{quantityField("Free-edge distance", "free_edge_distance")}{quantityField("Negative end distance", "negative_end_distance")}{quantityField("Positive end distance", "positive_end_distance")}</div>}
        </div>
      </details>
    </SidebarGroup>
  );
}

function InterfaceCard({ value }: { readonly value: ClipAngleInterfaceResult }) {
  const scenario = value.demand.scenarios[0];
  const handoff = value.resistance?.automatic_handoff_results[0] ?? null;
  return (
    <article className="source-card compact-source-card">
      <div className="card-title"><div><p className="eyebrow">{friendlyIdentifier(value.bolt_group_id)}</p><h4>{value.physical_name}</h4></div><span className="locked-badge">{handoff === null ? "PREVIEW" : friendlyEnum(handoff.overall_disposition)}</span></div>
      <dl className="property-grid">
        <div><dt>Normal action</dt><dd>{formatDisplayQuantity(value.normal_component, value.normal_component.unit === "kip" ? "US_CUSTOMARY" : "SI")}</dd></div>
        <div><dt>Normal path</dt><dd>{value.normal_action_supported ? "No normal requirement" : "Not evaluated"}</dd></div>
        <div><dt>Demand method</dt><dd>{friendlyEnum(value.demand.availability)}</dd></div>
        <div><dt>Method applicability</dt><dd>{friendlyEnum(value.demand.method_applicability)}</dd></div>
        <div><dt>Qualification</dt><dd>{friendlyEnum(value.demand.qualification)}</dd></div>
        <div><dt>Per-bolt demand</dt><dd>{scenario?.per_bolt[0] === undefined ? "Unavailable" : formatDisplayQuantity(scenario.per_bolt[0].total_force_magnitude, scenario.per_bolt[0].total_force_magnitude.unit === "kip" ? "US_CUSTOMARY" : "SI")}</dd></div>
        <div><dt>Resistance handoff</dt><dd>{handoff === null ? "Run Design Check" : friendlyEnum(handoff.coverage)}</dd></div>
        <div><dt>Minimum geometry clearance</dt><dd>{formatDisplayQuantity(value.placement.clearances.minimum, value.placement.clearances.minimum.unit === "in" ? "US_CUSTOMARY" : "SI")}</dd></div>
      </dl>
    </article>
  );
}

export function ClipAngleConnectorWorkspace() {
  const [request, setRequest] = useState<ClipAngleRequest>(initialRequest);
  const [revision, setRevision] = useState(0);
  const [design, setDesign] = useState<ClipAngleDesignResponse | null>(null);
  const [designError, setDesignError] = useState<EvaluationTransportError | null>(null);
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [selection, setSelection] = useState<SceneSelection>({ kind: "MEMBER", id: "single-clip-angle-connector" });
  const designController = useRef<AbortController | null>(null);
  useEffect(() => () => { designController.current?.abort(); }, []);

  const localValidation = clipAngleValidationMessage(request);
  const previewInput = useMemo(() => ({
    request,
    revision,
    immediate: revision === 0,
    validationMessage: localValidation,
  }), [localValidation, request, revision]);
  const preview = useClipAnglePreview(previewInput);
  const model = useMemo(() => {
    const visualization = preview.response?.result.visualization;
    return visualization === null || visualization === undefined
      ? null
      : buildClipAngleSceneModel(visualization);
  }, [preview.response]);

  const cancelDesign = () => {
    designController.current?.abort();
    designController.current = null;
    setLoading(false);
  };
  const update = (change: (next: ClipAngleRequest) => void) => {
    cancelDesign();
    setRequest((current) => {
      const next = structuredClone(current);
      change(next);
      return next;
    });
    setRevision((value) => value + 1);
    if (design !== null) setStale(true);
    setDesignError(null);
  };
  const loadBenchmark = (system: "US_CUSTOMARY" | "SI") => {
    cancelDesign();
    setRequest(loadClipAngleC2Benchmark(system));
    setRevision((value) => value + 1);
    setStale(design !== null);
    setDesignError(null);
  };
  const bodyMaterial = useConnectorBodyMaterial("clip-angle", request, revision, () => {
    designController.current?.abort(); designController.current = null; setLoading(false); setDesign(null); setDesignError(null); setStale(true);
  });
  const runDesign = async () => {
    if (bodyMaterial.material === "SS316") { await bodyMaterial.run(); return; }
    cancelDesign();
    const controller = new AbortController();
    designController.current = controller;
    setLoading(true);
    try {
      const result = await evaluateClipAngle(request, controller.signal);
      if (designController.current !== controller) return;
      setDesign(result);
      setStale(false);
    } catch (caught) {
      if (controller.signal.aborted) return;
      setDesignError(caught instanceof EvaluationTransportError
        ? caught
        : new EvaluationTransportError("RESPONSE", null, "Unexpected clip-angle design failure.", caught));
    } finally {
      if (designController.current === controller) {
        designController.current = null;
        setLoading(false);
      }
    }
  };

  const result = preview.response?.result ?? null;
  const designReady = localValidation === null
    && preview.state === "CURRENT_VALID"
    && result?.design_check_ready === true;
  const profileDefinition = TEE_PROFILE_DEFINITIONS[request.connected_member_profile.profile_family];
  const supportLabel = sharedSupportLabel(request.support_target_id);
  const connectedLabel = `${profileDefinition.label} ${request.connected_member_profile.role === "BRACE" ? "Brace" : "Beam"}`;
  const title = `${connectedLabel} → Single FRP Clip Angle → ${supportLabel}`;
  const quantityField = (
    label: string,
    group: "connector_dimensions",
    key: string,
  ) => {
    const value = (request[group] as unknown as Record<string, MultiRowQuantity>)[key];
    /* v8 ignore next -- fixed controls only request declared dimension keys */
    if (value === undefined) throw new Error(`Missing clip-angle dimension ${key}.`);
    return <DecimalField label={label} quantity={value} onChange={(nextValue) => { update((next) => { const target = (next[group] as unknown as Record<string, MultiRowQuantity>)[key]; /* v8 ignore next -- fixed controls retain the declared target */ if (target !== undefined) target.value = nextValue; }); }} />;
  };
  const profileField = (key: string, label: string) => {
    const value = request.connected_member_profile.dimensions[key];
    /* v8 ignore next -- selected registry keys and dimensions are created together */
    if (value === undefined) throw new Error(`Missing connected-profile dimension ${key}.`);
    return <DecimalField label={label} quantity={value} onChange={(nextValue) => { update((next) => { const target = next.connected_member_profile.dimensions[key]; /* v8 ignore next -- selected registry keys and request dimensions stay paired */ if (target !== undefined) target.value = nextValue; }); }} />;
  };
  const previewMessage = preview.state === "CURRENT_VALID"
    ? "Current backend geometry"
    : preview.state === "PREVIEW_PENDING"
      ? "Preview updating"
      : preview.state === "CURRENT_INVALID_SHOWING_LAST_VALID"
        ? "Current geometry invalid — showing last valid preview"
        : preview.state === "PREVIEW_FAILED_SHOWING_LAST_VALID"
          ? "Preview unavailable — showing last valid preview"
          : "No valid backend preview";

  return (
    <ConnectionWorkspaceShell family="clip-angle"
      className="clip-angle-workspace"
      banner={<section className="workspace-banner"><div><p className="eyebrow">Stage 3.3C2 · Single FRP Clip Angle</p><h2>{title}</h2><p>Backend-authoritative geometry preview with independent physical bolt groups.</p></div><div className="benchmark-actions"><button type="button" className="secondary-button" onClick={() => { loadBenchmark("US_CUSTOMARY"); }}>Load G1 U.S.</button><button type="button" className="secondary-button" onClick={() => { loadBenchmark("SI"); }}>Load G1 SI</button></div></section>}
    >
      <ConnectionWorkspaceSidebar ariaLabel="Single clip-angle engineering properties">
      <ConnectorBodyMaterialControl material={bodyMaterial.material} onChange={bodyMaterial.choose} />
        <SidebarGroup title="Connected Member" summary={connectedLabel} defaultOpen>
          <label className="field-control"><span>Connected role</span><select aria-label="Connected role" value={request.connected_member_profile.role} onChange={(event) => { const role = event.currentTarget.value as "BRACE" | "BEAM"; update((next) => { next.connected_member_profile.role = role; }); }}><option value="BRACE">Brace</option><option value="BEAM">Beam</option></select></label>
          <label className="field-control"><span>Profile family</span><select aria-label="Connected profile family" value={request.connected_member_profile.profile_family} onChange={(event) => { const family = event.currentTarget.value as Exclude<TeeProfileFamily, "ROUND_HOLLOW_SECTION">; update((next) => { next.connected_member_profile = connectedProfile(next.source_length_unit, family); }); }}>{CLIP_PROFILE_FAMILIES.map((family) => <option key={family} value={family}>{TEE_PROFILE_DEFINITIONS[family].label}</option>)}</select></label>
          <div className="field-grid">{profileDefinition.dimensions.map((field) => <span key={field.key}>{profileField(field.key, field.label)}</span>)}</div>
          <label className="field-control"><span>Selected physical surface</span><select aria-label="Connected profile surface" value={request.connected_member_profile.selected_profile_surface} onChange={(event) => { const surface = event.currentTarget.value as TeeProfileSurface; update((next) => { next.connected_member_profile.selected_profile_surface = surface; }); }}>{profileDefinition.surfaces.map((surface) => <option key={surface} value={surface}>{PROFILE_SURFACE_LABELS[surface]}</option>)}</select></label>
          <label className="field-control"><span>Profile roll</span><select aria-label="Connected profile roll" value={request.connected_member_profile.profile_orientation} onChange={(event) => { const orientation = event.currentTarget.value as ClipAngleRequest["connected_member_profile"]["profile_orientation"]; update((next) => { next.connected_member_profile.profile_orientation = orientation; }); }}><option value="ROTATION_0">0°</option><option value="ROTATION_90">90°</option><option value="ROTATION_180">180°</option><option value="ROTATION_270">270°</option></select></label>
          <DecimalField label="Connected-member inclination" quantity={{ value: request.connected_member_inclination_degrees, unit: "deg" }} onChange={(value) => { update((next) => { next.connected_member_inclination_degrees = value; }); }} />
          <label className="field-control tee-checkbox-control"><span>Apply end trim clearance</span><input aria-label="Apply end trim clearance" type="checkbox" checked={request.connected_member_end_trim_enabled} onChange={(event) => { const enabled = event.currentTarget.checked; update((next) => { next.connected_member_end_trim_enabled = enabled; next.connected_member_end_clearance = enabled ? { value: "0", unit: next.source_length_unit } : null; }); }} /></label>
          {request.connected_member_end_clearance === null ? null : <DecimalField label="End clearance to clip-angle support leg" quantity={request.connected_member_end_clearance} onChange={(value) => { update((next) => { /* v8 ignore next -- rendered trim field owns a non-null clearance */ if (next.connected_member_end_clearance !== null) next.connected_member_end_clearance.value = value; }); }} />}
        </SidebarGroup>

        <SidebarGroup title="Supporting Member" summary={supportLabel}>
          <SupportingMemberEditor targetId={request.support_target_id} profile={request.support_profile} onTargetChange={(target: SharedSupportTargetId) => { update((next) => { next.support_target_id = target; next.support_profile = initialSharedSupport(target, next.source_length_unit, "clip-angle-support"); }); }} onProfileChange={(change) => { update((next) => { change(next.support_profile); }); }} />
        </SidebarGroup>

        <SidebarGroup title="Clip-Angle Connector" summary="Pultruded FRP angle" defaultOpen>
          <div className="field-grid">{quantityField("Connected-leg width", "connector_dimensions", "connected_leg_width")}{quantityField("Support-leg width", "connector_dimensions", "support_leg_width")}{quantityField("Clip-angle thickness", "connector_dimensions", "thickness")}{quantityField("Connector length", "connector_dimensions", "connector_length")}</div>
          <label className="field-control"><span>Hand / side</span><select aria-label="Clip-angle hand" value={request.hand} onChange={(event) => { const hand = event.currentTarget.value as ClipAngleRequest["hand"]; update((next) => { next.hand = hand; }); }}><option value="POSITIVE_S_SIDE">Positive S side</option><option value="NEGATIVE_S_SIDE">Negative S side</option></select></label>
          <label className="field-control"><span>Length anchor</span><select aria-label="Clip-angle length anchor" value={request.connector_length_anchor} onChange={(event) => { const anchor = event.currentTarget.value as ClipAngleRequest["connector_length_anchor"]; update((next) => { next.connector_length_anchor = anchor; }); }}><option value="CENTER">Center</option><option value="POSITIVE_L_END">Positive L end</option><option value="NEGATIVE_L_END">Negative L end</option></select></label>
          <DecimalField label="Connector longitudinal position" quantity={request.connector_length_anchor_position} onChange={(value) => { update((next) => { next.connector_length_anchor_position.value = value; }); }} />
        </SidebarGroup>

        <BoltGroupEditor title="Connected Member ↔ Clip-Angle Connected Leg" value={request.interface_a_layout} result={result?.interface_a ?? null} onChange={(change) => { update((next) => { change(next.interface_a_layout); }); }} />
        <BoltGroupEditor title="Clip-Angle Support Leg ↔ Support" value={request.interface_b_layout} result={result?.interface_b ?? null} onChange={(change) => { update((next) => { change(next.interface_b_layout); }); }} />

        <SidebarGroup title="Materials" summary="Controlled directional FRP"><dl className="diagnostic-list"><div><dt>Connected leg</dt><dd>Region-specific LW/CW/TT basis</dd></div><div><dt>Support leg</dt><dd>Perpendicular region-specific basis</dd></div><div><dt>Strength inference</dt><dd>None</dd></div></dl></SidebarGroup>
        <SidebarGroup title="Fasteners" summary="316SS · ASTM F593"><div className="field-grid"><DecimalField label="Bolt diameter" quantity={request.bolt_diameter} onChange={(value) => { update((next) => { next.bolt_diameter.value = value; }); }} /><DecimalField label="Hole diameter" quantity={request.hole_diameter} onChange={(value) => { update((next) => { next.hole_diameter.value = value; }); }} /></div></SidebarGroup>
        <SidebarGroup title="Loads" summary="One canonical global action" defaultOpen><div className="field-grid">{(["x", "y", "z"] as const).map((axis) => <DecimalField key={`force-${axis}`} label={`Force ${axis.toUpperCase()}`} quantity={{ value: request.global_force[axis], unit: request.global_force.unit }} onChange={(value) => { update((next) => { next.global_force[axis] = value; }); }} />)}{(["x", "y", "z"] as const).map((axis) => <DecimalField key={`moment-${axis}`} label={`Moment ${axis.toUpperCase()}`} quantity={{ value: request.global_moment[axis], unit: request.global_moment.unit }} onChange={(value) => { update((next) => { next.global_moment[axis] = value; }); }} />)}{(["x", "y", "z"] as const).map((axis) => <DecimalField key={`reference-${axis}`} label={`Reference ${axis.toUpperCase()}`} quantity={{ value: request.global_reference_point[axis], unit: request.global_reference_point.unit }} onChange={(value) => { update((next) => { next.global_reference_point[axis] = value; }); }} />)}</div></SidebarGroup>
        <SidebarGroup title="Results / Diagnostics" summary={design === null ? "No design run" : stale ? "Stale" : friendlyEnum(design.assembly_status)}><dl className="diagnostic-list"><div><dt>Geometry/model</dt><dd>{previewMessage}</dd></div><div><dt>Design readiness</dt><dd>{result?.design_check_ready === true ? "Ready for supported interface checks" : "Limited by current method/action"}</dd></div><div><dt>Design status</dt><dd>{design === null ? "Run Design Check" : stale ? "Stale" : friendlyEnum(design.assembly_status)}</dd></div><div><dt>Connector body</dt><dd>Not evaluated</dd></div><div><dt>Engineering fingerprint</dt><dd>{result?.engineering_fingerprint ?? "Pending"}</dd></div><div><dt>Result fingerprint</dt><dd>{design?.result_fingerprint ?? "Pending"}</dd></div></dl></SidebarGroup>
        <section className="evaluate-panel sidebar-evaluate" aria-label="Clip-angle design-check controls"><p>Preview runs geometry, actions, and demand only. Resistance runs only on explicit request.</p><button type="button" className="primary-button" disabled={bodyMaterial.busy || loading || !designReady} onClick={() => { void runDesign(); }}>{loading ? "Running design check…" : "Run Design Check"}</button>{localValidation === null ? null : <p className="sidebar-note" role="status">{localValidation}</p>}</section>
      </ConnectionWorkspaceSidebar>

      <ConnectionWorkspaceMain><ConnectorBodyMaterialResult state={bodyMaterial} />
        <PersistentConnectionViewer unity={viewerUnity("clip-angle", design, { stale, checking: loading, error: designError, previewState: preview.state })}>
          <div className={`tee-preview-state tee-preview-state-${preview.state.toLowerCase()}`} role="status" aria-live="polite"><strong>{previewMessage}</strong>{preview.invalidDetail === null ? null : <span>{preview.invalidDetail}</span>}</div>
          {model === null ? <section className="viewer-prompt"><h3>Canonical clip-angle model unavailable</h3><p>{preview.invalidDetail ?? previewMessage}</p></section> : <VisualizationPanel model={model} title={title} contactSelectionLabel="Selected physical clip-angle contact surface" selection={selection} onSelect={setSelection} appliedActionInputValues={{ FX: request.global_force.x, FY: request.global_force.y, FZ: request.global_force.z, MX: request.global_moment.x, MY: request.global_moment.y, MZ: request.global_moment.z }} onAppliedActionValueChange={(component, value) => { const key = component.slice(1).toLowerCase() as "x" | "y" | "z"; update((next) => { if (component.startsWith("F")) next.global_force[key] = value; else next.global_moment[key] = value; }); }} actionSourceLabel="Canonical clip-angle member-end action" />}
        </PersistentConnectionViewer>
        {preview.error === null ? null : <div className="error-banner" role="alert"><strong>{preview.invalidDetail ?? preview.error.message}</strong><button type="button" onClick={preview.retry}>Retry preview</button></div>}
        {designError === null ? null : <div className="error-banner" role="alert">{designError.message}</div>}
        {stale ? <div className="stale-banner" role="status">Design results are stale. Run Design Check after the current backend preview is valid.</div> : null}
        <section className="tee-results-grid" aria-label="Single clip-angle grouped results">
          {result === null ? <p>No current clip-angle result.</p> : <><InterfaceCard value={design === null || stale ? result.interface_a : design.result.interface_a} /><InterfaceCard value={design === null || stale ? result.interface_b : design.result.interface_b} /><article className="qualification-banner tee-body-limitation"><span aria-hidden="true">!</span><div><strong>Single clip-angle connector body · Not evaluated</strong><p>Leg bending, heel/fillet, connector shear or rupture, torsion, prying, and single-angle eccentric body action remain outside Stage 3.3A. Ordinary whole-connection PASS is prohibited.</p></div></article></>}
        </section>
      </ConnectionWorkspaceMain>
    </ConnectionWorkspaceShell>
  );
}
