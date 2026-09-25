import { viewerUnity } from "./unityRatio";
import { ConnectorBodyMaterialControl, ConnectorBodyMaterialResult } from "./connectorBodyMaterial";
import { useConnectorBodyMaterial } from "./useConnectorBodyMaterial";
import { useEffect, useMemo, useRef, useState } from "react";

import type {
  ColumnBaseComponentTransfer,
  ColumnBaseDesignResponse,
  ColumnBaseProfileFamily,
  ColumnBaseVector,
  ColumnBaseWebAngleRequest,
  ColumnBaseWrench,
} from "../api/columnBaseWebAngleContracts";
import { EvaluationTransportError, evaluateColumnBaseWebAngle } from "../api/client";
import type { MultiRowQuantity } from "../api/multirowContracts";
import { loadColumnBaseWebAngleBenchmark } from "../fixtures/columnBaseWebAngleBenchmarks";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { buildColumnBaseWebAngleSceneModel } from "../visualization/columnBaseWebAngleSceneModel";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import { useColumnBaseWebAnglePreview } from "./columnBaseWebAngleWorkflow";
import {
  ConnectionWorkspaceMain,
  ConnectionWorkspaceShell,
  ConnectionWorkspaceSidebar,
  PersistentConnectionViewer,
  SidebarGroup,
} from "./ConnectionWorkspaceShell";
import { formatDisplayQuantity, friendlyEnum } from "./presentation";

function DecimalField({ label, quantity, onChange }: {
  readonly label: string;
  readonly quantity: MultiRowQuantity;
  readonly onChange: (value: string) => void;
}) {
  return <label className="field-control"><span>{label}</span><span className="input-with-unit"><input aria-label={label} type="text" inputMode="decimal" value={quantity.value} onChange={(event) => { onChange(event.currentTarget.value); }} /><small>{quantity.unit}</small></span></label>;
}

function vectorText(value: ColumnBaseVector, system: "US_CUSTOMARY" | "SI"): string {
  return `(${formatDisplayQuantity(value.s, system)}, ${formatDisplayQuantity(value.t, system)}, ${formatDisplayQuantity(value.longitudinal, system)})`;
}

function WrenchCard({ title, value, system }: { readonly title: string; readonly value: ColumnBaseWrench; readonly system: "US_CUSTOMARY" | "SI" }) {
  return <article className="source-card compact-source-card"><h4>{title}</h4><dl className="diagnostic-list"><div><dt>Reference S/T/L</dt><dd>{vectorText(value.reference_s_t_l, system)}</dd></div><div><dt>Force S/T/L</dt><dd>{vectorText(value.force_s_t_l, system)}</dd></div><div><dt>Shifted moment S/T/L</dt><dd>{vectorText(value.moment_s_t_l, system)}</dd></div><div><dt>Provenance</dt><dd>{value.provenance}</dd></div></dl></article>;
}

function signedQuantityText(value: { readonly value: string; readonly unit: string }, system: "US_CUSTOMARY" | "SI"): string {
  const text = formatDisplayQuantity(value, system);
  return Number(value.value) > 0 ? `+${text}` : text;
}

