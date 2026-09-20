import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import {
  SHARED_SUPPORT_OPTIONS,
  initialSharedSupport,
  sharedSupportLabel,
  type SharedSupportProfileRequest,
  type SharedSupportTargetId,
} from "../src/api/sharedSupportContracts";
import type { FullThroughBoltTrace } from "../src/api/teeContracts";
import {
  applyFullThroughBoltSpans,
  buildTeeSceneModel,
  type SceneCylinder,
} from "../src/visualization/sceneModel";
import { buildFastenerPresentations } from "../src/visualization/fastenerPresentation";
import { buildClipAngleSceneModel } from "../src/visualization/clipAngleSceneModel";
import { SupportingMemberEditor } from "../src/workspace/SupportingMemberEditor";
import { clipAnglePreviewFixture } from "./clipAngleFixtures";
import { teeVisualizationFixture } from "./teeFixtures";

function EditorHarness() {
  const [target, setTarget] = useState<SharedSupportTargetId>("W_COLUMN_FLANGE");
  const [profile, setProfile] = useState<SharedSupportProfileRequest>(() =>
    initialSharedSupport("W_COLUMN_FLANGE", "in", "support"),
  );
  return (
    <SupportingMemberEditor
      targetId={target}
      profile={profile}
      onTargetChange={(nextTarget) => {
        setTarget(nextTarget);
        setProfile(initialSharedSupport(nextTarget, "in", "support"));
      }}
      onProfileChange={(change) => {
        setProfile((current) => {
          const next = structuredClone(current);
          change(next);
          return next;
        });
      }}
    />
  );
}

function cylinder(
  kind: SceneCylinder["kind"],
  hardwareLocation: SceneCylinder["hardwareLocation"],
  start: number,
  end: number,
  ownerBoltId = "C2-BOLT-1",
): SceneCylinder {
  return {
    id: `${kind}:${hardwareLocation ?? "NONE"}`,
    label: kind,
    start: { x: start, y: 0, z: 0 },
    end: { x: end, y: 0, z: 0 },
    diameter: 0.5,
    kind,
    hardwareLocation,
    ownerBoltId,
    rowId: "ROW_1",
    boltLineId: "BOLT_LINE_1",
    penetratedLayerIds: [],
    interfaceId: "C2_INTERFACE",
  };
}

function endpointTrace(
  boltId: string,
  start: readonly [string, string, string],
  end: readonly [string, string, string],
): FullThroughBoltTrace {
  return {
    path: {
      bolt_id: boltId,
      segments: [
        { kind: "MATERIAL_LAYER", identity: "CONNECTOR", length: "0.5" },
        { kind: "MATERIAL_LAYER", identity: "RHS_NEAR_WALL", length: "0.5" },
        { kind: "FREE_SHANK_SPAN", identity: "RHS_CAVITY", length: "5" },
        { kind: "MATERIAL_LAYER", identity: "RHS_FAR_WALL", length: "0.5" },
      ],
    },
    hardware: {
      bolt_id: boltId,
      shank_length: "6.5",
      head_location: "EXTERIOR_NEAR_SIDE",
      nut_location: "EXTERIOR_FAR_SIDE",
      washer_locations: ["EXTERIOR_NEAR_SIDE", "EXTERIOR_FAR_SIDE"],
      physical_bolt_count: 1,
      continuous_shank_count: 1,
      internal_hardware_count: 0,
    },
    physical_start_point: { x: start[0], y: start[1], z: start[2] },
    physical_end_point: { x: end[0], y: end[1], z: end[2] },
    geometry_valid: true,
    path_fingerprint: `${boltId}-controlled-path`,
  };
}

