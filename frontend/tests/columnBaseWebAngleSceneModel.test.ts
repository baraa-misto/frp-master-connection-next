import { describe, expect, it } from "vitest";

import { buildColumnBaseWebAngleSceneModel } from "../src/visualization/columnBaseWebAngleSceneModel";
import { columnBasePreviewFixture } from "./columnBaseWebAngleFixtures";

describe("Stage 3.5C backend-authored physical scene adapter", () => {
  it("renders the finite base, full W/I, double angles, web bolts, blind anchors, frame, and material axes", () => {
    const visualization = columnBasePreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Controlled visualization required.");
    const model = buildColumnBaseWebAngleSceneModel(visualization);
    expect(model.boxes.filter((item) => item.ownerId === "column")).toHaveLength(3);
    expect(model.boxes.filter((item) => item.ownerId.includes("base-angle"))).toHaveLength(4);
    expect(model.boxes.filter((item) => item.ownerId === "concrete-base")).toHaveLength(1);
    expect(model.cylinders.filter((item) => item.id.endsWith(":bolt"))).toHaveLength(1);
    expect(model.cylinders.filter((item) => item.id.endsWith(":anchor"))).toHaveLength(2);
    expect(model.cylinders.filter((item) => item.id.endsWith(":washer"))).toHaveLength(2);
    expect(model.cylinders.filter((item) => item.id.endsWith(":hole"))).toHaveLength(3);
    expect(model.cylinders.every((item) => item.end.z <= 0.609 || item.interfaceId === "COLUMN_WEB_BASE_ANGLE_INTERFACE")).toBe(true);
    expect(model.frames[0]?.label).toContain("S_C / T_C / L_C");
    expect(model.markers[0]).toMatchObject({ id: "COLUMN_ACTION_REFERENCE", position: { z: 4 } });
    expect(model.zones[0]).toMatchObject({ patchId: "CONCRETE_BASE_TOP", selectedContact: true });
    expect(model.materialAxes).toHaveLength(7);
    expect(model.materialAxes.every((item) => item.componentId !== "concrete-base")).toBe(true);
    expect(model.boundsRadius).toBeGreaterThan(model.fitRadius);
  });

  it("uses the exact backend material bases and signed applied actions", () => {
    const visualization = columnBasePreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Controlled visualization required.");
    const model = buildColumnBaseWebAngleSceneModel(visualization);
    expect(model.appliedArrows.map((item) => [item.component, item.signedValue, item.sense, item.axis])).toEqual([
      ["FX", 4, "POSITIVE", { x: 1, y: 0, z: 0 }],
      ["FZ", 20, "NEGATIVE", { x: 0, y: 0, z: -1 }],
    ]);
    expect(model.appliedArrows[1]?.axialLoadingSense).toBe("COMPRESSION");
    expect(model.appliedArrows.every((item) => item.origin.x === 0 && item.origin.y === 0 && item.origin.z === 4)).toBe(true);
    expect(model.materialAxes.find((item) => item.elementId === "COLUMN_WEB")).toMatchObject({ lengthwise: { x: 0, y: 0, z: 1 }, crosswise: { x: 1, y: 0, z: 0 }, throughThickness: { x: 0, y: 1, z: 0 } });
    expect(model.materialAxes.find((item) => item.elementId === "POSITIVE_BASE_ANGLE_VERTICAL_LEG")).toMatchObject({ lengthwise: { x: 1, y: 0, z: 0 }, crosswise: { x: 0, y: 0, z: 1 }, throughThickness: { x: 0, y: -1, z: 0 } });
    expect(model.materialAxes.find((item) => item.elementId === "POSITIVE_BASE_ANGLE_HORIZONTAL_LEG")).toMatchObject({ lengthwise: { x: 1, y: 0, z: 0 }, crosswise: { x: 0, y: 1, z: 0 }, throughThickness: { x: 0, y: 0, z: 1 } });
  });

  it("reverses both signed shear axes, suppresses exact zero components, and presents compression as a positive magnitude along -L_C", () => {
    const visualization = structuredClone(columnBasePreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    visualization.applied_force_s_t_l.s.value = "4";
    visualization.applied_force_s_t_l.t.value = "10";
    let model = buildColumnBaseWebAngleSceneModel(visualization);
    expect(model.appliedArrows.map((item) => [item.component, item.axis, item.signedValue])).toEqual([
      ["FX", { x: 1, y: 0, z: 0 }, 4],
      ["FY", { x: 0, y: 1, z: 0 }, 10],
      ["FZ", { x: 0, y: 0, z: -1 }, 20],
    ]);
    visualization.applied_force_s_t_l.s.value = "-4";
    visualization.applied_force_s_t_l.t.value = "-10";
    model = buildColumnBaseWebAngleSceneModel(visualization);
    expect(model.appliedArrows.map((item) => [item.component, item.axis, item.signedValue])).toEqual([
      ["FX", { x: -1, y: 0, z: 0 }, -4],
      ["FY", { x: 0, y: -1, z: 0 }, -10],
      ["FZ", { x: 0, y: 0, z: -1 }, 20],
    ]);
    expect(model.appliedArrows.every((item) => item.referencePointId === "COLUMN_ACTION_REFERENCE" && item.origin.z === 4)).toBe(true);
    visualization.applied_force_s_t_l.s.value = "0";
    visualization.applied_force_s_t_l.t.value = "0";
    visualization.applied_force_s_t_l.longitudinal.value = "0";
    expect(buildColumnBaseWebAngleSceneModel(visualization).appliedArrows).toEqual([]);
  });

  it("keeps the signed convention invariant across Single positive, Single negative, Double, and every standard view", () => {
    const response = columnBasePreviewFixture();
    if (response.result.visualization === null) throw new Error("Controlled visualization required.");
    response.result.visualization.applied_force_s_t_l.s.value = "-4";
    response.result.visualization.applied_force_s_t_l.t.value = "10";
    for (const assembly of ["SINGLE_POSITIVE", "SINGLE_NEGATIVE", "SYMMETRIC_DOUBLE"] as const) {
      for (const view of ["3D", "Front", "Top", "Side 1", "Side 2"] as const) {
        const model = buildColumnBaseWebAngleSceneModel(response.result.visualization);
        expect([assembly, view, model.appliedArrows.map((item) => [item.component, item.axis])]).toEqual([
          assembly,
          view,
          [["FX", { x: -1, y: 0, z: 0 }], ["FY", { x: 0, y: 1, z: 0 }], ["FZ", { x: 0, y: 0, z: -1 }]],
        ]);
      }
    }
  });

  it("uses signed axial labels and directions for the R2 compression/uplift/zero matrix", () => {
    const visualization = structuredClone(columnBasePreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    let axial = buildColumnBaseWebAngleSceneModel(visualization, "3.5C-R2-RC1").appliedArrows.find((item) => item.component === "FZ");
    expect(axial).toMatchObject({ axis: { x: 0, y: 0, z: -1 }, signedValue: -20, sense: "NEGATIVE", axialLoadingSense: "COMPRESSION" });
    visualization.applied_force_s_t_l.longitudinal.value = "3";
    axial = buildColumnBaseWebAngleSceneModel(visualization, "3.5C-R2-RC1").appliedArrows.find((item) => item.component === "FZ");
    expect(axial).toMatchObject({ axis: { x: 0, y: 0, z: 1 }, signedValue: 3, sense: "POSITIVE", axialLoadingSense: "TENSION" });
    visualization.applied_force_s_t_l.longitudinal.value = "0";
    expect(buildColumnBaseWebAngleSceneModel(visualization, "3.5C-R2-RC1").appliedArrows.some((item) => item.component === "FZ")).toBe(false);
  });

  it("supports SI, missing material presentation targets, and a missing concrete box", () => {
    const visualization = structuredClone(columnBasePreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    visualization.web_bolt_diameter.unit = "mm";
    const first = visualization.material_regions[0];
    if (first === undefined) throw new Error("Controlled material region required.");
    const modified = {
      ...visualization,
      material_regions: [{ ...first, physical_element_id: "UNKNOWN" }, ...visualization.material_regions.slice(1)],
      boxes: visualization.boxes.filter((item) => item.owner_id !== "concrete-base"),
    };
    const model = buildColumnBaseWebAngleSceneModel(modified);
    expect(model.unitSystem).toBe("SI");
    expect(model.zones).toEqual([]);
    expect(model.materialAxes[0]).toMatchObject({ componentId: "column-base", origin: { x: 0, y: 0, z: 0 }, presentation: null });
    const firstBox = modified.boxes[0];
    if (firstBox === undefined) throw new Error("Controlled box required.");
    const unknownOwner = { ...modified, boxes: [{ ...firstBox, owner_id: "owner-not-registered" }, ...modified.boxes.slice(1)] };
    expect(buildColumnBaseWebAngleSceneModel(unknownOwner).boxes[0]?.ownerLabel).toBe("owner not registered");
  });

  it("labels every successor column family and falls back to the canonical frame basis", () => {
    const visualization = structuredClone(columnBasePreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    const { base_frame: _baseFrame, ...withoutFrame } = visualization;
    void _baseFrame;
    expect(buildColumnBaseWebAngleSceneModel(withoutFrame).frames[0]).toMatchObject({
      xAxis: { x: 1, y: 0, z: 0 },
      yAxis: { x: 0, y: 1, z: 0 },
      zAxis: { x: 0, y: 0, z: 1 },
    });
    expect(buildColumnBaseWebAngleSceneModel({
      ...visualization,
      base_frame: {
        s_axis: ["0", "1", "0"],
        t_axis: ["-1", "0", "0"],
        l_axis: ["0", "0", "1"],
        handedness: "S_C cross T_C = L_C",
      },
    }).frames[0]).toMatchObject({
      xAxis: { x: 0, y: 1, z: 0 },
      yAxis: { x: -1, y: 0, z: 0 },
      zAxis: { x: 0, y: 0, z: 1 },
    });
    for (const [profile_family, label] of [
      ["RECTANGULAR_HOLLOW_SECTION", "FRP RHS Column"],
      ["SOLID_RECTANGULAR_SECTION", "FRP Solid Rectangular Column"],
      ["ANGLE", "FRP Angle Column"],
    ] as const) {
      const model = buildColumnBaseWebAngleSceneModel({ ...visualization, profile_family });
      expect(model.boxes.find((item) => item.ownerId === "column")?.ownerLabel).toBe(label);
    }
  });

  it("fails closed on non-finite serialized geometry", () => {
    const visualization = structuredClone(columnBasePreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Controlled visualization required.");
    visualization.web_bolt_diameter.value = "not-finite";
    expect(() => buildColumnBaseWebAngleSceneModel(visualization)).toThrow("finite quantities");
  });
});