function ComponentTransferTrace({ transfer, assembly, system }: {
  readonly transfer: ColumnBaseComponentTransfer;
  readonly assembly: "SINGLE_BASE_ANGLE" | "DOUBLE_BASE_ANGLES" | "SYMMETRIC_DOUBLE_BASE_ANGLES";
  readonly system: "US_CUSTOMARY" | "SI";
}) {
  if ("column_web_axial_demand" in transfer) {
    return <div className="component-transfer-summary"><article className="source-card compact-source-card"><h4>Column Web Local Transfer</h4><p><strong>Axial design demand: {formatDisplayQuantity(transfer.column_web_axial_demand, system)} (100%)</strong></p><p>Material direction: LW</p></article><article className="source-card compact-source-card"><h4>{assembly === "SINGLE_BASE_ANGLE" ? "Base Angle" : "Base-Angle Pair"}</h4><p><strong>System axial design demand: {formatDisplayQuantity(transfer.angle_system_axial_demand, system)} (100%)</strong></p></article><article className="source-card compact-source-card"><h4>Foundation Reaction</h4><p><strong>Axial action counted once: {formatDisplayQuantity(transfer.foundation_axial_action, system)}</strong></p></article></div>;
  }
  if ("column_web_signed_axial_action" in transfer) {
    return <div className="component-transfer-summary"><article className="source-card compact-source-card"><h4>Column Web Local Transfer</h4><p><strong>Signed axial action: {signedQuantityText(transfer.column_web_signed_axial_action, system)}</strong></p><p>Design magnitude: {formatDisplayQuantity(transfer.column_web_design_magnitude, system)} (100%)</p><p>Material axis: {transfer.column_web_material_direction} · signed direction {transfer.column_web_signed_material_direction}</p><p>Mode: {transfer.axial_mode === "UPLIFT" ? "Uplift/Tension" : transfer.axial_mode === "COMPRESSION" ? "Compression" : "Zero"}</p></article><article className="source-card compact-source-card"><h4>{assembly === "SINGLE_BASE_ANGLE" ? "Base Angle" : "Base-Angle Pair"}</h4><p><strong>System signed action: {signedQuantityText(transfer.angle_system_signed_axial_action, system)}</strong></p>{transfer.positive_angle_signed_axial_action === null ? null : <p>Angle +: {signedQuantityText(transfer.positive_angle_signed_axial_action, system)} (50%)</p>}{transfer.negative_angle_signed_axial_action === null ? null : <p>Angle -: {signedQuantityText(transfer.negative_angle_signed_axial_action, system)} (50%)</p>}{transfer.single_angle_signed_axial_action === null ? null : <p>Single angle: {signedQuantityText(transfer.single_angle_signed_axial_action, system)} (100%)</p>}<p>Vertical-leg axis: {transfer.angle_vertical_leg_material_direction} · signed direction {transfer.angle_vertical_leg_signed_material_direction}</p></article><article className="source-card compact-source-card"><h4>Foundation Reaction</h4><p><strong>Axial reaction counted once: {signedQuantityText(transfer.foundation_signed_axial_action, system)}</strong></p></article></div>;
  }
  return <div className="component-transfer-summary">
    <article className="source-card compact-source-card"><h4>Column Local Transfer</h4><p><strong>Signed axial action: {signedQuantityText(transfer.column_signed_axial_action, system)}</strong></p><p>Design magnitude: {formatDisplayQuantity(transfer.column_design_magnitude, system)} (100%)</p><p>Material axis: {transfer.column_material_direction} · signed direction {transfer.column_signed_material_direction}</p><p>Mode: {transfer.axial_mode === "UPLIFT" ? "Uplift/Tension" : transfer.axial_mode === "COMPRESSION" ? "Compression" : "Zero"}</p></article>
    <article className="source-card compact-source-card"><h4>{assembly === "DOUBLE_BASE_ANGLES" ? "Base-Angle System" : "Base Angle"}</h4><p><strong>System signed action: {signedQuantityText(transfer.base_angle_system_signed_axial_action, system)}</strong></p><p>Design magnitude: {formatDisplayQuantity(transfer.base_angle_system_design_magnitude, system)} (100%)</p>{transfer.positive_angle_signed_axial_action === null ? null : <p>Angle +: {signedQuantityText(transfer.positive_angle_signed_axial_action, system)} (50%)</p>}{transfer.negative_angle_signed_axial_action === null ? null : <p>Angle -: {signedQuantityText(transfer.negative_angle_signed_axial_action, system)} (50%)</p>}{transfer.single_angle_signed_axial_action === null ? null : <p>Single angle: {signedQuantityText(transfer.single_angle_signed_axial_action, system)} (100%)</p>}<p>Vertical-leg axis: {transfer.base_angle_vertical_leg_material_direction} · signed direction {transfer.base_angle_vertical_leg_signed_material_direction}</p><p>Complete branch allocation: {friendlyEnum(transfer.complete_branch_allocation)}</p></article>
    <article className="source-card compact-source-card"><h4>Foundation Reaction</h4><p><strong>Axial reaction counted once: {signedQuantityText(transfer.foundation_signed_axial_action, system)}</strong></p><p>Column and angle-system component checks are not summed into a doubled reaction.</p></article>
  </div>;
}

function profileLabel(family: ColumnBaseProfileFamily): string {
  if (family === "WIDE_FLANGE_I") return "W/I";
  if (family === "RECTANGULAR_HOLLOW_SECTION") return "Rectangular Hollow Section";
  if (family === "SOLID_RECTANGULAR_SECTION") return "Solid Rectangular Section";
  return "Angle";
}

