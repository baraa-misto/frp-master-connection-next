import type { BeamConcretePairedAngleVisualization, ExternalAnchorTrace } from "../api/beamConcretePairedAngleContracts";
import type { ClipAngleQuantity } from "../api/clipAngleContracts";
import type { PairedProfileFamily } from "../api/pairedClipAngleContracts";
import { buildRegionEmbeddedMaterialAxisPresentation } from "./materialAxisPresentation";
import {
  calculatePresentationBounds,
  type SceneArrow,
  type SceneBox,
  type SceneCylinder,
  type SceneMaterialAxes,
  type SceneTriangleMesh,
  type SingleBoltSceneModel,
  type Vec3,
} from "./sceneModel";

function quantity(value: ClipAngleQuantity): number {
  const parsed = Number(value.value);
  if (!Number.isFinite(parsed)) throw new Error("Beam-to-concrete visualization requires finite quantities.");
  return parsed;
}

function vector(value: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity]): Vec3 {
  return { x: quantity(value[0]), y: quantity(value[1]), z: quantity(value[2]) };
}

function direction(value: readonly [string, string, string]): Vec3 {
  return { x: Number(value[0]), y: Number(value[1]), z: Number(value[2]) };
}

function wallPoint(value: { readonly h: ClipAngleQuantity; readonly v: ClipAngleQuantity; readonly n: ClipAngleQuantity }): Vec3 {
  return { x: quantity(value.h), y: -quantity(value.n), z: quantity(value.v) };
}

function localId(value: string): string;
function localId(value: null): null;
function localId(value: string | null): string | null;
function localId(value: string | null): string | null {
  return value === null ? null : value.slice(value.lastIndexOf(":") + 1);
}

const PROFILE_LABELS: Readonly<Record<PairedProfileFamily, string>> = {
  FLAT_PLATE: "Connected FRP Flat Plate",
  ANGLE: "Connected FRP Angle",
  CHANNEL: "Connected FRP Channel",
  WIDE_FLANGE_I: "Connected FRP W/I Member",
  RECTANGULAR_HOLLOW_SECTION: "Connected FRP Rectangular Tube",
  SOLID_RECTANGULAR_SECTION: "Connected FRP Solid Rectangular Member",
};

function renderableBoxBasis(
  basis: readonly [readonly [string, string, string], readonly [string, string, string], readonly [string, string, string]],
): readonly [Vec3, Vec3, Vec3] {
  const converted = [direction(basis[0]), direction(basis[1]), direction(basis[2])] as const;
  const [first, second, third] = converted;
  const determinant = first.x * (second.y * third.z - second.z * third.y)
    - first.y * (second.x * third.z - second.z * third.x)
    + first.z * (second.x * third.y - second.y * third.x);
  return determinant < 0
    ? [first, second, { x: -third.x, y: -third.y, z: -third.z }]
    : converted;
}

function sceneBoxes(value: BeamConcretePairedAngleVisualization, profileFamily: PairedProfileFamily): readonly SceneBox[] {
  return value.boxes.map((box) => {
    const connector = box.owner_id === "POSITIVE_CLIP_ANGLE" || box.owner_id === "NEGATIVE_CLIP_ANGLE";
    const beam = box.owner_id === "clip-angle-connected-member";
    const elementId = connector ? box.role : localId(box.physical_element_id);
    const materialRegionId = connector
      ? box.role === "CONNECTED_MEMBER_LEG" ? "CLIP_ANGLE_CONNECTED_MEMBER_LEG_REGION" : "CLIP_ANGLE_SUPPORT_LEG_REGION"
      : localId(box.material_region_id);
    return {
      id: box.id,
      label: box.role.replaceAll("_", " "),
      ownerId: box.owner_id,
      ownerLabel: box.owner_id === "POSITIVE_CLIP_ANGLE" ? "Positive FRP Clip Angle" : box.owner_id === "NEGATIVE_CLIP_ANGLE" ? "Negative FRP Clip Angle" : beam ? PROFILE_LABELS[profileFamily] : "Concrete Wall",
      ownerRole: beam ? "BRACE" : "OTHER",
      elementId,
      materialRegionId,
      center: vector(box.center),
      size: { x: quantity(box.size_s), y: quantity(box.size_p), z: quantity(box.size_l) },
      basis: renderableBoxBasis(box.basis),
      deferred: false,
      interference: false,
    };
  });
}

