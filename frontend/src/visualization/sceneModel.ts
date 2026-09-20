import type {
  ActionDirectionSnapshot,
  DirectionSnapshot,
  PointSnapshot,
  SnapshotParameter,
  VisualizationSnapshot,
} from "../api/contracts";
import type { MultiRowVisualization } from "../api/multirowContracts";
import type { FullThroughBoltTrace, TeeVisualization } from "../api/teeContracts";
import {
  buildRegionEmbeddedMaterialAxisPresentation,
  type RegionEmbeddedMaterialAxisPresentation,
} from "./materialAxisPresentation";

export type SceneViewId = "3D" | "Front" | "Top" | "Side 1" | "Side 2";

export interface Vec3 {
  readonly x: number;
  readonly y: number;
  readonly z: number;
}

export interface SceneViewDefinition {
  readonly id: SceneViewId;
  readonly cameraDirection: Vec3;
  readonly up: Vec3;
  readonly orthographic: boolean;
  readonly description: string;
}

export const SCENE_VIEWS: Readonly<Record<SceneViewId, SceneViewDefinition>> = {
  "3D": {
    id: "3D",
    cameraDirection: { x: 1, y: -1, z: 0.8 },
    up: { x: 0, y: 0, z: 1 },
    orthographic: false,
    description: "Perspective from global +X, -Y, +Z toward the model.",
  },
  Front: {
    id: "Front",
    cameraDirection: { x: 0, y: -1, z: 0 },
    up: { x: 0, y: 0, z: 1 },
    orthographic: true,
    description: "Orthographic view along global -Y with global +Z up.",
  },
  Top: {
    id: "Top",
    cameraDirection: { x: 0, y: 0, z: 1 },
    up: { x: 0, y: 1, z: 0 },
    orthographic: true,
    description: "Orthographic view along global +Z with global +Y up.",
  },
  "Side 1": {
    id: "Side 1",
    cameraDirection: { x: 1, y: 0, z: 0 },
    up: { x: 0, y: 0, z: 1 },
    orthographic: true,
    description: "Orthographic Side 1 view along global +X with global +Z up.",
  },
  "Side 2": {
    id: "Side 2",
    cameraDirection: { x: -1, y: 0, z: 0 },
    up: { x: 0, y: 0, z: 1 },
    orthographic: true,
    description: "Opposing orthographic Side 2 view along global -X with global +Z up.",
  },
};

export interface SceneBox {
  readonly id: string;
  readonly label: string;
  readonly ownerId: string;
  readonly ownerLabel: string;
  readonly ownerRole: "BRACE" | "COLUMN" | "OTHER";
  readonly elementId: string | null;
  readonly materialRegionId: string | null;
  readonly center: Vec3;
  readonly size: Vec3;
  readonly basis: readonly [Vec3, Vec3, Vec3];
  readonly deferred: boolean;
  readonly interference: boolean;
}

export interface SceneTriangleMesh {
  readonly id: string;
  readonly label: string;
  readonly ownerId: string;
  readonly ownerLabel: string;
  readonly ownerRole: "BRACE" | "COLUMN" | "OTHER";
  readonly elementId: string | null;
  readonly materialRegionId: string | null;
  readonly points: readonly Vec3[];
}

export interface SceneCylinder {
  readonly id: string;
  readonly label: string;
  readonly start: Vec3;
  readonly end: Vec3;
  readonly diameter: number;
  readonly kind: "BOLT" | "HOLE" | "WASHER";
  readonly hardwareLocation: "UNDER_HEAD" | "UNDER_NUT" | null;
  readonly ownerBoltId: string;
  readonly rowId: string | null;
  readonly boltLineId: string | null;
  readonly penetratedLayerIds: readonly string[];
  readonly interfaceId: string | null;
  readonly hardwareConfiguration?: "THROUGH_BOLT" | "EXTERIOR_NUT_WASHER_ANCHOR";
  /** Optional exact backend hardware, never inferred from diameter or strength. */
  readonly exactHardware?: {
    readonly source: string;
    readonly headStart: Vec3; readonly headEnd: Vec3; readonly headAcrossFlats: number;
    readonly nutStart: Vec3; readonly nutEnd: Vec3; readonly nutAcrossFlats: number;
  };
}

