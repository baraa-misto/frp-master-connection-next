import type { WebSpliceVector, WebSpliceVisualization } from "../api/webSpliceContracts";
import { buildRegionEmbeddedMaterialAxisPresentation } from "./materialAxisPresentation";
import { calculatePresentationBounds, type SceneArrow, type SceneBox, type SceneCylinder, type SceneMaterialAxes, type SingleBoltSceneModel, type Vec3 } from "./sceneModel";

const q = (value: { readonly value: string }): number => Number(value.value);
const point = (value: WebSpliceVector): Vec3 => ({ x: q(value.l), y: q(value.t), z: q(value.v) });
const axis = (value: readonly [string, string, string]): Vec3 => ({ x: Number(value[0]), y: Number(value[2]), z: Number(value[1]) });

function boxes(value: WebSpliceVisualization): readonly SceneBox[] {
  return value.boxes.map((box) => {
    const ownerId = box.component_id.startsWith("BEAM_A") ? "BEAM_A" : box.component_id.startsWith("BEAM_B") ? "BEAM_B" : box.component_id;
    return ({
    id: box.component_id, label: box.role.replaceAll("_", " "), ownerId,
    ownerLabel: ownerId.replaceAll("_", " "), ownerRole: "BRACE" as const,
    elementId: box.component_id, materialRegionId: box.component_id, center: point(box.center_l_v_t),
    size: { x: q(box.size_l_v_t.l), y: q(box.size_l_v_t.t), z: q(box.size_l_v_t.v) },
    basis: [{ x: 1, y: 0, z: 0 }, { x: 0, y: 1, z: 0 }, { x: 0, y: 0, z: 1 }],
    deferred: false, interference: false,
  });
  });
}

function cylinders(value: WebSpliceVisualization): readonly SceneCylinder[] {
  return value.bolts.flatMap((bolt) => {
    const common = { ownerBoltId: bolt.bolt_id, rowId: null, boltLineId: null, penetratedLayerIds: bolt.path_layers, interfaceId: bolt.group_id, hardwareLocation: null } as const;
    return [
      { ...common, id: `${bolt.bolt_id}:bolt`, label: `${bolt.bolt_id} Plate/Web/Plate through bolt`, start: point(bolt.stack_start_l_v_t), end: point(bolt.stack_end_l_v_t), diameter: q(value.bolt_diameter), kind: "BOLT" as const, hardwareConfiguration: "THROUGH_BOLT" as const },
      { ...common, id: `${bolt.bolt_id}:hole`, label: `${bolt.bolt_id} complete hole path`, start: point(bolt.stack_start_l_v_t), end: point(bolt.stack_end_l_v_t), diameter: q(value.hole_diameter), kind: "HOLE" as const },
    ];
  });
}

function boxPoints(box: SceneBox): Vec3[] {
  const result: Vec3[] = [];
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1]) result.push({ x: box.center.x + sx * box.size.x / 2, y: box.center.y + sy * box.size.y / 2, z: box.center.z + sz * box.size.z / 2 });
  return result;
}

export function buildWebSpliceSceneModel(value: WebSpliceVisualization): SingleBoltSceneModel {
  const sceneBoxes = boxes(value);
  const sceneCylinders = cylinders(value);
  const materialAxes: SceneMaterialAxes[] = value.material_regions.map((region) => {
    const box = sceneBoxes.find((candidate) => candidate.id === region.region_id);
    const source = { componentId: region.component_id, elementId: region.region_id, materialRegionId: region.region_id, lengthwise: axis(region.lw_axis), crosswise: axis(region.cw_axis), throughThickness: axis(region.tt_axis) };
    const presentation = buildRegionEmbeddedMaterialAxisPresentation(source, sceneBoxes, []);
    return { id: `web-splice:${region.region_id}`, componentId: region.component_id, componentLabel: box?.ownerLabel ?? region.component_id, sectionFamily: region.component_id.startsWith("BEAM") ? "WIDE_FLANGE" : "PLATE", elementId: region.region_id, elementLabel: region.region_id.replaceAll("_", " "), materialRegionId: region.region_id, origin: presentation?.origin ?? box?.center ?? { x: 0, y: 0, z: 0 }, presentation, lengthwise: source.lengthwise, crosswise: source.crosswise, throughThickness: source.throughThickness };
  });
  const force = value.applied_force_l_v_t;
  const origin = point(value.action_reference_l_v_t);
  const arrow = (component: "FX" | "FY" | "FZ", raw: number, positive: Vec3): SceneArrow | null => {
    if (raw === 0) return null;
    const signedAxis = raw < 0
      ? { x: positive.x === 0 ? 0 : -positive.x, y: positive.y === 0 ? 0 : -positive.y, z: positive.z === 0 ? 0 : -positive.z }
      : positive;
    return { id: `web-splice-${component}`, component, kind: "LINEAR", origin, axis: signedAxis, signedValue: raw, unit: force.l.unit, sense: raw < 0 ? "NEGATIVE" : "POSITIVE", isZero: false, referencePointId: "WEB_SPLICE_JOINT", frameId: "WEB_SPLICE_FRAME", axialLoadingSense: component === "FX" ? raw < 0 ? "COMPRESSION" : "TENSION" : null };
  };
  const appliedArrows = [arrow("FX", q(force.l), { x: 1, y: 0, z: 0 }), arrow("FZ", q(force.v), { x: 0, y: 0, z: 1 }), arrow("FY", q(force.t), { x: 0, y: 1, z: 0 })].filter((item): item is SceneArrow => item !== null);
  const bounds = calculatePresentationBounds([...sceneBoxes.flatMap(boxPoints), ...sceneCylinders.flatMap((item) => [item.start, item.end])]);
  return { snapshotVersion: "0.1.0-draft", unitSystem: value.beam_end_planes_l[0].unit === "in" ? "US_CUSTOMARY" : "SI", lengthUnit: value.beam_end_planes_l[0].unit, boxes: sceneBoxes, meshes: [], cylinders: sceneCylinders, frames: [{ id: "WEB_SPLICE_FRAME", label: "Web-splice L_S / T_S / V_S frame", kind: "JOINT_LOCAL", ownerId: null, origin, xAxis: { x: 1, y: 0, z: 0 }, yAxis: { x: 0, y: 1, z: 0 }, zAxis: { x: 0, y: 0, z: 1 }, valid: true }], markers: [{ id: "WEB_SPLICE_JOINT", label: "Joint transfer reference", kind: "REFERENCE_POINT", position: origin, connected: null, memberEnd: null }], positiveArrows: [], appliedArrows, connectionDemandArrows: [], perBoltDemandArrows: [], materialAxes, zones: [], connectionOrientation: null, boundsCenter: bounds.center, boundsRadius: bounds.radius, fitCenter: bounds.center, fitRadius: bounds.radius * 1.08 };
}
