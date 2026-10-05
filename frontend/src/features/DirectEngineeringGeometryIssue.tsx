import type { DirectEngineeringFace } from "../api/multirowContracts";
import { formatDecimal, friendlyIdentifier } from "../workspace/presentation";

function geometryCheckName(kind: string): string {
  switch (kind) {
    case "CHAPTER_8_EDGE_DISTANCE": return "Chapter 8 physical free-edge distance";
    case "CHAPTER_8_END_DISTANCE": return "Chapter 8 loaded-end distance";
    case "HOLE_PHYSICAL_CONTAINMENT": return "Physical hole containment";
    case "WASHER_SEATING": return "Washer seating / hardware clearance";
    case "COMPONENT_INTERFERENCE": return "Physical component interference";
    default: return "Physical geometry review";
  }
}

export function DirectEngineeringGeometryIssue({ record, unit }: {
  readonly record: DirectEngineeringFace;
  readonly unit: "in" | "mm";
}) {
  const controlling = record.checks.find((check) => check.pass_fail !== "PASS")
    ?? record.checks.find((check) => check.check_kind === "CHAPTER_8_EDGE_DISTANCE");
  const boundary = record.boundaries.find((item) => item.boundary_id === controlling?.engineering_boundary_id);
  if (controlling === undefined || boundary === undefined) return <p role="alert">The physical geometry witness is unavailable. Refresh the current model.</p>;
  const cross = record.transverse_axis;
  const u = Number(record.bolt_center_member_local[0]);
  const v = Number(record.bolt_center_member_local[cross]);
  const points = record.face_vertices_local.map((p): readonly [number, number] => [Number(p[0]), Number(p[cross])]);
  const margin = Number(record.washer_radius) * 2;
  const minU = Math.min(u, ...points.map((p) => p[0])) - margin;
  const minV = Math.min(v, ...points.map((p) => p[1])) - margin;
  const width = Math.max(u, ...points.map((p) => p[0])) + margin - minU;
  const height = Math.max(v, ...points.map((p) => p[1])) + margin - minV;
  const stroke = Math.max(width, height) / 140;
  const actual = formatDecimal(controlling.actual_distance, 3);
  const required = formatDecimal(controlling.required_distance, 3);
  const visibleChecks = record.checks.filter((check) => check.check_kind.startsWith("CHAPTER_8") || check.pass_fail !== "PASS");
  return <section className="geometry-status direct-engineering-geometry" aria-label="Physical engineering geometry">
    <h4>Geometry — {friendlyIdentifier(record.component_id)} {friendlyIdentifier(record.physical_element_id)} / {record.bolt_id}</h4>
    <p><strong>{geometryCheckName(controlling.check_kind)}</strong>: {actual} {unit}; required {required} {unit}. {controlling.pass_fail}.</p>
    <p>Controlling physical feature: {controlling.boundary_label}.</p>
    <svg role="img" aria-label={`${geometryCheckName(controlling.check_kind)}: ${actual} ${unit}; required ${required} ${unit}`} viewBox={[minU, minV, width, height].join(" ")} style={{ width: "100%", maxHeight: "22rem" }}>
      <polygon points={points.map((p) => p.join(",")).join(" ")} fill="#e6eff3" stroke="#536c7f" strokeWidth={stroke} />
      <line x1={boundary.start_local[0]} y1={boundary.start_local[cross]} x2={boundary.end_local[0]} y2={boundary.end_local[cross]} stroke="#bc2b2b" strokeWidth={stroke * 2} />
      <circle cx={u} cy={v} r={record.washer_radius} fill="none" stroke="#5684a8" strokeWidth={stroke} />
      <circle cx={u} cy={v} r={record.hole_radius} fill="none" stroke="#9b6520" strokeWidth={stroke} />
      <circle cx={u} cy={v} r={stroke * 2} fill="#bc2b2b" />
      <line data-testid="physical-boundary-dimension" x1={u} y1={v} x2={boundary.dimension_end_local[0]} y2={boundary.dimension_end_local[cross]} stroke="#bc2b2b" strokeWidth={stroke} />
    </svg>
    <p>Physical face view. Red identifies the controlling physical feature and backend dimension; brown is the hole; blue is the washer.</p>
    <table><caption>Physical engineering checks ({unit})</caption><thead><tr><th>Check / feature</th><th>Actual</th><th>Required</th><th>Outcome</th></tr></thead><tbody>{visibleChecks.map((check) => <tr key={`${check.check_kind}:${check.engineering_boundary_id}`}><th>{geometryCheckName(check.check_kind)} — {check.boundary_label}</th><td>{formatDecimal(check.actual_distance, 6)}</td><td>{formatDecimal(check.required_distance, 6)}</td><td>{check.pass_fail}</td></tr>)}</tbody></table>
    <p>Hole containment and washer seating use their physical radii separately. Computational contact-patch subdivisions do not supply Chapter 8 limits.</p>
    {record.limitations.map((text) => <p key={text}>{text}</p>)}
    <p>For a failed physical edge/end distance, adjust the actual bolt position or member geometry. For a hardware issue, provide adequate seating clearance.</p>
  </section>;
}
