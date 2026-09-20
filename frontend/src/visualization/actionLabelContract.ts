import type { SceneArrow } from "./sceneModel";

export type ActionLabelSource = "APPLIED" | "POSITIVE";

export interface ProjectedActionLabel {
  readonly key: string;
  readonly component: SceneArrow["component"];
  readonly kind: SceneArrow["kind"];
  readonly source: ActionLabelSource;
  readonly x: number;
  readonly y: number;
  readonly visible: boolean;
}

export function actionLabelKey(
  source: ActionLabelSource,
  component: SceneArrow["component"],
  arrowId?: string,
): string {
  return arrowId === undefined ? `${source}:${component}` : `${source}:${component}:${arrowId}`;
}
