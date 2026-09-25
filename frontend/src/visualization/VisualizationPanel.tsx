import { lazy, Suspense, useCallback, useRef, useState } from "react";
import type { RefCallback } from "react";
import { UnityRatioIndicator } from "../workspace/UnityRatioIndicator";
import { useUnityViewer } from "../workspace/UnityViewerContext";

import type {
  ActionDirectionSnapshot,
  CalculationResultDTO,
  JsonValue,
  ResolvedLayerDTO,
} from "../api/contracts";
import { formatDecimal, friendlyEnum, friendlyIdentifier } from "../workspace/presentation";
import type { ProjectedActionLabel } from "./actionLabelContract";
import { actionLabelKey } from "./actionLabelContract";
import type {
  CameraOrientation2D,
  SceneDisplayMode,
  SceneInterfaceHighlight,
  SceneSelection,
  SceneVisibility,
} from "./EngineeringScene";
import type {
  SceneFrame,
  SceneMarker,
  SceneMaterialAxes,
  SceneViewId,
  SingleBoltSceneModel,
} from "./sceneModel";
import { materialRegionLabel, SCENE_VIEWS } from "./sceneModel";

const EngineeringScene = lazy(() => import("./EngineeringScene"));

const INITIAL_VISIBILITY: SceneVisibility = {
  physicalGeometry: true,
  deferredGeometry: false,
  interfaceZones: false,
  selectedContactSurface: true,
  boltAndHoles: true,
  cornerGlobalTriad: true,
  globalAxes: false,
  memberAxes: "SELECTED",
  connectorAxes: false,
  interfaceAxes: false,
  boltGroupAxes: false,
  materialAxes: false,
  referencePoints: false,
  boltAxis: true,
  positiveDirections: false,
  appliedDirections: true,
  actionValues: true,
  zeroActions: false,
  perBoltDemands: false,
};

type ActionComponent = ActionDirectionSnapshot["component"];
type AppliedActionInputValues = Readonly<Record<ActionComponent, string>>;

export interface SelectedBoltCheckSummary {
  readonly id: string;
  readonly label: string;
  readonly status: string;
  readonly demand: string;
  readonly utilization: string;
}

interface VisualizationPanelProps {
  readonly model: SingleBoltSceneModel;
  readonly results?: readonly CalculationResultDTO[];
  readonly resolvedLayers?: readonly ResolvedLayerDTO[];
  readonly selection: SceneSelection;
  readonly onSelect: (selection: SceneSelection) => void;
  readonly appliedActionInputValues?: AppliedActionInputValues;
  readonly onAppliedActionValueChange?: (
    component: ActionComponent,
    value: string,
  ) => void;
  readonly actionSourceLabel?: string;
  readonly selectedBoltChecks?: readonly SelectedBoltCheckSummary[];
  readonly title?: string;
  readonly contactSelectionLabel?: string;
  readonly interfaceHighlight?: SceneInterfaceHighlight | null;
}

interface MaterialInspectorRow {
  readonly axes: SceneMaterialAxes;
  readonly bearing: CalculationResultDTO | undefined;
  readonly layer: ResolvedLayerDTO | null;
  readonly netTension: CalculationResultDTO | undefined;
  readonly rawAngle: string | null;
}

function Toggle({ label, checked, onChange }: {
  readonly label: string;
  readonly checked: boolean;
  readonly onChange: (checked: boolean) => void;
}) {
  return (
    <label className="scene-toggle">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => { onChange(event.currentTarget.checked); }}
      />
      <span>{label}</span>
    </label>
  );
}

function display(value: number): string {
  return value.toLocaleString(undefined, { maximumSignificantDigits: 6 });
}

function actionComponentLabel(component: ActionComponent): string {
  return `${component.slice(0, 1)}${component.slice(1).toLowerCase()}`;
}

