import { describe, expect, it } from "vitest";

import type { ClipAngleQuantity } from "../src/api/clipAngleContracts";
import { buildFastenerPresentations } from "../src/visualization/fastenerPresentation";
import { buildDirectSideLapConcreteSceneModel } from "../src/visualization/directSideLapConcreteSceneModel";
import { directSideLapPreviewFixture } from "./directSideLapConcreteFixtures";

function q(value: string, unit: string): ClipAngleQuantity {
  return { value, unit, canonical_value: value, canonical_unit: unit };
}

describe("Stage 3.5B backend-authoritative scene adapter", () => {
  it("renders finite wall, continuing Channel, frame, anchors, loads, and region axes", () => {
    const visualization = directSideLapPreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Controlled visualization required.");
    const model = buildDirectSideLapConcreteSceneModel(visualization);
    expect(model.boxes.some((item) => item.ownerId === "direct-side-lap-concrete-wall")).toBe(true);
    expect(model.boxes.filter((item) => item.ownerRole === "BRACE")).toHaveLength(3);
    expect(model.frames[0]?.label).toContain("L / S / N");
    expect(model.markers.map((item) => item.id)).toEqual(["SIDE_LAP_MEMBER_ACTION_REFERENCE", "DIRECT_SIDE_LAP_GROUP_REFERENCE", "WALL_FREE_END"]);
    expect(model.appliedArrows.map((item) => [item.component, item.signedValue, item.axis])).toEqual([
      ["FZ", -4, { x: 0, y: 0, z: -1 }],
    ]);
    expect(model.markers[0]?.position.x).toBe(0);
    expect(model.markers[0]?.position.y).toBeCloseTo(-1.1833333333333333);
    expect(model.markers[0]?.position.z).toBe(0);
    expect(model.materialAxes).toHaveLength(3);
    expect(model.materialAxes.map((item) => [
      item.componentId,
      item.elementId,
      item.materialRegionId,
      item.presentation?.primitiveIds,
    ])).toEqual([
      ["clip-angle-connected-member", "WEB", "WEB", ["MEMBER:clip-angle-connected-member:WEB:0"]],
      ["clip-angle-connected-member", "TOP_FLANGE", "FLANGES", ["MEMBER:clip-angle-connected-member:TOP_FLANGE:0"]],
      ["clip-angle-connected-member", "BOTTOM_FLANGE", "FLANGES", ["MEMBER:clip-angle-connected-member:BOTTOM_FLANGE:0"]],
    ]);
    expect(model.zones[0]).toMatchObject({ patchId: "CONCRETE_WALL:FINITE_EXTERIOR_FACE", selectedContact: true });
    expect(model.boundsRadius).toBeGreaterThan(model.fitRadius);
  });

  it("renders exterior-only blind hardware with no far-side nut or washer", () => {
    const visualization = directSideLapPreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Controlled visualization required.");
    const hardware = buildFastenerPresentations(buildDirectSideLapConcreteSceneModel(visualization).cylinders);
    expect(hardware).toHaveLength(2);
    expect(hardware.every((item) => item.washers.length === 1)).toBe(true);
    expect(hardware.every((item) => item.renderedHardware.length === 1 && item.renderedHardware[0]?.kind === "NUT")).toBe(true);
  });

  it("fails closed on non-finite scene quantities", () => {
    const visualization = structuredClone(directSideLapPreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    visualization.external_anchor_geometry.nominal_diameter.value = "not-a-number";
    expect(() => buildDirectSideLapConcreteSceneModel(visualization)).toThrow("finite");
  });

  it("maps the exact signed force matrix onto backend frame directions and one action origin", () => {
    const visualization = structuredClone(directSideLapPreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    visualization.user_force_lsn.l.value = "5";
    visualization.user_force_lsn.s.value = "-5";
    visualization.user_force_lsn.n.value = "3";
    let model = buildDirectSideLapConcreteSceneModel(visualization);
    expect(model.appliedArrows.map((item) => [item.component, item.axis, item.sense])).toEqual([
      ["FX", { x: 1, y: 0, z: 0 }, "POSITIVE"],
      ["FZ", { x: 0, y: 0, z: -1 }, "NEGATIVE"],
      ["FY", { x: 0, y: -1, z: 0 }, "POSITIVE"],
    ]);
    expect(model.appliedArrows.every((item) => item.origin === model.appliedArrows[0]?.origin)).toBe(true);
    expect(model.appliedArrows[0]).toMatchObject({ axialLoadingSense: "TENSION" });

    visualization.user_force_lsn.l.value = "-5";
    visualization.user_force_lsn.s.value = "5";
    visualization.user_force_lsn.n.value = "-3";
    model = buildDirectSideLapConcreteSceneModel(visualization);
    expect(model.appliedArrows.map((item) => [item.component, item.axis, item.sense])).toEqual([
      ["FX", { x: -1, y: 0, z: 0 }, "NEGATIVE"],
      ["FZ", { x: 0, y: 0, z: 1 }, "POSITIVE"],
      ["FY", { x: 0, y: 1, z: 0 }, "NEGATIVE"],
    ]);
    expect(model.appliedArrows[0]).toMatchObject({ axialLoadingSense: "COMPRESSION" });

    visualization.user_force_lsn.l.value = "0";
    visualization.user_force_lsn.s.value = "0";
    visualization.user_force_lsn.n.value = "0";
    expect(buildDirectSideLapConcreteSceneModel(visualization).appliedArrows).toEqual([]);
  });

  it("binds both Angle material regions by backend owner and preserves every TT record", () => {
    const visualization = structuredClone(directSideLapPreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    Object.assign(visualization, {
      connected_profile_family: "ANGLE" as const,
      selected_profile_surface: "LEG_Y_OUTER" as const,
      boxes: [
        { ...visualization.boxes[0], id: "MEMBER:clip-angle-connected-member:LEG_1:0", role: "LEG_1", physical_element_id: "LEG_1", material_region_id: "LEG_1", size_p: q("0.5", "in"), size_l: q("5.5", "in") },
        { ...visualization.boxes[1], id: "MEMBER:clip-angle-connected-member:LEG_2:0", role: "LEG_2", physical_element_id: "LEG_2", material_region_id: "LEG_2", size_p: q("5.5", "in"), size_l: q("0.5", "in") },
        visualization.boxes[3],
      ],
      material_regions: [
        { ...visualization.material_regions[0], id: "clip-angle-connected-member:LEG_1:material-axes", physical_element_id: "LEG_1", material_region_id: "LEG_1" },
        { ...visualization.material_regions[1], id: "clip-angle-connected-member:LEG_2:material-axes", physical_element_id: "LEG_2", material_region_id: "LEG_2", cw: ["0", "1", "0"] as const, tt: ["0", "0", "1"] as const },
      ],
    });
    const model = buildDirectSideLapConcreteSceneModel(visualization);
    expect(model.boxes.find((item) => item.ownerRole === "BRACE")?.ownerLabel).toBe("Connected FRP Angle");
    expect(model.materialAxes.map((item) => [item.elementId, item.presentation === null, item.throughThickness])).toEqual([
      ["LEG_1", false, { x: 0, y: -1, z: 0 }],
      ["LEG_2", false, { x: 0, y: 0, z: 1 }],
    ]);
    expect(model.materialAxes.every((item) => item.componentLabel === "Connected FRP Angle")).toBe(true);
    expect(model.materialAxes.every((item) => item.componentId !== "direct-side-lap-concrete-wall")).toBe(true);
  });

  it("normalizes every mixed length transport into the selected scene unit", () => {
    const visualization = structuredClone(directSideLapPreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    visualization.external_anchor_geometry.nominal_diameter.unit = "mm";
    const metric = buildDirectSideLapConcreteSceneModel(visualization);
    expect(metric.unitSystem).toBe("SI");
    expect(metric.boxes[0]?.center.x).toBe(50.8);
    expect(metric.markers[0]?.position.y).toBeCloseTo(-30.05666666666667);
  });

  it("omits the contact zone only when the strict wall owner is absent", () => {
    const visualization = structuredClone(directSideLapPreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    Object.assign(visualization, {
      boxes: visualization.boxes.filter(
        (item) => item.owner_id !== "direct-side-lap-concrete-wall",
      ),
    });
    expect(buildDirectSideLapConcreteSceneModel(visualization).zones).toEqual([]);
  });

  it("fails closed on unsupported scene length units and absent connected primitives", () => {
    const unsupportedScene = structuredClone(directSideLapPreviewFixture().result.visualization);
    if (unsupportedScene === null) throw new Error("Controlled visualization required.");
    unsupportedScene.external_anchor_geometry.nominal_diameter.unit = "cm";
    expect(() => buildDirectSideLapConcreteSceneModel(unsupportedScene)).toThrow("in or mm");

    const unsupportedQuantity = structuredClone(directSideLapPreviewFixture().result.visualization);
    if (unsupportedQuantity === null) throw new Error("Controlled visualization required.");
    unsupportedQuantity.action_reference_lsn.n.unit = "cm";
    expect(() => buildDirectSideLapConcreteSceneModel(unsupportedQuantity)).toThrow("quantities");

    const noConnectedPrimitive = structuredClone(directSideLapPreviewFixture().result.visualization);
    if (noConnectedPrimitive === null) throw new Error("Controlled visualization required.");
    Object.assign(noConnectedPrimitive, {
      boxes: noConnectedPrimitive.boxes.filter(
        (item) => item.owner_id === "direct-side-lap-concrete-wall",
      ),
    });
    expect(buildDirectSideLapConcreteSceneModel(noConnectedPrimitive).materialAxes.every(
      (item) => item.presentation === null,
    )).toBe(true);
  });
});
