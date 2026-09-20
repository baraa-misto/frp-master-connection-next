import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as clientModule from "../src/api/client";
import { loadColumnBaseWebAngleBenchmark } from "../src/fixtures/columnBaseWebAngleBenchmarks";
import { buildColumnBaseWebAngleSceneModel } from "../src/visualization/columnBaseWebAngleSceneModel";
import { buildFastenerPresentations } from "../src/visualization/fastenerPresentation";
import { ColumnBaseWebAngleWorkspace } from "../src/workspace/ColumnBaseWebAngleWorkspace";
import { columnBaseDesignFixture, columnBasePreviewFixture } from "./columnBaseWebAngleFixtures";

vi.mock("../src/visualization/VisualizationPanel", () => ({
  VisualizationPanel: ({ model }: { readonly model: { readonly boxes: readonly unknown[]; readonly cylinders: readonly unknown[]; readonly materialAxes: readonly unknown[] } }) => <div aria-label="stage-3-7a-viewer">{model.boxes.length} boxes · {model.cylinders.length} cylinders · {model.materialAxes.length} material axes</div>,
}));

describe("Stage 3.7A column-base profile matrix", () => {
  beforeEach(() => {
    vi.spyOn(clientModule, "previewColumnBaseWebAngle").mockResolvedValue(columnBasePreviewFixture());
    vi.spyOn(clientModule, "evaluateColumnBaseWebAngle").mockResolvedValue(columnBaseDesignFixture());
  });
  afterEach(() => { vi.restoreAllMocks(); });

  it("loads exact successor requests for all four profiles while retaining no moment fields", () => {
    for (const family of ["WIDE_FLANGE_I", "RECTANGULAR_HOLLOW_SECTION", "SOLID_RECTANGULAR_SECTION", "ANGLE"] as const) {
      const request = loadColumnBaseWebAngleBenchmark("US_CUSTOMARY", family);
      expect(request).toMatchObject({ orchestration_contract_version: "3.7A-RC1", assembly: "DOUBLE_BASE_ANGLES", column_profile: { profile_family: family } });
      expect(request).not.toHaveProperty("action_reference_s_t_l");
      expect(request).not.toHaveProperty("user_moment");
      expect(request.angle_double_topology).toBe("SAME_SELECTED_LEG_OPPOSITE_FACES");
    }
  });

  it("exposes exactly the controlled profile and assembly selectors", async () => {
    render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("stage-3-7a-viewer");
    expect(screen.getAllByLabelText("Column profile")[0]?.querySelectorAll("option")).toHaveLength(4);
    expect(screen.getAllByRole("option", { name: "W/I" })).toHaveLength(1);
    expect(screen.getAllByRole("option", { name: "Rectangular Hollow Section" })).toHaveLength(1);
    expect(screen.getAllByRole("option", { name: "Solid Rectangular Section" })).toHaveLength(1);
    expect(screen.getAllByRole("option", { name: "Angle" })).toHaveLength(1);
    expect(screen.queryByRole("option", { name: "Channel" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Base-angle assembly").querySelectorAll("option")).toHaveLength(2);
    expect(screen.getByRole("option", { name: "Single" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Double" })).toBeInTheDocument();
  });

  it("switches dynamic W/I, RHS, SRS, and Angle editors without parallel request state", async () => {
    render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("stage-3-7a-viewer");
    const selector = screen.getByLabelText("Column profile");
    expect(screen.getByLabelText("Web thickness")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Selected web face"), { target: { value: "WEB_NEG_FACE" } });
    fireEvent.change(selector, { target: { value: "RECTANGULAR_HOLLOW_SECTION" } });
    expect(screen.getByLabelText("Wall thickness")).toHaveValue("0.5");
    fireEvent.change(screen.getByLabelText("Outside depth"), { target: { value: "11" } });
    fireEvent.change(screen.getByLabelText("Outside width"), { target: { value: "9" } });
    fireEvent.change(screen.getByLabelText("Wall thickness"), { target: { value: "0.6" } });
    expect(screen.getByLabelText("Selected contact face")).toHaveValue("Y_POS_FACE");
    fireEvent.change(screen.getByLabelText("Selected contact face"), { target: { value: "Z_NEG_FACE" } });
    await waitFor(() => {
      const latestRequest = vi.mocked(clientModule.previewColumnBaseWebAngle).mock.calls.at(-1)?.[0];
      expect(latestRequest?.column_profile).toMatchObject({
        profile_family: "RECTANGULAR_HOLLOW_SECTION",
        selected_profile_surface: "Z_NEG_FACE",
      });
    });
    fireEvent.change(selector, { target: { value: "SOLID_RECTANGULAR_SECTION" } });
    expect(screen.getByLabelText("Outside width")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Outside depth"), { target: { value: "11" } });
    fireEvent.change(screen.getByLabelText("Outside width"), { target: { value: "9" } });
    fireEvent.change(screen.getByLabelText("Selected contact face"), { target: { value: "Y_NEG_FACE" } });
    expect(screen.queryByLabelText("Wall thickness")).not.toBeInTheDocument();
    fireEvent.change(selector, { target: { value: "ANGLE" } });
    expect(screen.getByLabelText("Leg Y width")).toHaveValue("6");
    expect(screen.getByLabelText("Leg Z width")).toHaveValue("6");
    fireEvent.change(screen.getByLabelText("Leg Y width"), { target: { value: "6.5" } });
    fireEvent.change(screen.getByLabelText("Leg Z width"), { target: { value: "5.5" } });
    fireEvent.change(screen.getByLabelText("Column angle thickness"), { target: { value: "0.625" } });
    expect(screen.getByLabelText("Selected column leg")).toHaveValue("LEG_Y_OUTER");
    fireEvent.change(screen.getByLabelText("Selected column leg"), { target: { value: "LEG_Z_OUTER" } });
    expect(screen.getByLabelText("Selected broad face")).toBeDisabled();
    expect(screen.getByText(/opposite broad faces of the same selected leg/iu)).toBeInTheDocument();
    expect(screen.queryByText(/different legs/iu)).not.toBeInTheDocument();
  });

  it("uses backend bolt endpoints as one continuous exterior through-bolt with schematic end hardware", () => {
    const visualization = columnBasePreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Controlled visualization required.");
    const successor = {
      ...visualization,
      profile_family: "RECTANGULAR_HOLLOW_SECTION" as const,
      selected_surface: "Y_POS_FACE",
      web_bolts: visualization.web_bolts.map((bolt) => ({
        ...bolt,
        layer_ids: ["POSITIVE_BASE_ANGLE_VERTICAL_LEG", "RHS_NEAR_WALL", "FREE_SHANK_CAVITY", "RHS_FAR_WALL", "NEGATIVE_BASE_ANGLE_VERTICAL_LEG"],
        stack_start: [bolt.stack_start[0], { ...bolt.stack_start[1], value: "4.5" }, bolt.stack_start[2]] as const,
        stack_end: [bolt.stack_end[0], { ...bolt.stack_end[1], value: "-4.5" }, bolt.stack_end[2]] as const,
      })),
    };
    const model = buildColumnBaseWebAngleSceneModel(successor, "3.7A-RC1");
    const shank = model.cylinders.find((item) => item.kind === "BOLT");
    expect(shank).toMatchObject({ start: { y: 4.5 }, end: { y: -4.5 }, hardwareConfiguration: "THROUGH_BOLT" });
    expect(model.cylinders.filter((item) => item.kind === "BOLT" && item.interfaceId === "COLUMN_WEB_BASE_ANGLE_INTERFACE")).toHaveLength(1);
    const hardware = buildFastenerPresentations(model.cylinders).find((item) => item.shank.id.endsWith(":bolt"));
    expect(hardware?.renderedHardware.map((item) => item.kind)).toEqual(["HEAD", "NUT"]);
    expect(model.boxes.some((item) => item.materialRegionId?.includes("CAVITY") === true)).toBe(false);
  });

  it("renders every Angle leg/face endpoint matrix without reconstructing the face sign", () => {
    const visualization = columnBasePreviewFixture().result.visualization;
    if (visualization === null) throw new Error("Controlled visualization required.");
    const sourceBolt = visualization.web_bolts[0];
    if (sourceBolt === undefined) throw new Error("Controlled web bolt required.");
    const cases = [
      ["LEG_Y_OUTER", 0.5, -0.5, "POSITIVE_BASE_ANGLE_VERTICAL_LEG"],
      ["LEG_Y_OUTER", -1, 0, "NEGATIVE_BASE_ANGLE_VERTICAL_LEG"],
      ["LEG_Z_OUTER", 0.5, -0.5, "POSITIVE_BASE_ANGLE_VERTICAL_LEG"],
      ["LEG_Z_OUTER", -1, 0, "NEGATIVE_BASE_ANGLE_VERTICAL_LEG"],
      ["LEG_Y_OUTER", 0.5, -1, "POSITIVE_BASE_ANGLE_VERTICAL_LEG"],
      ["LEG_Z_OUTER", 0.5, -1, "POSITIVE_BASE_ANGLE_VERTICAL_LEG"],
    ] as const;

    for (const [selectedSurface, startT, endT, firstLayer] of cases) {
      const successor = {
        ...visualization,
        profile_family: "ANGLE" as const,
        selected_surface: selectedSurface,
        web_bolts: [
          {
            ...sourceBolt,
            layer_ids: [firstLayer, "SELECTED_ANGLE_COLUMN_LEG"],
            stack_start: [
              sourceBolt.stack_start[0],
              { ...sourceBolt.stack_start[1], value: String(startT) },
              sourceBolt.stack_start[2],
            ] as const,
            stack_end: [
              sourceBolt.stack_end[0],
              { ...sourceBolt.stack_end[1], value: String(endT) },
              sourceBolt.stack_end[2],
            ] as const,
          },
        ],
      };
      const model = buildColumnBaseWebAngleSceneModel(successor, "3.7A-RC1");
      const shanks = model.cylinders.filter((item) => item.kind === "BOLT" && item.interfaceId === "COLUMN_WEB_BASE_ANGLE_INTERFACE");
      expect(shanks).toHaveLength(1);
      expect(shanks[0]).toMatchObject({ start: { y: startT }, end: { y: endT } });
      const hardware = buildFastenerPresentations(shanks)[0];
      if (hardware === undefined) throw new Error("Endpoint-driven hardware required.");
      expect(hardware.head.end.y).toBe(startT);
      expect(hardware.nut.start.y).toBe(endT);
      expect(Math.sign(hardware.nut.end.y - hardware.head.start.y)).toBe(Math.sign(endT - startT));
      expect(hardware.renderedHardware.map((item) => item.kind)).toEqual(["HEAD", "NUT"]);
    }
  });
});
