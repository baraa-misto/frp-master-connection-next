import { expect, it } from "vitest";
import { buildHybridScene } from "../src/visualization/hybridSceneModel";
import type { HybridResponse } from "../src/api/hybridWorkflow";
import type { SingleBoltSceneModel } from "../src/visualization/sceneModel";
import source from "./fixtures/hybridSourceMaterialAxes.json";
import specimens from "./fixtures/hybridLivePresentations.json";

it("embeds all five trusted source material regions on their actual owned physical elements", () => {
  const response = { ...specimens.source, scene: source } as unknown as HybridResponse;
  const model = buildHybridScene(response);
  expect(model?.materialAxes).toHaveLength(5);
  for (const axes of model?.materialAxes ?? []) {
    expect(axes.presentation).not.toBeNull();
    const owned = [...source.boxes, ...source.meshes].filter((p) => p.ownerId === axes.componentId && p.elementId === axes.elementId && p.materialRegionId === axes.materialRegionId).map((p) => p.id).sort();
    expect(axes.presentation?.primitiveIds).toEqual(owned);
    expect(axes.presentation?.lengthwiseLength).toBeGreaterThan(0);
    expect(axes.presentation?.crosswiseLength).toBeGreaterThan(0);
  }
  // Viewer presentation adds no axes or engineering values to the source object.
  expect((source as unknown as SingleBoltSceneModel).materialAxes.every((axes) => axes.presentation === null)).toBe(true);
});

it("retains native canonical axes and never uses them as a fallback on a source scene", () => {
  const response = specimens.native as unknown as HybridResponse;
  const native = buildHybridScene(response);
  expect(native?.materialAxes.length).toBeGreaterThanOrEqual(5);
  expect(buildHybridScene({ ...response, scene: source as unknown as SingleBoltSceneModel })?.materialAxes).toHaveLength(5);
  expect(buildHybridScene(null)).toBeNull();
  expect(buildHybridScene({ scene: null, native_geometry: null } as HybridResponse)).toBeNull();
  expect(buildHybridScene({} as HybridResponse)).toBeNull();
});