export interface SceneFrame {
  readonly id: string;
  readonly label: string;
  readonly kind: string;
  readonly ownerId: string | null;
  readonly origin: Vec3;
  readonly xAxis: Vec3;
  readonly yAxis: Vec3;
  readonly zAxis: Vec3;
  readonly valid: boolean;
}

export interface SceneMarker {
  readonly id: string;
  readonly label: string;
  readonly kind: string;
  readonly position: Vec3;
  readonly connected: boolean | null;
  readonly memberEnd: "START" | "END" | null;
}

export interface SceneArrow {
  readonly id: string;
  readonly componentLabel?: string;
  readonly component: ActionDirectionSnapshot["component"];
  readonly kind: ActionDirectionSnapshot["kind"];
  readonly origin: Vec3;
  readonly axis: Vec3;
  readonly signedValue: number | null;
  readonly unit: string | null;
  readonly sense: ActionDirectionSnapshot["sense"];
  readonly isZero: boolean;
  readonly referencePointId: string;
  readonly frameId: string;
  readonly axialLoadingSense: ActionDirectionSnapshot["axial_loading_sense"];
}

export interface SceneMaterialAxes {
  readonly id: string;
  readonly componentId: string;
  readonly componentLabel: string;
  readonly sectionFamily: string;
  readonly elementId: string;
  readonly elementLabel: string;
  readonly materialRegionId: string;
  readonly origin: Vec3;
  readonly presentation: RegionEmbeddedMaterialAxisPresentation | null;
  readonly lengthwise: Vec3;
  readonly crosswise: Vec3;
  readonly throughThickness: Vec3;
}

export function materialRegionLabel(axes: SceneMaterialAxes): string {
  const profile = {
    ANGLE: "Angle",
    CHANNEL: "Channel",
    FLAT_PLATE: "Flat Plate",
    I_SECTION: "I",
    PLATE: "Flat Plate",
    RECTANGULAR_TUBE: "RHS",
    TEE: "Tee",
    WIDE_FLANGE: "W",
  }[axes.sectionFamily] ?? axes.componentLabel;
  const region = {
    BOTTOM_FLANGE: "Negative flange",
    BOTTOM_WALL: "Bottom wall",
    FLANGE: "Flange",
    LEG_1: "Leg 1",
    LEG_2: "Leg 2",
    PLATE: "Plate",
    SIDE_WALL_1: "Side wall 1",
    SIDE_WALL_2: "Side wall 2",
    STEM: "Stem",
    TOP_FLANGE: "Positive flange",
    TOP_WALL: "Top wall",
    WEB: "Web",
  }[axes.elementId] ?? axes.elementLabel;
  return profile === "Flat Plate" ? profile : `${profile} — ${region}`;
}

export interface SceneZone {
  readonly id: string;
  readonly label: string;
  readonly side: string;
  readonly participantId: string;
  readonly interfaceId: string;
  readonly patchId: string;
  readonly normal: Vec3;
  readonly selectedContact: boolean;
  readonly corners: readonly Vec3[];
}

export interface SceneConnectionOrientation {
  readonly connectionSide: "EXTERIOR" | "WEB_SIDE";
  readonly connectedLeg: "LEG_1" | "LEG_2";
  readonly outstandingLegSide: "POSITIVE_INTERFACE_Z" | "NEGATIVE_INTERFACE_Z";
  readonly supportingMemberId: string;
  readonly connectedMemberId: string;
  readonly selectedFlangeElementId: string;
  readonly selectedFlangeSurfaceId: string;
  readonly selectedAngleSurfaceId: string;
  readonly selectedContactNormal: Vec3;
  readonly braceToColumnDirectedAngleDegrees: number;
  readonly planAngleDegrees: number;
  readonly interferenceClassifications: readonly string[];
  readonly interferenceParticipantIds: readonly string[];
  readonly interferencePhysicalElementIds: readonly string[];
  readonly geometryValid: boolean;
}

