import { MOUSE, Quaternion, Vector3 } from "three";
import { describe, expect, it, vi } from "vitest";

import {
  beginSelectionGesture,
  cancelSelectionGesture,
  completeSelectionGesture,
  createSelectionGestureState,
  installViewportNavigation,
  projectCameraOrientation,
} from "../src/visualization/viewportNavigation";

describe("Stage 2.3R4 viewport navigation", () => {
  it("distinguishes pointer-up selection from drag without capturing geometry", () => {
    const state = createSelectionGestureState();
    expect(completeSelectionGesture(state, 1, 10, 10)).toBe(false);

    beginSelectionGesture(state, 2, 10, 10);
    expect(completeSelectionGesture(state, 3, 10, 10)).toBe(false);
    cancelSelectionGesture(state);
    expect(completeSelectionGesture(state, 2, 10, 10)).toBe(false);

    beginSelectionGesture(state, 4, 10, 10);
    expect(completeSelectionGesture(state, 4, 14, 10)).toBe(true);

    beginSelectionGesture(state, 5, 10, 10);
    expect(completeSelectionGesture(state, 5, 15, 10)).toBe(false);
  });

  it("projects global axes from the camera quaternion for direct triad mutation", () => {
    expect(projectCameraOrientation(new Quaternion())).toEqual({
      x: [1, -0],
      y: [0, -1],
      z: [0, -0],
    });

    const quarterTurn = new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), Math.PI / 2);
    const projected = projectCameraOrientation(quarterTurn);
    expect(projected.x[0]).toBeCloseTo(0);
    expect(projected.x[1]).toBeCloseTo(1);
    expect(projected.y[0]).toBeCloseTo(1);
    expect(projected.y[1]).toBeCloseTo(0);
    expect(projected.z).toEqual([0, -0]);
  });

  it("mounts one explicit mouse contract and removes its listener exactly once", () => {
    let changeListener: (() => void) | null = null;
    const controls = {
      target: new Vector3(),
      enableDamping: true,
      mouseButtons: { LEFT: MOUSE.PAN, MIDDLE: MOUSE.ROTATE, RIGHT: MOUSE.DOLLY },
      addEventListener: vi.fn((_type: "change", listener: () => void) => {
        changeListener = listener;
      }),
      removeEventListener: vi.fn(),
      update: vi.fn(),
      dispose: vi.fn(),
    };
    const invalidate = vi.fn();
    const onCameraOrientationChange = vi.fn();
    const createControls = vi.fn(() => controls);
    const cleanup = installViewportNavigation({
      cameraQuaternion: new Quaternion(),
      createControls,
      invalidate,
      onCameraOrientationChange,
      target: new Vector3(1, 2, 3),
    });

    expect(createControls).toHaveBeenCalledTimes(1);
    expect(controls.target.toArray()).toEqual([1, 2, 3]);
    expect(controls.enableDamping).toBe(false);
    expect(controls.mouseButtons).toEqual({
      LEFT: MOUSE.ROTATE,
      MIDDLE: MOUSE.DOLLY,
      RIGHT: MOUSE.PAN,
    });
    expect(controls.addEventListener).toHaveBeenCalledWith("change", expect.any(Function));
    expect(controls.update).toHaveBeenCalledTimes(1);
    expect(onCameraOrientationChange).toHaveBeenCalledTimes(1);
    expect(invalidate).toHaveBeenCalledTimes(1);

    expect(changeListener).not.toBeNull();
    (changeListener as unknown as () => void)();
    expect(onCameraOrientationChange).toHaveBeenCalledTimes(2);
    expect(invalidate).toHaveBeenCalledTimes(2);

    cleanup();
    cleanup();
    expect(controls.removeEventListener).toHaveBeenCalledTimes(1);
    expect(controls.dispose).toHaveBeenCalledTimes(1);
  });
});