function sceneMeshes(value: BeamConcretePairedAngleVisualization, profileFamily: PairedProfileFamily): readonly SceneTriangleMesh[] {
  return value.meshes.map((mesh) => ({
    id: mesh.id,
    label: mesh.role.replaceAll("_", " "),
    ownerId: mesh.owner_id,
    ownerLabel: PROFILE_LABELS[profileFamily],
    ownerRole: "BRACE",
    elementId: localId(mesh.physical_element_id),
    materialRegionId: localId(mesh.material_region_id),
    points: mesh.points.map(vector),
  }));
}

function commonBolts(value: BeamConcretePairedAngleVisualization): readonly SceneCylinder[] {
  return value.common_beam_bolts.flatMap((bolt) => {
    const ownerBoltId = `COMMON_BEAM_GROUP:${bolt.bolt_id}`;
    const common = {
      start: vector(bolt.stack_start), end: vector(bolt.stack_end), ownerBoltId,
      rowId: bolt.row_id, boltLineId: bolt.bolt_line_id, penetratedLayerIds: bolt.layer_ids,
      interfaceId: "COMMON_BEAM_THROUGH_BOLT_GROUP", hardwareLocation: null,
      hardwareConfiguration: "THROUGH_BOLT" as const,
    };
    return [
      { ...common, id: `${ownerBoltId}:bolt`, label: `${bolt.bolt_id} common fastener`, diameter: quantity(value.common_bolt_diameter), kind: "BOLT" as const },
      { ...common, id: `${ownerBoltId}:hole`, label: `${bolt.bolt_id} common hole path`, diameter: quantity(value.common_hole_diameter), kind: "HOLE" as const },
    ];
  });
}

function externalAnchorCylinders(value: BeamConcretePairedAngleVisualization): readonly SceneCylinder[] {
  const diameter = quantity(value.external_anchor_geometry.nominal_diameter);
  const hole = quantity(value.external_anchor_geometry.hole_diameter);
  const washerDiameter = quantity(value.external_anchor_geometry.washer_outside_diameter);
  const washerThickness = quantity(value.external_anchor_geometry.washer_thickness);
  return value.external_anchors.flatMap((anchor: ExternalAnchorTrace) => {
    const angleOwnerId = anchor.group_id === "POSITIVE_WALL_ANCHOR_GROUP" ? "POSITIVE_CLIP_ANGLE" : "NEGATIVE_CLIP_ANGLE";
    const ownerBoltId = `${angleOwnerId}:${anchor.group_id}:${anchor.anchor_id}`;
    const start = wallPoint(anchor.shank_start_hvn);
    const end = wallPoint(anchor.shank_end_hvn);
    const washerStart = { ...start, y: start.y - washerThickness };
    const common = { ownerBoltId, rowId: null, boltLineId: null, penetratedLayerIds: ["FRP_CLIP_ANGLE_WALL_LEG", "EXTERNAL_CONCRETE_ANCHOR_COORDINATION"], interfaceId: anchor.group_id };
    return [
      { ...common, id: `${ownerBoltId}:anchor`, label: "External anchor — capacity designed elsewhere", start, end, diameter, kind: "BOLT" as const, hardwareLocation: null, hardwareConfiguration: "EXTERIOR_NUT_WASHER_ANCHOR" as const },
      { ...common, id: `${ownerBoltId}:hole`, label: `${anchor.anchor_id} coordination hole`, start, end, diameter: hole, kind: "HOLE" as const, hardwareLocation: null },
      { ...common, id: `${ownerBoltId}:exterior-washer`, label: `${anchor.anchor_id} exterior washer`, start: washerStart, end: start, diameter: washerDiameter, kind: "WASHER" as const, hardwareLocation: "UNDER_HEAD" as const },
    ];
  });
}

