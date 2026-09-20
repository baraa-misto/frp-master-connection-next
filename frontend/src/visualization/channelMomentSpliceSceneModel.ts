import type { ChannelMomentSpliceVector, ChannelMomentSpliceVisualization } from "../api/channelMomentSpliceContracts";
import { buildRegionEmbeddedMaterialAxisPresentation } from "./materialAxisPresentation";
import { calculatePresentationBounds, type SceneArrow, type SceneBox, type SceneCylinder, type SceneMaterialAxes, type SingleBoltSceneModel, type Vec3 } from "./sceneModel";

const q = (value: { readonly value: string }): number => Number(value.value);
const point = (value: ChannelMomentSpliceVector): Vec3 => ({ x: q(value.l), y: q(value.t), z: q(value.v) });
const axis = (value: readonly [string, string, string]): Vec3 => ({ x: Number(value[0]), y: Number(value[2]), z: Number(value[1]) });

function boxes(value: ChannelMomentSpliceVisualization): readonly SceneBox[] {
  return value.boxes.map((box) => {
    const ownerId = box.component_id.startsWith("BEAM_A") ? "BEAM_A" : box.component_id.startsWith("BEAM_B") ? "BEAM_B" : box.component_id;
    return { id: box.component_id, label: box.role.replaceAll("_", " "), ownerId, ownerLabel: ownerId.replaceAll("_", " "), ownerRole: "OTHER" as const, elementId: box.component_id, materialRegionId: box.component_id, center: point(box.center_l_v_t), size: { x: q(box.size_l_v_t.l), y: q(box.size_l_v_t.t), z: q(box.size_l_v_t.v) }, basis: [{ x: 1, y: 0, z: 0 }, { x: 0, y: 1, z: 0 }, { x: 0, y: 0, z: 1 }], deferred: false, interference: false };
  });
}

function cylinders(value: ChannelMomentSpliceVisualization): readonly SceneCylinder[] {
  return value.bolts.flatMap((bolt) => {
    const flange = bolt.path_layers[1].includes("FLANGE");
    const common = { ownerBoltId: bolt.bolt_id, rowId: null, boltLineId: null, penetratedLayerIds: bolt.path_layers, interfaceId: bolt.group_id, hardwareLocation: null } as const;
    return [
      { ...common, id: `${bolt.bolt_id}:bolt`, label: `${bolt.bolt_id} full-through bolt`, start: point(bolt.stack_start_l_v_t), end: point(bolt.stack_end_l_v_t), diameter: q(flange ? value.flange_bolt_diameter : value.web_bolt_diameter), kind: "BOLT" as const, hardwareConfiguration: "THROUGH_BOLT" as const },
      { ...common, id: `${bolt.bolt_id}:hole`, label: `${bolt.bolt_id} complete hole path`, start: point(bolt.stack_start_l_v_t), end: point(bolt.stack_end_l_v_t), diameter: q(flange ? value.flange_hole_diameter : value.web_hole_diameter), kind: "HOLE" as const },
    ];
  });
}

function boxPoints(box: SceneBox): Vec3[] {
  const result: Vec3[] = [];
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1]) result.push({ x: box.center.x + sx * box.size.x / 2, y: box.center.y + sy * box.size.y / 2, z: box.center.z + sz * box.size.z / 2 });
  return result;
}

function arrow(id: string, component: SceneArrow["component"], raw: number, origin: Vec3, positive: Vec3, unit: string, kind: SceneArrow["kind"]): SceneArrow | null {
  if (raw === 0) return null;
  return { id, component, kind, origin, axis: raw < 0 ? { x: -positive.x, y: -positive.y, z: -positive.z } : positive, signedValue: raw, unit, sense: raw < 0 ? "NEGATIVE" : "POSITIVE", isZero: false, referencePointId: "CHANNEL_MOMENT_SPLICE_CENTROID", frameId: "CHANNEL_MOMENT_SPLICE_FRAME", axialLoadingSense: component === "FX" ? raw < 0 ? "COMPRESSION" : "TENSION" : null };
}

