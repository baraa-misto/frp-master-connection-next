import { expect, it } from "vitest";
import type { DCTNArrangement, DCTNResponse } from "../src/api/dctnContracts";
import { buildDCTNScene } from "../src/visualization/dctnSceneModel";
import fixture from "./dctnNativeFixtures.json";

const data = fixture as unknown as {
  arrangements: Record<DCTNArrangement, { preview: DCTNResponse }>;
};
const arrangements = Object.keys(data.arrangements) as DCTNArrangement[];

it.each(arrangements)("renders corrected native axes, actions and Y shafts for %s", arrangement => {
  const p = data.arrangements[arrangement].preview.result.preview;
  const scene = buildDCTNScene(p);
  expect(p.geometry.status).toBe("VALID");
  expect(scene.frames.filter(f => f.ownerId?.startsWith("CHORD")).every(f => f.xAxis.x === 1 && f.origin.z === 0)).toBe(true);
  for (const frame of scene.frames.filter(f => !f.ownerId?.startsWith("CHORD"))) {
    expect(frame.origin.y).toBe(0);
    expect(frame.xAxis.y).toBe(0);
    expect(frame.zAxis).toEqual({x: 0, y: 1, z: 0});
  }
  for (const cylinder of scene.cylinders) {
    expect(cylinder.start.x).toBe(cylinder.end.x);
    expect(cylinder.start.z).toBe(cylinder.end.z);
    expect(cylinder.start.y).not.toBe(cylinder.end.y);
  }
  for (const arrow of scene.appliedArrows) {
    const frame = scene.frames.find(f => f.ownerId === arrow.id.split(":")[0]);
    expect(arrow.axis).toEqual(frame?.xAxis);
    expect(arrow.axis.y).toBe(0);
    if (arrow.id.startsWith("V:")) {
      expect(arrow.component).toBe("FZ");
      expect(arrow.frameId).toBe("GLOBAL");
      expect(arrow.componentLabel).toBe("Fz (global +Z)");
      expect(arrow.axis).toEqual({x: 0, y: 0, z: 1});
    } else {
      expect(arrow.frameId).toBe(frame?.id);
      expect(arrow.componentLabel).toContain("derived member axis in X-Z");
      expect(arrow.axis.z).toBeGreaterThan(0);
    }
  }
});
