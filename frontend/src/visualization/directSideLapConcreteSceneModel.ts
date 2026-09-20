import type {
  DirectSideLapAnchorTrace,
  DirectSideLapVisualization,
  SideLapVector,
} from "../api/directSideLapConcreteContracts";
import type { ClipAngleQuantity } from "../api/clipAngleContracts";
import {
  buildRegionEmbeddedMaterialAxisPresentation,
  normalizeMaterialAxisPrimitiveId,
  resolveMaterialAxisOwnedIdentity,
} from "./materialAxisPresentation";
import {
  calculatePresentationBounds,
  type SceneArrow,
  type SceneBox,
  type SceneCylinder,
  type SceneMaterialAxes,
  type SingleBoltSceneModel,
  type Vec3,
} from "./sceneModel";

function quantity(value: ClipAngleQuantity): number {
  const parsed = Number(value.value);
  if (!Number.isFinite(parsed)) throw new Error("Direct side-lap scene quantities must be finite.");
  return parsed;
}

type SceneLengthUnit = "in" | "mm";

function sceneLengthUnit(value: ClipAngleQuantity): SceneLengthUnit {
  if (value.unit === "in" || value.unit === "mm") return value.unit;
  throw new Error("Direct side-lap scene length unit must be in or mm.");
}

function lengthQuantity(value: ClipAngleQuantity, unit: SceneLengthUnit): number {
  const parsed = quantity(value);
  if (value.unit === unit) return parsed;
  if (value.unit === "mm" && unit === "in") return parsed / 25.4;
  if (value.unit === "in" && unit === "mm") return parsed * 25.4;
  throw new Error("Direct side-lap scene length quantities must use in or mm.");
}

function point(
  value: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity],
  unit: SceneLengthUnit,
): Vec3 {
  return {
    x: lengthQuantity(value[0], unit),
    y: lengthQuantity(value[1], unit),
    z: lengthQuantity(value[2], unit),
  };
}

function direction(value: readonly [string, string, string]): Vec3 {
  return { x: Number(value[0]), y: Number(value[1]), z: Number(value[2]) };
}

function sideLapPoint(value: SideLapVector, unit: SceneLengthUnit): Vec3 {
  return {
    x: lengthQuantity(value.l, unit),
    y: -lengthQuantity(value.n, unit),
    z: lengthQuantity(value.s, unit),
  };
}

function boxes(value: DirectSideLapVisualization, unit: SceneLengthUnit): readonly SceneBox[] {
  return value.boxes.map((box) => {
    const concrete = box.owner_id === "direct-side-lap-concrete-wall";
    return {
      id: box.id,
      label: concrete ? "Finite concrete wall" : box.role.replaceAll("_", " "),
      ownerId: box.owner_id,
      ownerLabel: concrete
        ? "Concrete Wall"
        : value.connected_profile_family === "CHANNEL" ? "Connected FRP Channel" : "Connected FRP Angle",
      ownerRole: concrete ? "OTHER" : "BRACE",
      elementId: box.physical_element_id === null
        ? null
        : normalizeMaterialAxisPrimitiveId(box.owner_id, box.physical_element_id),
      materialRegionId: box.material_region_id === null
        ? null
        : normalizeMaterialAxisPrimitiveId(box.owner_id, box.material_region_id),
      center: point(box.center, unit),
      size: {
        x: lengthQuantity(box.size_s, unit),
        y: lengthQuantity(box.size_p, unit),
        z: lengthQuantity(box.size_l, unit),
      },
      basis: [direction(box.basis[0]), direction(box.basis[1]), direction(box.basis[2])],
      deferred: false,
      interference: false,
    };
  });
}

