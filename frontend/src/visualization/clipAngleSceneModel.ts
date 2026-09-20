import type {
  ClipAngleBoltTrace,
  ClipAngleQuantity,
  ClipAngleVisualization,
} from "../api/clipAngleContracts";
import {
  buildRegionEmbeddedMaterialAxisPresentation,
  normalizeMaterialAxisPrimitiveId,
  resolveMaterialAxisOwnedIdentity,
} from "./materialAxisPresentation";
import {
  calculatePresentationBounds,
  applyFullThroughBoltSpans,
  type SceneArrow,
  type SceneBox,
  type SceneCylinder,
  type SceneMaterialAxes,
  type SceneTriangleMesh,
  type SceneZone,
  type SingleBoltSceneModel,
  type Vec3,
} from "./sceneModel";

const BASIS = [
  { x: 1, y: 0, z: 0 },
  { x: 0, y: 1, z: 0 },
  { x: 0, y: 0, z: 1 },
] as const;

function quantity(value: ClipAngleQuantity): number {
  const parsed = Number(value.value);
  if (!Number.isFinite(parsed)) throw new Error("Clip-angle visualization requires finite quantities.");
  return parsed;
}

function vector(
  value: readonly [ClipAngleQuantity, ClipAngleQuantity, ClipAngleQuantity],
): Vec3 {
  return { x: quantity(value[0]), y: quantity(value[1]), z: quantity(value[2]) };
}

function direction(value: readonly [string, string, string]): Vec3 {
  return { x: Number(value[0]), y: Number(value[1]), z: Number(value[2]) };
}

function boxCorners(value: SceneBox): readonly Vec3[] {
  const result: Vec3[] = [];
  for (const sx of [-1, 1]) {
    for (const sy of [-1, 1]) {
      for (const sz of [-1, 1]) {
        result.push({
          x: value.center.x
            + sx * value.basis[0].x * value.size.x / 2
            + sy * value.basis[1].x * value.size.y / 2
            + sz * value.basis[2].x * value.size.z / 2,
          y: value.center.y
            + sx * value.basis[0].y * value.size.x / 2
            + sy * value.basis[1].y * value.size.y / 2
            + sz * value.basis[2].y * value.size.z / 2,
          z: value.center.z
            + sx * value.basis[0].z * value.size.x / 2
            + sy * value.basis[1].z * value.size.y / 2
            + sz * value.basis[2].z * value.size.z / 2,
        });
      }
    }
  }
  return result;
}

function ownerRole(
  ownerId: string,
  connectedRole: ClipAngleVisualization["connected_member_role"],
): SceneBox["ownerRole"] {
  if (ownerId === "clip-angle-connected-member") {
    return connectedRole === "BRACE" ? "BRACE" : "OTHER";
  }
  if (ownerId === "clip-angle-support") return "COLUMN";
  return "OTHER";
}

function ownerLabel(ownerId: string, family: string): string {
  if (ownerId === "clip-angle-connected-member") {
    return `Connected member · ${family.replaceAll("_", " ")}`;
  }
  if (ownerId === "clip-angle-support") return "W support";
  return "Single FRP Clip Angle";
}

function boxes(value: ClipAngleVisualization): readonly SceneBox[] {
  return value.boxes.map((item) => {
    const connectorRegion = item.role === "CONNECTED_MEMBER_LEG"
      ? "CLIP_ANGLE_CONNECTED_MEMBER_LEG_REGION"
      : item.role === "SUPPORT_LEG"
        ? "CLIP_ANGLE_SUPPORT_LEG_REGION"
        : null;
    const elementId = normalizeMaterialAxisPrimitiveId(
      item.owner_id,
      item.physical_element_id ?? item.role,
    );
    const materialRegionId = item.material_region_id ?? connectorRegion;
    return {
      id: item.id,
      label: item.role.replaceAll("_", " "),
      ownerId: item.owner_id,
      ownerLabel: ownerLabel(item.owner_id, value.connected_member_profile_family),
      ownerRole: ownerRole(item.owner_id, value.connected_member_role),
      elementId,
      materialRegionId: materialRegionId === null
        ? null
        : normalizeMaterialAxisPrimitiveId(item.owner_id, materialRegionId),
      center: vector(item.center),
      size: { x: quantity(item.size_s), y: quantity(item.size_p), z: quantity(item.size_l) },
      basis: [direction(item.basis[0]), direction(item.basis[1]), direction(item.basis[2])],
      deferred: false,
      interference: false,
    };
  });
}

