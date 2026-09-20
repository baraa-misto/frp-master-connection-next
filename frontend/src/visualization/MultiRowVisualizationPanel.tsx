import type { MultiRowVisualization } from "../api/multirowContracts";
import { formatDisplayQuantity } from "../workspace/presentation";

interface MultiRowVisualizationPanelProps {
  readonly snapshot: MultiRowVisualization;
  readonly showBlockPaths: boolean;
  readonly displayUnitSystem: "US_CUSTOMARY" | "SI";
}

const WIDTH = 760;
const HEIGHT = 520;
const MARGIN = 62;

function requiredBolt(snapshot: MultiRowVisualization, index: number) {
  const bolt = snapshot.bolts[index];
  /* v8 ignore next -- mapped snapshot indexes and nonempty valid snapshots are invariants */
  if (bolt === undefined) throw new Error("A valid multi-row snapshot requires physical bolts.");
  return bolt;
}

function requiredAxis(
  axes: MultiRowVisualization["local_axes"],
  index: number,
): [string, [string, string]] {
  const axis = axes[index];
  /* v8 ignore next -- the backend visualization contract always supplies u and v */
  if (axis === undefined) throw new Error("A valid multi-row snapshot requires local axes.");
  return axis;
}

function boundaryNumber(snapshot: MultiRowVisualization, index: 0 | 1 | 2 | 3): number {
  return Number(snapshot.boundary[index]);
}

