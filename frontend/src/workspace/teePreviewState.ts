import type { TeePreviewResult } from "../api/teeContracts";
import type { SceneSelection } from "../visualization/EngineeringScene";
import type { SingleBoltSceneModel } from "../visualization/sceneModel";
import type { TeePreviewDisplayState } from "./teeWorkflow";

export function teeSelectionExists(
  model: SingleBoltSceneModel,
  selection: SceneSelection,
): boolean {
  return selection.kind === "MEMBER"
    ? ["tee-brace", "tee-support", "tee-connector"].includes(selection.id)
      || model.boxes.some((box) => box.ownerId === selection.id)
    : selection.kind === "BOLT"
      ? model.cylinders.some((cylinder) => cylinder.ownerBoltId === selection.id)
      : model.zones.some((zone) => zone.patchId === selection.id);
}

export function teeDesignBlocker(
  localValidation: string | null,
  previewState: TeePreviewDisplayState,
  currentPreview: TeePreviewResult | null,
): string | null {
  if (localValidation !== null) return localValidation;
  if (previewState !== "CURRENT_VALID") return "Awaiting current backend preview.";
  if (currentPreview === null) return "A current backend Tee preview is required.";
  if (!currentPreview.design_check_ready) {
    return "The backend has not marked both interfaces design-ready.";
  }
  return null;
}