function meshes(value: ClipAngleVisualization): readonly SceneTriangleMesh[] {
  return value.meshes.map((item) => ({
    id: item.id,
    label: `${item.role.replaceAll("_", " ")} trimmed member solid`,
    ownerId: item.owner_id,
    ownerLabel: ownerLabel(item.owner_id, value.connected_member_profile_family),
    ownerRole: ownerRole(item.owner_id, value.connected_member_role),
    elementId: normalizeMaterialAxisPrimitiveId(item.owner_id, item.physical_element_id),
    materialRegionId: normalizeMaterialAxisPrimitiveId(
      item.owner_id,
      item.material_region_id,
    ),
    points: item.points.map(vector),
  }));
}

function boltCylinders(
  bolts: readonly ClipAngleBoltTrace[],
  interfaceId: string,
  boltDiameter: number,
  holeDiameter: number,
): readonly SceneCylinder[] {
  return bolts.flatMap((bolt): readonly SceneCylinder[] => {
    const ownerBoltId = `${interfaceId}:${bolt.bolt_id}`;
    const common = {
      start: vector(bolt.stack_start),
      end: vector(bolt.stack_end),
      ownerBoltId,
      rowId: bolt.row_id,
      boltLineId: bolt.bolt_line_id,
      penetratedLayerIds: bolt.layer_ids,
      interfaceId,
      hardwareLocation: null,
    } as const;
    return [
      { ...common, id: `${ownerBoltId}:bolt`, label: `${bolt.bolt_id} fastener`, diameter: boltDiameter, kind: "BOLT" },
      { ...common, id: `${ownerBoltId}:hole`, label: `${bolt.bolt_id} hole path`, diameter: holeDiameter, kind: "HOLE" },
    ];
  });
}

function arrow(
  component: SceneArrow["component"],
  origin: Vec3,
  axis: Vec3,
  signedValue: number,
  unit: string,
): SceneArrow {
  return {
    id: `clip-angle-applied-${component}`,
    component,
    kind: component.startsWith("F") ? "LINEAR" : "ROTATIONAL",
    origin,
    axis,
    signedValue,
    unit,
    sense: signedValue === 0 ? "ZERO" : signedValue > 0 ? "POSITIVE" : "NEGATIVE",
    isZero: signedValue === 0,
    referencePointId: "CLIP_ANGLE_GLOBAL_ACTION_REFERENCE",
    frameId: "CLIP_ANGLE_SEMANTIC_FRAME",
    axialLoadingSense: null,
  };
}

function appliedArrows(value: ClipAngleVisualization): readonly SceneArrow[] {
  const origin = {
    x: quantity(value.global_reference_point.x),
    y: quantity(value.global_reference_point.y),
    z: quantity(value.global_reference_point.z),
  };
  return [
    arrow("FX", origin, BASIS[0], quantity(value.global_force.x), value.global_force.x.unit),
    arrow("FY", origin, BASIS[1], quantity(value.global_force.y), value.global_force.y.unit),
    arrow("FZ", origin, BASIS[2], quantity(value.global_force.z), value.global_force.z.unit),
    arrow("MX", origin, BASIS[0], quantity(value.global_moment.x), value.global_moment.x.unit),
    arrow("MY", origin, BASIS[1], quantity(value.global_moment.y), value.global_moment.y.unit),
    arrow("MZ", origin, BASIS[2], quantity(value.global_moment.z), value.global_moment.z.unit),
  ];
}

