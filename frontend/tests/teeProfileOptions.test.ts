import { describe, expect, it } from "vitest";

import type { TeeProfileFamily } from "../src/api/teeContracts";
import {
  initialConnectedMemberProfile,
  TEE_PROFILE_DEFINITIONS,
  TEE_PROFILE_FAMILIES,
} from "../src/workspace/teeProfileOptions";

const expected = {
  ANGLE: {
    keys: ["member_length", "leg_y", "leg_z", "thickness"],
    surfaces: ["LEG_Y_OUTER", "LEG_Z_OUTER"],
  },
  CHANNEL: {
    keys: ["member_length", "depth", "flange_width", "web_thickness", "flange_thickness"],
    surfaces: ["WEB_OUTER", "FLANGE_POS_OUTER", "FLANGE_NEG_OUTER"],
  },
  WIDE_FLANGE_I: {
    keys: ["member_length", "depth", "flange_width", "web_thickness", "flange_thickness"],
    surfaces: ["WEB_POS_FACE", "WEB_NEG_FACE", "FLANGE_POS_OUTER", "FLANGE_NEG_OUTER"],
  },
  RECTANGULAR_HOLLOW_SECTION: {
    keys: ["member_length", "depth", "width", "wall_thickness"],
    surfaces: ["Y_POS_FACE", "Y_NEG_FACE", "Z_POS_FACE", "Z_NEG_FACE"],
  },
  SOLID_RECTANGULAR_SECTION: {
    keys: ["member_length", "depth", "width"],
    surfaces: ["Z_POS_FACE", "Z_NEG_FACE", "Y_POS_FACE", "Y_NEG_FACE"],
  },
  FLAT_PLATE: {
    keys: ["member_length", "width", "thickness"],
    surfaces: ["FACE_POS", "FACE_NEG"],
  },
} as const satisfies Partial<Record<TeeProfileFamily, {
  readonly keys: readonly string[];
  readonly surfaces: readonly string[];
}>>;

describe("Stage 3.2-R2 connected-member profile controls", () => {
  it("uses exactly the authorized family-specific dimensions and planar surfaces", () => {
    for (const family of Object.keys(expected) as (keyof typeof expected)[]) {
      const profile = initialConnectedMemberProfile("in", family);
      expect(Object.keys(profile.dimensions)).toEqual(expected[family].keys);
      expect(TEE_PROFILE_DEFINITIONS[family].surfaces).toEqual(expected[family].surfaces);
      expect(profile.selected_profile_surface).toBe(expected[family].surfaces[0]);
      expect(profile).toMatchObject({
        role: "BRACE",
        size_basis: "CUSTOM_DIMENSIONS",
        profile_orientation: "ROTATION_0",
        material_kind: "PULTRUDED_FRP",
      });
      expect(Object.values(profile.dimensions).every((value) => value.unit === "in")).toBe(true);
    }
  });

  it("keeps all U.S./SI defaults physically equivalent and uses member_length", () => {
    for (const family of Object.keys(expected) as (keyof typeof expected)[]) {
      const customary = initialConnectedMemberProfile("in", family);
      const metric = initialConnectedMemberProfile("mm", family);
      expect(customary.dimensions).toHaveProperty("member_length");
      expect(customary.dimensions).not.toHaveProperty("view_length");
      for (const key of Object.keys(customary.dimensions)) {
        const customaryValue = customary.dimensions[key];
        const metricValue = metric.dimensions[key];
        if (customaryValue === undefined || metricValue === undefined) {
          throw new Error(`Missing ${family} dimension ${key}.`);
        }
        expect(Number(metricValue.value)).toBeCloseTo(Number(customaryValue.value) * 25.4, 10);
        expect(metricValue.unit).toBe("mm");
      }
    }
  });

  it("keeps round tube visible but unavailable for direct Tee contact", () => {
    expect(TEE_PROFILE_FAMILIES).toContain("ROUND_HOLLOW_SECTION");
    expect(TEE_PROFILE_DEFINITIONS.ROUND_HOLLOW_SECTION).toMatchObject({
      enabledForDirectTee: false,
      surfaces: [],
    });
    expect(() => initialConnectedMemberProfile("in", "ROUND_HOLLOW_SECTION")).toThrow(
      "Round hollow sections have no authorized direct Tee-stem surface.",
    );
  });
});
