import { describe, expect, it } from "vitest";

import {
  buildFastenerPresentation,
  buildFastenerPresentations,
  schematicHardwareDimensions,
  SCHEMATIC_HEAD_ACROSS_FLATS_RATIO,
  SCHEMATIC_HEAD_HEIGHT_RATIO,
  SCHEMATIC_NUT_ACROSS_FLATS_RATIO,
  SCHEMATIC_NUT_THICKNESS_RATIO,
} from "../src/visualization/fastenerPresentation";
import type { SceneCylinder } from "../src/visualization/sceneModel";

function cylinder(
  id: string,
  ownerBoltId: string,
  kind: SceneCylinder["kind"],
  start: number,
  end: number,
  hardwareLocation: SceneCylinder["hardwareLocation"] = null,
): SceneCylinder {
  return {
    id,
    label: id,
    start: { x: start, y: 0, z: 0 },
    end: { x: end, y: 0, z: 0 },
    diameter: kind === "WASHER" ? 1 : 0.5,
    kind,
    hardwareLocation,
    ownerBoltId,
    rowId: null,
    boltLineId: null,
    penetratedLayerIds: [],
    interfaceId: null,
  };
}

describe("R3 schematic fastener presentation", () => {
  it("uses the exact approved frontend-only head and nut ratios", () => {
    expect(SCHEMATIC_HEAD_ACROSS_FLATS_RATIO).toBe(1.5);
    expect(SCHEMATIC_HEAD_HEIGHT_RATIO).toBe(0.625);
    expect(SCHEMATIC_NUT_ACROSS_FLATS_RATIO).toBe(1.5);
    expect(SCHEMATIC_NUT_THICKNESS_RATIO).toBe(0.875);
    expect(schematicHardwareDimensions(2)).toEqual({
      headAcrossFlats: 3,
      headHeight: 1.25,
      nutAcrossFlats: 3,
      nutThickness: 1.75,
    });
  });

  it("uses authoritative UNDER_HEAD and UNDER_NUT washer faces and preserves washer geometry", () => {
    const shank = cylinder("bolt", "B1", "BOLT", 0, 2);
    const underHead = cylinder("head-washer", "B1", "WASHER", -0.1, 0, "UNDER_HEAD");
    const underNut = cylinder("nut-washer", "B1", "WASHER", 2, 2.2, "UNDER_NUT");
    const presentation = buildFastenerPresentation(shank, [underNut, underHead]);

    expect(presentation).not.toBeNull();
    expect(presentation?.washers).toEqual([underNut, underHead]);
    expect(presentation?.head).toMatchObject({
      start: { x: -0.4125, y: 0, z: 0 },
      end: underHead.start,
      acrossFlats: 0.75,
    });
    expect(presentation?.nut).toMatchObject({
      start: underNut.end,
      end: { x: 2.6375, y: 0, z: 0 },
      acrossFlats: 0.75,
    });
  });

  it("places schematic hardware immediately outside stack ends when washers are absent", () => {
    const presentation = buildFastenerPresentation(
      cylinder("bolt", "B1", "BOLT", 2, 0),
      [cylinder("foreign", "B2", "WASHER", 2, 2.1, "UNDER_NUT")],
    );

    expect(presentation?.washers).toEqual([]);
    expect(presentation?.head.start.x).toBe(2.3125);
    expect(presentation?.head.end.x).toBe(2);
    expect(presentation?.nut.start.x).toBe(0);
    expect(presentation?.nut.end.x).toBe(-0.4375);
  });

  it("uses one assembly mapping for every bolt and omits an unresolved zero-length axis", () => {
    const values: SceneCylinder[] = [
      cylinder("bolt-1", "B1", "BOLT", 0, 2),
      cylinder("bolt-2", "B2", "BOLT", 1, 3),
      cylinder("hole", "B1", "HOLE", 0, 2),
      cylinder("unresolved", "B3", "BOLT", 4, 4),
    ];

    expect(buildFastenerPresentations(values).map((value) => value.ownerBoltId)).toEqual(["B1", "B2"]);
    const unresolved = values[3];
    if (unresolved === undefined) throw new Error("Expected unresolved fixture shank.");
    expect(buildFastenerPresentation(unresolved, [])).toBeNull();
  });

  it("renders only one exterior nut for a blind embedded anchor", () => {
    const anchor = {
      ...cylinder("anchor", "A1", "BOLT", 0, 4),
      hardwareConfiguration: "EXTERIOR_NUT_WASHER_ANCHOR" as const,
    };
    const washer = cylinder("anchor-washer", "A1", "WASHER", -0.1, 0, "UNDER_HEAD");
    const presentation = buildFastenerPresentation(anchor, [washer]);
    expect(presentation?.renderedHardware).toHaveLength(1);
    expect(presentation?.renderedHardware[0]?.kind).toBe("NUT");
    expect(presentation?.renderedHardware[0]?.end).toEqual(washer.start);
  });

  it.each([
    ["1 x 1", 1],
    ["2 x 1", 2],
    ["2 x 2", 4],
    ["larger rectangular group", 8],
  ])("maps every bolt through the common renderer for %s", (_label, boltCount) => {
    const shanks = Array.from({ length: boltCount }, (_, index) =>
      cylinder(`bolt-${String(index + 1)}`, `B${String(index + 1)}`, "BOLT", 0, 2),
    );
    const presentations = buildFastenerPresentations(shanks);

    expect(presentations).toHaveLength(boltCount);
    expect(presentations.every((value) => value.head.acrossFlats === 0.75)).toBe(true);
    expect(presentations.every((value) => value.nut.acrossFlats === 0.75)).toBe(true);
  });

  it("keeps R9 head/nut geometry on the authoritative fixed axis during an R10 offset", () => {
    const baseline = buildFastenerPresentation(
      cylinder("bolt", "A_B_R1_L1", "BOLT", 0, 2),
      [],
    );
    const sourceShank = cylinder("bolt", "A_B_R1_L1", "BOLT", 0, 2);
    const movedShank = {
      ...sourceShank,
      start: { ...sourceShank.start, y: 1, z: -0.5 },
      end: { ...sourceShank.end, y: 1, z: -0.5 },
    };
    const moved = buildFastenerPresentation(movedShank, []);

    expect(baseline).not.toBeNull();
    expect(moved).not.toBeNull();
    for (const key of ["head", "nut"] as const) {
      expect((moved?.[key].start.y ?? 0) - (baseline?.[key].start.y ?? 0)).toBe(1);
      expect((moved?.[key].start.z ?? 0) - (baseline?.[key].start.z ?? 0)).toBe(-0.5);
      expect(moved?.[key].end.x).toBe(baseline?.[key].end.x);
      expect(moved?.[key].acrossFlats).toBe(baseline?.[key].acrossFlats);
    }
  });
});
