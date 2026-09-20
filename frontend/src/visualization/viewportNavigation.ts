import { MOUSE, Quaternion, Vector3 } from "three";

import type { CameraOrientation2D } from "./EngineeringScene";

export const SELECTION_DRAG_THRESHOLD_PX = 4;

export interface SelectionGestureState {
  active: boolean;
  pointerId: number;
  startX: number;
  startY: number;
}

interface NavigationControlsLike {
  readonly target: Vector3;
  enableDamping: boolean;
  readonly mouseButtons: {
    LEFT?: MOUSE | null | undefined;
    MIDDLE?: MOUSE | null | undefined;
    RIGHT?: MOUSE | null | undefined;
  };
  addEventListener(type: "change", listener: () => void): void;
  removeEventListener(type: "change", listener: () => void): void;
  update(): void;
  dispose(): void;
}

interface InstallViewportNavigationOptions {
  readonly cameraQuaternion: Quaternion;
  readonly createControls: () => NavigationControlsLike;
  readonly invalidate: () => void;
  readonly onCameraOrientationChange: (orientation: CameraOrientation2D) => void;
  readonly target: Vector3;
}

export function createSelectionGestureState(): SelectionGestureState {
  return { active: false, pointerId: -1, startX: 0, startY: 0 };
}

export function beginSelectionGesture(
  state: SelectionGestureState,
  pointerId: number,
  clientX: number,
  clientY: number,
): void {
  state.active = true;
  state.pointerId = pointerId;
  state.startX = clientX;
  state.startY = clientY;
}

export function completeSelectionGesture(
  state: SelectionGestureState,
  pointerId: number,
  clientX: number,
  clientY: number,
): boolean {
  if (!state.active || state.pointerId !== pointerId) return false;
  state.active = false;
  return Math.hypot(clientX - state.startX, clientY - state.startY) <= SELECTION_DRAG_THRESHOLD_PX;
}

export function cancelSelectionGesture(state: SelectionGestureState): void {
  state.active = false;
}

export function projectCameraOrientation(quaternion: Quaternion): CameraOrientation2D {
  const inverse = quaternion.clone().invert();
  const project = (axis: Vector3): readonly [number, number] => {
    const cameraAxis = axis.applyQuaternion(inverse);
    return [cameraAxis.x, -cameraAxis.y];
  };
  return {
    x: project(new Vector3(1, 0, 0)),
    y: project(new Vector3(0, 1, 0)),
    z: project(new Vector3(0, 0, 1)),
  };
}

export function installViewportNavigation({
  cameraQuaternion,
  createControls,
  invalidate,
  onCameraOrientationChange,
  target,
}: InstallViewportNavigationOptions): () => void {
  const controls = createControls();
  controls.target.copy(target);
  controls.enableDamping = false;
  controls.mouseButtons.LEFT = MOUSE.ROTATE;
  controls.mouseButtons.MIDDLE = MOUSE.DOLLY;
  controls.mouseButtons.RIGHT = MOUSE.PAN;

  const handleChange = () => {
    onCameraOrientationChange(projectCameraOrientation(cameraQuaternion));
    invalidate();
  };
  controls.addEventListener("change", handleChange);
  controls.update();
  handleChange();

  let disposed = false;
  return () => {
    if (disposed) return;
    disposed = true;
    controls.removeEventListener("change", handleChange);
    controls.dispose();
  };
}
