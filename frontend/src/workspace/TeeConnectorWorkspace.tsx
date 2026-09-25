import { viewerUnity } from "./unityRatio";
import { ConnectorBodyMaterialControl, ConnectorBodyMaterialResult } from "./connectorBodyMaterial";
import { useConnectorBodyMaterial } from "./useConnectorBodyMaterial";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  EvaluationTransportError,
  evaluateTeeConnector,
} from "../api/client";
import type { MultiRowQuantity } from "../api/multirowContracts";
import type {
  TeeBoltLayoutRequest,
  TeeConnectorDesignResponse,
  TeeConnectorLengthAnchor,
  TeeConnectorRequest,
  TeeInterfaceResult,
  TeeInterfacePlacementTrace,
  TeeProfileFamily,
  TeeProfileOrientation,
} from "../api/teeContracts";
import {
  initialSharedSupport,
  sharedSupportLabel,
  type SharedSupportTargetId,
} from "../api/sharedSupportContracts";
import { loadTeeWorkspaceDefault } from "../fixtures/connectionWorkspaceDefaults";
import { loadTeeBenchmark } from "../fixtures/teeBenchmarks";
import { buildTeeSceneModel } from "../visualization/sceneModel";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import type { SceneSelection } from "../visualization/EngineeringScene";
import {
  ConnectionWorkspaceMain,
  ConnectionWorkspaceShell,
  ConnectionWorkspaceSidebar,
  PersistentConnectionViewer,
  SidebarGroup,
} from "./ConnectionWorkspaceShell";
import {
  formatDisplayQuantity,
  friendlyEnum,
  friendlyIdentifier,
} from "./presentation";
import { useTeePreview } from "./teeWorkflow";
import {
  initialConnectedMemberProfile,
  PROFILE_SURFACE_LABELS,
  TEE_PROFILE_DEFINITIONS,
  TEE_PROFILE_FAMILIES,
} from "./teeProfileOptions";
import { teeValidationMessage } from "./teeValidation";
import { teeDesignBlocker, teeSelectionExists } from "./teePreviewState";
import { SupportingMemberEditor } from "./SupportingMemberEditor";
import {
  applyExactPlacementMode,
  clearanceRecoveryFromBackendDetail,
  requirePlacementOffset,
} from "./teePlacement";

function initialTeeRequest(): TeeConnectorRequest {
  return loadTeeWorkspaceDefault("US_CUSTOMARY");
}

function DecimalField({ label, accessibleLabel = label, helper, quantity: value, onChange }: {
  readonly label: string;
  readonly accessibleLabel?: string;
  readonly helper?: string;
  readonly quantity: MultiRowQuantity;
  readonly onChange: (value: string) => void;
}) {
  return (
    <label className="field-control">
      <span>{label}{helper === undefined ? null : <small className="field-helper">{helper}</small>}</span>
      <span className="input-with-unit">
        <input
          aria-label={accessibleLabel}
          type="text"
          inputMode="decimal"
          value={value.value}
          onChange={(event) => { onChange(event.currentTarget.value); }}
        />
        <small>{value.unit}</small>
      </span>
    </label>
  );
}