export function buildChannelMomentSpliceSceneModel(value: ChannelMomentSpliceVisualization): SingleBoltSceneModel {
  const sceneBoxes = boxes(value);
  const sceneCylinders = cylinders(value);
  const materialAxes: SceneMaterialAxes[] = value.material_regions.map((region) => {
    const box = sceneBoxes.find((candidate) => candidate.id === region.region_id);
    const source = { componentId: region.component_id, elementId: region.region_id, materialRegionId: region.region_id, lengthwise: axis(region.lw_axis), crosswise: axis(region.cw_axis), throughThickness: axis(region.tt_axis) };
    const presentation = buildRegionEmbeddedMaterialAxisPresentation(source, sceneBoxes, []);
    return { id: `channel-moment-splice:${region.region_id}`, componentId: region.component_id, componentLabel: box?.ownerLabel ?? region.component_id, sectionFamily: region.component_id.startsWith("BEAM") ? "CHANNEL" : "PLATE", elementId: region.region_id, elementLabel: region.region_id.replaceAll("_", " "), materialRegionId: region.region_id, origin: presentation?.origin ?? box?.center ?? { x: 0, y: 0, z: 0 }, presentation, lengthwise: source.lengthwise, crosswise: source.crosswise, throughThickness: source.throughThickness };
  });
  const origin = point(value.action_reference_l_v_t);
  const force = value.applied_force_l_v_t;
  const moment = value.applied_moment_l_v_t;
  const appliedArrows = [
    arrow("channel-moment-splice-FX", "FX", q(force.l), origin, { x: 1, y: 0, z: 0 }, force.l.unit, "LINEAR"),
    arrow("channel-moment-splice-FZ", "FZ", q(force.v), origin, { x: 0, y: 0, z: 1 }, force.v.unit, "LINEAR"),
    arrow("channel-moment-splice-MY", "MY", q(moment.t), origin, { x: 0, y: 1, z: 0 }, moment.t.unit, "ROTATIONAL"),
    arrow("channel-moment-splice-MX-generated", "MX", q(value.generated_centroidal_torsion), origin, { x: 1, y: 0, z: 0 }, value.generated_centroidal_torsion.unit, "ROTATIONAL"),
  ].filter((item): item is SceneArrow => item !== null);
  const bounds = calculatePresentationBounds([...sceneBoxes.flatMap(boxPoints), ...sceneCylinders.flatMap((item) => [item.start, item.end])]);
  return {
    snapshotVersion: "4.1B-PREVIEW-RC1",
    unitSystem: value.beam_end_planes_l[0].unit === "in" ? "US_CUSTOMARY" : "SI",
    lengthUnit: value.beam_end_planes_l[0].unit,
    boxes: sceneBoxes,
    meshes: [],
    cylinders: sceneCylinders,
    frames: [{ id: "CHANNEL_MOMENT_SPLICE_FRAME", label: "Channel moment-splice L_CH / T_CH / V_CH frame", kind: "JOINT_LOCAL", ownerId: null, origin, xAxis: { x: 1, y: 0, z: 0 }, yAxis: { x: 0, y: 1, z: 0 }, zAxis: { x: 0, y: 0, z: 1 }, valid: true }],
    markers: [
      { id: "CHANNEL_MOMENT_SPLICE_CENTROID", label: "Channel centroid action reference", kind: "REFERENCE_POINT", position: point(value.channel_centroid_l_v_t), connected: null, memberEnd: null },
      { id: "CHANNEL_MOMENT_SPLICE_SHEAR_CENTER", label: "Channel shear center", kind: "REFERENCE_POINT", position: point(value.channel_shear_center_l_v_t), connected: null, memberEnd: null },
    ],
    positiveArrows: [], appliedArrows, connectionDemandArrows: [], perBoltDemandArrows: [], materialAxes, zones: [], connectionOrientation: null,
    boundsCenter: bounds.center, boundsRadius: bounds.radius, fitCenter: bounds.center, fitRadius: bounds.radius * 1.08,
  };
}
