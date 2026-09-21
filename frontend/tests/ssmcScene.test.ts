import { assert, expect, it } from "vitest";
import type { SSMCResponse } from "../src/api/ssmcClient";
import { buildSSMCScene } from "../src/visualization/ssmcScene";
import fixture from "./ssmcNativeFixtures.json";

const data = fixture as unknown as { us: { response: SSMCResponse }; si: { response: SSMCResponse } };
it.each(["us", "si"] as const)("renders native actual polygon and independent hardware in %s", units => {
  const p = data[units].response.result;
  const scene = buildSSMCScene(p, true);
  expect(scene.meshes.filter(m => m.ownerId === "MITER_WEB_PLATE")).toHaveLength(1);
  expect(scene.cylinders.filter(c => c.kind === "BOLT")).toHaveLength(8);
  expect(scene.cylinders.filter(c => c.kind === "WASHER")).toHaveLength(16);
  expect(new Set(scene.cylinders.filter(c => c.kind === "BOLT").map(c => c.id)).size).toBe(8);
  expect(scene.materialAxes).toEqual([]); // Unknown cut must not invent plate LW.
  expect(scene.boundsRadius).toBeGreaterThan(0);
  expect(buildSSMCScene(p, false).appliedArrows).toEqual([]);
});
it.each([-1, 1])("preserves all local N/V/M arrow signs %s and hides stale actions", sign => {
  const p = structuredClone(data.us.response.result);
  p.input.N.value = String(sign * 8); p.input.V.value = String(sign * 4); p.input.M.value = String(sign * 20);
  const scene = buildSSMCScene(p, true), u = p.geometry.members[1]?.material_longitudinal;
  assert(u);
  expect(scene.appliedArrows.map(a => a.componentLabel)).toEqual(["N", "V", "M"]);
  expect(scene.appliedArrows[0]?.axis).toEqual({ x: sign * u.x, y: sign * u.y, z: sign * u.z });
  expect(scene.appliedArrows[1]?.axis).toEqual({ x: -sign * u.z, y: 0 * sign, z: sign * u.x });
  expect(scene.appliedArrows[2]?.axis.y).toBe(-sign);
  expect(scene.appliedArrows[0]?.axialLoadingSense).toBe(sign < 0 ? "COMPRESSION" : "TENSION");
  expect(buildSSMCScene(p, false).appliedArrows).toEqual([]);
});
it("does not draw zero actions and rejects missing member authority", () => {
  const p = structuredClone(data.us.response.result);
  p.input.N.value = "0"; p.input.V.value = "0"; p.input.M.value = "0";
  expect(buildSSMCScene(p, true).appliedArrows).toEqual([]);
  p.geometry.members.pop(); expect(() => buildSSMCScene(p, true)).toThrow("inclined member");
});
it("rejects a sparse native face instead of inventing a polygon vertex", () => {
  const p = structuredClone(data.us.response.result), face = p.geometry.members[0]?.trimmed.solids[0]?.faces[0];
  assert(face); Object.defineProperty(face.vertices, "0", { value: undefined });
  expect(() => buildSSMCScene(p, true)).toThrow("native face is incomplete");
});