function formattedSignedAction(value: number): string {
  const formatted = Math.abs(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${value < 0 ? "−" : "+"}${formatted}`;
}

function positionActionLabel(
  element: HTMLElement,
  projection: ProjectedActionLabel,
): void {
  element.style.left = `${String(projection.x)}px`;
  element.style.top = `${String(projection.y)}px`;
  element.style.visibility = projection.visible ? "visible" : "hidden";
  element.dataset.projectedX = String(projection.x);
  element.dataset.projectedY = String(projection.y);
}

function hideActionLabel(element: HTMLElement): void {
  element.style.visibility = "hidden";
}

function serverString(value: JsonValue | undefined): string | null {
  return typeof value === "string" ? value : null;
}

const INITIAL_CAMERA_ORIENTATION: CameraOrientation2D = {
  x: [1, 0],
  y: [0, -1],
  z: [0, 0],
};

const TRIAD_AXES = [
  ["X", "x", "#c83838"],
  ["Y", "y", "#32824d"],
  ["Z", "z", "#3468b2"],
] as const;

function triadEndpoint(axis: readonly [number, number]): readonly [number, number] {
  const length = Math.hypot(axis[0], axis[1]);
  const factor = length === 0 ? 0 : 25 / Math.max(1, length);
  return [42 + axis[0] * factor, 42 + axis[1] * factor];
}

function updateCornerGlobalTriad(
  element: SVGSVGElement,
  orientation: CameraOrientation2D,
): void {
  for (const [label, key] of TRIAD_AXES) {
    const [x, y] = triadEndpoint(orientation[key]);
    const line = element.querySelectorAll<SVGLineElement>(`[data-triad-line="${label}"]`).item(0);
    const text = element.querySelectorAll<SVGTextElement>(`[data-triad-label="${label}"]`).item(0);
    line.setAttribute("x2", String(x));
    line.setAttribute("y2", String(y));
    text.setAttribute("x", String(x + 4));
    text.setAttribute("y", String(y - 3));
  }
}

function CornerGlobalTriad({ triadRef }: { readonly triadRef: RefCallback<SVGSVGElement> }) {
  const axes = [
    ["X", INITIAL_CAMERA_ORIENTATION.x, "#c83838"],
    ["Y", INITIAL_CAMERA_ORIENTATION.y, "#32824d"],
    ["Z", INITIAL_CAMERA_ORIENTATION.z, "#3468b2"],
  ] as const;
  return (
    <svg ref={triadRef} className="corner-global-triad" viewBox="0 0 84 84" aria-label="Global X Y Z orientation triad">
      <circle cx="42" cy="42" r="3" fill="#263746" />
      {axes.map(([label, axis, color]) => {
        const [x, y] = triadEndpoint(axis);
        return (
          <g key={label}>
            <line data-triad-line={label} x1="42" y1="42" x2={x} y2={y} stroke={color} strokeWidth="3" />
            <text data-triad-label={label} x={x + 4} y={y - 3} fill={color}>{label}</text>
          </g>
        );
      })}
    </svg>
  );
}

function MaterialAxisLegendSymbol({ kind }: { readonly kind: "CW" | "LW" | "TT" }) {
  if (kind === "TT") {
    return (
      <svg
        aria-hidden="true"
        className="material-axis-legend-symbol material-axis-legend-tt"
        data-material-axis-symbol="TT"
        viewBox="0 0 44 18"
      >
        <circle cx="10" cy="9" r="6" />
        <circle className="material-axis-legend-dot" cx="10" cy="9" r="2" />
        <circle cx="34" cy="9" r="6" />
        <path d="M30 5l8 8M38 5l-8 8" />
      </svg>
    );
  }
  return (
    <svg
      aria-hidden="true"
      className={`material-axis-legend-symbol material-axis-legend-${kind.toLowerCase()}`}
      data-material-axis-symbol={kind}
      viewBox="0 0 44 18"
    >
      <path d="M4 9h36M4 9l6-4M4 9l6 4M40 9l-6-4M40 9l-6 4" />
    </svg>
  );
}

function MaterialAxesLegend() {
  return (
    <section className="material-axes-legend" aria-label="Material axes legend">
      <strong>Material axes</strong>
      <div><MaterialAxisLegendSymbol kind="LW" /><span><b>LW</b> — Longitudinal</span></div>
      <div><MaterialAxisLegendSymbol kind="CW" /><span><b>CW</b> — Crosswise</span></div>
      <div><MaterialAxisLegendSymbol kind="TT" /><span><b>TT</b> — Through-thickness</span></div>
    </section>
  );
}

function frameLabel(frame: SceneFrame): string {
  if (frame.kind === "GLOBAL") return "Global";
  if (frame.kind === "JOINT_LOCAL") return "Joint local";
  if (frame.kind === "MEMBER_LOCAL") return `${friendlyIdentifier(frame.ownerId)} local`;
  if (frame.kind === "INTERFACE_LOCAL") return "Interface local";
  if (frame.kind === "BOLT_GROUP_LOCAL") return "Bolt group local";
  return frame.label;
}

function referenceLabel(marker: SceneMarker): string {
  if (marker.id.startsWith("action:")) return "Member-end action reference point";
  if (marker.kind === "BOLT_CENTER") return "Bolt 1 center";
  if (marker.kind === "MEMBER_END" && marker.memberEnd !== null) {
    const identity = friendlyIdentifier(marker.id.replace(/:.*/u, ""));
    return `${identity} ${marker.memberEnd}${marker.connected === true ? " · connected end" : ""}`;
  }
  return marker.label;
}

function UnityRatioOverlay() {
  const unity = useUnityViewer();
  return unity === null ? null : <div className="unity-canvas-overlay"><UnityRatioIndicator value={unity} /></div>;
}

export function VisualizationPanel({
  model,
  results = [],
  resolvedLayers = [],
  selection,
  onSelect,
  appliedActionInputValues,
  onAppliedActionValueChange,
  actionSourceLabel = "Member",
  selectedBoltChecks = [],
  title = "Brace-to-column connection",
  contactSelectionLabel = "W Column Flange contact face",
  interfaceHighlight = null,
}: VisualizationPanelProps) {
  const [view, setView] = useState<SceneViewId>("3D");
  const [displayMode, setDisplayMode] = useState<SceneDisplayMode>("SOLID");
  const [visibility, setVisibility] = useState<SceneVisibility>(INITIAL_VISIBILITY);
  const [resetNonce, setResetNonce] = useState(0);
  const [editingAction, setEditingAction] = useState<ActionComponent | null>(null);
  const [actionDraft, setActionDraft] = useState("");
  const cornerTriadRef = useRef<SVGSVGElement>(null);
  const lastCameraOrientationRef = useRef<CameraOrientation2D>(INITIAL_CAMERA_ORIENTATION);
  const actionLabelElementsRef = useRef(new Map<string, HTMLElement>());
  const lastActionLabelProjectionsRef = useRef(new Map<string, ProjectedActionLabel>());
  const handleCameraOrientation = useCallback((value: CameraOrientation2D) => {
    lastCameraOrientationRef.current = value;
    if (cornerTriadRef.current !== null) {
      updateCornerGlobalTriad(cornerTriadRef.current, value);
    }
  }, []);
  const handleCornerTriadRef = useCallback<RefCallback<SVGSVGElement>>((element) => {
    cornerTriadRef.current = element;
    if (element !== null) {
      updateCornerGlobalTriad(element, lastCameraOrientationRef.current);
    }
  }, []);
  const handleActionLabelRef = useCallback((key: string, element: HTMLElement | null) => {
    if (element === null) {
      actionLabelElementsRef.current.delete(key);
      return;
    }
    actionLabelElementsRef.current.set(key, element);
    const projection = lastActionLabelProjectionsRef.current.get(key);
    if (projection !== undefined) positionActionLabel(element, projection);
  }, []);
  const handleActionLabelProjection = useCallback(
    (projections: readonly ProjectedActionLabel[]) => {
      const next = new Map(projections.map((projection) => [projection.key, projection]));
      lastActionLabelProjectionsRef.current = next;
      for (const [key, element] of actionLabelElementsRef.current) {
        const projection = next.get(key);
        if (projection === undefined) {
          hideActionLabel(element);
        } else {
          positionActionLabel(element, projection);
        }
      }
    },
    [],
  );
  const setFlag = <Key extends keyof SceneVisibility>(key: Key, value: SceneVisibility[Key]) => {
    setVisibility((current) => ({ ...current, [key]: value }));
  };
  const describedMarkers = model.markers.filter(
    (value) => value.memberEnd !== null || value.kind.includes("ORIGIN") || value.kind === "BOLT_CENTER",
  );
  const selectedBolt = selection.kind === "BOLT"
    ? model.cylinders.find(
        (value) => value.kind === "BOLT" && value.ownerBoltId === selection.id,
      ) ?? null
    : null;
  const materialRows: readonly MaterialInspectorRow[] = model.materialAxes.map((axes): MaterialInspectorRow => {
    const layer = resolvedLayers.find(
      (value) => value.participant_id === axes.componentId && value.physical_element_id === axes.elementId,
    );
    if (layer === undefined) {
      return { axes, bearing: undefined, layer: null, netTension: undefined, rawAngle: null };
    }
    const layerResults = results.filter((value) => value.plan.layer_id === layer.layer_id);
    const bearing = layerResults.find((value) => value.plan.limit_state === "PIN_BEARING");
    const netTension = layerResults.find((value) => value.plan.limit_state === "NET_SECTION_TENSION");
    const rawAngle = serverString((bearing ?? netTension)?.plan.theta_degrees);
    return { axes, bearing, layer, netTension, rawAngle };
  });
  const fitConnection = () => { setResetNonce((value) => value + 1); };
  const resetView = () => {
    setView("3D");
    setDisplayMode("SOLID");
    setVisibility(INITIAL_VISIBILITY);
    fitConnection();
  };
  const visibleAppliedActions = visibility.appliedDirections && visibility.actionValues
    ? model.appliedArrows.filter((value) => visibility.zeroActions || !value.isZero)
    : [];
  const visiblePositiveActions = visibility.positiveDirections ? model.positiveArrows : [];
  const startActionEdit = (component: ActionComponent) => {
    const value = appliedActionInputValues?.[component];
    if (value === undefined || onAppliedActionValueChange === undefined) return;
    setActionDraft(value);
    setEditingAction(component);
  };
  const cancelActionEdit = () => {
    setEditingAction(null);
    setActionDraft("");
  };
  const commitActionEdit = (
    component: ActionComponent,
    onChange: NonNullable<VisualizationPanelProps["onAppliedActionValueChange"]>,
  ) => {
    const trimmed = actionDraft.trim();
    if (trimmed === "" || !Number.isFinite(Number(trimmed))) {
      cancelActionEdit();
      return;
    }
    onChange(component, trimmed);
    setEditingAction(null);
    setActionDraft("");
  };

  return (
    <section className="visualization-panel" aria-labelledby="visualization-title">
      <div className="viewer-title-row">
        <div>
          <p className="eyebrow">Canonical connection view</p>
          <h3 id="visualization-title">{title}</h3>
        </div>
        <span className="schema-chip">Snapshot {model.snapshotVersion}</span>
      </div>
      <p id="canvas-description" className="sr-description">
        Solid standard-shape members, selected bolt and round holes, with optional
        server-resolved frames, material directions, reference points, interface zones,
        and signed action arrows. Canvas controls change presentation only.
        {visibility.materialAxes
          ? " Region-embedded material axes are active: purple longitudinal and amber crosswise bidirectional axes plus teal through-thickness normal markers."
          : " Region-embedded material axes are hidden."}
      </p>

      <div className="view-toolbar" aria-label="Visualization views and camera controls">
        <div className="segmented-control" role="group" aria-label="Engineering view">
          {(Object.keys(SCENE_VIEWS) as SceneViewId[]).map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={view === value}
              title={SCENE_VIEWS[value].description}
              onClick={() => { setView(value); }}
            >
              {value}
            </button>
          ))}
        </div>
        <button type="button" className="secondary-button" onClick={fitConnection}>
          Fit Connection
        </button>
        <button type="button" className="secondary-button" onClick={resetView}>
          Reset view
        </button>
        <label className="toolbar-select">
          <span>Display</span>
          <select
            aria-label="Geometry display"
            value={displayMode}
            onChange={(event) => { setDisplayMode(event.currentTarget.value as SceneDisplayMode); }}
          >
            <option value="SOLID">Solid</option>
            <option value="XRAY">X-ray</option>
          </select>
        </label>
        <details className="overlay-menu">
          <summary>Overlays</summary>
          <div className="overlay-grid">
            <Toggle label="Physical geometry" checked={visibility.physicalGeometry} onChange={(value) => { setFlag("physicalGeometry", value); }} />
            <Toggle label="Deferred geometry" checked={visibility.deferredGeometry} onChange={(value) => { setFlag("deferredGeometry", value); }} />
            <Toggle label="Interface zones" checked={visibility.interfaceZones} onChange={(value) => { setFlag("interfaceZones", value); }} />
            <Toggle label="Selected contact surface" checked={visibility.selectedContactSurface} onChange={(value) => { setFlag("selectedContactSurface", value); }} />
            <Toggle label="Bolts and holes" checked={visibility.boltAndHoles} onChange={(value) => { setFlag("boltAndHoles", value); }} />
            <Toggle label="Corner global X / Y / Z triad" checked={visibility.cornerGlobalTriad} onChange={(value) => { setFlag("cornerGlobalTriad", value); }} />
            <Toggle label="Full model-space global axes" checked={visibility.globalAxes} onChange={(value) => { setFlag("globalAxes", value); }} />
            <label className="scene-toggle select-toggle">
              <span>Member local axes</span>
              <select
                value={visibility.memberAxes}
                onChange={(event) => { setFlag("memberAxes", event.currentTarget.value as SceneVisibility["memberAxes"]); }}
              >
                <option value="OFF">Off</option>
                <option value="SELECTED">Selected member</option>
                <option value="ALL">All members</option>
              </select>
            </label>
            <Toggle label="Connector local axes" checked={visibility.connectorAxes} onChange={(value) => { setFlag("connectorAxes", value); }} />
            <Toggle label="Interface-local axes" checked={visibility.interfaceAxes} onChange={(value) => { setFlag("interfaceAxes", value); }} />
            <Toggle label="Bolt-group axes" checked={visibility.boltGroupAxes} onChange={(value) => { setFlag("boltGroupAxes", value); }} />
            <Toggle label="Material axes (LW / CW / TT)" checked={visibility.materialAxes} onChange={(value) => { setFlag("materialAxes", value); }} />
            <Toggle label="Reference points and START / END" checked={visibility.referencePoints} onChange={(value) => { setFlag("referencePoints", value); }} />
            <Toggle label="Bolt axis and round holes" checked={visibility.boltAxis} onChange={(value) => { setFlag("boltAxis", value); }} />
            <Toggle label="Positive sign-convention arrows" checked={visibility.positiveDirections} onChange={(value) => { setFlag("positiveDirections", value); }} />
            <Toggle label="Applied signed force / moment arrows" checked={visibility.appliedDirections} onChange={(value) => { setFlag("appliedDirections", value); }} />
            <Toggle label="Action values" checked={visibility.actionValues} onChange={(value) => { setFlag("actionValues", value); }} />
            <Toggle label="Show zero actions" checked={visibility.zeroActions} onChange={(value) => { setFlag("zeroActions", value); }} />
            {model.perBoltDemandArrows.length === 0 ? null : <Toggle label="Per-bolt demand vectors" checked={visibility.perBoltDemands} onChange={(value) => { setFlag("perBoltDemands", value); }} />}
          </div>
        </details>
      </div>

      <p className="viewport-navigation-help">
        {"3D navigation: left-drag rotate \u00b7 right-drag pan \u00b7 wheel zoom"}
      </p>
      {model.connectionDemandArrows.length === 0 ? null : <p className="connection-demand-legend"><span aria-hidden="true" /> Red resultant arrow: {model.perBoltDemandArrows.length === 0 ? "externally resolved connection demand" : "backend-projected member-end force at its physical reference point"}. Member-end action arrows remain separate context.</p>}
      {visibility.perBoltDemands ? <p className="connection-demand-legend"><span aria-hidden="true" /> Backend-authored total per-bolt demand vectors. Select a bolt for exact supported check values.</p> : null}
      {visibility.perBoltDemands ? <ul className="per-bolt-demand-values" aria-label="Per-bolt demand vector values">{model.perBoltDemandArrows.map((arrow) => <li key={arrow.id}><strong>{friendlyIdentifier(arrow.referencePointId)}</strong> {arrow.signedValue === null ? "—" : display(arrow.signedValue)} {arrow.unit}</li>)}</ul> : null}

      <div className="canvas-shell">
        <UnityRatioOverlay />
        <div className="scene-canvas-region" role="img" aria-describedby="canvas-description">
        <Suspense fallback={<div className="canvas-loading">Loading 3D renderer…</div>}>
          <EngineeringScene
            model={model}
            view={view}
            visibility={visibility}
            resetNonce={resetNonce}
            displayMode={displayMode}
            selection={selection}
            onSelect={onSelect}
            interfaceHighlight={interfaceHighlight}
            onCameraOrientationChange={handleCameraOrientation}
            onActionLabelProjectionChange={handleActionLabelProjection}
          />
        </Suspense>
        </div>
        <div
          className="action-label-layer"
          aria-label="Projected action labels"
          onPointerDown={(event) => { event.stopPropagation(); }}
          onClick={(event) => { event.stopPropagation(); }}
        >
          {visiblePositiveActions.map((arrow) => {
            const key = actionLabelKey("POSITIVE", arrow.component, arrow.id);
            return (
              <span
                className={`positive-action-label ${arrow.kind === "LINEAR" ? "force-action-label" : "moment-action-label"}`}
                key={key}
                ref={(element) => { handleActionLabelRef(key, element); }}
                data-action-component={arrow.component}
                data-action-kind={arrow.kind}
                data-action-label-placement="projected"
                data-action-source="POSITIVE"
              >
                +{actionComponentLabel(arrow.component)}
              </span>
            );
          })}
          {visibleAppliedActions.map((arrow) => {
            const label = [actionSourceLabel.trim(), arrow.componentLabel ?? actionComponentLabel(arrow.component)].filter(Boolean).join(" ");
            const key = actionLabelKey("APPLIED", arrow.component, arrow.id);
            if (
              editingAction === arrow.component &&
              onAppliedActionValueChange !== undefined
            ) {
              return (
                <label
                  className={`applied-action-editor ${arrow.kind === "LINEAR" ? "force-action-label" : "moment-action-label"}`}
                  key={key}
                  ref={(element) => { handleActionLabelRef(key, element); }}
                  data-action-component={arrow.component}
                  data-action-kind={arrow.kind}
                  data-action-label-placement="projected"
                  data-action-source={actionSourceLabel}
                >
                  <span>{label} =</span>
                  <span className="input-with-unit">
                    <input
                      autoFocus
                      aria-label={`Edit ${label} value`}
                      inputMode="decimal"
                      value={actionDraft}
                      onChange={(event) => { setActionDraft(event.currentTarget.value); }}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          commitActionEdit(arrow.component, onAppliedActionValueChange);
                        } else if (event.key === "Escape") {
                          event.preventDefault();
                          cancelActionEdit();
                        }
                      }}
                      onBlur={() => {
                        commitActionEdit(arrow.component, onAppliedActionValueChange);
                      }}
                    />
                    <small>{arrow.unit ?? ""}</small>
                  </span>
                </label>
              );
            }
            return (
              <button
                type="button"
                className={`applied-action-label ${arrow.kind === "LINEAR" ? "force-action-label" : "moment-action-label"}`}
                key={key}
                ref={(element) => { handleActionLabelRef(key, element); }}
                aria-label={`Edit ${label} applied load value`}
                data-action-component={arrow.component}
                data-action-kind={arrow.kind}
                data-action-label-placement="projected"
                data-action-source={actionSourceLabel}
                onClick={() => { startActionEdit(arrow.component); }}
              >
                <span>{label} =</span>
                <strong>{arrow.signedValue === null ? "—" : formattedSignedAction(arrow.signedValue)} {arrow.unit ?? ""}</strong>
              </button>
            );
          })}
        </div>
        {visibility.cornerGlobalTriad ? <CornerGlobalTriad triadRef={handleCornerTriadRef} /> : null}
        <div className="selection-legend" aria-label="Selected object">
          <span aria-hidden="true" /> Selected: {selection.kind === "MEMBER" ? friendlyIdentifier(selection.id) : selection.kind === "CONTACT" ? contactSelectionLabel : selectedBolt?.rowId === null ? "Bolt 1" : selectedBolt?.label ?? friendlyIdentifier(selection.id)}{interfaceHighlight === null ? "" : ` · Focus: ${interfaceHighlight.label}`}
        </div>
        <div className="viewer-legend-stack">
          <details className="axis-action-legend">
            <summary>Axis / action legend</summary>
            <p><strong>Global:</strong> X red, Y green, Z blue.</p>
            <p><strong>Selected member:</strong> local x/y/z use the same labeled colors.</p>
            <p><strong>Actions:</strong> applied signed arrows are red; optional positive conventions are navy.</p>
          </details>
          {visibility.materialAxes ? <MaterialAxesLegend /> : null}
        </div>
      </div>

      <div className="inspector-grid">
        {selectedBolt === null ? null : (
          <details open>
            <summary>Selected-bolt inspector</summary>
            <dl className="diagnostic-list">
              <div><dt>Bolt</dt><dd>{selectedBolt.label}</dd></div>
              <div><dt>Row</dt><dd>{friendlyIdentifier(selectedBolt.rowId)}</dd></div>
              <div><dt>Bolt line</dt><dd>{friendlyIdentifier(selectedBolt.boltLineId)}</dd></div>
              <div><dt>Penetrated layers</dt><dd>{selectedBolt.penetratedLayerIds.map(friendlyIdentifier).join(" · ")}</dd></div>
              <div><dt>Relevant checks</dt><dd>{selectedBoltChecks.length === 0 ? "No current design result" : <ul className="selected-bolt-checks">{selectedBoltChecks.map((check) => <li key={check.id}><strong>{check.label}</strong><span>{check.status} · demand {check.demand} · utilization {check.utilization}</span></li>)}</ul>}</dd></div>
            </dl>
          </details>
        )}
        {model.connectionOrientation === null ? null : (
          <details>
            <summary>Connection-orientation inspector</summary>
            <dl className="diagnostic-list">
              <div><dt>Connection face</dt><dd>{model.connectionOrientation.connectionSide === "EXTERIOR" ? "Exterior face" : "Interior / web-side face"}</dd></div>
              <div><dt>Connected angle leg</dt><dd>{friendlyIdentifier(model.connectionOrientation.connectedLeg)}</dd></div>
              <div><dt>Outstanding leg</dt><dd>{model.connectionOrientation.outstandingLegSide === "POSITIVE_INTERFACE_Z" ? "+ interface side" : "− interface side"}</dd></div>
              <div><dt>Selected surface</dt><dd>W Column Flange<small className="advanced-id">{model.connectionOrientation.selectedFlangeElementId} · {model.connectionOrientation.selectedFlangeSurfaceId}</small></dd></div>
              <div><dt>Geometry</dt><dd>{model.connectionOrientation.geometryValid ? "Valid contact; no unintended positive-volume overlap" : "Invalid geometry — unintended member interference"}</dd></div>
            </dl>
          </details>
        )}
        <details>
          <summary>Frame inspector</summary>
          <div className="table-scroll">
            <table>
              <thead><tr><th>Frame</th><th>Origin ({model.lengthUnit})</th><th>Basis</th><th>Status</th></tr></thead>
              <tbody>
                {model.frames.map((frame) => (
                  <tr key={frame.id}>
                    <td>{frameLabel(frame)}<small className="advanced-id">{frame.id}</small></td>
                    <td>{display(frame.origin.x)}, {display(frame.origin.y)}, {display(frame.origin.z)}</td>
                    <td>X({display(frame.xAxis.x)}, {display(frame.xAxis.y)}, {display(frame.xAxis.z)}) · Y({display(frame.yAxis.x)}, {display(frame.yAxis.y)}, {display(frame.yAxis.z)}) · Z({display(frame.zAxis.x)}, {display(frame.zAxis.y)}, {display(frame.zAxis.z)})</td>
                    <td><span className={`status-icon ${frame.valid ? "status-ok" : "status-review"}`} aria-hidden="true">{frame.valid ? "✓" : "!"}</span> {frame.valid ? "Right-handed orthonormal" : "Review required"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
        <details>
          <summary>Material-direction inspector</summary>
          <ul className="inspector-list">
            {materialRows.map(({ axes, bearing, layer, netTension, rawAngle }) => (
              <li key={layer?.layer_id ?? axes.id}>
                <strong>{materialRegionLabel(axes)}{layer === null ? "" : ` · ${friendlyIdentifier(layer.layer_id)}`}</strong>
                <span>LW({display(axes.lengthwise.x)}, {display(axes.lengthwise.y)}, {display(axes.lengthwise.z)}), CW({display(axes.crosswise.x)}, {display(axes.crosswise.y)}, {display(axes.crosswise.z)}), TT({display(axes.throughThickness.x)}, {display(axes.throughThickness.y)}, {display(axes.throughThickness.z)})</span>
                {bearing?.plan.selected_direction_family === null || bearing === undefined ? null : <span>Bearing property direction: {friendlyEnum(bearing.plan.selected_direction_family)}</span>}
                {netTension?.plan.selected_direction_family === null || netTension === undefined ? null : <span>Net-tension property direction: {friendlyEnum(netTension.plan.selected_direction_family)}</span>}
                {rawAngle === null ? null : <span>Force/material angle: {formatDecimal(rawAngle, 1)}°</span>}
                <small className="advanced-id">{axes.componentId} · {axes.elementId} · {axes.materialRegionId}{layer === null ? "" : ` · ${layer.layer_id}`}{rawAngle === null ? "" : ` · raw angle ${rawAngle}°`}</small>
              </li>
            ))}
          </ul>
        </details>
        <details>
          <summary>Reference-point and applied-action inspector</summary>
          <ul className="inspector-list">
            {describedMarkers.map((marker) => (
              <li key={marker.id}>
                <strong>{referenceLabel(marker)}</strong>
                <span>{marker.kind}{marker.connected === true ? " · connected" : ""}: ({display(marker.position.x)}, {display(marker.position.y)}, {display(marker.position.z)}) {model.lengthUnit}</span>
                <small className="advanced-id">{marker.id}</small>
              </li>
            ))}
            {model.appliedArrows.map((arrow) => (
              <li key={arrow.id}>
                <strong>{arrow.component}: {arrow.signedValue === null ? "—" : display(arrow.signedValue)} {arrow.unit ?? ""}</strong>
                <span>{arrow.sense} · {arrow.frameId}{arrow.axialLoadingSense === null ? "" : ` · axial sense ${arrow.axialLoadingSense}`}</span>
                <small className="advanced-id">Reference {arrow.referencePointId}</small>
              </li>
            ))}
            {model.connectionDemandArrows.map((arrow) => (
              <li key={arrow.id}>
                <strong>Externally resolved connection demand: {arrow.signedValue === null ? "—" : display(arrow.signedValue)} {arrow.unit ?? ""}</strong>
                <span>Resultant · {arrow.frameId} · separate from member-end actions</span>
                <small className="advanced-id">Reference {arrow.referencePointId}</small>
              </li>
            ))}
          </ul>
        </details>
      </div>
    </section>
  );
}