function validate(request: ColumnBaseWebAngleRequest): string | null {
  const dimensions = Object.values(request.column_profile.dimensions).map((value) => Number(value.value));
  const positive = [
    request.concrete.s_dimension.value, request.concrete.t_dimension.value, request.concrete.depth.value,
    ...dimensions,
    request.angle.connected_leg_width.value, request.angle.support_leg_width.value, request.angle.thickness.value,
    request.angle.connector_length.value, request.web_bolt_diameter.value, request.web_hole_diameter.value,
    request.external_anchor.nominal_diameter.value, request.external_anchor.specified_embedment.value,
  ].map(Number);
  if (positive.some((value) => !Number.isFinite(value) || value <= 0)) return "Column, base, angle, bolt, and anchor dimensions must be positive decimal values.";
  const forces = [request.signed_axial_force.value, request.connection_plane_shear.value, request.connection_normal_shear.value].map(Number);
  if (forces.some((value) => !Number.isFinite(value))) return "All three force fields must be finite decimal values.";
  return null;
}

export function ColumnBaseWebAngleWorkspace() {
  const [request, setRequest] = useState<ColumnBaseWebAngleRequest>(() => loadColumnBaseWebAngleBenchmark("US_CUSTOMARY"));
  const [revision, setRevision] = useState(0);
  const [design, setDesign] = useState<ColumnBaseDesignResponse | null>(null);
  const [designError, setDesignError] = useState<EvaluationTransportError | null>(null);
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [copyStatus, setCopyStatus] = useState("");
  const [selection, setSelection] = useState<SceneSelection>({ kind: "MEMBER", id: "column" });
  const designController = useRef<AbortController | null>(null);
  useEffect(() => () => { designController.current?.abort(); }, []);
  const validationMessage = validate(request);
  const previewInput = useMemo(() => ({ request, revision, immediate: revision === 0, validationMessage }), [request, revision, validationMessage]);
  const preview = useColumnBaseWebAnglePreview(previewInput);
  const result = preview.response?.result ?? null;
  const model = useMemo(() => result?.visualization === null || result?.visualization === undefined ? null : buildColumnBaseWebAngleSceneModel(result.visualization, preview.response?.orchestration_contract_version ?? "3.7A-RC1"), [preview.response?.orchestration_contract_version, result]);

  const update = (change: (next: ColumnBaseWebAngleRequest) => void) => {
    designController.current?.abort();
    designController.current = null;
    setLoading(false);
    setRequest((current) => { const next = structuredClone(current); change(next); return next; });
    setRevision((value) => value + 1);
    setStale(design !== null);
    setDesignError(null);
  };
  const loadBenchmark = (system: "US_CUSTOMARY" | "SI", family: ColumnBaseProfileFamily = request.column_profile.profile_family) => {
    setRequest(loadColumnBaseWebAngleBenchmark(system, family));
    setRevision((value) => value + 1);
    setStale(design !== null);
    setDesignError(null);
  };
  const q = (label: string, target: MultiRowQuantity, set: (next: ColumnBaseWebAngleRequest, value: string) => void) => <DecimalField label={label} quantity={target} onChange={(value) => { update((next) => { set(next, value); }); }} />;
  const integer = (label: string, value: number, set: (next: ColumnBaseWebAngleRequest, value: number) => void) => <label className="field-control"><span>{label}</span><input aria-label={label} type="number" min="1" step="1" value={value} onChange={(event) => { const nextValue = Number(event.currentTarget.value); update((next) => { set(next, nextValue); }); }} /></label>;
  const selectProfile = (family: ColumnBaseProfileFamily) => {
    const controlled = loadColumnBaseWebAngleBenchmark(request.unit_system, family);
    update((next) => {
      next.column_profile = controlled.column_profile;
      next.angle.connector_length = controlled.angle.connector_length;
      next.anchor_pattern.centroid_offset_t = controlled.anchor_pattern.centroid_offset_t;
    });
  };
  const bodyMaterial = useConnectorBodyMaterial("column-base-web-angles", request, revision, () => {
    designController.current?.abort(); designController.current = null; setLoading(false); setDesign(null); setDesignError(null); setStale(true);
  });
  const runDesign = async () => {
    if (bodyMaterial.material === "SS316") { await bodyMaterial.run(); return; }
    designController.current?.abort();
    const controller = new AbortController();
    designController.current = controller;
    setLoading(true);
    setDesignError(null);
    try {
      const response = await evaluateColumnBaseWebAngle(request, controller.signal);
      if (designController.current !== controller) return;
      setDesign(response);
      setStale(false);
    } catch (caught) {
      if (!controller.signal.aborted) setDesignError(caught instanceof EvaluationTransportError ? caught : new EvaluationTransportError("RESPONSE", null, "Unexpected column-base design-check failure.", caught));
    } finally {
      if (designController.current === controller) { designController.current = null; setLoading(false); }
    }
  };
  const copyHandoff = async () => {
    /* v8 ignore next -- disabled until a current backend handoff exists */
    if (result === null) return;
    await navigator.clipboard.writeText(result.external_handoff_json);
    setCopyStatus("Copied full-precision backend concrete/anchor handoff JSON.");
  };
  const downloadHandoff = () => {
    /* v8 ignore next -- disabled until a current backend handoff exists */
    if (result === null) return;
    const url = URL.createObjectURL(new Blob([result.external_handoff_json], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `${request.request_id}-concrete-anchor-handoff.json`; anchor.click(); URL.revokeObjectURL(url);
  };
  const previewMessage = preview.state === "CURRENT_VALID" ? "Current backend column-base geometry" : preview.state === "PREVIEW_PENDING" ? "Preview updating" : preview.state === "CURRENT_INVALID_SHOWING_LAST_VALID" ? "Current geometry invalid — showing last valid preview" : preview.state === "PREVIEW_FAILED_SHOWING_LAST_VALID" ? "Preview unavailable — showing last valid preview" : "No valid backend preview";
  const transfer = result?.component_transfer ?? null;
  const shown = design === null || stale ? result : design.result.preview;
  const profile = request.column_profile;

  return <ConnectionWorkspaceShell family="column-base-web-angles" className="clip-angle-workspace paired-clip-angle-workspace column-base-web-angle-workspace" banner={<section className="workspace-banner"><div><p className="eyebrow">Stage 3.7A · Column-base profile matrix</p><h2>Column connection — Single/double base angles to concrete</h2><p>Independent component design demands, exact generated moments, and one foundation reaction.</p></div><div className="benchmark-actions"><button type="button" className="secondary-button" onClick={() => { loadBenchmark("US_CUSTOMARY"); }}>Load 3.7A U.S.</button><button type="button" className="secondary-button" onClick={() => { loadBenchmark("SI"); }}>Load 3.7A SI</button></div></section>}>
    <ConnectionWorkspaceSidebar ariaLabel="Column-base profile engineering properties">
      <ConnectorBodyMaterialControl material={bodyMaterial.material} onChange={bodyMaterial.choose} />
      <SidebarGroup title="General / Case" summary="3.7A-RC1" defaultOpen><dl className="diagnostic-list"><div><dt>Connection</dt><dd>FRP column with single/double base angles</dd></div><div><dt>Profile</dt><dd>{profileLabel(profile.profile_family)}</dd></div><div><dt>Action scope</dt><dd>Signed axial force + two signed shears; no user moments</dd></div><div><dt>External authority</dt><dd>Concrete and anchors</dd></div></dl></SidebarGroup>
      <SidebarGroup title="FRP Column" summary={profileLabel(profile.profile_family)} defaultOpen>
        <label className="field-control"><span>Column profile</span><select aria-label="Column profile" value={profile.profile_family} onChange={(event) => { selectProfile(event.currentTarget.value as ColumnBaseProfileFamily); }}><option value="WIDE_FLANGE_I">W/I</option><option value="RECTANGULAR_HOLLOW_SECTION">Rectangular Hollow Section</option><option value="SOLID_RECTANGULAR_SECTION">Solid Rectangular Section</option><option value="ANGLE">Angle</option></select></label>
        <div className="field-grid">
          {profile.profile_family === "WIDE_FLANGE_I" ? <>{q("Column depth", profile.dimensions.depth, (next, value) => { /* v8 ignore else -- rendered W/I control owns the matching strict profile */ if (next.column_profile.profile_family === "WIDE_FLANGE_I") next.column_profile.dimensions.depth.value = value; })}{q("Flange width", profile.dimensions.flange_width, (next, value) => { /* v8 ignore else -- rendered W/I control owns the matching strict profile */ if (next.column_profile.profile_family === "WIDE_FLANGE_I") next.column_profile.dimensions.flange_width.value = value; })}{q("Web thickness", profile.dimensions.web_thickness, (next, value) => { /* v8 ignore else -- rendered W/I control owns the matching strict profile */ if (next.column_profile.profile_family === "WIDE_FLANGE_I") next.column_profile.dimensions.web_thickness.value = value; })}{q("Flange thickness", profile.dimensions.flange_thickness, (next, value) => { /* v8 ignore else -- rendered W/I control owns the matching strict profile */ if (next.column_profile.profile_family === "WIDE_FLANGE_I") next.column_profile.dimensions.flange_thickness.value = value; })}</> : null}
          {profile.profile_family === "RECTANGULAR_HOLLOW_SECTION" ? <>{q("Outside depth", profile.dimensions.depth, (next, value) => { /* v8 ignore else -- rendered RHS control owns the matching strict profile */ if (next.column_profile.profile_family === "RECTANGULAR_HOLLOW_SECTION") next.column_profile.dimensions.depth.value = value; })}{q("Outside width", profile.dimensions.width, (next, value) => { /* v8 ignore else -- rendered RHS control owns the matching strict profile */ if (next.column_profile.profile_family === "RECTANGULAR_HOLLOW_SECTION") next.column_profile.dimensions.width.value = value; })}{q("Wall thickness", profile.dimensions.wall_thickness, (next, value) => { /* v8 ignore else -- rendered RHS control owns the matching strict profile */ if (next.column_profile.profile_family === "RECTANGULAR_HOLLOW_SECTION") next.column_profile.dimensions.wall_thickness.value = value; })}</> : null}
          {profile.profile_family === "SOLID_RECTANGULAR_SECTION" ? <>{q("Outside depth", profile.dimensions.depth, (next, value) => { /* v8 ignore else -- rendered SRS control owns the matching strict profile */ if (next.column_profile.profile_family === "SOLID_RECTANGULAR_SECTION") next.column_profile.dimensions.depth.value = value; })}{q("Outside width", profile.dimensions.width, (next, value) => { /* v8 ignore else -- rendered SRS control owns the matching strict profile */ if (next.column_profile.profile_family === "SOLID_RECTANGULAR_SECTION") next.column_profile.dimensions.width.value = value; })}</> : null}
          {profile.profile_family === "ANGLE" ? <>{q("Leg Y width", profile.dimensions.leg_y, (next, value) => { /* v8 ignore else -- rendered Angle control owns the matching strict profile */ if (next.column_profile.profile_family === "ANGLE") next.column_profile.dimensions.leg_y.value = value; })}{q("Leg Z width", profile.dimensions.leg_z, (next, value) => { /* v8 ignore else -- rendered Angle control owns the matching strict profile */ if (next.column_profile.profile_family === "ANGLE") next.column_profile.dimensions.leg_z.value = value; })}{q("Column angle thickness", profile.dimensions.thickness, (next, value) => { /* v8 ignore else -- rendered Angle control owns the matching strict profile */ if (next.column_profile.profile_family === "ANGLE") next.column_profile.dimensions.thickness.value = value; })}</> : null}
          {q("Column display height", profile.dimensions.member_length, (next, value) => { next.column_profile.dimensions.member_length.value = value; })}
        </div>
        {profile.profile_family === "WIDE_FLANGE_I" ? <label className="field-control"><span>Selected web face</span><select aria-label="Selected web face" value={profile.selected_profile_surface} onChange={(event) => { const value = event.currentTarget.value as "WEB_POS_FACE" | "WEB_NEG_FACE"; update((next) => { /* v8 ignore else -- rendered W/I selector owns the matching strict profile */ if (next.column_profile.profile_family === "WIDE_FLANGE_I") next.column_profile.selected_profile_surface = value; }); }}><option value="WEB_POS_FACE">Web positive face</option><option value="WEB_NEG_FACE">Web negative face</option></select></label> : null}
        {profile.profile_family === "RECTANGULAR_HOLLOW_SECTION" || profile.profile_family === "SOLID_RECTANGULAR_SECTION" ? <label className="field-control"><span>Selected contact face</span><select aria-label="Selected contact face" value={profile.selected_profile_surface} onChange={(event) => { const value = event.currentTarget.value as "Y_POS_FACE" | "Y_NEG_FACE" | "Z_POS_FACE" | "Z_NEG_FACE"; update((next) => { /* v8 ignore else -- rendered rectangular selector owns the matching strict profile */ if (next.column_profile.profile_family === "RECTANGULAR_HOLLOW_SECTION" || next.column_profile.profile_family === "SOLID_RECTANGULAR_SECTION") next.column_profile.selected_profile_surface = value; }); }}><option value="Y_POS_FACE">Y positive face</option><option value="Y_NEG_FACE">Y negative face</option><option value="Z_POS_FACE">Z positive face</option><option value="Z_NEG_FACE">Z negative face</option></select></label> : null}
        {profile.profile_family === "ANGLE" ? <label className="field-control"><span>Selected column leg</span><select aria-label="Selected column leg" value={profile.selected_profile_surface} onChange={(event) => { const value = event.currentTarget.value as "LEG_Y_OUTER" | "LEG_Z_OUTER"; update((next) => { /* v8 ignore else -- rendered Angle selector owns the matching strict profile */ if (next.column_profile.profile_family === "ANGLE") next.column_profile.selected_profile_surface = value; }); }}><option value="LEG_Y_OUTER">Leg Y</option><option value="LEG_Z_OUTER">Leg Z</option></select></label> : null}
      </SidebarGroup>
      <SidebarGroup title="Concrete Base" summary="Finite coordination solid"><div className="field-grid">{q("Base S dimension", request.concrete.s_dimension, (next, value) => { next.concrete.s_dimension.value = value; })}{q("Base T dimension", request.concrete.t_dimension, (next, value) => { next.concrete.t_dimension.value = value; })}{q("Base depth", request.concrete.depth, (next, value) => { next.concrete.depth.value = value; })}</div><p className="sidebar-note">Concrete has no FRP LW/CW/TT material axes.</p></SidebarGroup>
      <SidebarGroup title="Base-Angle Assembly" summary={request.assembly === "DOUBLE_BASE_ANGLES" ? "Double" : "Single"} defaultOpen><label className="field-control"><span>Assembly</span><select aria-label="Base-angle assembly" value={request.assembly} onChange={(event) => { const value = event.currentTarget.value as ColumnBaseWebAngleRequest["assembly"]; update((next) => { next.assembly = value; }); }}><option value="SINGLE_BASE_ANGLE">Single</option><option value="DOUBLE_BASE_ANGLES">Double</option></select></label><label className="field-control"><span>{profile.profile_family === "ANGLE" ? "Selected broad face" : "Single-angle side"}</span><select aria-label={profile.profile_family === "ANGLE" ? "Selected broad face" : "Single-angle side"} disabled={request.assembly === "DOUBLE_BASE_ANGLES"} value={request.single_side} onChange={(event) => { const value = event.currentTarget.value as ColumnBaseWebAngleRequest["single_side"]; update((next) => { next.single_side = value; }); }}><option value="+T_C">Positive +T_C</option><option value="-T_C">Negative -T_C</option></select></label>{profile.profile_family === "ANGLE" && request.assembly === "DOUBLE_BASE_ANGLES" ? <p className="sidebar-note">Double is locked to opposite broad faces of the same selected leg. Different-leg topology is not available.</p> : null}<div className="field-grid">{q("Vertical-leg width", request.angle.connected_leg_width, (next, value) => { next.angle.connected_leg_width.value = value; })}{q("Horizontal-leg width", request.angle.support_leg_width, (next, value) => { next.angle.support_leg_width.value = value; })}{q("Angle thickness", request.angle.thickness, (next, value) => { next.angle.thickness.value = value; })}{q("Angle length", request.angle.connector_length, (next, value) => { next.angle.connector_length.value = value; })}</div></SidebarGroup>
      <SidebarGroup title="Column ↔ Base Angle(s)" summary="Backend-authoritative physical group"><div className="field-grid">{integer("Bolt rows", request.web_group.row_count, (next, value) => { next.web_group.row_count = value; })}{integer("Bolts per row", request.web_group.bolts_per_row, (next, value) => { next.web_group.bolts_per_row = value; })}{q("Bolt pitch", request.web_group.pitch, (next, value) => { next.web_group.pitch.value = value; })}{q("Bolt gauge", request.web_group.gauge, (next, value) => { next.web_group.gauge.value = value; })}{q("Group centroid height", request.web_group.centroid_height_l, (next, value) => { next.web_group.centroid_height_l.value = value; })}{q("Bolt diameter", request.web_bolt_diameter, (next, value) => { next.web_bolt_diameter.value = value; })}{q("Hole diameter", request.web_hole_diameter, (next, value) => { next.web_hole_diameter.value = value; })}</div><p className="sidebar-note">RHS and SRS use one continuous exterior-to-exterior through-bolt per axis. RHS cavity contains shank only—no internal hardware or material.</p></SidebarGroup>
      <SidebarGroup title="Base Anchor Group(s)" summary="Mirrored only after exact symmetry"><div className="field-grid">{integer("Anchor rows", request.anchor_pattern.row_count, (next, value) => { next.anchor_pattern.row_count = value; })}{integer("Anchors per row", request.anchor_pattern.anchors_per_row, (next, value) => { next.anchor_pattern.anchors_per_row = value; })}{q("Anchor pitch", request.anchor_pattern.pitch, (next, value) => { next.anchor_pattern.pitch.value = value; })}{q("Anchor gauge", request.anchor_pattern.gauge, (next, value) => { next.anchor_pattern.gauge.value = value; })}{q("Group centroid offset T", request.anchor_pattern.centroid_offset_t, (next, value) => { next.anchor_pattern.centroid_offset_t.value = value; })}</div></SidebarGroup>
      <SidebarGroup title="External Anchor Geometry" summary="Capacity designed elsewhere"><div className="field-grid">{q("Anchor diameter", request.external_anchor.nominal_diameter, (next, value) => { next.external_anchor.nominal_diameter.value = value; })}{q("Anchor hole diameter", request.external_anchor.hole_diameter, (next, value) => { next.external_anchor.hole_diameter.value = value; })}{q("Specified embedment", request.external_anchor.specified_embedment, (next, value) => { next.external_anchor.specified_embedment.value = value; })}{q("Washer outside diameter", request.external_anchor.washer_outside_diameter, (next, value) => { next.external_anchor.washer_outside_diameter.value = value; })}{q("Washer thickness", request.external_anchor.washer_thickness, (next, value) => { next.external_anchor.washer_thickness.value = value; })}</div><p className="sidebar-note">Exterior washer/nut and embedded shank only. No far-side concrete hardware.</p></SidebarGroup>
      <SidebarGroup title="Loads" summary="Column-base S_C / T_C / L_C" defaultOpen><div className="field-grid">{q("Axial force (+ uplift / - compression)", request.signed_axial_force, (next, value) => { next.signed_axial_force.value = value; })}{q("Connection-plane shear", request.connection_plane_shear, (next, value) => { next.connection_plane_shear.value = value; })}{q("Connection-normal shear", request.connection_normal_shear, (next, value) => { next.connection_normal_shear.value = value; })}</div><p className="sidebar-note">Positive axial force is uplift along +L_C; negative axial force is compression toward the base along -L_C. Shears are signed along backend-authored S_C and T_C. No user-applied moment fields.</p></SidebarGroup>
      <SidebarGroup title="Component Transfer Trace" summary="Signed serial design demands · not additive" defaultOpen>{transfer === null ? <p>Awaiting backend transfer trace.</p> : <ComponentTransferTrace transfer={transfer} assembly={request.assembly} system={request.unit_system} />}</SidebarGroup>
      <SidebarGroup title="Concrete / Anchor Handoff" summary="External design required" defaultOpen><div className="benchmark-actions"><button type="button" disabled={result === null} onClick={() => { void copyHandoff(); }}>Copy JSON</button><button type="button" disabled={result === null} onClick={downloadHandoff}>Download JSON</button></div><p className="sidebar-note" role="status">{copyStatus || "Full-precision backend wrench/reference authority; no frontend calculation."}</p><dl className="diagnostic-list"><div><dt>Handoff fingerprint</dt><dd>{result?.external_handoff.handoff_fingerprint ?? "Pending"}</dd></div><div><dt>Concrete/anchor capacity</dt><dd>EXTERNAL_DESIGN_REQUIRED</dd></div><div><dt>Foundation action</dt><dd>Counted once</dd></div></dl></SidebarGroup>
      <SidebarGroup title="Materials / Fasteners" summary="ICE FRP + F593 + external anchors"><dl className="diagnostic-list"><div><dt>Column profile</dt><dd>ICE locked pultruded FRP · backend region axes</dd></div><div><dt>Base-angle legs</dt><dd>ICE locked pultruded FRP · region-specific LW/CW/TT</dd></div><div><dt>Profile fasteners</dt><dd>316SS ASTM F593</dd></div><div><dt>External anchors</dt><dd>Classification/geometry handoff only</dd></div></dl></SidebarGroup>
      <SidebarGroup title="Geometry / Design Results" summary={design === null ? "No design run" : stale ? "Stale" : friendlyEnum(design.assembly_status)}><dl className="diagnostic-list"><div><dt>Geometry/model</dt><dd>{previewMessage}</dd></div><div><dt>Design status</dt><dd>{design === null ? "Run Design Check" : stale ? "Stale" : friendlyEnum(design.assembly_status)}</dd></div><div><dt>Ordinary PASS</dt><dd>Prohibited</dd></div><div><dt>External design</dt><dd>Required</dd></div><div><dt>Engineering fingerprint</dt><dd>{result?.engineering_fingerprint ?? "Pending"}</dd></div></dl></SidebarGroup>
      <SidebarGroup title="Advanced / Diagnostics" summary="Frames, methods, provenance"><dl className="diagnostic-list"><div><dt>Base frame</dt><dd>S_C × T_C = L_C</dd></div><div><dt>Selected surface/leg</dt><dd>{profile.selected_profile_surface}</dd></div><div><dt>Action reference</dt><dd>Actual backend member axis</dd></div><div><dt>Stage 2.5A demand</dt><dd>One call per physical group</dd></div><div><dt>Preview resistance calls</dt><dd>0</dd></div><div><dt>Limitations retained</dt><dd>{result?.limitations.length ?? 0}</dd></div><div><dt>Application fingerprint</dt><dd>{result?.application_fingerprint ?? "Pending"}</dd></div></dl></SidebarGroup>
      <section className="evaluate-panel sidebar-evaluate"><p>Run Design Check evaluates only existing authorized local FRP/fastener checks. Angle body/heel, concrete, anchors, and other listed boundaries remain not evaluated or external.</p><button type="button" className="primary-button" disabled={bodyMaterial.busy || loading || validationMessage !== null || preview.state !== "CURRENT_VALID" || preview.response?.design_check_ready !== true} onClick={() => { void runDesign(); }}>{loading ? "Running design check…" : "Run Design Check"}</button>{validationMessage === null ? null : <p className="sidebar-note" role="status">{validationMessage}</p>}</section>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain><ConnectorBodyMaterialResult state={bodyMaterial} /><PersistentConnectionViewer unity={viewerUnity("column-base-web-angle", design, { stale, checking: loading, error: designError, previewState: preview.state })}><div className={`tee-preview-state tee-preview-state-${preview.state.toLowerCase()}`} role="status"><strong>{previewMessage}</strong>{preview.invalidDetail === null ? null : <span>{preview.invalidDetail}</span>}</div>{model === null ? <section className="viewer-prompt"><h3>Canonical column-base model unavailable</h3><p>{preview.invalidDetail ?? previewMessage}</p></section> : <VisualizationPanel model={model} title="Column connection — Single/double base angles to concrete" contactSelectionLabel="Selected column/base-angle interface" selection={selection} onSelect={setSelection} appliedActionInputValues={{ FX: request.connection_plane_shear.value, FY: request.connection_normal_shear.value, FZ: request.signed_axial_force.value, MX: "0", MY: "0", MZ: "0" }} onAppliedActionValueChange={(component, value) => { if (component === "FX" || component === "FY" || component === "FZ") update((next) => { if (component === "FX") next.connection_plane_shear.value = value; else if (component === "FY") next.connection_normal_shear.value = value; else next.signed_axial_force.value = value; }); }} actionSourceLabel="Applied column-base force" />}</PersistentConnectionViewer>{preview.error === null ? null : <div className="error-banner" role="alert"><strong>{preview.error.message}</strong><button type="button" onClick={preview.retry}>Retry preview</button></div>}{designError === null ? null : <div className="error-banner" role="alert">{designError.message}</div>}{stale ? <div className="stale-banner" role="status">Design results are stale. Run Design Check after the current backend preview is valid.</div> : null}<section className="tee-results-grid" aria-label="Column-base transfer results">{shown === null ? <p>No current column-base result.</p> : <><WrenchCard title="Combined foundation reaction — counted once" value={shown.combined_foundation_wrench} system={request.unit_system} />{shown.anchor_groups.map((group) => group.branch_wrench === null ? <article key={group.group_id} className="source-card compact-source-card"><h4>{friendlyEnum(group.group_id)}</h4><p>Branch allocation NOT_EVALUATED; complete combined wrench retained.</p></article> : <WrenchCard key={group.group_id} title={`${friendlyEnum(group.group_id)} branch`} value={group.branch_wrench} system={request.unit_system} />)}<article className="qualification-banner tee-body-limitation"><span aria-hidden="true">!</span><div><strong>Concrete, anchors, and angle body/heel · Not calculated</strong><p>External design must independently verify the exact handoff. Component demands remain separate and the foundation reaction is counted once.</p>{shown.limitations.some(([name]) => name === "COLUMN_END_BEARING_FOR_UPLIFT") ? <p>Uplift: column-end bearing NOT_REQUIRED; angle body/heel and horizontal-leg prying NOT_EVALUATED; anchor tension and concrete uplift anchorage require external design.</p> : <p>Compression: column-end/base-angle bearing partition and base-angle-to-concrete bearing require external design.</p>}</div></article></>}</section></ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
