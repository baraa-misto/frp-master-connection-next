import { describe, expect, it } from "vitest";

import {
  buildRegionEmbeddedMaterialAxisPresentation,
  buildThroughThicknessMarkerBasis,
  classifyThroughThicknessMarkerFacing,
  materialAxisDepthTest,
  normalizeMaterialAxisPrimitiveId,
  resolveMaterialAxisOwnedIdentity,
  type MaterialAxisBoxPrimitive,
  type MaterialAxisRegionIdentity,
} from "../src/visualization/materialAxisPresentation";

const AXES: MaterialAxisRegionIdentity = {
  componentId: "profile",
  elementId: "WEB",
  materialRegionId: "WEB",
  lengthwise: { x: 1, y: 0, z: 0 },
  crosswise: { x: 0, y: 1, z: 0 },
  throughThickness: { x: 0, y: 0, z: 1 },
};

function box(
  overrides: Partial<MaterialAxisBoxPrimitive> = {},
): MaterialAxisBoxPrimitive {
  return {
    id: "profile:WEB",
    ownerId: "profile",
    elementId: "WEB",
    materialRegionId: "WEB",
    center: { x: 0, y: 0, z: 0 },
    size: { x: 10, y: 4, z: 0.5 },
    basis: [
      { x: 1, y: 0, z: 0 },
      { x: 0, y: 1, z: 0 },
      { x: 0, y: 0, z: 1 },
    ],
    ...overrides,
  };
}

