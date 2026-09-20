import type {
  PairedClipAngleVisualization,
} from "../api/pairedClipAngleContracts";
import { buildClipAngleSceneModel } from "./clipAngleSceneModel";
import type { SceneBox, SceneZone, SingleBoltSceneModel } from "./sceneModel";

function contactZone(
  box: SceneBox,
  interfaceId: string,
  side: string,
  normal: { readonly x: number; readonly y: number; readonly z: number },
  patchId: string,
): SceneZone {
  const halfX = box.size.x / 2;
  const halfY = box.size.y / 2;
  const halfZ = box.size.z / 2;
  const x = box.center.x - normal.x * halfX;
  const y = box.center.y - normal.y * halfY;
  return {
    id: `${interfaceId}:${box.id}:CONTACT`,
    label: `${box.ownerLabel} · ${box.label}`,
    side,
    participantId: box.ownerId,
    interfaceId,
    patchId,
    normal,
    selectedContact: true,
    corners: Math.abs(normal.x) === 1
      ? [
          { x, y: box.center.y - halfY, z: box.center.z - halfZ },
          { x, y: box.center.y + halfY, z: box.center.z - halfZ },
          { x, y: box.center.y + halfY, z: box.center.z + halfZ },
          { x, y: box.center.y - halfY, z: box.center.z + halfZ },
        ]
      : [
          { x: box.center.x - halfX, y, z: box.center.z - halfZ },
          { x: box.center.x + halfX, y, z: box.center.z - halfZ },
          { x: box.center.x + halfX, y, z: box.center.z + halfZ },
          { x: box.center.x - halfX, y, z: box.center.z + halfZ },
        ],
  };
}

/** Adapt one backend-authored physical pair into the accepted shared engineering renderer. */
export function buildPairedClipAngleSceneModel(
  value: PairedClipAngleVisualization,
): SingleBoltSceneModel {
  const base = buildClipAngleSceneModel({
    ...value,
    connected_member_role: "BRACE",
    connected_member_profile_orientation: "ROTATION_0",
    interface_a_bolts: value.common_member_bolts,
    interface_b_bolts: [...value.positive_support_bolts, ...value.negative_support_bolts],
    global_force: value.parent_force,
    global_moment: value.parent_moment,
    global_reference_point: value.parent_reference_point,
    support_target_id: value.support_target_id,
    support_material_regions: value.support_material_regions,
    rectangular_full_through_paths: value.rectangular_full_through_paths,
  });
  const boxes = base.boxes.map((box) => ({
    ...box,
    ownerLabel: box.ownerId === "POSITIVE_CLIP_ANGLE"
      ? "Positive FRP Clip Angle"
      : box.ownerId === "NEGATIVE_CLIP_ANGLE"
        ? "Negative FRP Clip Angle"
        : box.ownerLabel,
  }));
  const connectorBoxes = boxes.filter(
    (box) => box.ownerId === "POSITIVE_CLIP_ANGLE" || box.ownerId === "NEGATIVE_CLIP_ANGLE",
  );
  const zones = connectorBoxes.map((box) => {
    const positive = box.ownerId === "POSITIVE_CLIP_ANGLE";
    const memberLeg = box.label === "CONNECTED MEMBER LEG";
    return contactZone(
      box,
      memberLeg
        ? "COMMON_MEMBER_THROUGH_BOLT_GROUP"
        : positive ? "POSITIVE_SUPPORT_BOLT_GROUP" : "NEGATIVE_SUPPORT_BOLT_GROUP",
      memberLeg ? "CONNECTED_LEG_EXTERIOR" : "SUPPORT_LEG_EXTERIOR",
      memberLeg
        ? { x: positive ? -1 : 1, y: 0, z: 0 }
        : { x: 0, y: -1, z: 0 },
      memberLeg ? value.selected_connected_surface_id : value.selected_support_surface_id,
    );
  });
  const cylinders = base.cylinders.map((cylinder) => {
    const group = cylinder.ownerBoltId.includes("POS-SUPPORT")
      ? "POSITIVE_SUPPORT_BOLT_GROUP"
      : cylinder.ownerBoltId.includes("NEG-SUPPORT")
        ? "NEGATIVE_SUPPORT_BOLT_GROUP"
        : "COMMON_MEMBER_THROUGH_BOLT_GROUP";
    return {
      ...cylinder,
      interfaceId: group,
      ownerBoltId: `${group}:${cylinder.ownerBoltId.split(":").slice(-1).join("")}`,
    };
  });
  const pairFrame = base.frames[0];
  /* v8 ignore next -- the accepted clip-angle adapter always emits its semantic frame */
  if (pairFrame === undefined) throw new Error("Paired clip-angle semantic frame is unavailable.");
  return {
    ...base,
    boxes,
    cylinders,
    frames: [
      {
        ...pairFrame,
        id: "PAIRED_CLIP_ANGLE_FRAME",
        label: "Paired clip-angle S/P/L frame · symmetry plane S = 0",
        ownerId: "SYMMETRIC_PAIRED_CLIP_ANGLES",
      },
      ...base.frames.slice(1),
    ],
    zones,
  };
}