export function MultiRowVisualizationPanel({
  snapshot,
  showBlockPaths,
  displayUnitSystem,
}: MultiRowVisualizationPanelProps) {
  const minX = boundaryNumber(snapshot, 0);
  const maxX = boundaryNumber(snapshot, 1);
  const minY = boundaryNumber(snapshot, 2);
  const maxY = boundaryNumber(snapshot, 3);
  const scale = Math.min(
    (WIDTH - MARGIN * 2) / Math.max(maxX - minX, 1),
    (HEIGHT - MARGIN * 2) / Math.max(maxY - minY, 1),
  );
  const x = (value: string) => MARGIN + (Number(value) - minX) * scale;
  const y = (value: string) => HEIGHT - MARGIN - (Number(value) - minY) * scale;
  const boundaryWidth = (maxX - minX) * scale;
  const boundaryHeight = (maxY - minY) * scale;
  const holeRadius = (boltIndex: number) =>
    Number(requiredBolt(snapshot, boltIndex).hole_diameter.value) * scale / 2;
  const boltRadius = (boltIndex: number) =>
    Number(requiredBolt(snapshot, boltIndex).bolt_diameter.value) * scale / 2;
  const forceX = Number(snapshot.demand_components[0].value);
  const forceY = Number(snapshot.demand_components[1].value);
  const norm = Math.hypot(forceX, forceY);
  const arrowStartX = WIDTH - 168;
  const arrowStartY = 92;
  const arrowEndX = arrowStartX + (forceX / norm) * 72;
  const arrowEndY = arrowStartY - (forceY / norm) * 72;
  const [uLabel, uVector] = requiredAxis(snapshot.local_axes, 0);
  const [vLabel, vVector] = requiredAxis(snapshot.local_axes, 1);

  return (
    <section className="multirow-viewer" aria-labelledby="multirow-viewer-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Backend-authoritative interface plane</p>
          <h3 id="multirow-viewer-title">Multi-row connection viewer</h3>
        </div>
        <span className="locked-badge">{snapshot.schema_version}</span>
      </div>
      <svg
        viewBox={`0 0 ${String(WIDTH)} ${String(HEIGHT)}`}
        role="img"
        aria-label={`${String(snapshot.row_ids.length)} rows and ${String(snapshot.bolt_line_ids.length)} bolt lines`}
      >
        <defs>
          <marker id="multirow-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" fill="currentColor" />
          </marker>
        </defs>
        <rect
          className="multirow-layer-surface"
          x={MARGIN}
          y={HEIGHT - MARGIN - boundaryHeight}
          width={boundaryWidth}
          height={boundaryHeight}
        />
        <text
          className="multirow-loaded-boundary-label"
          x={MARGIN + boundaryWidth - 10}
          y={HEIGHT - MARGIN - boundaryHeight / 2}
          textAnchor="middle"
          transform={`rotate(-90 ${String(MARGIN + boundaryWidth - 10)} ${String(HEIGHT - MARGIN - boundaryHeight / 2)})`}
        >Loaded boundary</text>
        {showBlockPaths ? snapshot.block_paths.filter((path) => path.accepted).map((path) => (
          <polyline
            className="multirow-block-path"
            key={path.path_id}
            points={path.points.map(([px, py]) => `${String(x(px))},${String(y(py))}`).join(" ")}
          />
        )) : null}
        {snapshot.bolts.map((bolt, index) => (
          <g key={bolt.bolt_id} aria-label={`${bolt.row_id} ${bolt.bolt_line_id}`}>
            <circle className="multirow-hole" cx={x(bolt.x)} cy={y(bolt.y)} r={holeRadius(index)} />
            <circle className="multirow-bolt" cx={x(bolt.x)} cy={y(bolt.y)} r={boltRadius(index)} />
            {bolt.row_id === snapshot.row_1_id ? (
              <text x={x(bolt.x) + 10} y={y(bolt.y) - 10}>Row 1</text>
            ) : null}
          </g>
        ))}
        <text x={MARGIN} y={HEIGHT - 12}>Unloaded free end · e1 {formatDisplayQuantity(snapshot.unloaded_end_e1, displayUnitSystem)}</text>
        <line className="demand-arrow" x1={arrowStartX} y1={arrowStartY} x2={arrowEndX} y2={arrowEndY} markerEnd="url(#multirow-arrow)" />
        <text x={arrowStartX - 24} y={arrowStartY - 16}>Fx {formatDisplayQuantity(snapshot.demand_components[0], displayUnitSystem)} · Fy {formatDisplayQuantity(snapshot.demand_components[1], displayUnitSystem)}</text>
        <g className="axis-triad" transform="translate(82 98)">
          <line x1="0" y1="0" x2="48" y2="0" markerEnd="url(#multirow-arrow)" />
          <line x1="0" y1="0" x2="0" y2="-48" markerEnd="url(#multirow-arrow)" />
          <text x="54" y="5">X</text><text x="-5" y="-56">Y</text>
        </g>
        <g className="axis-triad local-axis-triad" transform="translate(180 98)">
          <line x1="0" y1="0" x2={Number(uVector[0]) * 48} y2={-Number(uVector[1]) * 48} markerEnd="url(#multirow-arrow)" />
          <line x1="0" y1="0" x2={Number(vVector[0]) * 48} y2={-Number(vVector[1]) * 48} markerEnd="url(#multirow-arrow)" />
          <text x="54" y="5">{uLabel}</text><text x="-5" y="-56">{vLabel}</text>
        </g>
        {snapshot.layers.map((layer, index) => {
          const radians = Number(layer.material_axis_angle_degrees) * Math.PI / 180;
          const originX = 82 + index * 94;
          return <g className="material-axis" key={layer.layer_id} transform={`translate(${String(originX)} 180)`}>
            <line x1="0" y1="0" x2={Math.cos(radians) * 42} y2={-Math.sin(radians) * 42} markerEnd="url(#multirow-arrow)" />
            <text x="48" y="5">LW</text>
          </g>;
        })}
      </svg>
      <dl className="multirow-view-facts">
        <div><dt>Pitch</dt><dd>{formatDisplayQuantity(snapshot.pitch, displayUnitSystem)}</dd></div>
        <div><dt>Gauge</dt><dd>{formatDisplayQuantity(snapshot.gauge, displayUnitSystem)}</dd></div>
        <div><dt>Loaded boundary to Row 1</dt><dd>{formatDisplayQuantity(snapshot.loaded_boundary_to_row_1_distance, displayUnitSystem)}</dd></div>
        <div><dt>Material</dt><dd>{snapshot.layers.map((layer) => `${layer.layer_id}: ${layer.material_direction}`).join(" · ")}</dd></div>
      </dl>
    </section>
  );
}