function materialAxes(
  value: ClipAngleVisualization,
  sceneBoxes: readonly SceneBox[],
  sceneMeshes: readonly SceneTriangleMesh[],
): readonly SceneMaterialAxes[] {
  const primitiveOwnerIds = [...new Set([
    ...sceneBoxes.map((item) => item.ownerId),
    ...sceneMeshes.map((item) => item.ownerId),
  ])];
  const connector = value.material_regions.map((region): SceneMaterialAxes => {
    const elementIdentity = resolveMaterialAxisOwnedIdentity(
      "single-clip-angle-connector",
      region.physical_element_id,
      primitiveOwnerIds,
    );
    const axes = {
      componentId: elementIdentity.ownerId,
      elementId: elementIdentity.localId,
      materialRegionId: resolveMaterialAxisOwnedIdentity(
        elementIdentity.ownerId,
        region.region_id,
        primitiveOwnerIds,
      ).localId,
      lengthwise: direction(region.lw),
      crosswise: direction(region.cw),
      throughThickness: direction(region.tt),
    };
    const presentation = buildRegionEmbeddedMaterialAxisPresentation(
      axes,
      sceneBoxes,
      sceneMeshes,
    );
    return {
      id: `clip-angle-material-axes:${region.region_id}`,
      componentId: axes.componentId,
      componentLabel: axes.componentId === "POSITIVE_CLIP_ANGLE"
        ? "Positive FRP Clip Angle"
        : axes.componentId === "NEGATIVE_CLIP_ANGLE"
          ? "Negative FRP Clip Angle"
          : "Single FRP Clip Angle",
      sectionFamily: "ANGLE",
      elementId: axes.elementId,
      elementLabel: axes.elementId.replaceAll("_", " "),
      materialRegionId: axes.materialRegionId,
      origin: presentation?.origin ?? { x: 0, y: 0, z: 0 },
      presentation,
      lengthwise: axes.lengthwise,
      crosswise: axes.crosswise,
      throughThickness: axes.throughThickness,
    };
  });
  const profile = value.connected_member_material_regions.map(
    (region): SceneMaterialAxes => {
      const axes = {
        componentId: "clip-angle-connected-member",
        elementId: region.physical_element_id,
        materialRegionId: region.material_region_id,
        lengthwise: direction(region.lw),
        crosswise: direction(region.cw),
        throughThickness: direction(region.tt),
      };
      const presentation = buildRegionEmbeddedMaterialAxisPresentation(
        axes,
        sceneBoxes,
        sceneMeshes,
      );
      return {
        id: region.id,
        componentId: axes.componentId,
        componentLabel: ownerLabel(
          axes.componentId,
          value.connected_member_profile_family,
        ),
        sectionFamily: value.connected_member_profile_family,
        elementId: axes.elementId,
        elementLabel: axes.elementId.replaceAll("_", " "),
        materialRegionId: axes.materialRegionId,
        origin: vector(region.origin),
        presentation,
        lengthwise: axes.lengthwise,
        crosswise: axes.crosswise,
        throughThickness: axes.throughThickness,
      };
    },
  );
  const support = value.support_material_regions.map(
    (region): SceneMaterialAxes => {
      const axes = {
        componentId: "clip-angle-support",
        elementId: region.physical_element_id,
        materialRegionId: region.material_region_id,
        lengthwise: direction(region.lw),
        crosswise: direction(region.cw),
        throughThickness: direction(region.tt),
      };
      const presentation = buildRegionEmbeddedMaterialAxisPresentation(
        axes,
        sceneBoxes,
        sceneMeshes,
      );
      return {
        id: region.id,
        componentId: axes.componentId,
        componentLabel: "Supporting member",
        sectionFamily: value.support_profile.profile_family,
        elementId: axes.elementId,
        elementLabel: axes.elementId.replaceAll("_", " "),
        materialRegionId: axes.materialRegionId,
        origin: vector(region.origin),
        presentation,
        lengthwise: axes.lengthwise,
        crosswise: axes.crosswise,
        throughThickness: axes.throughThickness,
      };
    },
  );
  return [...connector, ...profile, ...support];
}

function zones(value: ClipAngleVisualization, sceneBoxes: readonly SceneBox[]): readonly SceneZone[] {
  const connected = sceneBoxes.find((item) => item.id === "clip-angle-connected-leg-solid");
  const support = sceneBoxes.find((item) => item.id === "clip-angle-support-leg-solid");
  if (connected === undefined || support === undefined) return [];
  const aHalfP = connected.size.y / 2;
  const aHalfL = connected.size.z / 2;
  const bHalfS = support.size.x / 2;
  const bHalfL = support.size.z / 2;
  return [
    {
      id: "CLIP_ANGLE_INTERFACE_A_CONTACT",
      label: "Connected Member ↔ Clip-Angle Connected Leg",
      side: "CONNECTED_MEMBER_LEG_EXTERIOR",
      participantId: "single-clip-angle-connector",
      interfaceId: "CONNECTED_MEMBER_TO_CLIP_ANGLE",
      patchId: value.selected_connected_surface_id,
      normal: { x: 1, y: 0, z: 0 },
      selectedContact: true,
      corners: [
        { x: 0, y: connected.center.y - aHalfP, z: connected.center.z - aHalfL },
        { x: 0, y: connected.center.y + aHalfP, z: connected.center.z - aHalfL },
        { x: 0, y: connected.center.y + aHalfP, z: connected.center.z + aHalfL },
        { x: 0, y: connected.center.y - aHalfP, z: connected.center.z + aHalfL },
      ],
    },
    {
      id: "CLIP_ANGLE_INTERFACE_B_CONTACT",
      label: "Clip-Angle Support Leg ↔ Support",
      side: "SUPPORT_LEG_EXTERIOR",
      participantId: "single-clip-angle-connector",
      interfaceId: "CLIP_ANGLE_TO_SUPPORT",
      patchId: value.selected_support_surface_id,
      normal: { x: 0, y: -1, z: 0 },
      selectedContact: true,
      corners: [
        { x: support.center.x - bHalfS, y: 0, z: support.center.z - bHalfL },
        { x: support.center.x + bHalfS, y: 0, z: support.center.z - bHalfL },
        { x: support.center.x + bHalfS, y: 0, z: support.center.z + bHalfL },
        { x: support.center.x - bHalfS, y: 0, z: support.center.z + bHalfL },
      ],
    },
  ];
}

