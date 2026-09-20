import type {
  ColumnBaseAnchorTrace,
  ColumnBaseVector,
  ColumnBaseVisualization,
} from "../api/columnBaseWebAngleContracts";
import type { ClipAngleQuantity } from "../api/clipAngleContracts";
import { buildRegionEmbeddedMaterialAxisPresentation } from "./materialAxisPresentation";
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
  if (!Number.isFinite(parsed)) throw new Error("Column-base visualization requires finite quantities.");
  return parsed;
}

function vector(value: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity]): Vec3 {
  return { x: quantity(value[0]), y: quantity(value[1]), z: quantity(value[2]) };
}

function basePoint(value: ColumnBaseVector): Vec3 {
  return { x: quantity(value.s), y: quantity(value.t), z: quantity(value.longitudinal) };
}

function direction(value: readonly [string, string, string]): Vec3 {
  return { x: Number(value[0]), y: Number(value[1]), z: Number(value[2]) };
}

function scaledDirection(value: Vec3, scale: 1 | -1): Vec3 {
  const component = (item: number) => item === 0 ? 0 : item * scale;
  return { x: component(value.x), y: component(value.y), z: component(value.z) };
}

function ownerLabel(ownerId: string, profileFamily: ColumnBaseVisualization["profile_family"]): string {
  if (ownerId === "column") return `FRP ${profileFamily === "RECTANGULAR_HOLLOW_SECTION" ? "RHS" : profileFamily === "SOLID_RECTANGULAR_SECTION" ? "Solid Rectangular" : profileFamily === "ANGLE" ? "Angle" : "W/I"} Column`;
  if (ownerId === "concrete-base") return "Concrete Base";
  if (ownerId === "positive-base-angle") return "Positive Base Angle";
  if (ownerId === "negative-base-angle") return "Negative Base Angle";
  return ownerId.replaceAll("-", " ");
}

function sceneBoxes(value: ColumnBaseVisualization): readonly SceneBox[] {
  return value.boxes.map((box) => ({
    id: box.id,
    label: box.role.replaceAll("_", " "),
    ownerId: box.owner_id,
    ownerLabel: ownerLabel(box.owner_id, value.profile_family),
    ownerRole: box.owner_id === "column" ? "COLUMN" : "OTHER",
    elementId: box.physical_element_id,
    materialRegionId: box.material_region_id,
    center: vector(box.center),
    size: { x: quantity(box.size_s), y: quantity(box.size_p), z: quantity(box.size_l) },
    basis: [direction(box.basis[0]), direction(box.basis[1]), direction(box.basis[2])],
    deferred: false,
    interference: false,
  }));
}

function webBoltCylinders(value: ColumnBaseVisualization): readonly SceneCylinder[] {
  return value.web_bolts.flatMap((bolt) => {
    const common = {
      ownerBoltId: bolt.bolt_id,
      rowId: bolt.row_id,
      boltLineId: bolt.bolt_line_id,
      penetratedLayerIds: bolt.layer_ids,
      interfaceId: "COLUMN_WEB_BASE_ANGLE_INTERFACE",
      hardwareLocation: null,
    } as const;
    return [
      { ...common, id: `${bolt.bolt_id}:bolt`, label: `${bolt.bolt_id} common web bolt`, start: vector(bolt.stack_start), end: vector(bolt.stack_end), diameter: quantity(value.web_bolt_diameter), kind: "BOLT" as const, hardwareConfiguration: "THROUGH_BOLT" as const },
      { ...common, id: `${bolt.bolt_id}:hole`, label: `${bolt.bolt_id} hole path`, start: vector(bolt.stack_start), end: vector(bolt.stack_end), diameter: quantity(value.web_hole_diameter), kind: "HOLE" as const },
    ];
  });
}

