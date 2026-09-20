import type { Camera } from "three";
import { Quaternion, Vector3 } from "three";

import type { ActionLabelSource, ProjectedActionLabel } from "./actionLabelContract";
import { actionLabelKey } from "./actionLabelContract";
import {
  MOMENT_LABEL_ANGLE_RADIANS,
  calculateMomentArrowGeometry,
} from "./actionPrimitiveGeometry";
import type { SceneArrow, Vec3 } from "./sceneModel";

const SCREEN_OFFSETS: Readonly<
  Record<ActionLabelSource, Record<SceneArrow["component"], readonly [number, number]>>
> = {
  APPLIED: {
    FX: [14, -20],
    FY: [14, 0],
    FZ: [14, 20],
    MX: [-16, -22],
    MY: [-16, 0],
    MZ: [-16, 22],
  },
  POSITIVE: {
    FX: [10, -32],
    FY: [10, -12],
    FZ: [10, 8],
    MX: [-12, -34],
    MY: [-12, -12],
    MZ: [-12, 10],
  },
};

function vector(value: Vec3): Vector3 {
  return new Vector3(value.x, value.y, value.z);
}

export function actionLabelPresentationPoint(
  arrow: SceneArrow,
  boundsRadius: number,
  source: ActionLabelSource,
): Vec3 {
  const origin = vector(arrow.origin);
  const axis = vector(arrow.axis).normalize();
  const arrowLength = boundsRadius * (source === "POSITIVE" ? 0.45 : 0.55);
  if (arrow.kind === "LINEAR") {
    const point = origin.add(axis.multiplyScalar(arrowLength * 0.78));
    return { x: point.x, y: point.y, z: point.z };
  }

  const momentGeometry = calculateMomentArrowGeometry(arrowLength);
  const quaternion = new Quaternion().setFromUnitVectors(new Vector3(0, 0, 1), axis);
  const point = new Vector3(momentGeometry.radius, 0, 0)
    .applyAxisAngle(new Vector3(0, 0, 1), MOMENT_LABEL_ANGLE_RADIANS)
    .applyQuaternion(quaternion)
    .add(origin);
  return { x: point.x, y: point.y, z: point.z };
}

export function projectActionLabel(
  arrow: SceneArrow,
  boundsRadius: number,
  source: ActionLabelSource,
  camera: Camera,
  viewportWidth: number,
  viewportHeight: number,
): ProjectedActionLabel {
  const point = vector(actionLabelPresentationPoint(arrow, boundsRadius, source));
  camera.updateMatrixWorld();
  point.project(camera);
  const [offsetX, offsetY] = SCREEN_OFFSETS[source][arrow.component];
  return {
    key: actionLabelKey(source, arrow.component, arrow.id),
    component: arrow.component,
    kind: arrow.kind,
    source,
    x: ((point.x + 1) * viewportWidth) / 2 + offsetX,
    y: ((1 - point.y) * viewportHeight) / 2 + offsetY,
    visible:
      Math.abs(point.x) <= 1 &&
      Math.abs(point.y) <= 1 &&
      Math.abs(point.z) <= 1,
  };
}

export function projectActionLabels(
  arrows: readonly SceneArrow[],
  boundsRadius: number,
  source: ActionLabelSource,
  camera: Camera,
  viewportWidth: number,
  viewportHeight: number,
): readonly ProjectedActionLabel[] {
  return arrows.map((arrow) =>
    projectActionLabel(
      arrow,
      boundsRadius,
      source,
      camera,
      viewportWidth,
      viewportHeight,
    ),
  );
}