/** Adapt the backend-authored clip-angle snapshot to the shared engineering renderer. */
export function buildClipAngleSceneModel(value: ClipAngleVisualization): SingleBoltSceneModel {
  const sceneMeshes = meshes(value);
  const trimmedMemberPresent = sceneMeshes.some(
    (item) => item.ownerId === "clip-angle-connected-member",
  );
  const sceneBoxes = boxes(value).filter(
    (item) => !trimmedMemberPresent || item.ownerId !== "clip-angle-connected-member",
  );
  const cylinders = applyFullThroughBoltSpans([
    ...boltCylinders(
      value.interface_a_bolts,
      "CONNECTED_MEMBER_TO_CLIP_ANGLE",
      quantity(value.bolt_diameter),
      quantity(value.hole_diameter),
    ),
    ...boltCylinders(
      value.interface_b_bolts,
      "CLIP_ANGLE_TO_SUPPORT",
      quantity(value.bolt_diameter),
      quantity(value.hole_diameter),
    ),
  ], value.rectangular_full_through_paths);
  const reference = {
    x: quantity(value.global_reference_point.x),
    y: quantity(value.global_reference_point.y),
    z: quantity(value.global_reference_point.z),
  };
  const points = [
    ...sceneBoxes.flatMap(boxCorners),
    ...sceneMeshes.flatMap((item) => item.points),
    ...cylinders.flatMap((item) => [item.start, item.end]),
    reference,
  ];
  const bounds = calculatePresentationBounds(points);
  return {
    snapshotVersion: value.schema_version,
    unitSystem: value.bolt_diameter.unit === "in" ? "US_CUSTOMARY" : "SI",
    lengthUnit: value.bolt_diameter.unit,
    boxes: sceneBoxes,
    meshes: sceneMeshes,
    cylinders,
    frames: [
      {
        id: "CLIP_ANGLE_SEMANTIC_FRAME",
        label: "Clip-angle semantic S/P/L frame",
        kind: "CONNECTOR_LOCAL",
        ownerId: "single-clip-angle-connector",
        origin: { x: 0, y: 0, z: 0 },
        xAxis: direction(value.semantic_frame.s_axis),
        yAxis: direction(value.semantic_frame.p_axis),
        zAxis: direction(value.semantic_frame.l_axis),
        valid: true,
      },
      {
        id: "CONNECTED_MEMBER_TO_CLIP_ANGLE_FRAME",
        label: "Connected Member ↔ Clip-Angle Connected Leg frame",
        kind: "INTERFACE_LOCAL",
        ownerId: "CONNECTED_MEMBER_TO_CLIP_ANGLE",
        origin: { x: 0, y: 0, z: 0 },
        xAxis: { x: 0, y: 1, z: 0 },
        yAxis: { x: 0, y: 0, z: 1 },
        zAxis: { x: 1, y: 0, z: 0 },
        valid: true,
      },
      {
        id: "CLIP_ANGLE_TO_SUPPORT_FRAME",
        label: "Clip-Angle Support Leg ↔ Support frame",
        kind: "INTERFACE_LOCAL",
        ownerId: "CLIP_ANGLE_TO_SUPPORT",
        origin: { x: 0, y: 0, z: 0 },
        xAxis: { x: 1, y: 0, z: 0 },
        yAxis: { x: 0, y: 0, z: 1 },
        zAxis: { x: 0, y: -1, z: 0 },
        valid: true,
      },
    ],
    markers: [
      {
        id: "CLIP_ANGLE_GLOBAL_ACTION_REFERENCE",
        label: "Global action reference point",
        kind: "REFERENCE_POINT",
        position: reference,
        connected: null,
        memberEnd: null,
      },
    ],
    positiveArrows: [],
    appliedArrows: appliedArrows(value),
    connectionDemandArrows: [],
    perBoltDemandArrows: [],
    materialAxes: materialAxes(value, sceneBoxes, sceneMeshes),
    zones: zones(value, sceneBoxes),
    connectionOrientation: null,
    boundsCenter: bounds.center,
    boundsRadius: bounds.radius,
    fitCenter: bounds.center,
    fitRadius: bounds.radius,
  };
}