describe("region-embedded material-axis presentation", () => {
  it("resolves owner-qualified mirrored identities without changing fallback ownership", () => {
    const owners = ["POSITIVE_CLIP_ANGLE", "NEGATIVE_CLIP_ANGLE"];
    expect(resolveMaterialAxisOwnedIdentity(
      "single-clip-angle-connector",
      "POSITIVE_CLIP_ANGLE:CONNECTED_MEMBER_LEG",
      owners,
    )).toEqual({ ownerId: "POSITIVE_CLIP_ANGLE", localId: "CONNECTED_MEMBER_LEG" });
    expect(resolveMaterialAxisOwnedIdentity(
      "single-clip-angle-connector",
      "SUPPORT_LEG",
      owners,
    )).toEqual({ ownerId: "single-clip-angle-connector", localId: "SUPPORT_LEG" });
    expect(normalizeMaterialAxisPrimitiveId(
      "clip-angle-connected-member",
      "clip-angle-connected-member:WEB",
    )).toBe("WEB");
    expect(normalizeMaterialAxisPrimitiveId("other-owner", "profile:WEB")).toBe("profile:WEB");
  });

  it("anchors on the positive-TT box surface with bounded in-plane scale", () => {
    const presentation = buildRegionEmbeddedMaterialAxisPresentation(
      AXES,
      [
        box({ id: "wrong-owner", ownerId: "other" }),
        box({ id: "wrong-element", elementId: "FLANGE" }),
        box({ id: "wrong-region", materialRegionId: "OTHER" }),
        box({ id: "accepted-null-region", materialRegionId: null }),
        box({ id: "accepted-exact-region" }),
      ],
      [],
    );

    expect(presentation).toEqual({
      origin: { x: 0, y: 0, z: 0.274 },
      lengthwiseLength: 2.88,
      crosswiseLength: 2.32,
      markerRadius: 0.3,
      primitiveIds: ["accepted-exact-region", "accepted-null-region"],
      surfaceOffset: 0.024,
    });
    expect(presentation?.lengthwiseLength).toBeLessThan(4);
    expect(presentation?.crosswiseLength).toBeLessThan(4);
  });

  it("derives a stable oriented surface anchor from trimmed triangle meshes", () => {
    const axes: MaterialAxisRegionIdentity = {
      componentId: "angle",
      elementId: "LEG_2",
      materialRegionId: "LEG_2",
      lengthwise: { x: 1, y: 0, z: 0 },
      crosswise: { x: 0, y: 0, z: -1 },
      throughThickness: { x: 0, y: 1, z: 0 },
    };
    const presentation = buildRegionEmbeddedMaterialAxisPresentation(axes, [], [
      {
        id: "angle:LEG_2:trimmed",
        ownerId: "angle",
        elementId: "LEG_2",
        materialRegionId: "LEG_2",
        points: [
          { x: 0, y: -0.4, z: -3 },
          { x: 8, y: -0.4, z: -3 },
          { x: 8, y: 0, z: 0 },
          { x: 0, y: -0.4, z: -3 },
          { x: 8, y: 0, z: 0 },
          { x: 0, y: 0, z: 0 },
        ],
      },
    ]);

    expect(presentation).toMatchObject({
      origin: { x: 4, y: 0.018000000000000002, z: -1.5 },
      lengthwiseLength: 2.16,
      crosswiseLength: 1.7399999999999998,
      markerRadius: 0.22499999999999998,
      primitiveIds: ["angle:LEG_2:trimmed"],
      surfaceOffset: 0.018000000000000002,
    });
  });

  it("fails closed when no usable physical region span exists", () => {
    expect(buildRegionEmbeddedMaterialAxisPresentation(AXES, [], [])).toBeNull();
    expect(
      buildRegionEmbeddedMaterialAxisPresentation(
        AXES,
        [box({ size: { x: 10, y: 0, z: 0.5 } })],
        [],
      ),
    ).toBeNull();
    expect(
      buildRegionEmbeddedMaterialAxisPresentation(
        AXES,
        [box({ size: { x: 10, y: 4, z: 0 } })],
        [],
      ),
    ).toBeNull();
    expect(() =>
      buildRegionEmbeddedMaterialAxisPresentation(
        { ...AXES, lengthwise: { x: 0, y: 0, z: 0 } },
        [box()],
        [],
      )).toThrow("nonzero vectors");
  });

  it("selects dot, cross, and tangent TT markers from camera relation", () => {
    const origin = { x: 0, y: 0, z: 0 };
    const tt = { x: 0, y: 0, z: 1 };
    expect(classifyThroughThicknessMarkerFacing(origin, tt, { x: 0, y: 0, z: 10 })).toBe("DOT");
    expect(classifyThroughThicknessMarkerFacing(origin, tt, { x: 0, y: 0, z: -10 })).toBe("CROSS");
    expect(classifyThroughThicknessMarkerFacing(origin, tt, { x: 10, y: 0, z: 0 })).toBe("TANGENT");
    expect(() => classifyThroughThicknessMarkerFacing(origin, tt, origin)).toThrow(
      "nonzero vectors",
    );
  });

  it("builds proper TT presentation rotations for reflected W/I and clip-angle bases", () => {
    for (const tt of [
      { x: 1, y: 0, z: 0 },
      { x: 0, y: 0, z: -1 },
      { x: 0, y: 1, z: 0 },
      { x: -1, y: 0, z: 0 },
    ]) {
      const basis = buildThroughThicknessMarkerBasis(tt);
      expect(basis[2]).toEqual(tt);
      const [first, second, third] = basis;
      const determinant = first.x * (second.y * third.z - second.z * third.y)
        - first.y * (second.x * third.z - second.z * third.x)
        + first.z * (second.x * third.y - second.y * third.x);
      expect(determinant).toBeCloseTo(1, 12);
      expect(Math.abs(first.x * tt.x + first.y * tt.y + first.z * tt.z)).toBeLessThan(1e-12);
      expect(Math.abs(second.x * tt.x + second.y * tt.y + second.z * tt.z)).toBeLessThan(1e-12);
    }
    expect(() => buildThroughThicknessMarkerBasis({ x: 0, y: 0, z: 0 })).toThrow(
      "nonzero vectors",
    );
  });

  it("uses normal occlusion in Solid and readable overlay depth in X-ray", () => {
    expect(materialAxisDepthTest("SOLID")).toBe(true);
    expect(materialAxisDepthTest("XRAY")).toBe(false);
  });
});