function anchors(
  value: DirectSideLapVisualization,
  unit: SceneLengthUnit,
): readonly SceneCylinder[] {
  const diameter = lengthQuantity(value.external_anchor_geometry.nominal_diameter, unit);
  const hole = lengthQuantity(value.external_anchor_geometry.hole_diameter, unit);
  const washerDiameter = lengthQuantity(
    value.external_anchor_geometry.washer_outside_diameter,
    unit,
  );
  const washerThickness = lengthQuantity(
    value.external_anchor_geometry.washer_thickness,
    unit,
  );
  return value.external_anchors.flatMap((anchor: DirectSideLapAnchorTrace) => {
    const ownerBoltId = `${anchor.group_id}:${anchor.anchor_id}`;
    const start = sideLapPoint(anchor.shank_start_lsn, unit);
    const end = sideLapPoint(anchor.shank_end_lsn, unit);
    const washerStart = { ...start, y: start.y - washerThickness };
    const common = {
      ownerBoltId, rowId: null, boltLineId: null,
      penetratedLayerIds: anchor.penetrated_layers, interfaceId: anchor.group_id,
    };
    return [
      { ...common, id: `${ownerBoltId}:anchor`, label: "External anchor — capacity designed elsewhere", start, end, diameter, kind: "BOLT" as const, hardwareLocation: null, hardwareConfiguration: "EXTERIOR_NUT_WASHER_ANCHOR" as const },
      { ...common, id: `${ownerBoltId}:hole`, label: `${anchor.anchor_id} coordination hole`, start, end, diameter: hole, kind: "HOLE" as const, hardwareLocation: null },
      { ...common, id: `${ownerBoltId}:exterior-washer`, label: `${anchor.anchor_id} exterior washer`, start: washerStart, end: start, diameter: washerDiameter, kind: "WASHER" as const, hardwareLocation: "UNDER_HEAD" as const },
    ];
  });
}

function axes(
  value: DirectSideLapVisualization,
  sceneBoxes: readonly SceneBox[],
  unit: SceneLengthUnit,
): readonly SceneMaterialAxes[] {
  const primitiveOwnerIds = [...new Set(sceneBoxes.map((box) => box.ownerId))];
  const connectedOwnerId = sceneBoxes.find(
    (box) => box.ownerId !== "direct-side-lap-concrete-wall",
  )?.ownerId ?? "clip-angle-connected-member";
  return value.material_regions.map((region): SceneMaterialAxes => {
    const elementIdentity = resolveMaterialAxisOwnedIdentity(
      connectedOwnerId,
      region.physical_element_id,
      primitiveOwnerIds,
    );
    const materialIdentity = resolveMaterialAxisOwnedIdentity(
      elementIdentity.ownerId,
      region.material_region_id,
      primitiveOwnerIds,
    );
    const axisSet = {
      componentId: elementIdentity.ownerId,
      elementId: elementIdentity.localId,
      materialRegionId: materialIdentity.localId,
      lengthwise: direction(region.lw),
      crosswise: direction(region.cw),
      throughThickness: direction(region.tt),
    };
    const presentation = buildRegionEmbeddedMaterialAxisPresentation(axisSet, sceneBoxes, []);
    return {
      id: region.id,
      componentId: axisSet.componentId,
      componentLabel: value.connected_profile_family === "CHANNEL" ? "Connected FRP Channel" : "Connected FRP Angle",
      sectionFamily: value.connected_profile_family,
      elementId: axisSet.elementId,
      elementLabel: axisSet.elementId.replaceAll("_", " "),
      materialRegionId: axisSet.materialRegionId,
      origin: point(region.origin, unit),
      presentation,
      lengthwise: axisSet.lengthwise,
      crosswise: axisSet.crosswise,
      throughThickness: axisSet.throughThickness,
    };
  });
}

function forceArrow(id: string, component: "FX" | "FY" | "FZ", origin: Vec3, axis: Vec3, value: ClipAngleQuantity): SceneArrow {
  const signedValue = quantity(value);
  const signedAxis = signedValue < 0
    ? {
        x: axis.x === 0 ? 0 : -axis.x,
        y: axis.y === 0 ? 0 : -axis.y,
        z: axis.z === 0 ? 0 : -axis.z,
      }
    : axis;
  return {
    id, component, kind: "LINEAR", origin, axis: signedAxis, signedValue, unit: value.unit,
    sense: signedValue < 0 ? "NEGATIVE" : signedValue > 0 ? "POSITIVE" : "ZERO",
    isZero: signedValue === 0, referencePointId: "SIDE_LAP_MEMBER_ACTION_REFERENCE",
    frameId: "DIRECT_SIDE_LAP_FRAME", axialLoadingSense: component === "FX"
      ? signedValue > 0 ? "TENSION" : signedValue < 0 ? "COMPRESSION" : null
      : null,
  };
}

function boxPoints(box: SceneBox): Vec3[] {
  const halves = [
    { x: box.basis[0].x * box.size.x / 2, y: box.basis[0].y * box.size.x / 2, z: box.basis[0].z * box.size.x / 2 },
    { x: box.basis[1].x * box.size.y / 2, y: box.basis[1].y * box.size.y / 2, z: box.basis[1].z * box.size.y / 2 },
    { x: box.basis[2].x * box.size.z / 2, y: box.basis[2].y * box.size.z / 2, z: box.basis[2].z * box.size.z / 2 },
  ] as const;
  const result: Vec3[] = [];
  for (const a of [-1, 1]) for (const b of [-1, 1]) for (const c of [-1, 1]) result.push({
    x: box.center.x + a * halves[0].x + b * halves[1].x + c * halves[2].x,
    y: box.center.y + a * halves[0].y + b * halves[1].y + c * halves[2].y,
    z: box.center.z + a * halves[0].z + b * halves[1].z + c * halves[2].z,
  });
  return result;
}

