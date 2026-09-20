import type { DCTN3BPreview, DCTNPreview, DCTNRational3 } from "../api/dctnContracts";
import type { MultiRowQuantity } from "../api/multirowContracts";
import { buildRegionEmbeddedMaterialAxisPresentation } from "./materialAxisPresentation";
import { calculatePresentationBounds, type SceneArrow, type SceneBox, type SceneCylinder, type SceneMaterialAxes, type SingleBoltSceneModel, type Vec3 } from "./sceneModel";

const add = (a: Vec3, b: Vec3): Vec3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
const scale = (a: Vec3, n: number): Vec3 => ({ x: a.x * n, y: a.y * n, z: a.z * n });
const rational = (v: DCTNRational3): Vec3 => ({ x: Number(v[0].numerator) / Number(v[0].denominator), y: Number(v[1].numerator) / Number(v[1].denominator), z: Number(v[2].numerator) / Number(v[2].denominator) });
const inches = (q: MultiRowQuantity): number => Number(q.value) / (q.unit === "mm" ? 25.4 : 1);

export function buildDCTNScene(p: { readonly input: Pick<DCTNPreview["input"], "fastener" | "members">; readonly geometry: DCTNPreview["geometry"] }): SingleBoltSceneModel {
  // Presentation only. Geometry, physical shaft identity, material axes and
  // signed axial authority all come from this SAME accepted backend snapshot.
  const f = p.geometry.length_unit === "mm" ? 1 / 25.4 : 1;
  const point = (v: DCTNRational3) => scale(rational(v), f);
  const boxes: SceneBox[] = [];
  const materialAxes: SceneMaterialAxes[] = [];
  const corners: Vec3[] = [];
  for (const member of p.geometry.members) {
    for (const element of member.placement.physical_elements) {
      const frame = element.global_frame;
      const basis = [frame.x_axis, frame.y_axis, frame.z_axis] as const;
      const origin = scale(frame.origin, f);
      for (const [index, extrusion] of element.extrusions.entries()) {
        const e = extrusion.extent, r = extrusion.rectangle;
        const center = add(origin, add(scale(basis[0], (e.x_start + e.x_end) * f / 2), add(scale(basis[1], (r.min_y + r.max_y) * f / 2), scale(basis[2], (r.min_z + r.max_z) * f / 2))));
        const size = { x: (e.x_end - e.x_start) * f, y: (r.max_y - r.min_y) * f, z: (r.max_z - r.min_z) * f };
        const id = member.physical_id + ":" + element.source_element.id + ":" + String(index);
        boxes.push({ id, label: id, ownerId: member.physical_id, ownerLabel: member.physical_id, ownerRole: member.physical_id.startsWith("CHORD") ? "COLUMN" : "BRACE", elementId: element.source_element.id, materialRegionId: element.source_element.material_region_id, center, size, basis, deferred: false, interference: false });
        for (const x of [-1, 1]) for (const y of [-1, 1]) for (const z of [-1, 1]) corners.push(add(center, add(scale(basis[0], x * size.x / 2), add(scale(basis[1], y * size.y / 2), scale(basis[2], z * size.z / 2)))));
        const orientation = element.source_material_region.orientation;
        const axes = { X: basis[0], Y: basis[1], Z: basis[2] };
        const source = { componentId: member.physical_id, elementId: element.source_element.id, materialRegionId: element.source_element.material_region_id, lengthwise: basis[0], crosswise: scale(axes[orientation.crosswise_axis], orientation.crosswise_sign), throughThickness: scale(axes[orientation.through_thickness_axis], orientation.through_thickness_sign) };
        materialAxes.push({ ...source, id: id + ":MATERIAL", componentLabel: member.physical_id, sectionFamily: member.profile.family, elementLabel: element.source_element.id, origin: center, presentation: buildRegionEmbeddedMaterialAxisPresentation(source, boxes, []) });
      }
    }
    // Native finite RHS corner regions remain visible occupied geometry, but
    // have no invented material/resistance region or targetable engineering role.
    for (const feature of member.placement.deferred_features) {
      if (!("rectangle" in feature.extrusion)) continue;
      const { extent: e, rectangle: r } = feature.extrusion;
      const frame = feature.global_frame;
      const basis = [frame.x_axis, frame.y_axis, frame.z_axis] as const;
      const center = add(scale(frame.origin, f), add(scale(basis[0], (e.x_start + e.x_end) * f / 2), add(scale(basis[1], (r.min_y + r.max_y) * f / 2), scale(basis[2], (r.min_z + r.max_z) * f / 2))));
      const size = { x: (e.x_end - e.x_start) * f, y: (r.max_y - r.min_y) * f, z: (r.max_z - r.min_z) * f };
      boxes.push({ id: member.physical_id + ":DEFERRED:" + feature.source_feature.id, label: "Native deferred corner — no local resistance authority", ownerId: member.physical_id, ownerLabel: member.physical_id, ownerRole: "BRACE", elementId: null, materialRegionId: null, center, size, basis, deferred: true, interference: false });
      for (const x of [-1, 1]) for (const y of [-1, 1]) for (const z of [-1, 1]) corners.push(add(center, add(scale(basis[0], x * size.x / 2), add(scale(basis[1], y * size.y / 2), scale(basis[2], z * size.z / 2)))));
    }
  }
  const h = p.input.fastener.hardware;
  const wt = inches(h.washer_thickness), hh = inches(h.head_height), nh = inches(h.nut_height), extension = inches(h.end_extension);
  const cylinders: SceneCylinder[] = p.geometry.shafts.flatMap(s => {
    const entry = point(s.start), exit = point(s.end);
    const delta = add(exit, scale(entry, -1));
    const direction = scale(delta, 1 / Math.hypot(delta.x, delta.y, delta.z));
    const headWasherOuter = add(entry, scale(direction, -wt));
    const headOuter = add(headWasherOuter, scale(direction, -hh));
    const nutInner = add(exit, scale(direction, wt));
    const nutOuter = add(nutInner, scale(direction, nh));
    const boltEnd = add(nutOuter, scale(direction, extension));
    const common = { ownerBoltId: s.bolt_id, penetratedLayerIds: s.layer_owners, interfaceId: s.member_id + ":" + s.side, rowId: "ROW_" + String(s.row), boltLineId: null, hardwareLocation: null };
    return [
      { ...common, id: s.bolt_id, label: s.bolt_id + " — one physical bolt", start: headOuter, end: boltEnd, diameter: inches(p.input.fastener.diameter), kind: "BOLT", hardwareConfiguration: "THROUGH_BOLT", exactHardware: { source: h.geometry_source, headStart: headOuter, headEnd: headWasherOuter, headAcrossFlats: inches(h.head_across_flats), nutStart: nutInner, nutEnd: nutOuter, nutAcrossFlats: inches(h.nut_across_flats) } },
      { ...common, id: s.bolt_id + ":HEAD_WASHER", label: "Exterior head washer", start: headWasherOuter, end: entry, diameter: inches(h.washer_diameter), kind: "WASHER", hardwareLocation: "UNDER_HEAD" },
      { ...common, id: s.bolt_id + ":NUT_WASHER", label: "Exterior nut washer", start: exit, end: nutInner, diameter: inches(h.washer_diameter), kind: "WASHER", hardwareLocation: "UNDER_NUT" },
    ];
  });
  const frames = p.geometry.members.map(m => ({ id: m.physical_id + ":FRAME", label: m.physical_id + " native u/v/w", kind: "MEMBER_LOCAL" as const, ownerId: m.physical_id, origin: point(m.start), xAxis: rational(m.u), yAxis: rational(m.v), zAxis: rational(m.w), valid: true }));
  const appliedArrows: SceneArrow[] = p.input.members.flatMap(m => {
    const frame = frames.find(item => item.ownerId === m.slot);
    if (frame === undefined) throw new Error("DCTN member frame is missing.");
    const value = Number(m.axial_force.value);
    if (value === 0) return [];
    return [{ id: m.slot + ":AXIAL_P", component: m.slot === "V" ? "FZ" : "FX", componentLabel: m.slot === "V" ? "Fz (global +Z)" : m.slot + " P (derived member axis in X-Z)", kind: "LINEAR", origin: frame.origin, axis: scale(frame.xAxis, Math.sign(value)), signedValue: value, unit: m.axial_force.unit, sense: value < 0 ? "NEGATIVE" : "POSITIVE", isZero: false, referencePointId: m.slot + ":START", frameId: m.slot === "V" ? "GLOBAL" : frame.id, axialLoadingSense: value < 0 ? "COMPRESSION" : "TENSION" }];
  });
  const bounds = calculatePresentationBounds(corners);
  return { snapshotVersion: "DCTN-2-RC1", unitSystem: "US_CUSTOMARY", lengthUnit: "in", boxes, meshes: [], cylinders, materialAxes, frames,
    markers: frames.map(frame => ({ id: frame.ownerId + ":START", label: frame.ownerId + " physical START", kind: "MEMBER_END", position: frame.origin, connected: true, memberEnd: "START" })),
    positiveArrows: [], appliedArrows, connectionDemandArrows: [], perBoltDemandArrows: [], zones: [], connectionOrientation: null, boundsCenter: bounds.center, boundsRadius: bounds.radius, fitCenter: bounds.center, fitRadius: bounds.radius * 1.05 };
}