function LayoutEditor({
  title,
  interfaceLabel,
  interfaceId,
  value,
  verticalExtent,
  horizontalExtent,
  displayedPlacement,
  currentPlacement,
  invalidDetail,
  onChange,
  selected = false,
  onSelect,
}: {
  readonly title: string;
  readonly interfaceLabel: "Interface A" | "Interface B";
  readonly interfaceId: string;
  readonly value: TeeBoltLayoutRequest;
  readonly verticalExtent: MultiRowQuantity;
  readonly horizontalExtent: MultiRowQuantity;
  readonly displayedPlacement: TeeInterfacePlacementTrace | null;
  readonly currentPlacement: TeeInterfacePlacementTrace | null;
  readonly invalidDetail: string | null;
  readonly onChange: (change: (layoutValue: TeeBoltLayoutRequest) => void) => void;
  readonly selected?: boolean;
  readonly onSelect?: () => void;
}) {
  const [conversionMessage, setConversionMessage] = useState<string | null>(null);
  const quantityField = (
    label: string,
    key:
      | "pitch"
      | "gauge"
      | "unloaded_end_distance"
      | "loaded_end_distance"
      | "negative_side_distance"
      | "positive_side_distance",
  ) => (
    <DecimalField
      label={label}
      quantity={value[key]}
      onChange={(next) => { onChange((layoutValue) => { layoutValue[key].value = next; }); }}
    />
  );
  const offsetMode = value.placement_mode === "GROUP_OFFSET_CONTROLLED";
  const selectMode = (mode: "EDGE_DISTANCE_CONTROLLED" | "GROUP_OFFSET_CONTROLLED") => {
    const candidate = structuredClone(value);
    if (!applyExactPlacementMode(candidate, mode, currentPlacement)) {
      setConversionMessage(
        "Exact conversion is unavailable until the current placement has an accepted backend preview. The bolt group was not repositioned.",
      );
      return;
    }
    setConversionMessage(null);
    onChange((layoutValue) => {
      applyExactPlacementMode(layoutValue, mode, currentPlacement);
    });
  };
  const centerGroup = () => {
    setConversionMessage(null);
    onChange((layoutValue) => {
      layoutValue.placement_mode = "GROUP_OFFSET_CONTROLLED";
      layoutValue.vertical_offset = { value: "0", unit: verticalExtent.unit };
      layoutValue.horizontal_offset = { value: "0", unit: horizontalExtent.unit };
    });
  };
  const displayUnitSystem = verticalExtent.unit === "in" ? "US_CUSTOMARY" : "SI";
  const signedClearance = (quantity: MultiRowQuantity): string => {
    const formatted = formatDisplayQuantity(quantity, displayUnitSystem);
    const numeric = Number(quantity.value);
    if (numeric === 0) {
      const unit = formatted.slice(formatted.lastIndexOf(" ") + 1);
      return `0.0000 ${unit}`;
    }
    return numeric > 0 ? `+${formatted}` : formatted;
  };
  const recovery = clearanceRecoveryFromBackendDetail(invalidDetail, interfaceId);
  return (
    <SidebarGroup title={title} summary={`${String(value.row_count)} × ${String(value.bolts_per_row)}`} defaultOpen selected={selected} onSelect={onSelect} onFocusCapture={onSelect}>
        <section className="tee-placement-section" aria-label={`${interfaceLabel} bolt pattern`}>
          <h4>Bolt Pattern</h4>
        <div className="field-grid">
          <label className="field-control"><span>Rows</span><input aria-label={`${title} rows`} type="number" min="1" value={value.row_count} onChange={(event) => { const count = Number(event.currentTarget.value); onChange((layoutValue) => { layoutValue.row_count = count; }); }} /></label>
          <label className="field-control"><span>Bolts per row</span><input aria-label={`${title} bolts per row`} type="number" min="1" value={value.bolts_per_row} onChange={(event) => { const count = Number(event.currentTarget.value); onChange((layoutValue) => { layoutValue.bolts_per_row = count; }); }} /></label>
          {quantityField("Pitch", "pitch")}
          {quantityField("Gauge", "gauge")}
        </div>
        </section>
        <section className="tee-placement-section" aria-label={`${interfaceLabel} bolt group position`}>
          <h4>Bolt Group Position</h4>
          <div className="field-grid">
          {offsetMode ? <>
            <DecimalField label="Vertical offset" accessibleLabel={`${interfaceLabel} vertical offset`} helper="+ up / − down" quantity={requirePlacementOffset(value.vertical_offset)} onChange={(next) => { onChange((layoutValue) => { requirePlacementOffset(layoutValue.vertical_offset).value = next; }); }} />
            <DecimalField label="Horizontal offset" accessibleLabel={`${interfaceLabel} horizontal offset`} helper="Uses the interface H-axis shown in the viewer/inspector" quantity={requirePlacementOffset(value.horizontal_offset)} onChange={(next) => { onChange((layoutValue) => { requirePlacementOffset(layoutValue.horizontal_offset).value = next; }); }} />
          </> : <p className="sidebar-note placement-mode-summary">Positioning: edge-distance controlled</p>}
          </div>
          <button type="button" className="secondary-button center-bolt-group" aria-label={`Center ${interfaceLabel} bolt group`} onClick={centerGroup}>Center bolt group</button>
        </section>
        <section className="tee-placement-section" aria-label={`${interfaceLabel} computed clearances`}>
          <h4>Computed Clearances</h4>
          {displayedPlacement === null ? <p className="sidebar-note">Awaiting server-authored clearances.</p> : <dl className="diagnostic-list tee-clearance-trace"><div><dt>Vertical + clearance</dt><dd>{signedClearance(displayedPlacement.clearances.vertical_positive)}</dd></div><div><dt>Vertical − clearance</dt><dd>{signedClearance(displayedPlacement.clearances.vertical_negative)}</dd></div><div><dt>Horizontal + clearance</dt><dd>{signedClearance(displayedPlacement.clearances.horizontal_positive)}</dd></div><div><dt>Horizontal − clearance</dt><dd>{signedClearance(displayedPlacement.clearances.horizontal_negative)}</dd></div><div><dt>Tee +L end clearance</dt><dd>{signedClearance(displayedPlacement.clearances.tee_positive_end_complete_hole_clearance)}</dd></div><div><dt>Tee −L end clearance</dt><dd>{signedClearance(displayedPlacement.clearances.tee_negative_end_complete_hole_clearance)}</dd></div><div><dt>Governing Tee end</dt><dd>{friendlyIdentifier(displayedPlacement.clearances.governing_tee_end_id)}</dd></div><div><dt>Governing Tee-end bolt</dt><dd>{friendlyIdentifier(displayedPlacement.clearances.governing_tee_end_bolt_id)}</dd></div><div><dt>Governing geometry clearance</dt><dd>{signedClearance(displayedPlacement.clearances.minimum)}</dd></div><div><dt>Placement datum</dt><dd>{friendlyIdentifier(displayedPlacement.datum_id)}</dd></div></dl>}
          {displayedPlacement !== null && Number(displayedPlacement.clearances.minimum.value) === 0 ? <p className="clearance-status clearance-boundary" role="status">{signedClearance(displayedPlacement.clearances.minimum)} — complete hole is exactly at the physical containment boundary</p> : null}
          {recovery === null ? null : <div className="clearance-status clearance-invalid" role="alert"><strong>Current governing geometry clearance {recovery.clearance} {recovery.unit}</strong><span>Move the group inward ({recovery.direction}) by at least {recovery.clearance.slice(1)} {recovery.unit} to restore complete-hole containment.</span></div>}
          {displayedPlacement?.clearances.minimum_complete_hole_containment === null || displayedPlacement?.clearances.minimum_complete_hole_containment === undefined ? null : <p className="sidebar-note">Physical complete-hole containment threshold: {formatDisplayQuantity(displayedPlacement.clearances.minimum_complete_hole_containment, displayUnitSystem)}</p>}
          <dl className="diagnostic-list placement-authority-distinction"><div><dt>Geometry containment</dt><dd>Backend physical-surface result</dd></div><div><dt>Code / engineering minimum</dt><dd>Not established by this containment output</dd></div></dl>
          <p className="sidebar-note">Geometry containment verifies that the complete hole remains inside the finite physical surface. It is not, by itself, a code-required edge-distance check.</p>
        </section>
        <details className="tee-advanced-placement">
          <summary>Advanced placement</summary>
          <div className="tee-advanced-placement-body">
            <label className="field-control"><span>Placement method</span><select aria-label={`${interfaceLabel} placement method`} value={offsetMode ? "GROUP_OFFSET_CONTROLLED" : "EDGE_DISTANCE_CONTROLLED"} onChange={(event) => { selectMode(event.currentTarget.value as "EDGE_DISTANCE_CONTROLLED" | "GROUP_OFFSET_CONTROLLED"); }}><option value="GROUP_OFFSET_CONTROLLED">Bolt-group offsets</option><option value="EDGE_DISTANCE_CONTROLLED">Edge-distance controlled</option></select></label>
            {offsetMode ? null : <div className="field-grid">
              {quantityField("Unloaded end distance", "unloaded_end_distance")}
              {quantityField("Loaded end distance", "loaded_end_distance")}
              {quantityField("Negative side distance", "negative_side_distance")}
              {quantityField("Positive side distance", "positive_side_distance")}
            </div>}
            {conversionMessage === null ? null : <p className="sidebar-note placement-conversion-message" role="status">{conversionMessage}</p>}
          </div>
        </details>
    </SidebarGroup>
  );
}