describe("Stage 3.3C2 shared support and full-through presentation", () => {
  it("offers the exact seven controlled support targets and excludes W Beam Web", () => {
    expect(SHARED_SUPPORT_OPTIONS.map((option) => option.id)).toEqual([
      "W_COLUMN_FLANGE",
      "W_BEAM_FLANGE",
      "W_COLUMN_WEB",
      "CHANNEL_COLUMN_WEB",
      "ANGLE_COLUMN_LEG",
      "RECTANGULAR_HOLLOW_COLUMN_WALL",
      "SOLID_RECTANGULAR_COLUMN_FACE",
    ]);
    expect(SHARED_SUPPORT_OPTIONS.map((option) => option.id)).not.toContain("W_BEAM_WEB");
  });

  it("uses one editor contract for target-specific dimensions, contact face, and angle roll", () => {
    render(<EditorHarness />);
    const target = screen.getByLabelText<HTMLSelectElement>("Supporting member");
    expect(target.options).toHaveLength(7);

    fireEvent.change(target, { target: { value: "ANGLE_COLUMN_LEG" } });
    expect(screen.getByLabelText("Support Leg Y")).toBeInTheDocument();
    expect(screen.getByLabelText("Support Leg Z")).toBeInTheDocument();
    expect(screen.getByLabelText("Support profile roll")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Support contact face"), {
      target: { value: "LEG_Z_OUTER" },
    });
    expect(screen.getByLabelText<HTMLSelectElement>("Support contact face").value).toBe(
      "LEG_Z_OUTER",
    );
    fireEvent.change(screen.getByLabelText("Support profile roll"), {
      target: { value: "ROTATION_180" },
    });
    expect(screen.getByLabelText<HTMLSelectElement>("Support profile roll").value).toBe(
      "ROTATION_180",
    );

    fireEvent.change(target, { target: { value: "RECTANGULAR_HOLLOW_COLUMN_WALL" } });
    expect(screen.getByLabelText("Support outside width")).toBeInTheDocument();
    expect(screen.getByLabelText("Support wall thickness")).toBeInTheDocument();
    expect(screen.queryByLabelText("Support profile roll")).not.toBeInTheDocument();
  });

  it("constructs exact US/SI default physical dimensions for every support target", () => {
    for (const option of SHARED_SUPPORT_OPTIONS) {
      const customary = initialSharedSupport(option.id, "in", "support");
      const metric = initialSharedSupport(option.id, "mm", "support");
      expect(customary.profile_family).toBe(metric.profile_family);
      expect(customary.selected_profile_surface).toBe(metric.selected_profile_surface);
      expect(customary.member_length).toEqual({ value: "12", unit: "in" });
      expect(metric.member_length).toEqual({ value: "304.8", unit: "mm" });
    }
    expect(sharedSupportLabel("W_COLUMN_WEB")).toBe("W Column Web");
    expect(sharedSupportLabel("UNRECOGNIZED" as SharedSupportTargetId)).toBe("UNRECOGNIZED");
  });

  it("extends one shank through the backend-authoritative path and moves only the far washer", () => {
    const trace: FullThroughBoltTrace = {
      path: {
        bolt_id: "C2-BOLT-1",
        segments: [
          { kind: "MATERIAL_LAYER", identity: "CONNECTOR", length: "0.5" },
          { kind: "MATERIAL_LAYER", identity: "RHS_NEAR_WALL", length: "0.5" },
          { kind: "FREE_SHANK_SPAN", identity: "RHS_CAVITY", length: "5" },
          { kind: "MATERIAL_LAYER", identity: "RHS_FAR_WALL", length: "0.5" },
        ],
      },
      hardware: {
        bolt_id: "C2-BOLT-1",
        shank_length: "6.5",
        head_location: "EXTERIOR_NEAR_SIDE",
        nut_location: "EXTERIOR_FAR_SIDE",
        washer_locations: ["EXTERIOR_NEAR_SIDE", "EXTERIOR_FAR_SIDE"],
        physical_bolt_count: 1,
        continuous_shank_count: 1,
        internal_hardware_count: 0,
      },
      physical_start_point: { x: "0", y: "0", z: "0" },
      physical_end_point: { x: "6.5", y: "0", z: "0" },
      geometry_valid: true,
      path_fingerprint: "controlled-path",
    };
    const result = applyFullThroughBoltSpans(
      [
        cylinder("BOLT", null, 0, 1),
        cylinder("WASHER", "UNDER_HEAD", -0.1, 0),
        cylinder("WASHER", "UNDER_NUT", 1, 1.1),
      ],
      [trace],
    );
    const bolt = result.find((item) => item.kind === "BOLT");
    const headWasher = result.find((item) => item.hardwareLocation === "UNDER_HEAD");
    const nutWasher = result.find((item) => item.hardwareLocation === "UNDER_NUT");
    expect(bolt?.start.x).toBe(0);
    expect(bolt?.end.x).toBe(6.5);
    expect(headWasher?.start.x).toBe(-0.1);
    expect(nutWasher?.start.x).toBe(6.5);
    expect(nutWasher?.end.x).toBeCloseTo(6.6);
  });

  it("preserves accepted cylinders exactly when no rectangular path is present", () => {
    const accepted = [cylinder("BOLT", null, 0, 1)];
    expect(applyFullThroughBoltSpans(accepted, [])).toBe(accepted);
  });

  it("resolves namespaced bolt identities and fails closed for a zero-length shank", () => {
    const trace: FullThroughBoltTrace = {
      path: {
        bolt_id: "C2-BOLT-1",
        segments: [{ kind: "MATERIAL_LAYER", identity: "LAYER", length: "2" }],
      },
      hardware: {
        bolt_id: "C2-BOLT-1",
        shank_length: "2",
        head_location: "EXTERIOR_NEAR_SIDE",
        nut_location: "EXTERIOR_FAR_SIDE",
        washer_locations: ["EXTERIOR_NEAR_SIDE", "EXTERIOR_FAR_SIDE"],
        physical_bolt_count: 1,
        continuous_shank_count: 1,
        internal_hardware_count: 0,
      },
      physical_start_point: { x: "0", y: "0", z: "0" },
      physical_end_point: { x: "2", y: "0", z: "0" },
      geometry_valid: true,
      path_fingerprint: "namespaced-path",
    };
    const namespaced = cylinder("BOLT", null, 0, 1, "GROUP:C2-BOLT-1");
    expect(applyFullThroughBoltSpans([namespaced], [trace])[0]?.end.x).toBe(2);

    const unmatched = cylinder("BOLT", null, 0, 1, "OTHER-BOLT");
    expect(applyFullThroughBoltSpans([unmatched], [trace])[0]).toBe(unmatched);
    expect(() => applyFullThroughBoltSpans([cylinder("BOLT", null, 0, 1)], [{
      ...trace,
      physical_end_point: trace.physical_start_point,
    }])).toThrow(
      "Full-through bolt shank requires a nonzero axis.",
    );
  });

  it("uses physical endpoints when a connected-RHS engineering axis points the other way", () => {
    const trace: FullThroughBoltTrace = {
      path: {
        bolt_id: "C2-BOLT-1",
        segments: [
          { kind: "MATERIAL_LAYER", identity: "CONNECTOR", length: "0.5" },
          { kind: "MATERIAL_LAYER", identity: "RHS_NEAR_WALL", length: "0.5" },
          { kind: "FREE_SHANK_SPAN", identity: "RHS_CAVITY", length: "5" },
          { kind: "MATERIAL_LAYER", identity: "RHS_FAR_WALL", length: "0.5" },
        ],
      },
      hardware: {
        bolt_id: "C2-BOLT-1",
        shank_length: "6.5",
        head_location: "EXTERIOR_NEAR_SIDE",
        nut_location: "EXTERIOR_FAR_SIDE",
        washer_locations: ["EXTERIOR_NEAR_SIDE", "EXTERIOR_FAR_SIDE"],
        physical_bolt_count: 1,
        continuous_shank_count: 1,
        internal_hardware_count: 0,
      },
      physical_start_point: { x: "0.5", y: "1.25", z: "-1" },
      physical_end_point: { x: "-6", y: "1.25", z: "-1" },
      geometry_valid: true,
      path_fingerprint: "connected-rhs-path",
    };
    const result = applyFullThroughBoltSpans(
      [
        cylinder("BOLT", null, -0.5, 0.5),
        cylinder("WASHER", "UNDER_HEAD", -0.6, -0.5),
        cylinder("WASHER", "UNDER_NUT", 0.5, 0.6),
      ],
      [trace],
    );
    const bolt = result.find((item) => item.kind === "BOLT");
    const headWasher = result.find((item) => item.hardwareLocation === "UNDER_HEAD");
    const nutWasher = result.find((item) => item.hardwareLocation === "UNDER_NUT");
    expect(bolt?.start).toEqual({ x: 0.5, y: 1.25, z: -1 });
    expect(bolt?.end).toEqual({ x: -6, y: 1.25, z: -1 });
    expect(headWasher?.start.x).toBeCloseTo(0.6);
    expect(headWasher?.end.x).toBe(0.5);
    expect(nutWasher?.start.x).toBe(-6);
    expect(nutWasher?.end.x).toBeCloseTo(-6.1);
    const hardware = buildFastenerPresentations(result);
    expect(hardware).toHaveLength(1);
    expect(hardware[0]?.head.start.x).toBeGreaterThan(0.6);
    expect(hardware[0]?.nut.end.x).toBeLessThan(-6.1);
  });

  it("binds Tee connected-RHS scene hardware to server endpoints, not the engineering axis", () => {
    const visualization = teeVisualizationFixture();
    visualization.rectangular_full_through_paths = [
      endpointTrace("A_B_R1_L1", ["3.5", "-0.25", "-3"], ["3.5", "6.25", "-3"]),
    ];
    const model = buildTeeSceneModel(visualization);
    const shanks = model.cylinders.filter(
      (item) => item.kind === "BOLT" && item.ownerBoltId === "A_B_R1_L1",
    );
    expect(shanks).toHaveLength(1);
    expect(shanks[0]?.start).toEqual({ x: 3.5, y: -0.25, z: -3 });
    expect(shanks[0]?.end).toEqual({ x: 3.5, y: 6.25, z: -3 });
    const hardware = buildFastenerPresentations(model.cylinders).find(
      (item) => item.ownerBoltId === "A_B_R1_L1",
    );
    expect(hardware?.head.start.y).toBeLessThan(-0.25);
    expect(hardware?.nut.end.y).toBeGreaterThan(6.25);
  });

  it("binds Single connected-RHS scene hardware and both external ends exactly once", () => {
    const response = clipAnglePreviewFixture();
    const visualization = response.result.visualization;
    if (visualization === null) throw new Error("Clip-angle visualization fixture is required.");
    visualization.rectangular_full_through_paths = [
      endpointTrace("CLIP-A-R1-B1", ["0.5", "1.25", "-1"], ["-6", "1.25", "-1"]),
    ];
    const model = buildClipAngleSceneModel(visualization);
    const owner = "CONNECTED_MEMBER_TO_CLIP_ANGLE:CLIP-A-R1-B1";
    const shanks = model.cylinders.filter(
      (item) => item.kind === "BOLT" && item.ownerBoltId === owner,
    );
    expect(shanks).toHaveLength(1);
    expect(shanks[0]?.start).toEqual({ x: 0.5, y: 1.25, z: -1 });
    expect(shanks[0]?.end).toEqual({ x: -6, y: 1.25, z: -1 });
    const hardware = buildFastenerPresentations(model.cylinders).find(
      (item) => item.ownerBoltId === owner,
    );
    expect(hardware?.head.start.x).toBeGreaterThan(0.5);
    expect(hardware?.nut.end.x).toBeLessThan(-6);
    expect(hardware?.washers).toHaveLength(0);
  });

  it("preserves support-RHS direction and follows each latest trim-authored endpoint pair", () => {
    const response = clipAnglePreviewFixture();
    const visualization = response.result.visualization;
    if (visualization === null) throw new Error("Clip-angle visualization fixture is required.");
    visualization.rectangular_full_through_paths = [
      endpointTrace("CLIP-B-R1-B1", ["1.25", "0.5", "-1"], ["1.25", "-6", "-1"]),
    ];
    const owner = "CLIP_ANGLE_TO_SUPPORT:CLIP-B-R1-B1";
    const first = buildClipAngleSceneModel(visualization).cylinders.find(
      (item) => item.kind === "BOLT" && item.ownerBoltId === owner,
    );
    expect(first?.start).toEqual({ x: 1.25, y: 0.5, z: -1 });
    expect(first?.end).toEqual({ x: 1.25, y: -6, z: -1 });

    visualization.rectangular_full_through_paths = [
      endpointTrace("CLIP-B-R1-B1", ["1.5", "0.5", "-1"], ["1.5", "-6", "-1"]),
    ];
    const latest = buildClipAngleSceneModel(visualization).cylinders.find(
      (item) => item.kind === "BOLT" && item.ownerBoltId === owner,
    );
    expect(latest?.start.x).toBe(1.5);
    expect(latest?.end.x).toBe(1.5);
  });

  it("keeps the shared editor fail-safe when an external caller supplies a mismatched profile", () => {
    const displayed = initialSharedSupport("W_COLUMN_FLANGE", "in", "support");
    const missing = initialSharedSupport("SOLID_RECTANGULAR_COLUMN_FACE", "in", "support");
    const view = render(
      <SupportingMemberEditor
        targetId="W_COLUMN_FLANGE"
        profile={displayed}
        onTargetChange={() => undefined}
        onProfileChange={(change) => {
          change(missing);
        }}
      />,
    );
    fireEvent.change(screen.getByLabelText("Support flange width"), {
      target: { value: "9" },
    });
    expect(missing.width?.value).toBe("8");

    view.rerender(
      <SupportingMemberEditor
        targetId="W_COLUMN_FLANGE"
        profile={missing}
        onTargetChange={() => undefined}
        onProfileChange={() => undefined}
      />,
    );
    expect(screen.queryByLabelText("Support flange width")).not.toBeInTheDocument();
  });
});