export function buildDCTN3BScene(p: DCTN3BPreview): SingleBoltSceneModel {
  // Geometry/hardware reuse only. No manufactured legacy response or force sharing.
  const model = buildDCTNScene({ geometry: p.geometry, input: { fastener: p.input.fastener, members: [] } });
  const frames = model.frames.map(frame => ({ ...frame, label: frame.label.replace("u/v/w", "u/p/q") }));
  const appliedArrows: SceneArrow[] = p.demand.members.flatMap(m => {
    const frame = frames.find(f => f.ownerId === m.member_id);
    const input = p.input.members.find(i => i.slot === m.member_id);
    if (frame === undefined || input === undefined) throw new Error("DCTN-3B native action frame is missing.");
    return ([
      ["P", m.u, "FX"],
      ["Qp", m.p, "FY"],
      ["Qq", m.q, "FZ"],
    ] as const).flatMap(([key, axis, component]) => {
      const value = Number(input[key].value);
      if (value === 0) return [];
      return [{
        id: m.member_id + ":" + key, component, componentLabel: m.member_id + " " + key,
        kind: "LINEAR", origin: frame.origin, axis: scale(rational(axis), Math.sign(value)),
        signedValue: value, unit: input[key].unit, sense: value < 0 ? "NEGATIVE" : "POSITIVE",
        isZero: false, referencePointId: m.member_id + ":START", frameId: frame.id,
        axialLoadingSense: key === "P" ? value < 0 ? "COMPRESSION" : "TENSION" : null,
      }];
    });
  });
  return { ...model, snapshotVersion: "DCTN-3B-RC1", frames, appliedArrows };
}