function anchorCylinders(value: ColumnBaseVisualization): readonly SceneCylinder[] {
  const diameter = quantity(value.external_anchor_geometry.nominal_diameter);
  const hole = quantity(value.external_anchor_geometry.hole_diameter);
  const washerDiameter = quantity(value.external_anchor_geometry.washer_outside_diameter);
  const washerThickness = quantity(value.external_anchor_geometry.washer_thickness);
  return value.anchors.flatMap((anchor: ColumnBaseAnchorTrace) => {
    const ownerBoltId = `${anchor.group_id}:${anchor.anchor_id}`;
    const common = {
      ownerBoltId, rowId: null, boltLineId: null, penetratedLayerIds: anchor.penetrated_layers,
      interfaceId: anchor.group_id, hardwareConfiguration: "EXTERIOR_NUT_WASHER_ANCHOR" as const,
    };
    return [
      { ...common, id: `${ownerBoltId}:anchor`, label: `${anchor.anchor_id} external anchor`, start: basePoint(anchor.shank_start_s_t_l), end: basePoint(anchor.shank_end_s_t_l), diameter, kind: "BOLT" as const, hardwareLocation: null },
      { ...common, id: `${ownerBoltId}:hole`, label: `${anchor.anchor_id} coordination hole`, start: basePoint(anchor.shank_start_s_t_l), end: basePoint(anchor.shank_end_s_t_l), diameter: hole, kind: "HOLE" as const, hardwareLocation: null },
      { ...common, id: `${ownerBoltId}:washer`, label: `${anchor.anchor_id} exterior washer`, start: { ...basePoint(anchor.exterior_washer_center_s_t_l), z: basePoint(anchor.exterior_washer_center_s_t_l).z - washerThickness / 2 }, end: { ...basePoint(anchor.exterior_washer_center_s_t_l), z: basePoint(anchor.exterior_washer_center_s_t_l).z + washerThickness / 2 }, diameter: washerDiameter, kind: "WASHER" as const, hardwareLocation: "UNDER_NUT" as const },
    ];
  });
}

function materialAxes(value: ColumnBaseVisualization, boxes: readonly SceneBox[]): readonly SceneMaterialAxes[] {
  return value.material_regions.map((region) => {
    const box = boxes.find((item) => item.elementId === region.physical_element_id);
    const axes = {
      componentId: box?.ownerId ?? "column-base",
      elementId: region.physical_element_id,
      materialRegionId: region.region_id,
      lengthwise: direction(region.lw),
      crosswise: direction(region.cw),
      throughThickness: direction(region.tt),
    };
    const presentation = buildRegionEmbeddedMaterialAxisPresentation(axes, boxes, []);
    return {
      id: `column-base:${region.region_id}`,
      componentId: axes.componentId,
      componentLabel: box?.ownerLabel ?? "FRP component",
      sectionFamily: region.physical_element_id.includes("ANGLE") ? "ANGLE" : "WIDE_FLANGE",
      elementId: axes.elementId,
      elementLabel: axes.elementId.replaceAll("_", " "),
      materialRegionId: axes.materialRegionId,
      origin: presentation?.origin ?? box?.center ?? { x: 0, y: 0, z: 0 },
      presentation,
      lengthwise: axes.lengthwise,
      crosswise: axes.crosswise,
      throughThickness: axes.throughThickness,
    };
  });
}

function appliedArrows(
  value: ColumnBaseVisualization,
  contractVersion: "3.5C-RC1" | "3.5C-R2-RC1" | "3.7A-RC1",
): readonly SceneArrow[] {
  const origin = basePoint(value.action_reference_s_t_l);
  const arrow = (
    id: string,
    component: "FX" | "FY" | "FZ",
    positiveAxis: Vec3,
    item: ClipAngleQuantity,
  ): SceneArrow | null => {
    const engineeringValue = quantity(item);
    if (engineeringValue === 0) return null;
    const negative = engineeringValue < 0;
    return {
      id, component, kind: "LINEAR", origin,
      axis: scaledDirection(positiveAxis, negative ? -1 : 1),
      signedValue: component === "FZ" && contractVersion === "3.5C-RC1"
        ? Math.abs(engineeringValue)
        : engineeringValue,
      unit: item.unit,
      sense: negative ? "NEGATIVE" : "POSITIVE",
      isZero: false, referencePointId: "COLUMN_ACTION_REFERENCE", frameId: "COLUMN_BASE_FRAME",
      axialLoadingSense: component === "FZ" ? negative ? "COMPRESSION" : "TENSION" : null,
    };
  };
  return [
    arrow("column-base-FX", "FX", { x: 1, y: 0, z: 0 }, value.applied_force_s_t_l.s),
    arrow("column-base-FY", "FY", { x: 0, y: 1, z: 0 }, value.applied_force_s_t_l.t),
    arrow("column-base-FZ", "FZ", { x: 0, y: 0, z: 1 }, value.applied_force_s_t_l.longitudinal),
  ].filter((item): item is SceneArrow => item !== null);
}