function materialAxes(value: BeamConcretePairedAngleVisualization, boxes: readonly SceneBox[], meshes: readonly SceneTriangleMesh[], profileFamily: PairedProfileFamily): readonly SceneMaterialAxes[] {
  const connector = value.material_regions.map((region): SceneMaterialAxes => {
    const componentId = region.physical_element_id.startsWith("POSITIVE_") ? "POSITIVE_CLIP_ANGLE" : "NEGATIVE_CLIP_ANGLE";
    const elementId = region.physical_element_id.slice(region.physical_element_id.lastIndexOf(":") + 1);
    const materialRegionId = region.region_id.slice(region.region_id.lastIndexOf(":") + 1);
    const axes = { componentId, elementId, materialRegionId, lengthwise: direction(region.lw), crosswise: direction(region.cw), throughThickness: direction(region.tt) };
    const presentation = buildRegionEmbeddedMaterialAxisPresentation(axes, boxes, meshes);
    return { id: `beam-concrete:${region.region_id}`, componentId, componentLabel: componentId === "POSITIVE_CLIP_ANGLE" ? "Positive FRP Clip Angle" : "Negative FRP Clip Angle", sectionFamily: "ANGLE", elementId, elementLabel: elementId.replaceAll("_", " "), materialRegionId, origin: presentation?.origin ?? { x: 0, y: 0, z: 0 }, presentation, lengthwise: axes.lengthwise, crosswise: axes.crosswise, throughThickness: axes.throughThickness };
  });
  const beam = value.beam_material_regions.map((region): SceneMaterialAxes => {
    const axes = { componentId: "clip-angle-connected-member", elementId: localId(region.physical_element_id), materialRegionId: localId(region.material_region_id), lengthwise: direction(region.lw), crosswise: direction(region.cw), throughThickness: direction(region.tt) };
    const presentation = buildRegionEmbeddedMaterialAxisPresentation(axes, boxes, meshes);
    return { id: region.id, componentId: axes.componentId, componentLabel: PROFILE_LABELS[profileFamily], sectionFamily: profileFamily, elementId: axes.elementId, elementLabel: axes.elementId.replaceAll("_", " "), materialRegionId: axes.materialRegionId, origin: vector(region.origin), presentation, lengthwise: axes.lengthwise, crosswise: axes.crosswise, throughThickness: axes.throughThickness };
  });
  return [...connector, ...beam];
}

function boxPoints(box: SceneBox): Vec3[] {
  const halfAxes = [
    { x: box.basis[0].x * box.size.x / 2, y: box.basis[0].y * box.size.x / 2, z: box.basis[0].z * box.size.x / 2 },
    { x: box.basis[1].x * box.size.y / 2, y: box.basis[1].y * box.size.y / 2, z: box.basis[1].z * box.size.y / 2 },
    { x: box.basis[2].x * box.size.z / 2, y: box.basis[2].y * box.size.z / 2, z: box.basis[2].z * box.size.z / 2 },
  ] as const;
  const result: Vec3[] = [];
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1]) result.push({
    x: box.center.x + sx * halfAxes[0].x + sy * halfAxes[1].x + sz * halfAxes[2].x,
    y: box.center.y + sx * halfAxes[0].y + sy * halfAxes[1].y + sz * halfAxes[2].y,
    z: box.center.z + sx * halfAxes[0].z + sy * halfAxes[1].z + sz * halfAxes[2].z,
  });
  return result;
}

function reactionArrow(value: BeamConcretePairedAngleVisualization): SceneArrow {
  const signedValue = quantity(value.reaction_shear);
  return { id: "beam-concrete-reaction-shear", component: "FZ", kind: "LINEAR", origin: wallPoint(value.beam_reference_hvn), axis: { x: 0, y: 0, z: 1 }, signedValue, unit: value.reaction_shear.unit, sense: signedValue < 0 ? "NEGATIVE" : signedValue > 0 ? "POSITIVE" : "ZERO", isZero: signedValue === 0, referencePointId: "BEAM_GROUP_REFERENCE", frameId: "CONCRETE_WALL_FRAME", axialLoadingSense: null };
}

function wallForceArrow(
  id: string,
  component: "FX" | "FY" | "FZ",
  origin: Vec3,
  axis: Vec3,
  quantityValue: ClipAngleQuantity,
): SceneArrow {
  const signedValue = quantity(quantityValue);
  return {
    id,
    component,
    kind: "LINEAR",
    origin,
    axis,
    signedValue,
    unit: quantityValue.unit,
    sense: signedValue < 0 ? "NEGATIVE" : signedValue > 0 ? "POSITIVE" : "ZERO",
    isZero: signedValue === 0,
    referencePointId: "BEAM_GROUP_REFERENCE",
    frameId: "CONCRETE_WALL_FRAME",
    axialLoadingSense: component === "FY"
      ? signedValue > 0 ? "TENSION" : signedValue < 0 ? "COMPRESSION" : null
      : null,
  };
}

