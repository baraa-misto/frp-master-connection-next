import { describe, expect, it } from "vitest";

import { buildFastenerPresentations } from "../src/visualization/fastenerPresentation";
import { buildBeamConcretePairedAngleSceneModel } from "../src/visualization/beamConcretePairedAngleSceneModel";
import { beamConcretePreviewFixture } from "./beamConcretePairedAngleFixtures";

describe("Stage 3.5A backend-authored physical scene adapter", () => {
  it("renders wall, W/I beam, mirrored angles, common bolts, blind anchors, frames, and material axes", () => {
    const visualization = beamConcretePreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Controlled visualization required.");
    const model = buildBeamConcretePairedAngleSceneModel(visualization);
    expect(model.boxes.some((item) => item.ownerId === "concrete-wall")).toBe(true);
    expect(model.boxes.some((item) => item.ownerId === "clip-angle-connected-member")).toBe(true);
    expect(model.boxes.some((item) => item.ownerId === "POSITIVE_CLIP_ANGLE")).toBe(true);
    expect(model.boxes.some((item) => item.ownerId === "NEGATIVE_CLIP_ANGLE")).toBe(true);
    expect(model.frames[0]?.label).toContain("H_W / V_W / N_W");
    expect(model.markers.map((item) => item.id)).toEqual(["BEAM_GROUP_REFERENCE", "WALL_REFERENCE"]);
    expect(model.appliedArrows.map((item) => [item.component, item.signedValue, item.unit])).toEqual([
      ["FX", 0, "kip"],
      ["FZ", -4, "kip"],
      ["FY", 0, "kip"],
    ]);
    expect(model.zones[0]).toMatchObject({ patchId: "CONCRETE_WALL:EXTERIOR_FACE", selectedContact: true });
    expect(model.materialAxes.every((item) => item.componentId !== "concrete-wall")).toBe(true);
    expect(model.boundsRadius).toBeGreaterThan(model.fitRadius);
  });

  it("uses one exterior nut/washer and no far-wall hardware for every external anchor", () => {
    const visualization = beamConcretePreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Controlled visualization required.");
    const model = buildBeamConcretePairedAngleSceneModel(visualization);
    const anchors = buildFastenerPresentations(model.cylinders).filter((item) => item.shank.hardwareConfiguration === "EXTERIOR_NUT_WASHER_ANCHOR");
    expect(anchors).toHaveLength(2);
    expect(anchors.every((item) => item.washers.length === 1)).toBe(true);
    expect(anchors.every((item) => item.renderedHardware.length === 1 && item.renderedHardware[0]?.kind === "NUT")).toBe(true);
    expect(anchors.every((item) => item.shank.end.y > item.shank.start.y)).toBe(true);
  });

  it("keeps every reflected backend box renderable with a right-handed basis", () => {
    const visualization = beamConcretePreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Controlled visualization required.");
    const model = buildBeamConcretePairedAngleSceneModel(visualization);
    for (const box of model.boxes) {
      const [first, second, third] = box.basis;
      const determinant = first.x * (second.y * third.z - second.z * third.y)
        - first.y * (second.x * third.z - second.z * third.x)
        + first.z * (second.x * third.y - second.y * third.x);
      expect(determinant).toBeCloseTo(1, 12);
    }
    expect(model.boxes.filter((item) => item.ownerId === "POSITIVE_CLIP_ANGLE")).toHaveLength(2);
    expect(model.boxes.filter((item) => item.ownerId === "NEGATIVE_CLIP_ANGLE")).toHaveLength(2);
  });

  it("fails closed on non-finite serialized quantities", () => {
    const visualization = structuredClone(beamConcretePreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    visualization.common_bolt_diameter.value = "not-a-number";
    expect(() => buildBeamConcretePairedAngleSceneModel(visualization)).toThrow("finite quantities");
  });

  it("maps optional meshes, missing presentation anchors, wall absence, SI, and all reaction senses", () => {
    const visualization = structuredClone(beamConcretePreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    const beamBox = visualization.boxes.find((item) => item.owner_id === "clip-angle-connected-member");
    if (beamBox === undefined) throw new Error("Controlled beam box required.");
    const mesh = {
      id: "beam-mesh", role: "WEB_MESH", owner_id: "clip-angle-connected-member",
      physical_element_id: "beam:WEB", material_region_id: "beam:WEB_REGION",
      points: [beamBox.center, beamBox.center, beamBox.center],
    };
    const firstRegion = visualization.material_regions[0];
    if (firstRegion === undefined) throw new Error("Controlled connector region required.");
    if (visualization.user_force_hvn === undefined) throw new Error("Controlled R2 user force required.");
    const modified = {
      ...visualization,
      meshes: [...visualization.meshes, mesh],
      material_regions: [{ ...firstRegion, physical_element_id: "POSITIVE_UNKNOWN:ELEMENT", region_id: "POSITIVE_UNKNOWN:REGION" }, ...visualization.material_regions.slice(1)],
      boxes: visualization.boxes.filter((item) => item.owner_id !== "concrete-wall"),
      common_bolt_diameter: { ...visualization.common_bolt_diameter, unit: "mm" as const },
      user_force_hvn: { ...visualization.user_force_hvn, h: { ...visualization.user_force_hvn.h, value: "4" } },
    };
    let model = buildBeamConcretePairedAngleSceneModel(modified);
    expect(model.meshes).toHaveLength(1);
    expect(model.materialAxes[0]?.presentation).toBeNull();
    expect(model.materialAxes[0]?.origin).toEqual({ x: 0, y: 0, z: 0 });
    expect(model.zones).toEqual([]);
    expect(model.unitSystem).toBe("SI");
    expect(model.appliedArrows[0]?.sense).toBe("POSITIVE");
    model = buildBeamConcretePairedAngleSceneModel({ ...modified, user_force_hvn: { ...modified.user_force_hvn, h: { ...modified.user_force_hvn.h, value: "0" } } });
    expect(model.appliedArrows[0]).toMatchObject({ sense: "ZERO", isZero: true });
  });

  it("preserves historical reaction arrows and all R2 axial loading senses", () => {
    const visualization = structuredClone(beamConcretePreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    const historical = structuredClone(visualization);
    delete historical.user_force_hvn;
    for (const [value, sense] of [["-4", "NEGATIVE"], ["4", "POSITIVE"], ["0", "ZERO"]] as const) {
      const model = buildBeamConcretePairedAngleSceneModel({
        ...historical,
        reaction_shear: { ...historical.reaction_shear, value },
      });
      expect(model.appliedArrows).toHaveLength(1);
      expect(model.appliedArrows[0]).toMatchObject({ component: "FZ", sense });
    }
    if (visualization.user_force_hvn === undefined) throw new Error("Controlled R2 force required.");
    for (const [value, loadingSense] of [["4", "TENSION"], ["-4", "COMPRESSION"]] as const) {
      const model = buildBeamConcretePairedAngleSceneModel({
        ...visualization,
        user_force_hvn: {
          ...visualization.user_force_hvn,
          n: { ...visualization.user_force_hvn.n, value },
        },
      });
      expect(model.appliedArrows.find((item) => item.component === "FY")?.axialLoadingSense).toBe(loadingSense);
    }
  });
});