export interface SingleBoltSceneModel {
  readonly snapshotVersion: string;
  readonly unitSystem: VisualizationSnapshot["unit_system"];
  readonly lengthUnit: string;
  readonly boxes: readonly SceneBox[];
  readonly meshes: readonly SceneTriangleMesh[];
  readonly cylinders: readonly SceneCylinder[];
  readonly frames: readonly SceneFrame[];
  readonly markers: readonly SceneMarker[];
  readonly positiveArrows: readonly SceneArrow[];
  readonly appliedArrows: readonly SceneArrow[];
  readonly connectionDemandArrows: readonly SceneArrow[];
  readonly perBoltDemandArrows: readonly SceneArrow[];
  readonly materialAxes: readonly SceneMaterialAxes[];
  readonly zones: readonly SceneZone[];
  readonly connectionOrientation: SceneConnectionOrientation | null;
  readonly boundsCenter: Vec3;
  readonly boundsRadius: number;
  readonly fitCenter: Vec3;
  readonly fitRadius: number;
}

function decimal(value: string, field: string): number {
  if (value.trim() === "") throw new Error(`${field} must be a decimal string.`);
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) throw new Error(`${field} must be finite.`);
  return parsed;
}

function point(value: Pick<PointSnapshot, "x" | "y" | "z">): Vec3 {
  return {
    x: decimal(value.x, "point.x"),
    y: decimal(value.y, "point.y"),
    z: decimal(value.z, "point.z"),
  };
}

function direction(value: DirectionSnapshot): Vec3 {
  return {
    x: decimal(value.x, "direction.x"),
    y: decimal(value.y, "direction.y"),
    z: decimal(value.z, "direction.z"),
  };
}

function parameters(values: readonly SnapshotParameter[]): ReadonlyMap<string, number> {
  return new Map(values.map((value) => [value.name, decimal(value.value, value.name)]));
}

function required(values: ReadonlyMap<string, number>, name: string): number {
  const value = values.get(name);
  if (value === undefined) throw new Error(`Visualization primitive lacks ${name}.`);
  return value;
}