function boxPoints(box: SceneBox): Vec3[] {
  const result: Vec3[] = [];
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1]) result.push({
    x: box.center.x + sx * box.size.x / 2,
    y: box.center.y + sy * box.size.y / 2,
    z: box.center.z + sz * box.size.z / 2,
  });
  return result;
}

export function buildColumnBaseWebAngleSceneModel(
  value: ColumnBaseVisualization,
  contractVersion: "3.5C-RC1" | "3.5C-R2-RC1" | "3.7A-RC1" = "3.5C-RC1",
): SingleBoltSceneModel {
  const boxes = sceneBoxes(value);
  const cylinders = [...webBoltCylinders(value), ...anchorCylinders(value)];
  const bounds = calculatePresentationBounds([...boxes.flatMap(boxPoints), ...cylinders.flatMap((item) => [item.start, item.end])]);
  const connectionBoxes = boxes.filter((item) => item.ownerId !== "concrete-base");
  const fit = calculatePresentationBounds([...connectionBoxes.flatMap(boxPoints), ...cylinders.flatMap((item) => [item.start, item.end])]);
  const concrete = boxes.find((item) => item.ownerId === "concrete-base");
  const reference = basePoint(value.action_reference_s_t_l);
  return {
    snapshotVersion: value.schema_version,
    unitSystem: value.web_bolt_diameter.unit === "in" ? "US_CUSTOMARY" : "SI",
    lengthUnit: value.web_bolt_diameter.unit,
    boxes, meshes: [], cylinders,
    frames: [{ id: "COLUMN_BASE_FRAME", label: "Column-base S_C / T_C / L_C frame", kind: "INTERFACE_LOCAL", ownerId: "column", origin: { x: 0, y: 0, z: 0 }, xAxis: value.base_frame === undefined ? { x: 1, y: 0, z: 0 } : direction(value.base_frame.s_axis), yAxis: value.base_frame === undefined ? { x: 0, y: 1, z: 0 } : direction(value.base_frame.t_axis), zAxis: value.base_frame === undefined ? { x: 0, y: 0, z: 1 } : direction(value.base_frame.l_axis), valid: true }],
    markers: [{ id: "COLUMN_ACTION_REFERENCE", label: "Authoritative column action reference", kind: "REFERENCE_POINT", position: reference, connected: null, memberEnd: "START" }],
    positiveArrows: [], appliedArrows: appliedArrows(value, contractVersion), connectionDemandArrows: [], perBoltDemandArrows: [],
    materialAxes: materialAxes(value, boxes),
    zones: concrete === undefined ? [] : [{
      id: "CONCRETE_BASE_TOP", label: "Concrete base top interface", side: "TOP", participantId: "concrete-base", interfaceId: "EXTERNAL_BASE_ANCHOR_INTERFACE", patchId: "CONCRETE_BASE_TOP", normal: { x: 0, y: 0, z: 1 }, selectedContact: true,
      corners: [
        { x: concrete.center.x - concrete.size.x / 2, y: concrete.center.y - concrete.size.y / 2, z: 0 },
        { x: concrete.center.x + concrete.size.x / 2, y: concrete.center.y - concrete.size.y / 2, z: 0 },
        { x: concrete.center.x + concrete.size.x / 2, y: concrete.center.y + concrete.size.y / 2, z: 0 },
        { x: concrete.center.x - concrete.size.x / 2, y: concrete.center.y + concrete.size.y / 2, z: 0 },
      ],
    }],
    connectionOrientation: null,
    boundsCenter: bounds.center, boundsRadius: bounds.radius, fitCenter: fit.center, fitRadius: fit.radius * 1.08,
  };
}
