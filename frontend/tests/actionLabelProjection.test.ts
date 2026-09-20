import { OrthographicCamera } from "three";
import { describe, expect, it } from "vitest";

import {
  actionLabelPresentationPoint,
  projectActionLabel,
  projectActionLabels,
} from "../src/visualization/actionLabelProjection";
import { actionLabelKey } from "../src/visualization/actionLabelContract";
import type { SceneArrow } from "../src/visualization/sceneModel";
import { buildSingleBoltSceneModel } from "../src/visualization/sceneModel";
import { visualizationFixture } from "./fixtures";

function arrow(overrides: Partial<SceneArrow> = {}): SceneArrow {
  return {
    id: "action:FX",
    component: "FX",
    kind: "LINEAR",
    origin: { x: 1, y: 2, z: 3 },
    axis: { x: 1, y: 0, z: 0 },
    signedValue: 1,
    unit: "kip",
    sense: "POSITIVE",
    isZero: false,
    referencePointId: "action-reference",
    frameId: "MEMBER_LOCAL:member-a",
    axialLoadingSense: "TENSION",
    ...overrides,
  };
}

function camera(): OrthographicCamera {
  const value = new OrthographicCamera(-2, 2, 2, -2, 0.1, 100);
  value.position.set(0, 0, 10);
  value.lookAt(0, 0, 0);
  value.updateProjectionMatrix();
  value.updateMatrixWorld();
  return value;
}

describe("Stage 2.3R7 action-label projection", () => {
  it("derives force and moment presentation points only from their rendered primitives", () => {
    expect(actionLabelKey("APPLIED", "FX")).toBe("APPLIED:FX");
    expect(actionLabelKey("POSITIVE", "MZ")).toBe("POSITIVE:MZ");
    expect(actionLabelKey("APPLIED", "FX", "UPPER:member-end:FX")).toBe(
      "APPLIED:FX:UPPER:member-end:FX",
    );
    expect(actionLabelPresentationPoint(arrow(), 10, "APPLIED")).toEqual({
      x: 5.29,
      y: 2,
      z: 3,
    });
    expect(actionLabelPresentationPoint(arrow(), 10, "POSITIVE")).toEqual({
      x: 4.51,
      y: 2,
      z: 3,
    });

    const momentPoint = actionLabelPresentationPoint(
      arrow({ kind: "ROTATIONAL", component: "MZ", axis: { x: 0, y: 0, z: 1 } }),
      10,
      "APPLIED",
    );
    expect(momentPoint.x).toBeCloseTo(-1.058225, 5);
    expect(momentPoint.y).toBeCloseTo(0.951286, 5);
    expect(momentPoint.z).toBe(3);
  });

  it("projects labels into screen space with deterministic component offsets", () => {
    const projected = projectActionLabel(
      arrow({ origin: { x: 0, y: 0, z: 0 } }),
      1,
      "APPLIED",
      camera(),
      100,
      100,
    );
    expect(projected).toMatchObject({
      key: "APPLIED:FX:action:FX",
      component: "FX",
      kind: "LINEAR",
      source: "APPLIED",
      visible: true,
    });
    expect(projected.x).toBeCloseTo(74.725);
    expect(projected.y).toBeCloseTo(30);

    const behindCamera = projectActionLabel(
      arrow({ origin: { x: 0, y: 0, z: 20 } }),
      1,
      "POSITIVE",
      camera(),
      100,
      100,
    );
    expect(behindCamera.visible).toBe(false);

    const outsideViewport = projectActionLabel(
      arrow({ origin: { x: 20, y: 0, z: 0 } }),
      1,
      "POSITIVE",
      camera(),
      100,
      100,
    );
    expect(outsideViewport.visible).toBe(false);
  });

  it("projects all six force and moment components without changing their identities", () => {
    const model = buildSingleBoltSceneModel(visualizationFixture());
    const projected = projectActionLabels(
      model.positiveArrows,
      model.boundsRadius,
      "POSITIVE",
      camera(),
      640,
      480,
    );
    expect(projected.map((value) => value.key)).toEqual(
      model.positiveArrows.map((value) => actionLabelKey("POSITIVE", value.component, value.id)),
    );
    expect(projected.map((value) => value.kind)).toEqual([
      "LINEAR",
      "LINEAR",
      "LINEAR",
      "ROTATIONAL",
      "ROTATIONAL",
      "ROTATIONAL",
    ]);
    expect(new Set(projected.map((value) => `${String(value.x)},${String(value.y)}`)).size).toBe(6);
  });
});