function subtract(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

function add(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}

function scale(value: Vec3, factor: number): Vec3 {
  return { x: value.x * factor, y: value.y * factor, z: value.z * factor };
}

function magnitude(value: Vec3): number {
  return Math.hypot(value.x, value.y, value.z);
}

/** Extend accepted bolt hardware from backend-authored C1/C2 physical path spans. */
export function applyFullThroughBoltSpans(
  cylinders: readonly SceneCylinder[],
  traces: readonly FullThroughBoltTrace[],
): readonly SceneCylinder[] {
  if (traces.length === 0) return cylinders;
  const byBolt = new Map(traces.map((value) => [value.path.bolt_id, value]));
  const traceFor = (ownerBoltId: string) => byBolt.get(ownerBoltId)
    ?? [...byBolt].find(([boltId]) => ownerBoltId.endsWith(`:${boltId}`))?.[1];
  const fullEnds = new Map<string, { readonly start: Vec3; readonly end: Vec3; readonly axis: Vec3 }>();
  for (const cylinder of cylinders) {
    if (cylinder.kind !== "BOLT") continue;
    const trace = traceFor(cylinder.ownerBoltId);
    if (trace === undefined) continue;
    const start = point(trace.physical_start_point);
    const end = point(trace.physical_end_point);
    const vector = subtract(end, start);
    const physicalLength = magnitude(vector);
    if (physicalLength === 0) throw new Error("Full-through bolt shank requires a nonzero axis.");
    const axis = scale(vector, 1 / physicalLength);
    fullEnds.set(cylinder.ownerBoltId, {
      start,
      end,
      axis,
    });
  }
  return cylinders.map((cylinder) => {
    const span = fullEnds.get(cylinder.ownerBoltId);
    if (span === undefined) return cylinder;
    if (cylinder.kind === "BOLT") return { ...cylinder, start: span.start, end: span.end };
    if (cylinder.kind === "WASHER" && cylinder.hardwareLocation === "UNDER_HEAD") {
      const thickness = magnitude(subtract(cylinder.end, cylinder.start));
      return {
        ...cylinder,
        start: add(span.start, scale(span.axis, -thickness)),
        end: span.start,
      };
    }
    if (cylinder.kind === "WASHER" && cylinder.hardwareLocation === "UNDER_NUT") {
      const thickness = magnitude(subtract(cylinder.end, cylinder.start));
      return {
        ...cylinder,
        start: span.end,
        end: add(span.end, scale(span.axis, thickness)),
      };
    }
    return cylinder;
  });
}

function actionArrows(
  values: readonly ActionDirectionSnapshot[],
  references: ReadonlyMap<string, Vec3>,
): SceneArrow[] {
  return values.map((value) => {
    const origin = references.get(value.reference_point_id);
    if (origin === undefined) {
      throw new Error(`Action direction lacks reference ${value.reference_point_id}.`);
    }
    return {
      id: `${value.reference_point_id}:${value.component}`,
      component: value.component,
      kind: value.kind,
      origin,
      axis: direction(value.axis),
      signedValue:
        value.signed_value === null ? null : decimal(value.signed_value, value.component),
      unit: value.unit,
      sense: value.sense,
      isZero: value.is_zero,
      referencePointId: value.reference_point_id,
      frameId: value.frame_id,
      axialLoadingSense: value.axial_loading_sense,
    };
  });
}

export function calculatePresentationBounds(
  points: readonly Vec3[],
): { center: Vec3; radius: number } {
  const first = points[0];
  if (first === undefined) return { center: { x: 0, y: 0, z: 0 }, radius: 1 };
  const minimum = { ...first };
  const maximum = { ...first };
  for (const value of points.slice(1)) {
    minimum.x = Math.min(minimum.x, value.x);
    minimum.y = Math.min(minimum.y, value.y);
    minimum.z = Math.min(minimum.z, value.z);
    maximum.x = Math.max(maximum.x, value.x);
    maximum.y = Math.max(maximum.y, value.y);
    maximum.z = Math.max(maximum.z, value.z);
  }
  const center = {
    x: (minimum.x + maximum.x) / 2,
    y: (minimum.y + maximum.y) / 2,
    z: (minimum.z + maximum.z) / 2,
  };
  return {
    center,
    radius: Math.max(1, ...points.map((value) => magnitude(subtract(value, center)))),
  };
}

export function calculateOrthographicZoom(viewportPixels: number, radius: number): number {
  return Math.max(0.01, viewportPixels / (Math.max(radius, 1) * 2.8));
}

export function canonicalCylinderRadius(diameter: number): number {
  return diameter / 2;
}

export function calculatePerspectiveDistance(radius: number, fovDegrees: number): number {
  const halfVisibleAngle = (fovDegrees * 0.72 * Math.PI) / 360;
  return Math.max(radius, 1) / Math.tan(halfVisibleAngle);
}

export function calculateCameraClippingPlanes(
  distance: number,
  radius: number,
): { readonly far: number; readonly near: number } {
  const safeRadius = Math.max(radius, 1);
  return {
    near: safeRadius * 0.001,
    far: Math.max(distance + safeRadius * 100, safeRadius * 101),
  };
}

function boxCorners(value: SceneBox): Vec3[] {
  const xHalf = scale(value.basis[0], value.size.x / 2);
  const yHalf = scale(value.basis[1], value.size.y / 2);
  const zHalf = scale(value.basis[2], value.size.z / 2);
  const corners: Vec3[] = [];
  for (const xSign of [-1, 1]) {
    for (const ySign of [-1, 1]) {
      for (const zSign of [-1, 1]) {
        corners.push(
          add(
            add(add(value.center, scale(xHalf, xSign)), scale(yHalf, ySign)),
            scale(zHalf, zSign),
          ),
        );
      }
    }
  }
  return corners;
}

function cylindersForBolt(
  bolt: VisualizationSnapshot["bolt"],
  rowId: string | null,
  boltLineId: string | null,
  resolvedLayerIds?: readonly string[],
  interfaceId: string | null = null,
): SceneCylinder[] {
  const penetratedLayerIds = resolvedLayerIds ??
    bolt.holes.map((value) => value.physical_element_id);
  return [
    {
      id: `${bolt.bolt_group_id}:${bolt.bolt_location_id}:bolt`,
      label: friendlyBoltLabel(bolt.bolt_location_id),
      start: point(bolt.stack_start),
      end: point(bolt.stack_end),
      diameter: decimal(bolt.bolt_diameter, "bolt_diameter"),
      kind: "BOLT",
      hardwareLocation: null,
      ownerBoltId: bolt.bolt_location_id,
      rowId,
      boltLineId,
      penetratedLayerIds,
      interfaceId,
    },
    ...bolt.holes.map((value) => ({
      id: value.id,
      label: `Round hole through ${value.physical_element_id}`,
      start: point(value.start),
      end: point(value.end),
      diameter: decimal(value.diameter, "hole_diameter"),
      kind: "HOLE" as const,
      hardwareLocation: null,
      ownerBoltId: bolt.bolt_location_id,
      rowId,
      boltLineId,
      penetratedLayerIds,
      interfaceId,
    })),
    ...bolt.washers.map((value) => ({
      id: value.id,
      label: value.location === "UNDER_HEAD" ? "Under-head washer" : "Under-nut washer",
      start: point(value.start),
      end: point(value.end),
      diameter: decimal(value.outside_diameter, "washer_outside_diameter"),
      kind: "WASHER" as const,
      hardwareLocation: value.location,
      ownerBoltId: bolt.bolt_location_id,
      rowId,
      boltLineId,
      penetratedLayerIds,
      interfaceId,
    })),
  ];
}

function friendlyBoltLabel(id: string): string {
  const match = /^B_R(\d+)_L(\d+)$/u.exec(id);
  return match === null
    ? "Selected bolt"
    : `Bolt · Row ${String(match[1])} · Line ${String(match[2])}`;
}

export function buildSingleBoltSceneModel(
  snapshot: VisualizationSnapshot,
): SingleBoltSceneModel {
  const components = new Map(snapshot.components.map((value) => [value.id, value]));
  const interferenceParticipants = new Set(
    snapshot.connection_orientation?.interference_participant_ids ?? [],
  );
  const interferenceElements = new Set(
    snapshot.connection_orientation?.interference_physical_element_ids ?? [],
  );
  const viewExtensionOwners = new Set(
    snapshot.view_extension_primitives.map((value) => value.owner_id),
  );
  const displayedPrimitives = [
    ...snapshot.primitives.filter((value) => !viewExtensionOwners.has(value.owner_id)),
    ...snapshot.view_extension_primitives,
  ];
  const boxes = displayedPrimitives
    .filter((value) => value.kind === "BOX" || value.kind === "DEFERRED_RECTANGLE")
    .map((value): SceneBox => {
      if (
        value.center === null ||
        value.x_axis === null ||
        value.y_axis === null ||
        value.z_axis === null
      ) {
        throw new Error(`Box ${value.id} lacks canonical placement data.`);
      }
      const data = parameters(value.parameters);
      const component = components.get(value.owner_id);
      return {
        id: value.id,
        label: value.label,
        ownerId: value.owner_id,
        ownerLabel: component?.label ?? value.owner_id,
        ownerRole: component?.section_family === "WIDE_FLANGE"
          ? "COLUMN"
          : component?.section_family === "ANGLE"
            ? "BRACE"
            : "OTHER",
        elementId: value.physical_element_id,
        materialRegionId: value.material_region_id,
        center: point(value.center),
        size: {
          x: required(data, "x_end") - required(data, "x_start"),
          y: required(data, "max_y") - required(data, "min_y"),
          z: required(data, "max_z") - required(data, "min_z"),
        },
        basis: [direction(value.x_axis), direction(value.y_axis), direction(value.z_axis)],
        deferred: value.resolution_status === "DEFERRED",
        interference:
          interferenceParticipants.has(value.owner_id) &&
          value.physical_element_id !== null &&
          interferenceElements.has(value.physical_element_id),
      };
    });
  const meshes = displayedPrimitives
    .filter((value) => value.kind === "TRIANGLE_MESH")
    .map((value): SceneTriangleMesh => {
      if (value.points.length < 3 || value.points.length % 3 !== 0) {
        throw new Error(`Triangle mesh ${value.id} must contain complete triangles.`);
      }
      const component = components.get(value.owner_id);
      return {
        id: value.id,
        label: value.label,
        ownerId: value.owner_id,
        ownerLabel: component?.label ?? value.owner_id,
        ownerRole: component?.section_family === "WIDE_FLANGE"
          ? "COLUMN"
          : component?.section_family === "ANGLE"
            ? "BRACE"
            : "OTHER",
        elementId: value.physical_element_id,
        materialRegionId: value.material_region_id,
        points: value.points.map(point),
      };
    });
  const bolt = snapshot.bolt;
  const cylinders = cylindersForBolt(bolt, null, null, undefined, snapshot.interface_id);
  const frames = snapshot.frames.map((value): SceneFrame => ({
    id: value.id,
    label: value.label,
    kind: value.kind,
    ownerId: value.owner_id,
    origin: point(value.frame.origin),
    xAxis: direction(value.frame.x_axis),
    yAxis: direction(value.frame.y_axis),
    zAxis: direction(value.frame.z_axis),
    valid:
      value.inspection.orthonormal === true && value.inspection.right_handed === true,
  }));
  const markers = snapshot.reference_points.map((value): SceneMarker => ({
    id: value.id,
    label: value.label,
    kind: value.kind,
    position: point(value.position),
    connected: value.connected,
    memberEnd: value.member_end,
  }));
  const references = new Map(markers.map((value) => [value.id, value.position]));
  const materialAxes = snapshot.material_directions.flatMap((value): SceneMaterialAxes[] => {
    if (
      value.resolution_status !== "EXACT" ||
      value.lengthwise === null ||
      value.crosswise === null ||
      value.through_thickness === null
    ) {
      return [];
    }
    const component = components.get(value.component_id);
    const element = component?.elements.find(
      (candidate) => candidate.id === value.physical_element_id,
    );
    const elementLabel = element?.label;
    const axes = {
      id: value.id,
      componentId: value.component_id,
      componentLabel: component?.label ?? value.component_id,
      sectionFamily: component?.section_family ?? "UNKNOWN",
      elementId: value.physical_element_id,
      elementLabel:
        typeof elementLabel === "string" ? elementLabel : value.physical_element_id,
      materialRegionId: value.material_region_id,
      origin: point(value.origin),
      lengthwise: direction(value.lengthwise),
      crosswise: direction(value.crosswise),
      throughThickness: direction(value.through_thickness),
    };
    return [
      {
        ...axes,
        presentation: buildRegionEmbeddedMaterialAxisPresentation(axes, boxes, meshes),
      },
    ];
  });
  const zones = snapshot.interface_zones.map((value): SceneZone => {
    return {
      id: value.id,
      label: value.label,
      side: value.side,
      participantId: value.participant_id,
      interfaceId: value.interface_id,
      patchId: value.patch_id,
      normal: direction(value.normal),
      selectedContact:
        snapshot.connection_orientation?.selected_flange_surface_id === value.patch_id,
      corners: value.corners.map(point),
    };
  });
  const orientation = snapshot.connection_orientation;
  const connectionOrientation = orientation === null ? null : {
    connectionSide: orientation.connection_side,
    connectedLeg: orientation.connected_leg,
    outstandingLegSide: orientation.outstanding_leg_side,
    supportingMemberId: orientation.supporting_member_id,
    connectedMemberId: orientation.connected_member_id,
    selectedFlangeElementId: orientation.selected_flange_element_id,
    selectedFlangeSurfaceId: orientation.selected_flange_surface_id,
    selectedAngleSurfaceId: orientation.selected_angle_surface_id,
    selectedContactNormal: direction(orientation.selected_contact_normal),
    braceToColumnDirectedAngleDegrees: decimal(
      orientation.brace_to_column_directed_angle_degrees,
      "brace_to_column_directed_angle_degrees",
    ),
    planAngleDegrees: decimal(orientation.plan_angle_degrees, "plan_angle_degrees"),
    interferenceClassifications: orientation.interference_classifications,
    interferenceParticipantIds: orientation.interference_participant_ids,
    interferencePhysicalElementIds: orientation.interference_physical_element_ids,
    geometryValid: orientation.geometry_valid,
  };
  const presentationPoints = [
    ...boxes.flatMap(boxCorners),
    ...meshes.flatMap((value) => value.points),
    ...cylinders.flatMap((value) => [value.start, value.end]),
    ...markers.map((value) => value.position),
    ...zones.flatMap((value) => value.corners),
  ];
  const bounds = calculatePresentationBounds(presentationPoints);
  const fitCenter = point(bolt.center);
  const fitRadius = Math.max(
    1,
    ...presentationPoints.map((value) => magnitude(subtract(value, fitCenter))),
  );
  return {
    snapshotVersion: snapshot.snapshot_version,
    unitSystem: snapshot.unit_system,
    lengthUnit: snapshot.length_unit,
    boxes,
    meshes,
    cylinders,
    frames,
    markers,
    positiveArrows: actionArrows(snapshot.positive_action_directions, references),
    appliedArrows: actionArrows(snapshot.applied_action_directions, references),
    connectionDemandArrows: [],
    perBoltDemandArrows: [],
    materialAxes,
    zones,
    connectionOrientation,
    boundsCenter: bounds.center,
    boundsRadius: bounds.radius,
    fitCenter,
    fitRadius,
  };
}

export function buildMultiRowSceneModel(
  snapshot: MultiRowVisualization,
): SingleBoltSceneModel {
  const physicalConnection = snapshot.physical_connection;
  if (physicalConnection === null || physicalConnection === undefined) {
    throw new Error("Multi-row visualization lacks canonical physical connection geometry.");
  }
  if (snapshot.physical_bolts === undefined || snapshot.physical_bolts.length === 0) {
    throw new Error("Multi-row visualization lacks canonical physical bolt placements.");
  }
  const base = buildSingleBoltSceneModel(physicalConnection);
  const cylinders = snapshot.physical_bolts.flatMap((value) =>
    cylindersForBolt(
      value.display,
      value.row_id,
      value.bolt_line_id,
      value.penetrated_layer_ids,
      physicalConnection.interface_id,
    ),
  );
  const boltMarkers = snapshot.physical_bolts.map((value): SceneMarker => ({
    id: value.bolt_id,
    label: friendlyBoltLabel(value.bolt_id),
    kind: "BOLT_CENTER",
    position: point(value.display.center),
    connected: null,
    memberEnd: null,
  }));
  const markers = [
    ...base.markers.filter((value) => value.kind !== "BOLT_CENTER"),
    ...boltMarkers,
  ];
  const presentationPoints = [
    ...base.boxes.flatMap(boxCorners),
    ...base.meshes.flatMap((value) => value.points),
    ...cylinders.flatMap((value) => [value.start, value.end]),
    ...markers.map((value) => value.position),
    ...base.zones.flatMap((value) => value.corners),
  ];
  const bounds = calculatePresentationBounds(presentationPoints);
  /* v8 ignore next 3 -- physical_bolts is validated nonempty before marker mapping */
  if (boltMarkers[0] === undefined) {
    throw new Error("Multi-row visualization lacks a first physical bolt marker.");
  }
  const fitCenter = boltMarkers[0].position;
  const fitRadius = Math.max(
    1,
    ...presentationPoints.map((value) => magnitude(subtract(value, fitCenter))),
  );
  const connectionDemand = snapshot.connection_demand;
  const connectionDemandArrows: SceneArrow[] = connectionDemand === null || connectionDemand === undefined
    ? []
    : [{
        id: connectionDemand.reference_point_id,
        component: "FX",
        kind: "LINEAR",
        origin: point(connectionDemand.origin),
        axis: direction(connectionDemand.axis),
        signedValue: decimal(connectionDemand.resultant.value, "connection_demand"),
        unit: connectionDemand.resultant.unit,
        sense: "POSITIVE",
        isZero: false,
        referencePointId: connectionDemand.reference_point_id,
        frameId: connectionDemand.frame_id,
        axialLoadingSense: null,
      }];
  const perBoltDemandArrows: SceneArrow[] = snapshot.automatic_bolt_demands.flatMap((value) =>
    value.total_axis === null
      ? []
      : [{
          id: `automatic-demand:${value.bolt_id}`,
          component: "FX" as const,
          kind: "LINEAR" as const,
          origin: point(value.origin),
          axis: direction(value.total_axis),
          signedValue: decimal(value.total_magnitude.value, `${value.bolt_id}:total_magnitude`),
          unit: value.total_magnitude.unit,
          sense: "POSITIVE" as const,
          isZero: false,
          referencePointId: value.bolt_id,
          frameId: value.bolt_line_id,
          axialLoadingSense: null,
        }],
  );
  return {
    ...base,
    cylinders,
    markers,
    boundsCenter: bounds.center,
    boundsRadius: bounds.radius,
    fitCenter,
    fitRadius,
    connectionDemandArrows,
    perBoltDemandArrows,
  };
}

function teeBoltIdentity(id: string): {
  readonly interfaceLabel: string;
  readonly lineId: string | null;
  readonly rowId: string | null;
} {
  const match = /^([AB])_B_R(\d+)_L(\d+)$/u.exec(id);
  if (match === null) {
    return { interfaceLabel: "Tee interface", lineId: null, rowId: null };
  }
  return {
    interfaceLabel: match[1] === "A" ? "Brace to Tee Stem" : "Tee Flange to Support",
    rowId: `ROW_${String(match[2])}`,
    lineId: `BOLT_LINE_${String(match[3])}`,
  };
}

export function buildTeeSceneModel(snapshot: TeeVisualization): SingleBoltSceneModel {
  const frames = new Map(
    [
      ...snapshot.base_connection.frames,
      ...snapshot.interface_b_connection.frames,
    ].map((value) => [value.id, value]),
  );
  const firstBolt = snapshot.interface_a_bolts[0];
  if (firstBolt === undefined) {
    throw new Error("Tee visualization lacks Interface A bolt placements.");
  }
  const base = buildSingleBoltSceneModel({
    ...snapshot.base_connection,
    frames: [...frames.values()],
    interface_zones: snapshot.interface_zones,
    bolt: firstBolt,
  });
  const physicalBolts = [
    ...snapshot.interface_a_bolts.map((bolt) => ({
      bolt,
      interfaceId: snapshot.base_connection.interface_id,
    })),
    ...snapshot.interface_b_bolts.map((bolt) => ({
      bolt,
      interfaceId: snapshot.interface_b_connection.interface_id,
    })),
  ];
  const cylinders = applyFullThroughBoltSpans(physicalBolts.flatMap(({ bolt, interfaceId }) => {
    const identity = teeBoltIdentity(bolt.bolt_location_id);
    return cylindersForBolt(
      bolt,
      identity.rowId,
      identity.lineId,
      bolt.holes.map((hole) => `${hole.participant_id}:${hole.physical_element_id}`),
      interfaceId,
    );
  }), snapshot.rectangular_full_through_paths);
  const boltMarkers = physicalBolts.map(({ bolt }): SceneMarker => {
    const identity = teeBoltIdentity(bolt.bolt_location_id);
    return {
      id: bolt.bolt_location_id,
      label: `${identity.interfaceLabel} · ${friendlyBoltLabel(
        bolt.bolt_location_id.replace(/^[AB]_/u, ""),
      )}`,
      kind: "BOLT_CENTER",
      position: point(bolt.center),
      connected: null,
      memberEnd: null,
    };
  });
  const markers = [
    ...base.markers.filter((value) => value.kind !== "BOLT_CENTER"),
    ...boltMarkers,
  ];
  const supportParticipantId = snapshot.interface_zones.find(
    (value) => value.patch_id === snapshot.selected_support_surface_id,
  )?.participant_id;
  const boxes = base.boxes.map((value): SceneBox => ({
    ...value,
    ownerRole:
      value.ownerId === snapshot.connected_member_profile.member_id
        ? "BRACE"
        : value.ownerId === supportParticipantId
          ? "COLUMN"
          : value.ownerRole,
  }));
  const meshes = base.meshes.map((value): SceneTriangleMesh => ({
    ...value,
    ownerRole:
      value.ownerId === snapshot.connected_member_profile.member_id
        ? "BRACE"
        : value.ownerId === supportParticipantId
          ? "COLUMN"
          : value.ownerRole,
  }));
  const zones = base.zones.map((value) => ({
    ...value,
    selectedContact:
      value.patchId === snapshot.selected_support_surface_id ||
      value.patchId === snapshot.selected_connected_surface_patch_id,
  }));
  const presentationPoints = [
    ...boxes.flatMap(boxCorners),
    ...meshes.flatMap((value) => value.points),
    ...cylinders.flatMap((value) => [value.start, value.end]),
    ...markers.map((value) => value.position),
    ...zones.flatMap((value) => value.corners),
  ];
  const bounds = calculatePresentationBounds(presentationPoints);
  const fitCenter = point(firstBolt.center);
  const fitRadius = Math.max(
    1,
    ...presentationPoints.map((value) => magnitude(subtract(value, fitCenter))),
  );
  return {
    ...base,
    boxes,
    meshes,
    cylinders,
    markers,
    zones,
    boundsCenter: bounds.center,
    boundsRadius: bounds.radius,
    fitCenter,
    fitRadius,
  };
}
