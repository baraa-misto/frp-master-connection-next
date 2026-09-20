import type { MultiMemberTeeVisualization } from "../api/multiMemberTeeContracts";
import {
  buildTeeSceneModel,
  calculatePresentationBounds,
  type SceneArrow,
  type SceneBox,
  type SceneCylinder,
  type SceneFrame,
  type SceneMarker,
  type SceneMaterialAxes,
  type SceneTriangleMesh,
  type SceneZone,
  type SingleBoltSceneModel,
} from "./sceneModel";

function label(slotId: string, family: string): string {
  const semantic = { UPPER_BRACE: "Upper Member", MIDDLE_BEAM: "Middle Member (horizontal)", LOWER_BRACE: "Lower Member" }[slotId] ?? slotId;
  return `${semantic} · ${family.replaceAll("_", " ")}`;
}

interface SlotParts {
  boxes: SceneBox[];
  meshes: SceneTriangleMesh[];
  cylinders: SceneCylinder[];
  frames: SceneFrame[];
  markers: SceneMarker[];
  arrows: SceneArrow[];
  materialAxes: SceneMaterialAxes[];
  zones: SceneZone[];
}

export function collectTriangleMeshPoints(
  meshes: readonly SceneTriangleMesh[],
): SceneTriangleMesh["points"][number][] {
  return meshes.flatMap((item) => item.points);
}

function slotParts(slot: MultiMemberTeeVisualization["slots"][number], model: SingleBoltSceneModel): SlotParts {
  const prefix = slot.slot_id;
  const connectedRole: SceneBox["ownerRole"] = prefix === "MIDDLE_BEAM" ? "OTHER" : "BRACE";
  const sourceMember = slot.visualization.connected_member_profile.member_id;
  const slotLabel = label(prefix, slot.visualization.connected_member_profile.profile_family);
  const interfaceId = slot.visualization.base_connection.interface_id;
  const belongs = (ownerId: string | null) => ownerId === sourceMember || ownerId === interfaceId;
  const rename = (value: string) => value === sourceMember ? slot.connected_member_id : `${prefix}:${value}`;
  return {
    boxes: model.boxes.filter((item) => item.ownerId === sourceMember).map((item) => ({ ...item, id: `${prefix}:${item.id}`, ownerId: slot.connected_member_id, ownerLabel: slotLabel, ownerRole: connectedRole })),
    /* v8 ignore next -- current exact standard profiles are box primitives; triangle meshes remain transport-safe */
    meshes: model.meshes.filter((item) => item.ownerId === sourceMember).map((item) => ({ ...item, id: `${prefix}:${item.id}`, ownerId: slot.connected_member_id, ownerLabel: slotLabel, ownerRole: connectedRole })),
    cylinders: model.cylinders.filter((item) => item.interfaceId === interfaceId).map((item) => ({ ...item, id: `${prefix}:${item.id}`, ownerBoltId: `${prefix}:${item.ownerBoltId}`, interfaceId: slot.bolt_group_id })),
    frames: model.frames.filter((item) => belongs(item.ownerId)).map((item) => ({ ...item, id: `${prefix}:${item.id}`, ownerId: rename(String(item.ownerId)), label: `${slotLabel} · ${item.label}` })),
    markers: model.markers.filter((item) => item.id.includes(sourceMember) || item.id.startsWith("A_")).map((item) => ({ ...item, id: `${prefix}:${item.id}`, label: `${slotLabel} · ${item.label}` })),
    arrows: [...model.appliedArrows, ...model.connectionDemandArrows].map((item) => ({ ...item, id: `${prefix}:${item.id}`, referencePointId: `${prefix}:${item.referencePointId}`, frameId: `${prefix}:${item.frameId}` })),
    materialAxes: model.materialAxes.filter((item) => item.componentId === sourceMember).map((item) => ({ ...item, id: `${prefix}:${item.id}`, componentId: slot.connected_member_id, componentLabel: slotLabel })),
    zones: model.zones.filter((item) => [item.interfaceId === interfaceId, item.participantId === sourceMember].includes(true)).map((item) => ({ ...item, id: `${prefix}:${item.id}`, participantId: item.participantId === sourceMember ? slot.connected_member_id : item.participantId, interfaceId: slot.bolt_group_id, label: `${slotLabel} · ${item.label}` })),
  };
}

export function buildMultiMemberTeeSceneModel(snapshot: MultiMemberTeeVisualization): SingleBoltSceneModel {
  const first = snapshot.slots[0];
  if (first === undefined) throw new Error("Multi-Member Tee visualization requires an active slot.");
  const modeled = snapshot.slots.map((slot) => ({ slot, model: buildTeeSceneModel(slot.visualization) }));
  const firstModel = modeled[0]?.model;
  /* v8 ignore next -- a present first mapped slot necessarily has a mapped model */
  if (firstModel === undefined) throw new Error("Multi-Member Tee visualization requires a current scene.");
  const sourceMember = first.visualization.connected_member_profile.member_id;
  const interfaceA = first.visualization.base_connection.interface_id;
  const common: SlotParts = {
    boxes: firstModel.boxes.filter((item) => item.ownerId !== sourceMember),
    /* v8 ignore next -- current exact standard profiles are box primitives; triangle meshes remain transport-safe */
    meshes: firstModel.meshes.filter((item) => item.ownerId !== sourceMember),
    cylinders: firstModel.cylinders.filter((item) => item.interfaceId !== interfaceA),
    frames: firstModel.frames.filter((item) => item.ownerId !== sourceMember && item.ownerId !== interfaceA),
    markers: firstModel.markers.filter((item) => !item.id.includes(sourceMember) && !item.id.startsWith("A_")),
    arrows: [],
    materialAxes: firstModel.materialAxes.filter((item) => item.componentId !== sourceMember),
    zones: firstModel.zones.filter((item) => ![item.interfaceId === interfaceA, item.participantId === sourceMember].includes(true)),
  };
  const parts = modeled.map(({ slot, model }) => slotParts(slot, model));
  const boxes = [...common.boxes, ...parts.flatMap((item) => item.boxes)];
  const meshes = [...common.meshes, ...parts.flatMap((item) => item.meshes)];
  const cylinders = [...common.cylinders, ...parts.flatMap((item) => item.cylinders)];
  const markers = [...common.markers, ...parts.flatMap((item) => item.markers)];
  const zones = [...common.zones, ...parts.flatMap((item) => item.zones)];
  const points = [
    ...boxes.map((item) => item.center),
    ...collectTriangleMeshPoints(meshes),
    ...cylinders.flatMap((item) => [item.start, item.end]), ...markers.map((item) => item.position),
    ...zones.flatMap((item) => item.corners),
  ];
  const bounds = calculatePresentationBounds(points);
  return {
    ...firstModel,
    boxes,
    meshes,
    cylinders,
    frames: [...common.frames, ...parts.flatMap((item) => item.frames)],
    markers,
    appliedArrows: parts.flatMap((item) => item.arrows),
    connectionDemandArrows: [],
    perBoltDemandArrows: [],
    materialAxes: [...common.materialAxes, ...parts.flatMap((item) => item.materialAxes)],
    zones,
    boundsCenter: bounds.center,
    boundsRadius: bounds.radius,
    fitCenter: bounds.center,
    fitRadius: bounds.radius,
  };
}