function appliedForceArrows(value: BeamConcretePairedAngleVisualization): readonly SceneArrow[] {
  const origin = wallPoint(value.beam_reference_hvn);
  if (value.user_force_hvn === undefined) return [reactionArrow(value)];
  return [
    wallForceArrow("beam-concrete-minor-shear", "FX", origin, { x: 1, y: 0, z: 0 }, value.user_force_hvn.h),
    wallForceArrow("beam-concrete-major-shear", "FZ", origin, { x: 0, y: 0, z: 1 }, value.user_force_hvn.v),
    wallForceArrow("beam-concrete-axial-force", "FY", origin, { x: 0, y: -1, z: 0 }, value.user_force_hvn.n),
  ];
}

export function buildBeamConcretePairedAngleSceneModel(value: BeamConcretePairedAngleVisualization, profileFamily: PairedProfileFamily = "WIDE_FLANGE_I"): SingleBoltSceneModel {
  const boxes = sceneBoxes(value, profileFamily);
  const meshes = sceneMeshes(value, profileFamily);
  const cylinders = [...commonBolts(value), ...externalAnchorCylinders(value)];
  const wall = boxes.find((item) => item.ownerId === "concrete-wall");
  const points = [...boxes.flatMap(boxPoints), ...meshes.flatMap((item) => item.points), ...cylinders.flatMap((item) => [item.start, item.end])];
  const bounds = calculatePresentationBounds(points);
  const fitPoints = [
    ...boxes.filter((item) => item.ownerId !== "concrete-wall").flatMap(boxPoints),
    ...meshes.flatMap((item) => item.points),
    ...cylinders.flatMap((item) => [item.start, item.end]),
  ];
  const fitBounds = calculatePresentationBounds(fitPoints);
  const beamReference = wallPoint(value.beam_reference_hvn);
  const wallReference = wallPoint(value.wall_reference_hvn);
  return {
    snapshotVersion: value.schema_version,
    unitSystem: value.common_bolt_diameter.unit === "in" ? "US_CUSTOMARY" : "SI",
    lengthUnit: value.common_bolt_diameter.unit,
    boxes, meshes, cylinders,
    frames: [{ id: "CONCRETE_WALL_FRAME", label: "Concrete wall H_W / V_W / N_W frame", kind: "INTERFACE_LOCAL", ownerId: "concrete-wall", origin: wallReference, xAxis: { x: 1, y: 0, z: 0 }, yAxis: { x: 0, y: 0, z: 1 }, zAxis: { x: 0, y: -1, z: 0 }, valid: true }],
    markers: [
      { id: "BEAM_GROUP_REFERENCE", label: "Beam common-group reference", kind: "REFERENCE_POINT", position: beamReference, connected: null, memberEnd: null },
      { id: "WALL_REFERENCE", label: "Wall handoff reference", kind: "REFERENCE_POINT", position: wallReference, connected: null, memberEnd: null },
    ],
    positiveArrows: [], appliedArrows: appliedForceArrows(value), connectionDemandArrows: [], perBoltDemandArrows: [],
    materialAxes: materialAxes(value, boxes, meshes, profileFamily),
    zones: wall === undefined ? [] : [{ id: "CONCRETE_WALL_EXTERIOR_FACE", label: "Selected concrete wall exterior face", side: "EXTERIOR_FACE", participantId: "concrete-wall", interfaceId: "WALL_ANCHOR_INTERFACE", patchId: value.selected_wall_surface_id, normal: { x: 0, y: -1, z: 0 }, selectedContact: true, corners: [{ x: wall.center.x - wall.size.x / 2, y: wall.center.y - wall.size.y / 2, z: wall.center.z - wall.size.z / 2 }, { x: wall.center.x + wall.size.x / 2, y: wall.center.y - wall.size.y / 2, z: wall.center.z - wall.size.z / 2 }, { x: wall.center.x + wall.size.x / 2, y: wall.center.y - wall.size.y / 2, z: wall.center.z + wall.size.z / 2 }, { x: wall.center.x - wall.size.x / 2, y: wall.center.y - wall.size.y / 2, z: wall.center.z + wall.size.z / 2 }] }],
    connectionOrientation: null,
    boundsCenter: bounds.center, boundsRadius: bounds.radius, fitCenter: fitBounds.center, fitRadius: fitBounds.radius * 1.08,
  };
}