function InterfaceResultCard({ label, value, displayUnitSystem }: {
  readonly label: string;
  readonly value: TeeInterfaceResult;
  readonly displayUnitSystem: "US_CUSTOMARY" | "SI";
}) {
  const normal = value.normal_component;
  const handoff = value.design?.automatic_handoff_results[0] ?? null;
  return (
    <article className="source-card compact-source-card">
      <div className="card-title"><div><p className="eyebrow">{friendlyIdentifier(value.bolt_group_id)}</p><h4>{label}</h4></div><span className="locked-badge">{handoff === null ? "PREVIEW" : friendlyEnum(handoff.overall_disposition)}</span></div>
      <dl className="property-grid">
        <div><dt>Normal action</dt><dd>{normal === null ? "Unavailable" : formatDisplayQuantity(normal, displayUnitSystem)}</dd></div>
        <div><dt>Axis tension generated</dt><dd>No</dd></div>
        <div><dt>Normal path</dt><dd>{value.normal_action_supported ? "No normal requirement" : "Not evaluated"}</dd></div>
        <div><dt>Demand method</dt><dd>{friendlyEnum(value.preview.automatic_demand_result?.availability ?? "PENDING")}</dd></div>
        <div><dt>Resistance handoff</dt><dd>{handoff === null ? "Run Design Check" : friendlyEnum(handoff.coverage)}</dd></div>
        <div><dt>Fixed-grid method</dt><dd>{friendlyEnum(value.placement.method_compatibility)}</dd></div>
        <div><dt>Minimum geometry clearance</dt><dd>{formatDisplayQuantity(value.placement.clearances.minimum, displayUnitSystem)}</dd></div>
      </dl>
    </article>
  );
}