export function buildDirectSideLapConcreteSceneModel(value: DirectSideLapVisualization): SingleBoltSceneModel {
  const lengthUnit = sceneLengthUnit(value.external_anchor_geometry.nominal_diameter);
  const sceneBoxes = boxes(value, lengthUnit);
  const cylinders = anchors(value, lengthUnit);
  const action = sideLapPoint(value.action_reference_lsn, lengthUnit);
  const group = sideLapPoint(value.anchor_group_reference_lsn, lengthUnit);
  const wall = sceneBoxes.find((item) => item.ownerId === "direct-side-lap-concrete-wall");
  const allPoints = [...sceneBoxes.flatMap(boxPoints), ...cylinders.flatMap((item) => [item.start, item.end])];
  const bounds = calculatePresentationBounds(allPoints);
  const fitPoints = [
    ...sceneBoxes.filter((item) => item.ownerId !== "direct-side-lap-concrete-wall").flatMap(boxPoints),
    ...cylinders.flatMap((item) => [item.start, item.end]),
  ];
  const fit = calculatePresentationBounds(fitPoints);
  return {
    snapshotVersion: value.schema_version,
    unitSystem: value.external_anchor_geometry.nominal_diameter.unit === "in" ? "US_CUSTOMARY" : "SI",
    lengthUnit,
    boxes: sceneBoxes, meshes: [], cylinders,
    frames: [{ id: "DIRECT_SIDE_LAP_FRAME", label: "Side-lap L / S / N frame", kind: "INTERFACE_LOCAL", ownerId: "direct-side-lap-concrete-wall", origin: { x: 0, y: 0, z: 0 }, xAxis: { x: 1, y: 0, z: 0 }, yAxis: { x: 0, y: 0, z: 1 }, zAxis: { x: 0, y: -1, z: 0 }, valid: true }],
    markers: [
      { id: "SIDE_LAP_MEMBER_ACTION_REFERENCE", label: "Member action reference at wall free end", kind: "REFERENCE_POINT", position: action, connected: null, memberEnd: "START" },
      { id: "DIRECT_SIDE_LAP_GROUP_REFERENCE", label: "Direct anchor-group centroid", kind: "REFERENCE_POINT", position: group, connected: null, memberEnd: null },
      { id: "WALL_FREE_END", label: "Finite wall free-end plane", kind: "REFERENCE_POINT", position: { x: 0, y: 0, z: 0 }, connected: null, memberEnd: null },
    ],
    positiveArrows: [],
    appliedArrows: [
      forceArrow("side-lap-axial", "FX", action, { x: 1, y: 0, z: 0 }, value.user_force_lsn.l),
      forceArrow("side-lap-major", "FZ", action, { x: 0, y: 0, z: 1 }, value.user_force_lsn.s),
      forceArrow("side-lap-minor", "FY", action, { x: 0, y: -1, z: 0 }, value.user_force_lsn.n),
    ].filter((arrow) => !arrow.isZero),
    connectionDemandArrows: [], perBoltDemandArrows: [], materialAxes: axes(value, sceneBoxes, lengthUnit),
    zones: wall === undefined ? [] : [{
      id: "DIRECT_SIDE_LAP_CONTACT", label: "Selected finite wall/contact face", side: "EXTERIOR_FACE",
      participantId: "direct-side-lap-concrete-wall", interfaceId: "DIRECT_SIDE_LAP_WALL_ANCHOR_GROUP",
      patchId: value.selected_wall_surface_id, normal: { x: 0, y: -1, z: 0 }, selectedContact: true,
      corners: [
        { x: -wall.size.x, y: 0, z: -wall.size.z / 2 }, { x: 0, y: 0, z: -wall.size.z / 2 },
        { x: 0, y: 0, z: wall.size.z / 2 }, { x: -wall.size.x, y: 0, z: wall.size.z / 2 },
      ],
    }],
    connectionOrientation: null,
    boundsCenter: bounds.center, boundsRadius: bounds.radius,
    fitCenter: fit.center, fitRadius: fit.radius * 1.08,
  };
}
