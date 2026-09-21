import { ExtrudeGeometry, Path, Shape } from "three";
import type { SSMCResponse } from "../api/ssmcClient";
import type { MultiRowQuantity } from "../api/multirowContracts";
import { calculatePresentationBounds, type SceneArrow, type SceneCylinder, type SceneTriangleMesh, type SingleBoltSceneModel, type Vec3 } from "./sceneModel";

const scale = (v: Vec3, f: number): Vec3 => ({ x: v.x * f, y: v.y * f, z: v.z * f });
const add = (a: Vec3, b: Vec3): Vec3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
const inches = (q: MultiRowQuantity): number => Number(q.value) / (q.unit === "mm" ? 25.4 : 1);

export function buildSSMCScene(p: SSMCResponse["result"], current: boolean): SingleBoltSceneModel {
  const geometry = p.geometry, f = geometry.length_unit === "mm" ? 1 / 25.4 : 1;
  const meshes: SceneTriangleMesh[] = geometry.members.flatMap(member => member.trimmed.solids.map(solid => ({
    id: member.owner + ":" + solid.physical_element_id, label: member.owner + " " + solid.physical_element_id,
    ownerId: member.owner, ownerLabel: member.owner, ownerRole: "BRACE" as const,
    elementId: solid.physical_element_id, materialRegionId: solid.material_region_id,
    points: solid.faces.flatMap(face => face.vertices.slice(1, -1).flatMap((v, index) => {
      const first = face.vertices[0], third = face.vertices[index + 2];
      if (first === undefined || third === undefined) throw new Error("SSMC native face is incomplete.");
      return [first, v, third].map(point => scale(point, f));
    })),
  })));
  // Downstream presentation only: the backend analytic polygon/hole loops
  // remain authoritative. Circle tessellation never returns to engineering.
  const shape = new Shape();
  geometry.polygon.boundary.forEach(([x, z], index) => { if (index === 0) shape.moveTo(x * f, z * f); else shape.lineTo(x * f, z * f); });
  shape.closePath();
  for (const hole of geometry.polygon_paths.holes) {
    const path = new Path(); path.absarc(hole.center[0] * f, hole.center[1] * f, hole.radius * f, 0, Math.PI * 2, true); shape.holes.push(path);
  }
  const extruded = new ExtrudeGeometry(shape, { depth: (geometry.plate_y_interval[1] - geometry.plate_y_interval[0]) * f, bevelEnabled: false, curveSegments: 24 });
  const buffer = extruded.getAttribute("position"), points: Vec3[] = [];
  for (let i = 0; i < buffer.count; i++) points.push({ x: buffer.getX(i), y: geometry.plate_y_interval[0] * f + buffer.getZ(i), z: buffer.getY(i) });
  extruded.dispose();
  meshes.push({ id: "MITER_WEB_PLATE", label: "One-piece miter plate — CW basis, unknown cut", ownerId: "MITER_WEB_PLATE", ownerLabel: "Miter web plate", ownerRole: "OTHER", elementId: "PLATE", materialRegionId: "MITER_PLATE_CW_BASIS_UNKNOWN_CUT", points });
  const h = p.input.fastener.hardware;
  const wt = inches(h.washer_thickness), hh = inches(h.head_height), nh = inches(h.nut_height);
  const cylinders: SceneCylinder[] = geometry.shafts.flatMap(s => {
    const entry = scale(s.start, f), exit = scale(s.end, f);
    const direction = { x: 0, y: Math.sign(exit.y - entry.y), z: 0 };
    const headWasher = add(entry, scale(direction, -wt)), headOuter = add(headWasher, scale(direction, -hh));
    const nutInner = add(exit, scale(direction, wt)), nutOuter = add(nutInner, scale(direction, nh));
    const common = { ownerBoltId: s.id, rowId: String(s.row), boltLineId: String(s.line), penetratedLayerIds: s.layer_owners, interfaceId: s.group, hardwareLocation: null };
    return [
      { ...common, id: s.id, label: s.id, kind: "BOLT", diameter: inches(p.input.fastener.diameter), start: headOuter, end: add(nutOuter, scale(direction, inches(h.end_extension))), exactHardware: { source: h.geometry_source, headStart: headOuter, headEnd: headWasher, headAcrossFlats: inches(h.head_across_flats), nutStart: nutInner, nutEnd: nutOuter, nutAcrossFlats: inches(h.nut_across_flats) } },
      { ...common, id: s.id + ":HEAD_WASHER", label: "Plate-side washer", kind: "WASHER", hardwareLocation: "UNDER_HEAD", diameter: inches(h.washer_diameter), start: headWasher, end: entry },
      { ...common, id: s.id + ":NUT_WASHER", label: "Member-side washer", kind: "WASHER", hardwareLocation: "UNDER_NUT", diameter: inches(h.washer_diameter), start: exit, end: nutInner },
    ];
  });
  const frames = geometry.members.map(m => ({ id: m.owner + ":FRAME", ownerId: m.owner, label: m.owner + " native member axes", kind: "MEMBER_LOCAL", origin: scale(m.end_reference, f), xAxis: m.material_longitudinal, yAxis: { x: m.material_longitudinal.z * m.material_depth.y, y: m.material_longitudinal.x * m.material_depth.z - m.material_longitudinal.z * m.material_depth.x, z: 0 }, zAxis: m.material_depth, valid: true }));
  const inclined = geometry.members[1];
  if (inclined === undefined) throw new Error("SSMC inclined member is missing.");
  const u = inclined.material_longitudinal, pAxis = { x: -u.z, y: 0, z: u.x };
  const appliedArrows: SceneArrow[] = current ? ([
    ["N", "FX", "LINEAR", u], ["V", "FZ", "LINEAR", pAxis], ["M", "MY", "ROTATIONAL", { x: 0, y: -1, z: 0 }],
  ] as const).flatMap(([key, component, kind, axis]) => {
    const q = p.input[key], value = Number(q.value);
    return value === 0 ? [] : [{ id: "SSMC:" + key, componentLabel: key, component, kind, origin: scale(inclined.end_reference, f), axis: scale(axis, Math.sign(value)), signedValue: value, unit: q.unit, sense: value < 0 ? "NEGATIVE" : "POSITIVE", isZero: false, referencePointId: "INCLINED_STRINGER:END", frameId: "INCLINED_STRINGER:FRAME", axialLoadingSense: key === "N" ? value < 0 ? "COMPRESSION" : "TENSION" : null }];
  }) : [];
  const bounds = calculatePresentationBounds(meshes.flatMap(m => m.points));
  return { snapshotVersion: "SSMC-2-RC1", unitSystem: "US_CUSTOMARY", lengthUnit: "in", boxes: [], meshes, cylinders, frames, materialAxes: [], markers: frames.map(frame => ({ id: frame.id + ":END", label: frame.label, kind: "MEMBER_END", position: frame.origin, connected: true, memberEnd: "END" })), positiveArrows: [], appliedArrows, connectionDemandArrows: [], perBoltDemandArrows: [], zones: [], connectionOrientation: null, boundsCenter: bounds.center, boundsRadius: bounds.radius, fitCenter: bounds.center, fitRadius: bounds.radius * 1.05 };
}