export function TeeConnectorWorkspace() {
  const [request, setRequest] = useState<TeeConnectorRequest>(initialTeeRequest);
  const [revision, setRevision] = useState(0);
  const [design, setDesign] = useState<TeeConnectorDesignResponse | null>(null);
  const [designError, setDesignError] = useState<EvaluationTransportError | null>(null);
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);
  const [selection, setSelection] = useState<SceneSelection>({ kind: "MEMBER", id: "tee-connector" });
  const [interfaceFocus, setInterfaceFocus] = useState<"BRACE_TEE" | "TEE_SUPPORT" | null>(null);
  const designController = useRef<AbortController | null>(null);
  useEffect(() => () => {
    designController.current?.abort();
    designController.current = null;
  }, []);
  const previewInput = useMemo(() => ({
    request,
    revision,
    immediate: revision === 0,
    validationMessage: teeValidationMessage(request),
  }), [request, revision]);
  const preview = useTeePreview(previewInput);
  const model = useMemo(() => {
    const visualization = preview.response?.result.visualization;
    return visualization === null || visualization === undefined
      ? null
      : buildTeeSceneModel(visualization);
  }, [preview.response]);
  useEffect(() => {
    if (model === null) return;
    let disposed = false;
    queueMicrotask(() => {
      /* v8 ignore next -- unmount cancellation guard */
      if (disposed) return;
      setSelection((current) => {
        return teeSelectionExists(model, current)
          ? current
          : { kind: "MEMBER", id: "tee-connector" };
      });
    });
    return () => { disposed = true; };
  }, [model]);

  const cancelPendingDesign = () => {
    designController.current?.abort();
    designController.current = null;
    setLoading(false);
  };
  const update = (change: (next: TeeConnectorRequest) => void) => {
    cancelPendingDesign();
    setRequest((current) => {
      const next = structuredClone(current);
      change(next);
      return next;
    });
    setRevision((value) => value + 1);
    if (design !== null) setStale(true);
    setDesignError(null);
  };
  const loadBenchmark = (unitSystem: "US_CUSTOMARY" | "SI") => {
    cancelPendingDesign();
    setRequest(loadTeeBenchmark(unitSystem));
    setRevision((value) => value + 1);
    setStale(design !== null);
    setDesignError(null);
  };
  const updateLayout = (
    key: "interface_a_layout" | "interface_b_layout",
    change: (layoutValue: TeeBoltLayoutRequest) => void,
  ) => { update((next) => { change(next[key]); }); };
  const switchSupportTarget = (target: SharedSupportTargetId) => {
    update((next) => {
      const oldLongitudinal = next.support_target_id === "W_BEAM_FLANGE"
        ? next.global_force.x
        : next.global_force.z;
      next.support_target_id = target;
      next.support_profile = initialSharedSupport(target, next.source_length_unit, "tee-support");
      const beam = target === "W_BEAM_FLANGE";
      next.global_force.x = beam ? oldLongitudinal : "0";
      next.global_force.z = beam ? "0" : oldLongitudinal;
    });
  };
  const bodyMaterial = useConnectorBodyMaterial("tee-connector", request, revision, () => {
    cancelPendingDesign(); setDesign(null); setDesignError(null); setStale(true);
  });
  const runDesign = async () => {
    if (bodyMaterial.material === "SS316") { await bodyMaterial.run(); return; }
    designController.current?.abort();
    const controller = new AbortController();
    designController.current = controller;
    setLoading(true);
    setDesignError(null);
    try {
      const result = await evaluateTeeConnector(request, controller.signal);
      if (designController.current !== controller) return;
      setDesign(result);
      setStale(false);
    } catch (caught) {
      if (controller.signal.aborted) return;
      setDesignError(
        caught instanceof EvaluationTransportError
          ? caught
          : new EvaluationTransportError("RESPONSE", null, "Unexpected Tee design failure.", caught),
      );
    } finally {
      if (designController.current === controller) {
        designController.current = null;
        setLoading(false);
      }
    }
  };
  const lastValidPreviewResult = preview.response?.result ?? null;
  const currentPreviewResult = preview.state === "CURRENT_VALID" ? lastValidPreviewResult : null;
  const shownResult = design === null || stale ? lastValidPreviewResult : design.result.preview;
  const localValidation = teeValidationMessage(request);
  const blocker = teeDesignBlocker(localValidation, preview.state, currentPreviewResult);
  const switchLengthAnchor = (anchor: TeeConnectorLengthAnchor) => {
    const placement = currentPreviewResult?.tee_longitudinal_placement;
    /* v8 ignore next -- the anchor control is disabled until a current accepted preview exists */
    if (placement === undefined) return;
    const coordinate = anchor === "CENTER"
      ? placement.body_center_coordinate
      : anchor === "POSITIVE_L_END"
        ? placement.positive_end_coordinate
        : placement.negative_end_coordinate;
    update((next) => {
      next.connector_length_anchor = anchor;
      next.connector_length_anchor_position = {
        value: coordinate.value,
        unit: next.source_length_unit,
      };
    });
  };

  const dimensionField = (
    label: string,
    group: "connector_dimensions",
    key: string,
  ) => {
    const values = request[group] as unknown as Record<string, MultiRowQuantity>;
    const current = values[key];
    /* v8 ignore next -- fixed Stage 3.2 controls only request declared dimension keys */
    if (current === undefined) throw new Error(`Missing Tee dimension ${key}.`);
    return <DecimalField label={label} quantity={current} onChange={(value) => { update((next) => { const target = next[group] as unknown as Record<string, MultiRowQuantity>; const item = target[key]; /* v8 ignore next -- key is fixed by the declared control above */ if (item === undefined) throw new Error(`Missing Tee dimension ${key}.`); item.value = value; }); }} />;
  };
  const profileDefinition = TEE_PROFILE_DEFINITIONS[request.connected_member_profile.profile_family];
  const profileDimensionField = (key: string, label: string) => {
    const current = request.connected_member_profile.dimensions[key];
    /* v8 ignore next -- controls are defined by the selected profile-family registry */
    if (current === undefined) throw new Error(`Missing connected-member profile dimension ${key}.`);
    return <DecimalField label={label} quantity={current} onChange={(value) => { update((next) => { const item = next.connected_member_profile.dimensions[key]; /* v8 ignore next -- selected registry keys and request dimensions are created together */ if (item === undefined) throw new Error(`Missing connected-member profile dimension ${key}.`); item.value = value; }); }} />;
  };
  const changeProfileFamily = (family: TeeProfileFamily) => {
    const definition = TEE_PROFILE_DEFINITIONS[family];
    if (!definition.enabledForDirectTee) return;
    update((next) => {
      next.connected_member_profile = initialConnectedMemberProfile(next.source_length_unit, family);
    });
  };
  const profileLabel = profileDefinition.label;
  const supportLabel = sharedSupportLabel(request.support_target_id);
  const connectionTitle = `FRP ${profileLabel} Brace → FRP Tee → ${supportLabel}`;
  const displayedProfileFamily = lastValidPreviewResult?.connected_member_profile.profile_family ?? null;
  const displayedProfileLabel = displayedProfileFamily === null
    ? null
    : TEE_PROFILE_DEFINITIONS[displayedProfileFamily].label;
  const displayedSupportLabel = lastValidPreviewResult === null
    ? supportLabel
    : sharedSupportLabel(lastValidPreviewResult.support_target_id);
  const displayedConnectionTitle = displayedProfileLabel === null
    ? connectionTitle
    : `FRP ${displayedProfileLabel} Brace → FRP Tee → ${displayedSupportLabel}`;
  const displayedAssemblyStatus = friendlyEnum(
    lastValidPreviewResult?.assembly_status ?? "NOT_EVALUATED",
  );
  const previewStateMessage = preview.state === "CURRENT_VALID"
    ? null
    : preview.state === "PREVIEW_PENDING"
      ? model === null
        ? "Preview updating — waiting for the first valid backend preview"
        : "Preview updating — showing last valid preview"
      : preview.state === "CURRENT_INVALID_SHOWING_LAST_VALID"
        ? "Current inputs are invalid — showing last valid preview"
        : preview.state === "PREVIEW_FAILED_SHOWING_LAST_VALID"
          ? "Preview failed — showing last valid preview"
          : "Current inputs have no valid backend preview";
  const currentPreviewDetail = localValidation ?? preview.invalidDetail;
  const previewStatusLabel = preview.state === "CURRENT_VALID"
    ? `${displayedAssemblyStatus} model`
    : preview.state === "PREVIEW_PENDING"
      ? "Updating model…"
      : preview.state === "CURRENT_INVALID_SHOWING_LAST_VALID"
        ? "Last valid preview"
        : preview.state === "PREVIEW_FAILED_SHOWING_LAST_VALID"
          ? "Preview failed · last valid"
          : "No valid preview";
  const highlightedInterface = interfaceFocus === null ? null : interfaceFocus === "BRACE_TEE"
    ? {
        interfaceId: lastValidPreviewResult?.interface_a.interface_id ?? "TEE_INTERFACE_A_BRACE_TO_STEM",
        label: "Brace ↔ Tee Stem",
      }
    : {
        interfaceId: lastValidPreviewResult?.interface_b.interface_id ?? "TEE_INTERFACE_B_FLANGE_TO_SUPPORT",
        label: "Tee Flange ↔ Support",
      };

  return (
    <ConnectionWorkspaceShell
      className="tee-workspace"
      banner={<section className="workspace-banner tee-workspace-banner" aria-labelledby="tee-workspace-title">
        <div><p className="eyebrow">Shear · Brace connection — Tee connector</p><h2 id="tee-workspace-title">{connectionTitle}</h2></div>
        <div className="workspace-scope-chips"><span>{profileLabel} brace</span><span>{supportLabel}</span><span>Session only</span><span>{previewStatusLabel}</span></div>
      </section>}
    >
      <ConnectionWorkspaceSidebar ariaLabel="Tee connector engineering inputs">
      <ConnectorBodyMaterialControl material={bodyMaterial.material} onChange={bodyMaterial.choose} />
        <SidebarGroup title="General / Case" summary={request.unit_system} defaultOpen>
          <div className="benchmark-buttons"><button type="button" onClick={() => { loadBenchmark("US_CUSTOMARY"); }}>Load U.S. Tee benchmark</button><button type="button" onClick={() => { loadBenchmark("SI"); }}>Load SI Tee benchmark</button></div>
          <div className="readonly-value"><span>Unit system</span><strong>{request.unit_system === "US_CUSTOMARY" ? "U.S. customary" : "SI"}</strong></div>
          <p className="sidebar-note">Session only · not saved</p>
        </SidebarGroup>

        <SidebarGroup title="Connection" summary="Brace → Tee → support" defaultOpen>
          <p className="demand-boundary-note">One backend-authoritative Tee connector with two independently resolved physical interfaces.</p>
          <dl className="diagnostic-list"><div><dt>Connected member role</dt><dd>Brace</dd></div><div><dt>Connector</dt><dd>FRP Tee</dd></div><div><dt>Supporting profile</dt><dd>{supportLabel}</dd></div></dl>
        </SidebarGroup>

        <SidebarGroup title="Connected Member" summary={`FRP ${profileLabel}`} defaultOpen selected={selection.kind === "MEMBER" && selection.id === "tee-brace"} onSelect={() => { setSelection({ kind: "MEMBER", id: "tee-brace" }); setInterfaceFocus(null); }}>
          <label className="field-control"><span>Brace profile family</span><select aria-label="Brace profile family" value={request.connected_member_profile.profile_family} onChange={(event) => { changeProfileFamily(event.currentTarget.value as TeeProfileFamily); }}><optgroup label="Flat contact profiles">{TEE_PROFILE_FAMILIES.map((family) => <option key={family} value={family} disabled={!TEE_PROFILE_DEFINITIONS[family].enabledForDirectTee}>{TEE_PROFILE_DEFINITIONS[family].label}</option>)}</optgroup></select></label>
          <div className="field-grid">{profileDefinition.dimensions.map((field) => <span className="profile-dimension-control" key={field.key}>{profileDimensionField(field.key, field.label)}</span>)}</div>
          <label className="field-control"><span>Brace inclination</span><span className="input-with-unit"><input aria-label="Brace inclination" type="number" min="-90" max="90" step="any" value={request.brace_inclination_degrees} onChange={(event) => { const value = event.currentTarget.value; update((next) => { next.brace_inclination_degrees = value; }); }} /><small>deg</small></span></label>
          <label className="field-control"><span>Profile roll about member axis</span><select aria-label="Profile roll about member axis" value={request.connected_member_profile.profile_orientation} onChange={(event) => { const orientation = event.currentTarget.value as TeeProfileOrientation; update((next) => { next.connected_member_profile.profile_orientation = orientation; }); }}><option value="ROTATION_0">0° about member axis</option><option value="ROTATION_90">90° about member axis</option><option value="ROTATION_180">180° about member axis</option><option value="ROTATION_270">270° about member axis</option></select></label>
          <label className="field-control"><span>Brace connection surface</span><select aria-label="Brace connection surface" value={request.connected_member_profile.selected_profile_surface} onChange={(event) => { const surface = event.currentTarget.value as TeeConnectorRequest["connected_member_profile"]["selected_profile_surface"]; update((next) => { next.connected_member_profile.selected_profile_surface = surface; }); }}>{profileDefinition.surfaces.map((surface) => <option key={surface} value={surface}>{PROFILE_SURFACE_LABELS[surface]}</option>)}</select></label>
          <section className="tee-placement-section" aria-label="Member end trim">
            <h4>Member end trim</h4>
            <label className="field-control tee-checkbox-control"><span>Apply end trim clearance</span><input aria-label="Apply end trim clearance" type="checkbox" checked={request.connected_member_end_trim_enabled} onChange={(event) => { const enabled = event.currentTarget.checked; update((next) => { next.connected_member_end_trim_enabled = enabled; next.connected_member_end_clearance = enabled ? { value: "0", unit: next.source_length_unit } : null; }); }} /></label>
            {request.connected_member_end_trim_enabled && request.connected_member_end_clearance !== null
              ? <DecimalField label="End clearance to Tee flange" helper="Perpendicular gap between the fabricated member end and the Tee flange/root clearance plane." quantity={request.connected_member_end_clearance} onChange={(value) => { update((next) => { next.connected_member_end_clearance = { value, unit: next.source_length_unit }; }); }} />
              : <p className="sidebar-note">No fabrication end trim</p>}
          </section>
          <p className="sidebar-note">Profile geometry and the selected physical surface are validated and placed by the backend. Shape and dimensions never infer strength.</p>
        </SidebarGroup>

        <SidebarGroup title="Supporting Member" summary={supportLabel} selected={selection.kind === "MEMBER" && selection.id === "tee-support"} onSelect={() => { setSelection({ kind: "MEMBER", id: "tee-support" }); setInterfaceFocus(null); }}>
          <SupportingMemberEditor targetId={request.support_target_id} profile={request.support_profile} onTargetChange={switchSupportTarget} onProfileChange={(change) => { update((next) => { change(next.support_profile); }); }} />
          <p className="sidebar-note">The selected target, complete physical profile, contact face, and material regions are resolved by the backend.</p>
        </SidebarGroup>

        <SidebarGroup title="Connector" summary="Pultruded FRP Tee" selected={selection.kind === "MEMBER" && selection.id === "tee-connector"} onSelect={() => { setSelection({ kind: "MEMBER", id: "tee-connector" }); setInterfaceFocus(null); }}>
          <div className="field-grid">{dimensionField("Connector length", "connector_dimensions", "connector_length")}{dimensionField("Flange width", "connector_dimensions", "flange_width")}{dimensionField("Flange thickness", "connector_dimensions", "flange_thickness")}{dimensionField("Stem depth", "connector_dimensions", "stem_depth")}{dimensionField("Stem thickness", "connector_dimensions", "stem_thickness")}</div>
          <label className="field-control"><span>Length anchor</span><select aria-label="Length anchor" value={request.connector_length_anchor} disabled={currentPreviewResult === null} onChange={(event) => { switchLengthAnchor(event.currentTarget.value as TeeConnectorLengthAnchor); }}><option value="CENTER">Centered</option><option value="POSITIVE_L_END">{request.support_target_id === "W_BEAM_FLANGE" ? "Keep +L end fixed" : "Keep upper end fixed"}</option><option value="NEGATIVE_L_END">{request.support_target_id === "W_BEAM_FLANGE" ? "Keep −L end fixed" : "Keep lower end fixed"}</option></select></label>
          <DecimalField label={request.support_target_id === "W_BEAM_FLANGE" ? "Tee longitudinal position" : "Tee vertical position"} helper="Position of the selected length anchor along the Tee longitudinal axis. + moves toward +L / upper direction." quantity={request.connector_length_anchor_position} onChange={(value) => { update((next) => { next.connector_length_anchor_position.value = value; }); }} />
        </SidebarGroup>

        <LayoutEditor title="Brace ↔ Tee Stem" interfaceLabel="Interface A" interfaceId="TEE_INTERFACE_A_BRACE_TO_STEM" value={request.interface_a_layout} verticalExtent={request.connector_dimensions.connector_length} horizontalExtent={request.connector_dimensions.stem_depth} displayedPlacement={lastValidPreviewResult?.interface_a.placement ?? null} currentPlacement={currentPreviewResult?.interface_a.placement ?? null} invalidDetail={currentPreviewDetail} selected={interfaceFocus === "BRACE_TEE"} onSelect={() => { setInterfaceFocus("BRACE_TEE"); }} onChange={(change) => { updateLayout("interface_a_layout", change); }} />
        <LayoutEditor title="Tee Flange ↔ Support" interfaceLabel="Interface B" interfaceId="TEE_INTERFACE_B_FLANGE_TO_SUPPORT" value={request.interface_b_layout} verticalExtent={request.connector_dimensions.connector_length} horizontalExtent={request.connector_dimensions.flange_width} displayedPlacement={lastValidPreviewResult?.interface_b.placement ?? null} currentPlacement={currentPreviewResult?.interface_b.placement ?? null} invalidDetail={currentPreviewDetail} selected={interfaceFocus === "TEE_SUPPORT"} onSelect={() => { setInterfaceFocus("TEE_SUPPORT"); }} onChange={(change) => { updateLayout("interface_b_layout", change); }} />

        <SidebarGroup title="Materials" summary="Controlled FRP">
          <dl className="diagnostic-list"><div><dt>Brace</dt><dd>Pultruded FRP · controlled separately from profile</dd></div><div><dt>Tee</dt><dd>Pultruded FRP · ICE locked data</dd></div><div><dt>Strength inference</dt><dd>None; explicit snapshot gate only</dd></div></dl>
        </SidebarGroup>
        <SidebarGroup title="Fasteners" summary="316SS · ASTM F593 snapshot">
          <DecimalField label="Bolt diameter" quantity={request.bolt_diameter} onChange={(value) => { update((next) => { next.bolt_diameter.value = value; }); }} />
          <p className="sidebar-note">Explicit 316 stainless-steel fastener authority; no material inferred from profile geometry.</p>
        </SidebarGroup>
        <SidebarGroup title="Loads / Member-End Action" summary="Global frame" defaultOpen>
          <p className="demand-boundary-note">The backend resolves this one canonical action and physical reference point independently into each physical interface frame.</p><div className="field-grid">
            {(["x", "y", "z"] as const).map((axis) => <DecimalField key={`force-${axis}`} label={`Force ${axis.toUpperCase()}`} quantity={{ value: request.global_force[axis], unit: request.global_force.unit }} onChange={(value) => { update((next) => { next.global_force[axis] = value; }); }} />)}
            {(["x", "y", "z"] as const).map((axis) => <DecimalField key={`moment-${axis}`} label={`Moment ${axis.toUpperCase()}`} quantity={{ value: request.global_moment[axis], unit: request.global_moment.unit }} onChange={(value) => { update((next) => { next.global_moment[axis] = value; }); }} />)}
            {(["x", "y", "z"] as const).map((axis) => <DecimalField key={`reference-${axis}`} label={`Reference ${axis.toUpperCase()}`} quantity={{ value: request.global_reference_point[axis], unit: request.global_reference_point.unit }} onChange={(value) => { update((next) => { next.global_reference_point[axis] = value; }); }} />)}
          </div>
        </SidebarGroup>
        <SidebarGroup title="Factors / Method" summary="Inherited accepted engines"><p className="sidebar-note">Stage 2.5A/2.5B/2.6A/2.6B demand and resistance behavior is reused unchanged. No new profile-specific resistance is inferred.</p></SidebarGroup>
        <SidebarGroup title="Model / Geometry Status" summary={previewStatusLabel} defaultOpen>
          <strong>{previewStateMessage ?? `${displayedAssemblyStatus} current model`}</strong>
          {currentPreviewDetail === null ? null : <p className="sidebar-note">{currentPreviewDetail}</p>}
          <dl className="diagnostic-list"><div><dt>Current form profile</dt><dd>{request.connected_member_profile.profile_family}</dd></div><div><dt>Current form surface</dt><dd>{request.connected_member_profile.selected_profile_surface}</dd></div><div><dt>Displayed preview profile</dt><dd>{lastValidPreviewResult?.connected_member_profile.profile_family ?? "None"}</dd></div><div><dt>Displayed preview surface</dt><dd>{lastValidPreviewResult?.visualization?.selected_connected_surface_id ?? "None"}</dd></div><div><dt>Member end trim</dt><dd>{lastValidPreviewResult?.connected_member_end_trim.enabled === true ? "Applied" : "No fabrication end trim"}</dd></div><div><dt>Tee-root interference</dt><dd>{friendlyEnum(lastValidPreviewResult?.connected_member_end_trim.interference_status ?? "Not resolved")}</dd></div>{lastValidPreviewResult?.connected_member_end_trim.measured_plane_clearance === null || lastValidPreviewResult?.connected_member_end_trim.measured_plane_clearance === undefined ? null : <div><dt>Measured trim gap</dt><dd>{formatDisplayQuantity(lastValidPreviewResult.connected_member_end_trim.measured_plane_clearance, request.unit_system)}</dd></div>}{lastValidPreviewResult?.connected_member_end_trim.minimum_hole_edge_clearance === null || lastValidPreviewResult?.connected_member_end_trim.minimum_hole_edge_clearance === undefined ? null : <div><dt>Hole-edge clearance to trim</dt><dd>{formatDisplayQuantity(lastValidPreviewResult.connected_member_end_trim.minimum_hole_edge_clearance, request.unit_system)}</dd></div>}</dl>
        </SidebarGroup>
        <SidebarGroup title="Design Results" summary={design === null ? "No design run" : stale ? "Stale" : friendlyEnum(design.assembly_status)} defaultOpen><p className="sidebar-note">{design === null ? "Run Design Check to populate resistance results." : stale ? "Previous design results are stale." : `${friendlyEnum(design.assembly_status)} · ordinary whole-connection PASS prohibited`}</p></SidebarGroup>
        <SidebarGroup title="Advanced / Diagnostics" summary="Stable IDs and fingerprints"><dl className="diagnostic-list"><div><dt>Current profile ID</dt><dd>{request.connected_member_profile.profile_id}</dd></div><div><dt>Current profile family</dt><dd>{request.connected_member_profile.profile_family}</dd></div><div><dt>Current surface ID</dt><dd>{request.connected_member_profile.selected_profile_surface}</dd></div><div><dt>Displayed brace inclination</dt><dd>{lastValidPreviewResult?.connected_member_profile.brace_inclination_degrees ?? "None"}°</dd></div><div><dt>Tee longitudinal datum</dt><dd>{friendlyIdentifier(lastValidPreviewResult?.tee_longitudinal_placement.tee_longitudinal_datum_id ?? "Not resolved")}</dd></div><div><dt>Tee +L direction</dt><dd>{lastValidPreviewResult === null ? "Not resolved" : `(${lastValidPreviewResult.tee_longitudinal_placement.longitudinal_axis.x}, ${lastValidPreviewResult.tee_longitudinal_placement.longitudinal_axis.y}, ${lastValidPreviewResult.tee_longitudinal_placement.longitudinal_axis.z})`}</dd></div><div><dt>Tee −L / +L ends</dt><dd>{lastValidPreviewResult === null ? "Not resolved" : `${formatDisplayQuantity(lastValidPreviewResult.tee_longitudinal_placement.negative_end_coordinate, request.unit_system)} / ${formatDisplayQuantity(lastValidPreviewResult.tee_longitudinal_placement.positive_end_coordinate, request.unit_system)}`}</dd></div><div><dt>Displayed profile fingerprint</dt><dd>{lastValidPreviewResult?.connected_member_profile.profile_geometry_fingerprint ?? "None"}</dd></div><div><dt>Displayed Tee-body fingerprint</dt><dd>{lastValidPreviewResult?.tee_longitudinal_placement.body_geometry_fingerprint ?? "None"}</dd></div><div><dt>Displayed engineering fingerprint</dt><dd>{lastValidPreviewResult?.engineering_fingerprint ?? "None"}</dd></div></dl></SidebarGroup>
        <section className="evaluate-panel sidebar-evaluate" aria-label="Tee design-check controls"><p>Preview updates geometry and actions only. Resistance runs only on explicit request.</p><button type="button" className="primary-button" disabled={bodyMaterial.busy || loading || blocker !== null} title={blocker ?? undefined} onClick={() => { void runDesign(); }}>{loading ? "Running design check…" : "Run Design Check"}</button>{blocker === null ? null : <p className="sidebar-note" role="status">{blocker}</p>}</section>
      </ConnectionWorkspaceSidebar>

      <ConnectionWorkspaceMain><ConnectorBodyMaterialResult state={bodyMaterial} />
        <PersistentConnectionViewer unity={viewerUnity("tee", design, { stale, checking: loading, error: designError, previewState: preview.state })}>
          {previewStateMessage === null ? null : <div className={`tee-preview-state tee-preview-state-${preview.state.toLowerCase()}`} role="status" aria-live="polite"><strong>{previewStateMessage}</strong>{currentPreviewDetail === null ? null : <span>{currentPreviewDetail}</span>}</div>}
          {model === null ? <section className="viewer-prompt"><h3>Canonical Tee model unavailable</h3><p>{currentPreviewDetail ?? previewStateMessage}</p><div className="viewer-prompt-graphic" aria-hidden="true"><span /><span /><span /></div></section> : <VisualizationPanel model={model} title={displayedConnectionTitle} contactSelectionLabel="Selected physical Tee connection surface" interfaceHighlight={highlightedInterface} selection={selection} onSelect={setSelection} appliedActionInputValues={{ FX: request.global_force.x, FY: request.global_force.y, FZ: request.global_force.z, MX: request.global_moment.x, MY: request.global_moment.y, MZ: request.global_moment.z }} onAppliedActionValueChange={(component, value) => { const forceKey = component.startsWith("F") ? component.slice(1).toLowerCase() as "x" | "y" | "z" : null; const momentKey = component.startsWith("M") ? component.slice(1).toLowerCase() as "x" | "y" | "z" : null; update((next) => { if (forceKey !== null) next.global_force[forceKey] = value; if (momentKey !== null) next.global_moment[momentKey] = value; }); }} actionSourceLabel="Canonical Tee member-end action" />}
        </PersistentConnectionViewer>
        {preview.error === null ? null : <div className="error-banner" role="alert"><strong>{preview.invalidDetail ?? preview.error.message}</strong>{preview.invalidDetail === null ? null : <span>{preview.error.message}</span>}<button type="button" onClick={preview.retry}>Retry preview</button></div>}
        {designError === null ? null : <div className="error-banner" role="alert">{designError.message}</div>}
        {stale ? <div className="stale-banner" role="status">Design results are stale. {preview.state === "CURRENT_VALID" ? "The 3D model reflects the current backend preview." : "The viewer may be showing the last valid backend preview."} Run the design check again after a current valid preview.</div> : null}
        {previewStateMessage === null || lastValidPreviewResult === null ? null : <div className="stale-banner preview-result-context" role="status">{previewStateMessage}. Results below belong to the displayed last valid preview.</div>}
        <section className="tee-results-grid" aria-label="Tee connector grouped results">
          {shownResult === null ? <p>No current Tee result.</p> : <>
            <InterfaceResultCard label="Brace ↔ Tee Stem" value={shownResult.interface_a} displayUnitSystem={request.unit_system} />
            <InterfaceResultCard label="Tee Flange ↔ Support" value={shownResult.interface_b} displayUnitSystem={request.unit_system} />
            <article className="qualification-banner tee-body-limitation"><span aria-hidden="true">!</span><div><strong>Tee connector body · Not evaluated</strong><p>General Tee flange/stem bending, yielding, rupture, and prying are outside Stage 3.2. Ordinary whole-connection PASS is prohibited. A supported interface failure still governs FAIL.</p></div></article>
          </>}
        </section>
        <details className="results-drawer" open={design !== null}><summary><span>Design results &amp; trace</span><small>{design === null ? "Run Design Check to populate" : stale ? "STALE" : friendlyEnum(design.assembly_status)}</small></summary><div className="results-drawer-body"><dl className="diagnostic-list"><div><dt>Assembly status</dt><dd>{design === null ? "No design run" : friendlyEnum(design.assembly_status)}</dd></div><div><dt>Ordinary PASS allowed</dt><dd>No</dd></div><div><dt>Supported interface failure</dt><dd>{design?.supported_interface_failure_present === true ? "Yes" : "No"}</dd></div><div><dt>Displayed connected profile</dt><dd>{displayedProfileLabel ?? "None"}</dd></div><div><dt>Displayed selected surface</dt><dd>{lastValidPreviewResult?.visualization === null || lastValidPreviewResult?.visualization === undefined ? "None" : PROFILE_SURFACE_LABELS[lastValidPreviewResult.visualization.selected_connected_surface_id]}</dd></div><div><dt>Displayed engineering fingerprint</dt><dd>{lastValidPreviewResult?.engineering_fingerprint ?? "None"}</dd></div><div><dt>Result fingerprint</dt><dd>{design?.result_fingerprint ?? "Pending"}</dd></div></dl></div></details>
      </ConnectionWorkspaceMain>
    </ConnectionWorkspaceShell>
  );
}
