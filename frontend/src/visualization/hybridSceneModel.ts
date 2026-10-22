import type { HybridResponse } from "../api/hybridWorkflow";
import { buildRegionEmbeddedMaterialAxisPresentation } from "./materialAxisPresentation";
import { buildMultiRowSceneModel } from "./sceneModel";
import type { SingleBoltSceneModel } from "./sceneModel";

/** Display backend-authored regions with the shared presentation convention. */
export function buildHybridScene(response: HybridResponse | null): SingleBoltSceneModel | null {
  const scene = response?.scene;
  if (scene !== null && scene !== undefined) return { ...scene, materialAxes: scene.materialAxes.map((axes) => ({ ...axes, presentation: buildRegionEmbeddedMaterialAxisPresentation(axes, scene.boxes, scene.meshes) })) };
  const native = response?.native_geometry;
  return native === null || native === undefined ? null : buildMultiRowSceneModel(native.visualization, native.direct_support_end_authority);
}
