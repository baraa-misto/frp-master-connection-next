import type { DirectFaceClearance } from "../api/multirowContracts";
import { formatDecimal } from "../workspace/presentation";

export function DirectGeometryIssue({ record, unit }: {
  readonly record: DirectFaceClearance;
  readonly unit: "in" | "mm";
}) {
  const edge = record.boundaries.find((item) => item.boundary_id === record.controlling_boundary_id);
  if (edge === undefined) return <p role="alert">The controlling boundary is unavailable. Refresh the canonical model.</p>;
  const u = Number(record.face_point_local[0]);
  const v = Number(record.face_point_local[1]);
  const points = record.boundaries.map((item): readonly [number, number] => [Number(item.start_local[0]), Number(item.start_local[1])]);
  const margin = Number(record.washer_radius) * 2;
  const minU = Math.min(u, ...points.map((p) => p[0])) - margin;
  const minV = Math.min(v, ...points.map((p) => p[1])) - margin;
  const width = Math.max(u, ...points.map((p) => p[0])) + margin - minU;
  const height = Math.max(v, ...points.map((p) => p[1])) + margin - minV;
  const stroke = Math.max(width, height) / 140;
  const actual = formatDecimal(record.center_to_boundary, 3);
  const required = formatDecimal(record.validator_minimum, 3);
  return <section className="geometry-status" aria-label="Canonical geometry issue">
    <h4>Geometry — {record.component_id} / {record.physical_element_id} / {record.bolt_id}</h4>
    <p>Bolt center to selected contact-patch boundary: <strong>{actual} {unit}</strong>. Required minimum: <strong>{required} {unit}</strong>.</p>
    <p>Controlling boundary: {record.controlling_boundary_id}. Contact patches can be subfaces; this boundary is not automatically a physical free member edge.</p>
    <svg role="img" aria-label={`Backend boundary dimension: ${actual} ${unit}; required ${required} ${unit}`} viewBox={[minU, minV, width, height].join(" ")} style={{ width: "100%", maxHeight: "22rem" }}>
      <polygon points={points.map((p) => p.join(",")).join(" ")} fill="#e6eff3" stroke="#536c7f" strokeWidth={stroke} />
      <line x1={edge.start_local[0]} y1={edge.start_local[1]} x2={edge.end_local[0]} y2={edge.end_local[1]} stroke="#bc2b2b" strokeWidth={stroke * 2} />
      <circle cx={u} cy={v} r={record.washer_radius} fill="none" stroke="#5684a8" strokeWidth={stroke} />
      <circle cx={u} cy={v} r={record.hole_radius} fill="none" stroke="#9b6520" strokeWidth={stroke} />
      <circle cx={u} cy={v} r={record.bolt_radius} fill="none" stroke="#273e50" strokeWidth={stroke} />
      <circle cx={u} cy={v} r={stroke * 2} fill="#bc2b2b" />
      <line data-testid="canonical-boundary-dimension" x1={u} y1={v} x2={edge.dimension_end_local[0]} y2={edge.dimension_end_local[1]} stroke="#bc2b2b" strokeWidth={stroke} />
    </svg>
    <p>Face-normal diagnostic view. Red: backend controlling boundary and dimension; dark: bolt; brown: hole; blue: washer. Camera and view extents do not measure this dimension.</p>
    <table><caption>Backend distances to each contact-patch boundary ({unit})</caption><thead><tr><th>Boundary</th><th>Signed center-to-boundary distance</th></tr></thead><tbody>{record.boundaries.map((item) => <tr key={item.boundary_id}><th>{item.boundary_id}</th><td>{formatDecimal(item.distance, 6)}</td></tr>)}</tbody></table>
    <p>Hole radius {formatDecimal(record.hole_radius, 4)} {unit}; washer radius {formatDecimal(record.washer_radius, 4)} {unit}; Chapter 8 center-distance minimum {formatDecimal(record.chapter_8_minimum, 3)} {unit}; plane offset {formatDecimal(record.plane_offset, 6)} {unit}. Bolt-to-bolt spacing is a separate layout input.</p>
    <p>Remaining outside hole: {formatDecimal(record.hole_ligament, 4)} {unit}; outside washer: {formatDecimal(record.washer_ligament, 4)} {unit}.</p>
    <p>Adjust bolt placement or layout within the current members first. Increase member width only if no valid position exists.</p>
  </section>;
}
