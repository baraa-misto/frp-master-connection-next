import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useEffect } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationTransportError } from "../src/api/client";
import type { TeeConnectorRequest, TeeInterfaceResult } from "../src/api/teeContracts";
import { loadTeeBenchmark } from "../src/fixtures/teeBenchmarks";
import { ShearConnectionsWorkspace } from "../src/workspace/ShearConnectionsWorkspace";
import { TeeConnectorWorkspace } from "../src/workspace/TeeConnectorWorkspace";
import {
  applyExactPlacementMode,
  clearanceRecoveryFromBackendDetail,
  exactOffset,
  initializeGroupOffsetPlacement,
  requirePlacementOffset,
} from "../src/workspace/teePlacement";
import { teeDesignBlocker, teeSelectionExists } from "../src/workspace/teePreviewState";
import { buildTeeSceneModel } from "../src/visualization/sceneModel";
import { teeValidationMessage } from "../src/workspace/teeValidation";
import { teeDesignFixture, teePreviewFixture, teeVisualizationFixture } from "./teeFixtures";
import historicalStartup from "../../backend/tests/golden/cme1_tee_current_startup.json";

// These historical interaction/geometry assertions retain their original explicit input.
vi.mock("../src/fixtures/connectionWorkspaceDefaults", async (importOriginal) => ({
  ...await importOriginal<typeof import("../src/fixtures/connectionWorkspaceDefaults")>(),
  loadTeeWorkspaceDefault: () => structuredClone(historicalStartup),
}));

const mocks = vi.hoisted(() => ({
  preview: vi.fn(),
  evaluate: vi.fn(),
  viewerMount: vi.fn(),
  viewerUnmount: vi.fn(),
}));

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return {
    ...actual,
    previewTeeConnector: mocks.preview,
    evaluateTeeConnector: mocks.evaluate,
  };
});

vi.mock("../src/workspace/SingleBoltEngineeringWorkspace", () => ({
  SingleBoltEngineeringWorkspace: () => <div>Direct reference workspace sentinel</div>,
}));

vi.mock("../src/visualization/VisualizationPanel", () => ({
  VisualizationPanel: ({ model, onSelect, onAppliedActionValueChange, interfaceHighlight, selection, title }: {
    readonly model: import("../src/visualization/sceneModel").SingleBoltSceneModel;
    readonly onSelect: (selection: { kind: "MEMBER" | "BOLT" | "CONTACT"; id: string }) => void;
    readonly onAppliedActionValueChange: (component: "FX" | "FY" | "FZ" | "MX" | "MY" | "MZ", value: string) => void;
    readonly interfaceHighlight: { readonly interfaceId: string; readonly label: string } | null;
    readonly selection: { readonly kind: "MEMBER" | "BOLT" | "CONTACT"; readonly id: string };
    readonly title: string;
  }) => {
    useEffect(() => {
      mocks.viewerMount();
      return () => { mocks.viewerUnmount(); };
    }, []);
    return (
      <div data-testid="tee-viewer" data-bolts={model.cylinders.filter((value) => value.kind === "BOLT").length} data-a-bolts={model.cylinders.filter((value) => value.kind === "BOLT" && value.interfaceId === "interface-1").length} data-b-bolts={model.cylinders.filter((value) => value.kind === "BOLT" && value.interfaceId === "TEE_INTERFACE_B_FLANGE_TO_SUPPORT").length} data-brace-boxes={model.boxes.filter((value) => value.ownerRole === "BRACE").length} data-boxes={model.boxes.length} data-interface-focus={interfaceHighlight?.interfaceId ?? ""} data-selection={`${selection.kind}:${selection.id}`} data-tee-bounds={JSON.stringify(model.boxes.filter((value) => value.ownerId === "tee-connector").map((value) => [value.center.x, value.center.y, value.center.z, value.size.x]))} data-bolt-centers={JSON.stringify(model.cylinders.filter((value) => value.kind === "BOLT").map((value) => [(value.start.x + value.end.x) / 2, (value.start.y + value.end.y) / 2, (value.start.z + value.end.z) / 2]))}>
        Canonical Tee 3D view
        <span>{title}</span>
        <button type="button" onClick={() => { onSelect({ kind: "CONTACT", id: "patch-b" }); }}>Select support contact</button>
        <button type="button" onClick={() => { const bolt = model.cylinders.filter((value) => value.kind === "BOLT" && value.interfaceId === "interface-1").at(-1); if (bolt !== undefined) onSelect({ kind: "BOLT", id: bolt.ownerBoltId }); }}>Select last Interface A bolt</button>
        <button type="button" onClick={() => { onAppliedActionValueChange("FX", "2"); }}>Edit force arrow</button>
        <button type="button" onClick={() => { onAppliedActionValueChange("MX", "4"); }}>Edit moment arrow</button>
      </div>
    );
  },
}));

function requestAwarePreview(request: TeeConnectorRequest) {
  const response = teePreviewFixture();
  const length = Number(request.connector_dimensions.connector_length.value);
  const anchorPosition = Number(request.connector_length_anchor_position.value);
  const center = request.connector_length_anchor === "CENTER"
    ? anchorPosition
    : request.connector_length_anchor === "POSITIVE_L_END"
      ? anchorPosition - length / 2
      : anchorPosition + length / 2;
  const positiveEnd = center + length / 2;
  const negativeEnd = center - length / 2;
  response.request_id = request.request_id;
  response.result.request_id = request.request_id;
  response.result.connector_dimensions.connector_length = (
    request.connector_dimensions.connector_length.value
  );
  response.result.tee_longitudinal_placement = {
    ...response.result.tee_longitudinal_placement,
    connector_length_anchor: request.connector_length_anchor,
    connector_length_anchor_position: structuredClone(
      request.connector_length_anchor_position,
    ),
    body_center_coordinate: { value: String(center), unit: request.source_length_unit },
    positive_end_coordinate: { value: String(positiveEnd), unit: request.source_length_unit },
    negative_end_coordinate: { value: String(negativeEnd), unit: request.source_length_unit },
    body_geometry_fingerprint: [center, positiveEnd, negativeEnd].map(String).join(":"),
  };
  response.result.connected_member_profile = {
    ...response.result.connected_member_profile,
    profile_id: request.connected_member_profile.profile_id,
    profile_family: request.connected_member_profile.profile_family,
    dimensions: Object.fromEntries(Object.entries(request.connected_member_profile.dimensions).map(([key, value]) => [key, value.value])),
    profile_orientation: request.connected_member_profile.profile_orientation,
    selected_profile_surface: request.connected_member_profile.selected_profile_surface,
    brace_inclination_degrees: request.brace_inclination_degrees,
  };
  if (!request.connected_member_end_trim_enabled && request.brace_inclination_degrees === "25") {
    response.result.connected_member_end_trim = {
      ...response.result.connected_member_end_trim,
      interference_status: "INTERFERENCE_DETECTED",
      interfering_physical_element_ids: ["LEG_Y", "LEG_Z"],
    };
    response.result.warnings = ["CONNECTED_MEMBER_INTERFERES_WITH_TEE_FLANGE_ROOT"];
    response.warnings = [...response.result.warnings];
    response.result.design_check_ready = false;
    response.design_check_ready = false;
  }
  if (request.connected_member_end_trim_enabled) {
    response.result.connected_member_end_trim = {
      ...response.result.connected_member_end_trim,
      enabled: true,
      normalized_clearance: structuredClone(request.connected_member_end_clearance),
      cut_plane_id: "CONNECTED_MEMBER_END_CUT_PLANE",
      cut_plane_origin: { x: "0.75", y: "0", z: "0" },
      cut_plane_normal: { x: "1", y: "0", z: "0" },
      measured_plane_clearance: structuredClone(request.connected_member_end_clearance),
      interference_status: "TRIMMED_CLEAR",
      trimmed_member_geometry_identity: "c".repeat(64),
      fabricated_trim_edge_ids: ["tee-brace:LEG_Y:TRIM_EDGE"],
      bolt_clearances: [{
        bolt_id: "A_B_R1_L1",
        center_to_trim_edge: { value: "0.75", unit: request.source_length_unit },
        hole_edge_to_trim_edge: { value: "0.4685", unit: request.source_length_unit },
        trim_edge_id: "tee-brace:LEG_Y:TRIM_EDGE",
      }],
      governing_bolt_id: "A_B_R1_L1",
      governing_trim_edge_id: "tee-brace:LEG_Y:TRIM_EDGE",
      minimum_hole_edge_clearance: {
        value: "0.4685",
        unit: request.source_length_unit,
      },
    };
    response.result.design_check_ready = false;
    response.design_check_ready = false;
  }
  for (const [layout, result] of [
    [request.interface_a_layout, response.result.interface_a],
    [request.interface_b_layout, response.result.interface_b],
  ] as const) {
    result.placement.placement_mode = layout.placement_mode ?? "EDGE_DISTANCE_CONTROLLED";
    if (layout.vertical_offset !== undefined) {
      result.placement.vertical_offset = structuredClone(layout.vertical_offset);
    }
    if (layout.horizontal_offset !== undefined) {
      result.placement.horizontal_offset = structuredClone(layout.horizontal_offset);
    }
    if (layout.row_count === 1) {
      result.preview.plan_availability = "CALCULATION_NOT_SUPPORTED";
      result.preview.design_check_ready = false;
      result.preview.automatic_demand_result = {
        availability: "CALCULATION_NOT_SUPPORTED",
      } as TeeInterfaceResult["preview"]["automatic_demand_result"];
      response.design_check_ready = false;
      response.result.design_check_ready = false;
    }
  }
  if (response.result.visualization !== null) {
    const visualization = response.result.visualization;
    visualization.connected_member_profile = response.result.connected_member_profile;
    visualization.selected_connected_surface_id = request.connected_member_profile.selected_profile_surface;
    const bolts = (prefix: "A" | "B", countRows: number, countLines: number) => {
      const source = prefix === "A" ? visualization.interface_a_bolts[0] : visualization.interface_b_bolts[0];
      if (source === undefined) throw new Error("A Tee bolt fixture is required.");
      return Array.from({ length: countRows }, (_, row) => Array.from(
        { length: countLines },
        (_, line) => {
          const bolt = structuredClone(source);
          bolt.bolt_location_id = `${prefix}_B_R${String(row + 1)}_L${String(line + 1)}`;
          return bolt;
        },
      )).flat();
    };
    visualization.interface_a_bolts = bolts(
      "A",
      request.interface_a_layout.row_count,
      request.interface_a_layout.bolts_per_row,
    );
    visualization.interface_b_bolts = bolts(
      "B",
      request.interface_b_layout.row_count,
      request.interface_b_layout.bolts_per_row,
    );
    const base = visualization.base_connection;
    for (const primitive of base.primitives.filter((value) => value.owner_id === "tee-connector")) {
      const xStart = primitive.parameters.find((value) => value.name === "x_start");
      const xEnd = primitive.parameters.find((value) => value.name === "x_end");
      if (xStart !== undefined) xStart.value = String(negativeEnd);
      if (xEnd !== undefined) xEnd.value = String(positiveEnd);
      if (primitive.center !== null && primitive.x_axis !== null) {
        primitive.center = {
          x: String(Number(primitive.center.x) + Number(primitive.x_axis.x) * center),
          y: String(Number(primitive.center.y) + Number(primitive.x_axis.y) * center),
          z: String(Number(primitive.center.z) + Number(primitive.x_axis.z) * center),
          unit: primitive.center.unit,
        };
      }
    }
    const template = base.primitives.find((primitive) => primitive.kind === "BOX");
    if (template === undefined) throw new Error("A Tee box fixture is required.");
    const elementCount = request.connected_member_profile.profile_family === "FLAT_PLATE" ? 1 : 2;
    base.primitives = [
      ...base.primitives.filter((primitive) => primitive.owner_id !== "member-a" && primitive.owner_id !== "tee-brace"),
      ...Array.from({ length: elementCount }, (_, index) => ({
        ...structuredClone(template),
        id: `tee-brace:ELEMENT_${String(index + 1)}`,
        owner_id: "tee-brace",
        physical_element_id: `ELEMENT_${String(index + 1)}`,
        material_region_id: `ELEMENT_${String(index + 1)}`,
      })),
    ];
  }
  return response;
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<Value>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe("Stage 3.2 unified Tee connection workspace", () => {
  beforeEach(() => {
    mocks.preview.mockReset();
    mocks.evaluate.mockReset();
    mocks.viewerMount.mockReset();
    mocks.viewerUnmount.mockReset();
    mocks.preview.mockImplementation((request: TeeConnectorRequest) => Promise.resolve(requestAwarePreview(request)));
    mocks.evaluate.mockResolvedValue(teeDesignFixture());
  });

  it("shows the R13 length-anchor, body-position, finite-end, and +L diagnostics", async () => {
    render(<TeeConnectorWorkspace />);
    await screen.findByTestId("tee-viewer");

    const anchor = screen.getByLabelText("Length anchor");
    expect(anchor).toBeEnabled();
    expect(anchor).toHaveValue("CENTER");
    expect(within(anchor).getByRole("option", { name: "Centered" })).toBeInTheDocument();
    expect(within(anchor).getByRole("option", { name: "Keep upper end fixed" }))
      .toBeInTheDocument();
    expect(within(anchor).getByRole("option", { name: "Keep lower end fixed" }))
      .toBeInTheDocument();
    expect(screen.getByLabelText("Tee vertical position")).toHaveValue("0");
    expect(screen.getByText(/Position of the selected length anchor along the Tee longitudinal axis/iu))
      .toBeInTheDocument();
    expect(screen.getByText("Tee longitudinal datum")).toBeInTheDocument();
    expect(screen.getByText("Tee +L direction")).toBeInTheDocument();
    expect(screen.getAllByText("Tee +L end clearance").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tee −L end clearance").length).toBeGreaterThan(0);
  });

  it("converts anchor modes from current server extents without a viewer jump", async () => {
    render(<TeeConnectorWorkspace />);
    const viewer = await screen.findByTestId("tee-viewer");
    const initialBounds = viewer.getAttribute("data-tee-bounds");
    const initialBolts = viewer.getAttribute("data-bolt-centers");
    const anchor = screen.getByLabelText("Length anchor");

    fireEvent.change(anchor, { target: { value: "POSITIVE_L_END" } });
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.connector_length_anchor).toBe("POSITIVE_L_END");
      expect(submitted.connector_length_anchor_position).toEqual({ value: "4", unit: "in" });
      expect(anchor).toBeEnabled();
    });
    expect(viewer).toHaveAttribute("data-tee-bounds", initialBounds);
    expect(viewer).toHaveAttribute("data-bolt-centers", initialBolts);

    fireEvent.change(anchor, { target: { value: "NEGATIVE_L_END" } });
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.connector_length_anchor).toBe("NEGATIVE_L_END");
      expect(submitted.connector_length_anchor_position).toEqual({ value: "-4", unit: "in" });
    });
    expect(viewer).toHaveAttribute("data-tee-bounds", initialBounds);
    expect(viewer).toHaveAttribute("data-bolt-centers", initialBolts);

    fireEvent.change(anchor, { target: { value: "CENTER" } });
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.connector_length_anchor).toBe("CENTER");
      expect(submitted.connector_length_anchor_position).toEqual({ value: "0", unit: "in" });
    });
    expect(viewer).toHaveAttribute("data-tee-bounds", initialBounds);
    expect(viewer).toHaveAttribute("data-bolt-centers", initialBolts);
    expect(mocks.viewerMount).toHaveBeenCalledTimes(1);
  });

  it("refuses anchor conversion until a current backend preview supplies exact extents", () => {
    const pending = deferred<ReturnType<typeof teePreviewFixture>>();
    mocks.preview.mockReturnValue(pending.promise);

    render(<TeeConnectorWorkspace />);

    expect(screen.getByLabelText("Length anchor")).toBeDisabled();
  });

  it("applies centered and one-sided 6-to-8 length growth while bolts stay fixed", async () => {
    render(<TeeConnectorWorkspace />);
    const viewer = await screen.findByTestId("tee-viewer");
    const bolts = viewer.getAttribute("data-bolt-centers");
    const length = screen.getByLabelText("Connector length");
    const anchor = screen.getByLabelText("Length anchor");

    fireEvent.change(length, { target: { value: "6" } });
    await waitFor(() => {
      expect(screen.getByText("-3 in / 3 in")).toBeInTheDocument();
    });
    fireEvent.change(anchor, { target: { value: "POSITIVE_L_END" } });
    await waitFor(() => {
      expect(screen.getByLabelText("Tee vertical position")).toHaveValue("3");
    });
    fireEvent.change(length, { target: { value: "8" } });
    await waitFor(() => {
      expect(screen.getByText("-5 in / 3 in")).toBeInTheDocument();
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.connector_length_anchor_position.value).toBe("3");
    });
    expect(viewer).toHaveAttribute("data-bolt-centers", bolts);

    fireEvent.change(length, { target: { value: "6" } });
    await waitFor(() => { expect(anchor).toBeEnabled(); });
    fireEvent.change(anchor, { target: { value: "NEGATIVE_L_END" } });
    await waitFor(() => {
      expect(screen.getByLabelText("Tee vertical position")).toHaveValue("-3");
    });
    fireEvent.change(length, { target: { value: "8" } });
    await waitFor(() => {
      expect(screen.getByText("-3 in / 5 in")).toBeInTheDocument();
    });
    expect(viewer).toHaveAttribute("data-bolt-centers", bolts);
  });

  it("translates only the Tee body, stales design, and preserves the last-valid scene", async () => {
    mocks.preview.mockImplementation((request: TeeConnectorRequest) => {
      if (request.connector_length_anchor_position.value === "4") {
        return Promise.reject(new EvaluationTransportError(
          "VALIDATION",
          422,
          "The server rejected the translated Tee body.",
          {
            detail: "Complete-hole clearance -1.2815 in; governing Tee end TEE_NEGATIVE_L_END; governing bolt A_B_R1_L1.",
          },
        ));
      }
      return Promise.resolve(requestAwarePreview(request));
    });
    render(<TeeConnectorWorkspace />);
    const viewer = await screen.findByTestId("tee-viewer");
    const initialBounds = viewer.getAttribute("data-tee-bounds");
    const bolts = viewer.getAttribute("data-bolt-centers");
    const run = screen.getByRole("button", { name: "Run Design Check" });
    fireEvent.click(run);
    await waitFor(() => { expect(mocks.evaluate).toHaveBeenCalledTimes(1); });

    const position = screen.getByLabelText("Tee vertical position");
    fireEvent.change(position, { target: { value: "1" } });
    await waitFor(() => {
      expect(viewer.getAttribute("data-tee-bounds")).not.toBe(initialBounds);
      expect(screen.getByText(/Design results are stale/u)).toBeInTheDocument();
    });
    expect(viewer).toHaveAttribute("data-bolt-centers", bolts);
    const validBounds = viewer.getAttribute("data-tee-bounds");

    fireEvent.change(position, { target: { value: "4" } });
    await waitFor(() => {
      expect(screen.getAllByText(/Complete-hole clearance -1\.2815 in/u).length)
        .toBeGreaterThan(0);
    });
    expect(viewer).toHaveAttribute("data-tee-bounds", validBounds);
    expect(viewer).toHaveAttribute("data-bolt-centers", bolts);
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(mocks.viewerMount).toHaveBeenCalledTimes(1);
  });

  it("converts exact decimal edge placement to signed group offsets", () => {
    expect(exactOffset("1", 2, "2", "8")).toBe("-2");
    expect(exactOffset("1.2815", 2, "2", "8")).toBe("-1.7185");
    expect(exactOffset("5", 2, "2", "8")).toBe("2");
    expect(exactOffset("4.5", 2, "2", "8")).toBe("1.5");
    expect(exactOffset("-1", 2, "2", "8")).toBe("-4");
    expect(exactOffset("", 1, "", "")).toBe("0");
    expect(requirePlacementOffset("0")).toBe("0");
    expect(() => { requirePlacementOffset(undefined); }).toThrow(/requires both in-plane offsets/u);
    const request = teePreviewFixture();
    const layout: TeeConnectorRequest["interface_a_layout"] = {
      row_count: 2,
      bolts_per_row: 2,
      pitch: { value: "2", unit: "in" },
      gauge: { value: "2", unit: "in" },
      unloaded_end_distance: { value: "1", unit: "in" },
      loaded_end_distance: { value: "1", unit: "in" },
      negative_side_distance: { value: "1", unit: "in" },
      positive_side_distance: { value: "1", unit: "in" },
    };
    initializeGroupOffsetPlacement(layout, "8", "4");
    expect(layout).toMatchObject({
      placement_mode: "GROUP_OFFSET_CONTROLLED",
      vertical_offset: { value: "-2", unit: "in" },
      horizontal_offset: { value: "0", unit: "in" },
    });
    expect(applyExactPlacementMode(
      layout,
      "EDGE_DISTANCE_CONTROLLED",
      request.result.interface_a.placement,
    )).toBe(true);
    expect(layout.placement_mode).toBe("EDGE_DISTANCE_CONTROLLED");
    expect(layout.vertical_offset).toBeUndefined();
    expect(applyExactPlacementMode(layout, "EDGE_DISTANCE_CONTROLLED", null)).toBe(true);
    const implicitEdgeLayout = structuredClone(layout);
    delete implicitEdgeLayout.placement_mode;
    expect(applyExactPlacementMode(
      implicitEdgeLayout,
      "EDGE_DISTANCE_CONTROLLED",
      null,
    )).toBe(true);
    const mismatchedTrace = structuredClone(request.result.interface_a.placement);
    mismatchedTrace.equivalent_edge_distances.pitch = "2.1";
    expect(applyExactPlacementMode(
      layout,
      "GROUP_OFFSET_CONTROLLED",
      mismatchedTrace,
    )).toBe(false);
    expect(clearanceRecoveryFromBackendDetail(null, "TEE_INTERFACE_A_BRACE_TO_STEM")).toBeNull();
    expect(clearanceRecoveryFromBackendDetail("Unrelated detail.", "TEE_INTERFACE_A_BRACE_TO_STEM")).toBeNull();
    expect(clearanceRecoveryFromBackendDetail(
      "Complete-hole clearance -0.2815 in; governing boundary TEE_INTERFACE_A_BRACE_TO_STEM:VERTICAL_POSITIVE; governing bolt A_B_R2_L1.",
      "TEE_INTERFACE_A_BRACE_TO_STEM",
    )).toEqual({ clearance: "-0.2815", unit: "in", direction: "down" });
    expect(clearanceRecoveryFromBackendDetail(
      "Complete-hole clearance -1 in; governing boundary TEE_INTERFACE_A_BRACE_TO_STEM:VERTICAL_NEGATIVE; governing bolt A_B_R2_L1.",
      "TEE_INTERFACE_A_BRACE_TO_STEM",
    )).toEqual({ clearance: "-1", unit: "in", direction: "up" });
    expect(clearanceRecoveryFromBackendDetail(
      "Complete-hole clearance -0.1 in; governing boundary TEE_INTERFACE_A_BRACE_TO_STEM:HORIZONTAL_POSITIVE; governing bolt A_B_R2_L1.",
      "TEE_INTERFACE_A_BRACE_TO_STEM",
    )).toEqual({ clearance: "-0.1", unit: "in", direction: "toward negative H" });
    expect(clearanceRecoveryFromBackendDetail(
      "Complete-hole clearance -0.1 in; governing boundary TEE_INTERFACE_B_FLANGE_TO_SUPPORT:HORIZONTAL_NEGATIVE; governing bolt B_B_R2_L1.",
      "TEE_INTERFACE_B_FLANGE_TO_SUPPORT",
    )).toEqual({ clearance: "-0.1", unit: "in", direction: "toward positive H" });
    expect(clearanceRecoveryFromBackendDetail(
      "Complete-hole clearance -0.1 in; governing boundary TEE_INTERFACE_B_FLANGE_TO_SUPPORT:UNKNOWN; governing bolt B_B_R2_L1.",
      "TEE_INTERFACE_B_FLANGE_TO_SUPPORT",
    )).toBeNull();
    expect(clearanceRecoveryFromBackendDetail(
      "Complete-hole clearance -0.1 in; governing boundary TEE_INTERFACE_B_FLANGE_TO_SUPPORT:HORIZONTAL_NEGATIVE; governing bolt B_B_R2_L1.",
      "TEE_INTERFACE_A_BRACE_TO_STEM",
    )).toBeNull();

    const missingVertical = structuredClone(layout);
    missingVertical.placement_mode = "GROUP_OFFSET_CONTROLLED";
    delete missingVertical.vertical_offset;
    const invalidOffsetRequest = loadTeeBenchmark("US_CUSTOMARY");
    invalidOffsetRequest.interface_a_layout = missingVertical;
    expect(teeValidationMessage(invalidOffsetRequest)).toMatch(/requires finite vertical/u);

    const blankBodyPosition = loadTeeBenchmark("US_CUSTOMARY");
    blankBodyPosition.connector_length_anchor_position.value = "";
    expect(teeValidationMessage(blankBodyPosition)).toMatch(/longitudinal position/u);
    const nonfiniteBodyPosition = loadTeeBenchmark("US_CUSTOMARY");
    nonfiniteBodyPosition.connector_length_anchor_position.value = "NaN";
    expect(teeValidationMessage(nonfiniteBodyPosition)).toMatch(/longitudinal position/u);
  });

  it("does not reposition when exact mode conversion is unavailable", async () => {
    const pending = deferred<ReturnType<typeof teePreviewFixture>>();
    mocks.preview.mockReturnValue(pending.promise);
    render(<TeeConnectorWorkspace />);

    const placementMethod = await screen.findByLabelText("Interface A placement method");
    const interfaceA = screen.getByText("Brace ↔ Tee Stem", { selector: "span" }).closest("details");
    if (interfaceA === null) throw new Error("Interface A layout group is required.");
    expect(placementMethod).toHaveValue("GROUP_OFFSET_CONTROLLED");
    fireEvent.change(placementMethod, { target: { value: "EDGE_DISTANCE_CONTROLLED" } });
    expect(placementMethod).toHaveValue("GROUP_OFFSET_CONTROLLED");
    expect(within(interfaceA).getByText(/Exact conversion is unavailable/iu)).toBeInTheDocument();
    expect(screen.getByLabelText("Interface A vertical offset")).toHaveValue("-2");
    expect(mocks.preview).toHaveBeenCalledTimes(1);
  });

  it("retains only selections that exist in the accepted model", () => {
    const model = buildTeeSceneModel(teeVisualizationFixture());
    const memberId = model.boxes[0]?.ownerId;
    const boltId = model.cylinders.find((value) => value.kind === "BOLT")?.ownerBoltId;
    const contactId = model.zones[0]?.patchId;
    if (memberId === undefined || boltId === undefined || contactId === undefined) {
      throw new Error("The selection fixture requires a member, bolt, and contact.");
    }
    expect(teeSelectionExists(model, { kind: "MEMBER", id: "tee-brace" })).toBe(true);
    expect(teeSelectionExists(model, { kind: "MEMBER", id: memberId })).toBe(true);
    expect(teeSelectionExists(model, { kind: "MEMBER", id: "missing-member" })).toBe(false);
    expect(teeSelectionExists(model, { kind: "BOLT", id: boltId })).toBe(true);
    expect(teeSelectionExists(model, { kind: "BOLT", id: "missing-bolt" })).toBe(false);
    expect(teeSelectionExists(model, { kind: "CONTACT", id: contactId })).toBe(true);
    expect(teeSelectionExists(model, { kind: "CONTACT", id: "missing-contact" })).toBe(false);
  });

  it("fails design closed for local, pending, absent, and unready preview states", () => {
    const current = teePreviewFixture().result;
    expect(teeDesignBlocker("Local reason.", "NO_VALID_PREVIEW", null)).toBe("Local reason.");
    expect(teeDesignBlocker(null, "PREVIEW_PENDING", null)).toBe("Awaiting current backend preview.");
    expect(teeDesignBlocker(null, "CURRENT_VALID", null)).toBe("A current backend Tee preview is required.");
    current.design_check_ready = false;
    expect(teeDesignBlocker(null, "CURRENT_VALID", current)).toBe(
      "The backend has not marked both interfaces design-ready.",
    );
    current.design_check_ready = true;
    expect(teeDesignBlocker(null, "CURRENT_VALID", current)).toBeNull();
  });

  it("keeps the direct connection default and selects Tee in the same workspace", async () => {
    render(<ShearConnectionsWorkspace />);
    expect(screen.getByText("Direct reference workspace sentinel")).toBeInTheDocument();
    const selector = screen.getByRole("combobox", { name: "Connection type" });
    expect(selector).toHaveValue("DIRECT_REFERENCE");
    expect(screen.getByRole("option", { name: "Brace/beam connection — Direct" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Brace/beam connection — Tee connector" })).toBeInTheDocument();
    expect(screen.queryByText(/two interfaces/i)).not.toBeInTheDocument();
    fireEvent.change(selector, { target: { value: "FRP_TEE" } });
    expect(await screen.findByRole("heading", { name: "FRP Angle Brace → FRP Tee → W Column Flange" })).toBeInTheDocument();
    fireEvent.change(selector, { target: { value: "DIRECT_REFERENCE" } });
    expect(screen.getByText("Direct reference workspace sentinel")).toBeInTheDocument();
  });

  it("renders the real two-interface Tee model, controlled materials, and grouped limitation", async () => {
    render(<TeeConnectorWorkspace />);
    await waitFor(() => { expect(mocks.preview).toHaveBeenCalled(); });
    expect(await screen.findByTestId("tee-viewer")).toHaveAttribute("data-bolts", "8");
    expect(screen.getByText("Canonical Tee 3D view")).toBeInTheDocument();
    expect(screen.getAllByText("Brace ↔ Tee Stem").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tee Flange ↔ Support").length).toBeGreaterThan(0);
    expect(screen.getByText(/Tee connector body · Not evaluated/)).toBeInTheDocument();
    expect(screen.getByText(/Pultruded FRP · ICE locked data/)).toBeInTheDocument();
    expect(screen.getByText(/316SS · ASTM F593 snapshot/)).toBeInTheDocument();
    expect(screen.queryByText(/carbon steel/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Select support contact" }));
  });

  it("uses the shared persistent-view shell without remounting the viewer for sidebar focus", async () => {
    render(<TeeConnectorWorkspace />);
    const viewer = await screen.findByTestId("tee-viewer");
    const sidebar = screen.getByLabelText("Tee connector engineering inputs");
    expect(sidebar).toHaveClass("properties-sidebar");
    expect(sidebar.closest(".workspace-body")).not.toBeNull();
    expect(viewer.closest(".persistent-connection-viewer")).not.toBeNull();
    await waitFor(() => { expect(mocks.viewerMount).toHaveBeenCalledTimes(1); });

    mocks.preview.mockClear();
    fireEvent.click(screen.getByText("Brace ↔ Tee Stem", { selector: "span" }));
    expect(viewer).toHaveAttribute("data-interface-focus", "TEE_INTERFACE_A_BRACE_TO_STEM");
    fireEvent.click(screen.getByText("Tee Flange ↔ Support", { selector: "span" }));
    expect(viewer).toHaveAttribute("data-interface-focus", "TEE_INTERFACE_B_FLANGE_TO_SUPPORT");
    expect(mocks.viewerMount).toHaveBeenCalledTimes(1);
    expect(mocks.viewerUnmount).not.toHaveBeenCalled();
    expect(mocks.preview).not.toHaveBeenCalled();
    expect(screen.queryByText(/Design results are stale/)).not.toBeInTheDocument();
  });

  it("synchronizes member groups to canonical scene owners without engineering updates", async () => {
    render(<TeeConnectorWorkspace />);
    const viewer = await screen.findByTestId("tee-viewer");
    mocks.preview.mockClear();

    fireEvent.click(screen.getByText("Connected Member", { selector: "span" }));
    expect(viewer).toHaveAttribute("data-selection", "MEMBER:tee-brace");
    fireEvent.click(screen.getByText("Supporting Member", { selector: "span" }));
    expect(viewer).toHaveAttribute("data-selection", "MEMBER:tee-support");
    fireEvent.click(screen.getByText("Connector", { selector: "span" }));
    expect(viewer).toHaveAttribute("data-selection", "MEMBER:tee-connector");
    expect(mocks.preview).not.toHaveBeenCalled();
    expect(screen.queryByText(/Design results are stale/)).not.toBeInTheDocument();
  });

  it("focuses each physical interface from any control without changing edit semantics", async () => {
    render(<TeeConnectorWorkspace />);
    const viewer = await screen.findByTestId("tee-viewer");
    const interfaceA = screen.getByText(/Brace .* Tee Stem/u, { selector: "span" }).closest("details");
    const interfaceB = screen.getByText(/Tee Flange .* Support/u, { selector: "span" }).closest("details");
    if (interfaceA === null || interfaceB === null) throw new Error("Both interface groups are required.");
    const pitchA = within(interfaceA).getByLabelText("Pitch");
    const pitchB = within(interfaceB).getByLabelText("Pitch");

    mocks.preview.mockClear();
    fireEvent.focus(pitchA);
    expect(viewer).toHaveAttribute("data-interface-focus", "TEE_INTERFACE_A_BRACE_TO_STEM");
    expect(mocks.preview).not.toHaveBeenCalled();
    expect(screen.queryByText(/Design results are stale/)).not.toBeInTheDocument();
    fireEvent.change(pitchA, { target: { value: "2.25" } });
    expect(viewer).toHaveAttribute("data-interface-focus", "TEE_INTERFACE_A_BRACE_TO_STEM");

    fireEvent.focus(pitchB);
    expect(viewer).toHaveAttribute("data-interface-focus", "TEE_INTERFACE_B_FLANGE_TO_SUPPORT");
    fireEvent.change(pitchB, { target: { value: "2.5" } });
    expect(viewer).toHaveAttribute("data-interface-focus", "TEE_INTERFACE_B_FLANGE_TO_SUPPORT");
  });

  it("uses stable interface IDs while the first preview is pending", () => {
    const pending = deferred<ReturnType<typeof teePreviewFixture>>();
    mocks.preview.mockReturnValue(pending.promise);
    render(<TeeConnectorWorkspace />);

    fireEvent.click(screen.getByText(/Brace .* Tee Stem/u, { selector: "span" }));
    fireEvent.click(screen.getByText(/Tee Flange .* Support/u, { selector: "span" }));
    expect(screen.getByRole("heading", { name: "Canonical Tee model unavailable" })).toBeInTheDocument();
  });

  it("filters physical surfaces and profile-specific controls for every enabled brace family", async () => {
    render(<TeeConnectorWorkspace />);
    await screen.findByTestId("tee-viewer");
    const interfaceA = screen.getByText("Brace ↔ Tee Stem", { selector: "span" }).closest("details");
    if (interfaceA === null) throw new Error("Interface A layout group is required.");
    const connected = screen.getByText("Connected Member", { selector: "span" }).closest("details");
    if (connected === null) throw new Error("Connected-member group is required.");
    const profile = within(connected).getByLabelText("Brace profile family");
    const surface = within(connected).getByLabelText("Brace connection surface");

    expect(profile).toHaveValue("ANGLE");
    expect(within(connected).getByLabelText("Leg Y")).toBeInTheDocument();
    expect(within(connected).getByRole("option", { name: /Round tube/ })).toBeDisabled();
    expect(within(connected).getAllByRole("option").filter((option) => (
      option.parentElement === surface
    )).map((option) => option.getAttribute("value"))).toEqual(["LEG_Y_OUTER", "LEG_Z_OUTER"]);

    for (const [family, expectedControl, expectedSurfaces, title] of [
      ["CHANNEL", "Web thickness", ["WEB_OUTER", "FLANGE_POS_OUTER", "FLANGE_NEG_OUTER"], "FRP Channel Brace"],
      ["WIDE_FLANGE_I", "Flange thickness", ["WEB_POS_FACE", "WEB_NEG_FACE", "FLANGE_POS_OUTER", "FLANGE_NEG_OUTER"], "FRP Wide-flange / I Brace"],
      ["RECTANGULAR_HOLLOW_SECTION", "Wall thickness", ["Y_POS_FACE", "Y_NEG_FACE", "Z_POS_FACE", "Z_NEG_FACE"], "FRP Rectangular tube Brace"],
      ["FLAT_PLATE", "Width", ["FACE_POS", "FACE_NEG"], "FRP Flat plate Brace"],
    ] as const) {
      fireEvent.change(profile, { target: { value: family } });
      expect(within(connected).getByLabelText(expectedControl)).toBeInTheDocument();
      expect(Array.from((surface as HTMLSelectElement).options).map((option) => option.value)).toEqual(expectedSurfaces);
      expect(screen.getAllByText(new RegExp(title, "u")).length).toBeGreaterThan(0);
    }

    fireEvent.change(within(connected).getByLabelText("Profile roll about member axis"), {
      target: { value: "ROTATION_90" },
    });
    fireEvent.change(surface, { target: { value: "FACE_NEG" } });

    await waitFor(() => {
      const latest = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest | undefined;
      expect(latest?.connected_member_profile.profile_family).toBe("FLAT_PLATE");
    });
    const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
    expect(submitted.orchestration_contract_version).toBe("3.3C2-RC1");
    expect(submitted).not.toHaveProperty("brace_dimensions");
    expect(submitted.connected_member_profile).toMatchObject({
      role: "BRACE",
      profile_family: "FLAT_PLATE",
      size_basis: "CUSTOM_DIMENSIONS",
      profile_orientation: "ROTATION_90",
      selected_profile_surface: "FACE_NEG",
      material_kind: "PULTRUDED_FRP",
    });

    mocks.preview.mockClear();
    fireEvent.change(profile, { target: { value: "ROUND_HOLLOW_SECTION" } });
    expect(profile).toHaveValue("FLAT_PLATE");
    expect(mocks.preview).not.toHaveBeenCalled();
    const unavailable = structuredClone(submitted);
    unavailable.connected_member_profile.profile_family = "ROUND_HOLLOW_SECTION";
    expect(teeValidationMessage(unavailable)).toMatch(/separately defined compatible interface/u);
  });

  it("keeps fabrication end trim explicit, unit-aware, validated, and backend-reported", async () => {
    render(<TeeConnectorWorkspace />);
    await screen.findByTestId("tee-viewer");
    const connected = screen.getByText("Connected Member", { selector: "span" }).closest("details");
    if (connected === null) throw new Error("Connected-member group is required.");
    const trim = within(connected).getByRole("region", { name: "Member end trim" });
    const toggle = within(trim).getByLabelText("Apply end trim clearance");

    expect(toggle).not.toBeChecked();
    expect(within(trim).getByText("No fabrication end trim")).toBeInTheDocument();
    expect(within(trim).queryByLabelText("End clearance to Tee flange")).not.toBeInTheDocument();
    expect(screen.getByText("No fabrication end trim", { selector: "dd" })).toBeInTheDocument();

    fireEvent.click(toggle);
    const clearance = within(trim).getByLabelText("End clearance to Tee flange");
    expect(clearance).toHaveValue("0");
    expect(within(trim).getByText("in")).toBeInTheDocument();
    expect(within(trim).getByText(/Perpendicular gap between the fabricated member end/iu))
      .toBeInTheDocument();
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.connected_member_end_trim_enabled).toBe(true);
      expect(submitted.connected_member_end_clearance).toEqual({ value: "0", unit: "in" });
      expect(screen.getByText("Applied", { selector: "dd" })).toBeInTheDocument();
      expect(screen.getByText("Trimmed Clear", { selector: "dd" })).toBeInTheDocument();
      expect(screen.getByText(/0\.4685 in/u, { selector: "dd" })).toBeInTheDocument();
    });

    mocks.preview.mockClear();
    fireEvent.change(clearance, { target: { value: "-0.01" } });
    expect(screen.getAllByText(/finite nonnegative value/u).length).toBeGreaterThan(0);
    await new Promise((resolve) => { setTimeout(resolve, 350); });
    expect(mocks.preview).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();

    fireEvent.click(toggle);
    expect(within(trim).queryByLabelText("End clearance to Tee flange")).not.toBeInTheDocument();
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.connected_member_end_trim_enabled).toBe(false);
      expect(submitted.connected_member_end_clearance).toBeNull();
    });
  });

  it("shows backend interference and preserves the last valid trimmed preview through recovery", async () => {
    mocks.preview.mockImplementation((request: TeeConnectorRequest) => {
      if (
        request.connected_member_end_trim_enabled
        && request.connected_member_end_clearance?.value === "1"
      ) {
        return Promise.reject(new EvaluationTransportError(
          "VALIDATION",
          422,
          "The server rejected the current member end trim.",
          {
            detail: {
              code: "CANONICAL_TEE_MAPPING_INVALID",
              message: "Hole-edge-to-trim clearance -0.2815 in; governing bolt A_B_R1_L2; move the bolt group away from the fabricated end or reduce clearance.",
            },
          },
        ));
      }
      return Promise.resolve(requestAwarePreview(request));
    });
    render(<TeeConnectorWorkspace />);
    await screen.findByTestId("tee-viewer");

    fireEvent.change(screen.getByLabelText("Brace inclination"), { target: { value: "25" } });
    await waitFor(() => {
      expect(screen.getByText("Interference Detected", { selector: "dd" })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();

    fireEvent.click(screen.getByLabelText("Apply end trim clearance"));
    fireEvent.change(screen.getByLabelText("End clearance to Tee flange"), {
      target: { value: "0.25" },
    });
    await waitFor(() => {
      expect(screen.getByText("Trimmed Clear", { selector: "dd" })).toBeInTheDocument();
      expect(screen.getByText(/0\.4685 in/u, { selector: "dd" })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("End clearance to Tee flange"), {
      target: { value: "1" },
    });
    await waitFor(() => {
      expect(screen.getAllByText(/Hole-edge-to-trim clearance -0\.2815 in/u).length)
        .toBeGreaterThan(0);
    });
    expect(screen.getAllByText(/showing last valid preview/u).length).toBeGreaterThan(0);
    expect(screen.getByText("Trimmed Clear", { selector: "dd" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("End clearance to Tee flange"), {
      target: { value: "0.5" },
    });
    await waitFor(() => {
      expect(screen.queryAllByText(/showing last valid preview/u)).toHaveLength(0);
    });
    expect(screen.getByText("0.5 in", { selector: "dd" })).toBeInTheDocument();
  });

  it("stales design for profile engineering edits but not for display-only interface focus", async () => {
    render(<TeeConnectorWorkspace />);
    const run = await screen.findByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(run).toBeEnabled(); });
    fireEvent.click(run);
    await waitFor(() => { expect(mocks.evaluate).toHaveBeenCalledTimes(1); });
    mocks.preview.mockClear();

    fireEvent.click(screen.getByText("Brace ↔ Tee Stem", { selector: "span" }));
    expect(screen.queryByText(/Design results are stale/)).not.toBeInTheDocument();
    expect(mocks.preview).not.toHaveBeenCalled();
    expect(mocks.evaluate).toHaveBeenCalledTimes(1);

    const connected = screen.getByText("Connected Member", { selector: "span" }).closest("details");
    if (connected === null) throw new Error("Connected-member group is required.");
    fireEvent.change(within(connected).getByLabelText("Brace profile family"), {
      target: { value: "CHANNEL" },
    });
    expect(screen.getByText(/Design results are stale/)).toBeInTheDocument();
    expect(mocks.evaluate).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(screen.getByText(/3D model reflects the current backend preview/)).toBeInTheDocument();
    });
  });

  it("edits every Tee, support, brace, A/B layout, action, and reference control", async () => {
    render(<TeeConnectorWorkspace />);
    await screen.findByTestId("tee-viewer");

    fireEvent.change(screen.getByLabelText("Supporting member"), { target: { value: "W_BEAM_FLANGE" } });
    expect(screen.getByRole("heading", { name: /W beam flange/i })).toBeInTheDocument();
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.support_target_id).toBe("W_BEAM_FLANGE");
    });
    fireEvent.change(screen.getByLabelText("Support contact face"), {
      target: { value: "FLANGE_NEG_OUTER" },
    });

    for (const label of [
      "Connector length", "Flange width", "Flange thickness", "Stem depth", "Stem thickness",
      "Leg Y", "Leg Z", "Thickness", "Member / view length", "Support member / view length", "Support depth",
      "Support flange width", "Support web thickness", "Support flange thickness", "Bolt diameter",
    ]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: "5" } });
    }
    for (const [title, interfaceLabel] of [["Brace ↔ Tee Stem", "Interface A"], ["Tee Flange ↔ Support", "Interface B"]] as const) {
      fireEvent.change(screen.getByLabelText(`${title} rows`), { target: { value: "3" } });
      fireEvent.change(screen.getByLabelText(`${title} bolts per row`), { target: { value: "3" } });
      const group = screen.getByText(title, { selector: "span" }).closest("details");
      if (group === null) throw new Error("Layout group fixture is required.");
      for (const label of ["Pitch", "Gauge"]) {
        fireEvent.change(within(group).getByLabelText(label), { target: { value: "1.25" } });
      }
      fireEvent.change(screen.getByLabelText(`${interfaceLabel} vertical offset`), {
        target: { value: "1.25" },
      });
      fireEvent.change(screen.getByLabelText(`${interfaceLabel} horizontal offset`), {
        target: { value: "1.25" },
      });
    }
    for (const label of [
      "Force X", "Force Y", "Force Z", "Moment X", "Moment Y", "Moment Z",
      "Reference X", "Reference Y", "Reference Z",
    ]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: "1" } });
    }
    fireEvent.click(screen.getByRole("button", { name: "Edit force arrow" }));
    expect(screen.getByLabelText("Force X")).toHaveValue("2");
    fireEvent.click(screen.getByRole("button", { name: "Edit moment arrow" }));
    expect(screen.getByLabelText("Moment X")).toHaveValue("4");
    expect(mocks.evaluate).not.toHaveBeenCalled();
  });

  it("loads exact US/SI Tee benchmarks and maps the support longitudinal action", async () => {
    render(<TeeConnectorWorkspace />);
    await screen.findByTestId("tee-viewer");
    expect(screen.getByLabelText("Interface A placement method")).toHaveValue("GROUP_OFFSET_CONTROLLED");
    fireEvent.click(screen.getByRole("button", { name: "Load SI Tee benchmark" }));
    expect(screen.getByLabelText("Connector length")).toHaveValue("203.2");
    expect(screen.getByLabelText("Bolt diameter")).toHaveValue("12.7");
    expect(screen.getByLabelText("Interface A placement method")).toHaveValue("EDGE_DISTANCE_CONTROLLED");
    expect(screen.getAllByText("Positioning: edge-distance controlled", { selector: "p" })).toHaveLength(2);
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.request_id).toBe("TEE-WORKSPACE-SI");
      expect(submitted.interface_a_layout.placement_mode).toBeUndefined();
      expect(submitted.interface_b_layout.placement_mode).toBeUndefined();
    });
    fireEvent.click(screen.getByRole("button", { name: "Load U.S. Tee benchmark" }));
    expect(screen.getByLabelText("Connector length")).toHaveValue("8");
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.request_id).toBe("TEE-WORKSPACE-US_CUSTOMARY");
      expect(submitted.interface_a_layout).toMatchObject({
        unloaded_end_distance: { value: "1", unit: "in" },
        loaded_end_distance: { value: "1", unit: "in" },
      });
    });
    fireEvent.change(screen.getByLabelText("Supporting member"), { target: { value: "W_BEAM_FLANGE" } });
    expect(screen.getByLabelText("Force X")).toHaveValue("0.1");
    expect(screen.getByLabelText("Force Z")).toHaveValue("0");
    fireEvent.change(screen.getByLabelText("Supporting member"), { target: { value: "W_COLUMN_FLANGE" } });
    expect(screen.getByLabelText("Force Z")).toHaveValue("0.1");
  });

  it("runs design only on explicit request, groups handoffs, and stales on engineering edits", async () => {
    render(<TeeConnectorWorkspace />);
    const run = await screen.findByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(run).toBeEnabled(); });
    expect(mocks.evaluate).not.toHaveBeenCalled();
    fireEvent.click(run);
    await waitFor(() => { expect(mocks.evaluate).toHaveBeenCalledTimes(1); });
    expect((await screen.findAllByText("Partial", { exact: true }))).toHaveLength(2);
    expect(screen.getByText("Design results & trace")).toBeInTheDocument();
    const interfaceAGroup = screen.getByText("Brace ↔ Tee Stem", { selector: "span" }).closest("details");
    if (interfaceAGroup === null) throw new Error("Interface A layout group is required.");
    fireEvent.change(within(interfaceAGroup).getByLabelText("Pitch"), {
      target: { value: "2.25" },
    });
    expect(screen.getByText(/Design results are stale/)).toBeInTheDocument();
    expect(mocks.evaluate).toHaveBeenCalledTimes(1);
  });

  it("shows no guessed geometry when the first backend preview is invalid", async () => {
    mocks.preview.mockResolvedValue(teePreviewFixture("INVALID_GEOMETRY"));
    render(<TeeConnectorWorkspace />);
    await waitFor(() => {
      expect(screen.getAllByText(/no valid backend preview/i).length).toBeGreaterThan(0);
    });
    expect(screen.queryByTestId("tee-viewer")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Connector length"), { target: { value: "0" } });
    expect(screen.getAllByText(/dimensions must be finite and greater than zero/).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Connector length"), { target: { value: "8" } });
    fireEvent.change(screen.getByLabelText("Brace ↔ Tee Stem rows"), {
      target: { value: "0" },
    });
    expect(screen.getAllByText(/positive row and bolt counts/).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Brace ↔ Tee Stem rows"), {
      target: { value: "2" },
    });
    fireEvent.change(screen.getByLabelText("Brace inclination"), {
      target: { value: "90.1" },
    });
    expect(screen.getAllByText(/from -90° through \+90°/u).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Brace inclination"), {
      target: { value: "0" },
    });
    fireEvent.change(screen.getByLabelText("Force X"), { target: { value: "" } });
    expect(screen.getAllByText(/components must be finite decimals/).length).toBeGreaterThan(0);
  });

  it("binds valid profile and independent A/B bolt-layout edits to the accepted scene", async () => {
    render(<TeeConnectorWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Load U.S. Tee benchmark" }));
    const viewer = await screen.findByTestId("tee-viewer");
    await waitFor(() => { expect(viewer).toHaveAttribute("data-brace-boxes", "1"); });

    fireEvent.change(screen.getByLabelText("Brace profile family"), { target: { value: "ANGLE" } });
    fireEvent.change(screen.getByLabelText("Leg Y"), { target: { value: "6" } });
    fireEvent.change(screen.getByLabelText("Leg Z"), { target: { value: "6" } });
    fireEvent.change(screen.getByLabelText("Thickness"), { target: { value: "0.5" } });
    fireEvent.change(screen.getByLabelText("Member / view length"), { target: { value: "8" } });
    const interfaceA = screen.getByText("Brace ↔ Tee Stem", { selector: "span" }).closest("details");
    if (interfaceA === null) throw new Error("Interface A layout group is required.");
    fireEvent.change(within(interfaceA).getByLabelText("Unloaded end distance"), {
      target: { value: "1.2815" },
    });
    expect(screen.getAllByText(/Preview updating .* showing last valid preview/u).length).toBeGreaterThan(0);
    await waitFor(() => { expect(viewer).toHaveAttribute("data-brace-boxes", "2"); });
    expect(screen.queryAllByText(/Preview updating .* showing last valid preview/u)).toHaveLength(0);
    const profileRequest = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
    expect(profileRequest.connected_member_profile.dimensions).toMatchObject({
      member_length: { value: "8" },
      leg_y: { value: "6" },
      leg_z: { value: "6" },
      thickness: { value: "0.5" },
    });
    expect(profileRequest.interface_a_layout.unloaded_end_distance.value).toBe("1.2815");

    fireEvent.change(screen.getByLabelText("Brace ↔ Tee Stem rows"), { target: { value: "3" } });
    await waitFor(() => { expect(viewer).toHaveAttribute("data-a-bolts", "6"); });
    expect(viewer).toHaveAttribute("data-b-bolts", "4");
    fireEvent.click(screen.getByRole("button", { name: "Select last Interface A bolt" }));
    expect(viewer).toHaveAttribute("data-selection", "BOLT:A_B_R3_L2");
    fireEvent.change(screen.getByLabelText("Brace ↔ Tee Stem rows"), { target: { value: "2" } });
    await waitFor(() => { expect(viewer).toHaveAttribute("data-a-bolts", "4"); });
    await waitFor(() => { expect(viewer).toHaveAttribute("data-selection", "MEMBER:tee-connector"); });

    fireEvent.change(screen.getByLabelText("Tee Flange ↔ Support rows"), { target: { value: "3" } });
    await waitFor(() => { expect(viewer).toHaveAttribute("data-b-bolts", "6"); });
    expect(viewer).toHaveAttribute("data-a-bolts", "4");
  });

  it("presents simple placement and preserves exact geometry across Advanced mode switches", async () => {
    render(<TeeConnectorWorkspace />);
    const viewer = await screen.findByTestId("tee-viewer");
    const interfaceA = screen.getByText("Brace ↔ Tee Stem", { selector: "span" }).closest("details");
    if (interfaceA === null) throw new Error("Interface A layout group is required.");
    expect(within(interfaceA).getByRole("region", { name: "Interface A bolt pattern" })).toBeInTheDocument();
    expect(within(interfaceA).getByRole("region", { name: "Interface A bolt group position" })).toBeInTheDocument();
    expect(screen.queryByText("Position by", { selector: "span" })).not.toBeInTheDocument();
    expect(screen.getAllByText(/Physical complete-hole containment threshold: 1\.2815 in/u).length)
      .toBeGreaterThan(0);
    expect(screen.getByLabelText("Interface A vertical offset")).toHaveValue("-2");
    expect(screen.getByLabelText("Interface A horizontal offset")).toHaveValue("0");
    expect(screen.getByLabelText("Interface B vertical offset")).toHaveValue("-2");
    expect(screen.getByLabelText("Interface B horizontal offset")).toHaveValue("-1");
    expect(within(interfaceA).getByText("+ up / − down")).toBeInTheDocument();
    expect(within(interfaceA).getByText(/interface H-axis shown in the viewer\/inspector/u)).toBeInTheDocument();
    expect(within(interfaceA).getByText(/Geometry containment verifies that the complete hole/iu)).toBeInTheDocument();
    expect(within(interfaceA).getAllByText("+0.7185 in", { selector: "dd" })).toHaveLength(6);

    const advanced = within(interfaceA).getByText("Advanced placement").closest("details");
    if (advanced === null) throw new Error("Advanced placement details are required.");
    expect(advanced).not.toHaveAttribute("open");
    fireEvent.click(within(advanced).getByText("Advanced placement"));
    expect(advanced).toHaveAttribute("open");

    const placementMethod = within(interfaceA).getByLabelText("Interface A placement method");
    expect(placementMethod).toHaveValue("GROUP_OFFSET_CONTROLLED");
    fireEvent.change(placementMethod, { target: { value: "EDGE_DISTANCE_CONTROLLED" } });
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.interface_a_layout).toMatchObject({
        placement_mode: "EDGE_DISTANCE_CONTROLLED",
        unloaded_end_distance: { value: "1", unit: "in" },
        loaded_end_distance: { value: "1", unit: "in" },
        negative_side_distance: { value: "1", unit: "in" },
        positive_side_distance: { value: "1", unit: "in" },
      });
      expect(submitted.interface_a_layout.vertical_offset).toBeUndefined();
      expect(submitted.interface_a_layout.horizontal_offset).toBeUndefined();
      expect(submitted.interface_b_layout).toMatchObject({
        placement_mode: "GROUP_OFFSET_CONTROLLED",
        vertical_offset: { value: "-2", unit: "in" },
        horizontal_offset: { value: "-1", unit: "in" },
      });
    });
    expect(screen.queryByLabelText("Interface A vertical offset")).not.toBeInTheDocument();
    expect(within(interfaceA).getByText("Positioning: edge-distance controlled")).toBeInTheDocument();
    expect(within(interfaceA).getByLabelText("Unloaded end distance")).toHaveValue("1");
    expect(advanced).toHaveAttribute("open");

    await waitFor(() => { expect(placementMethod).toHaveValue("EDGE_DISTANCE_CONTROLLED"); });
    fireEvent.change(placementMethod, { target: { value: "GROUP_OFFSET_CONTROLLED" } });
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.interface_a_layout).toMatchObject({
        placement_mode: "GROUP_OFFSET_CONTROLLED",
        vertical_offset: { value: "-2", unit: "in" },
        horizontal_offset: { value: "0", unit: "in" },
      });
    });
    expect(within(interfaceA).queryByLabelText("Unloaded end distance")).not.toBeInTheDocument();
    expect(viewer).toBeInTheDocument();
    expect(mocks.viewerMount).toHaveBeenCalledTimes(1);
  });

  it("centers each bolt group independently without changing either pattern", async () => {
    render(<TeeConnectorWorkspace />);
    await screen.findByTestId("tee-viewer");
    fireEvent.change(screen.getByLabelText("Interface A vertical offset"), {
      target: { value: "0.75" },
    });
    fireEvent.change(screen.getByLabelText("Interface A horizontal offset"), {
      target: { value: "-0.25" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Center Interface A bolt group" }));

    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.interface_a_layout).toMatchObject({
        row_count: 2,
        bolts_per_row: 2,
        pitch: { value: "2" },
        gauge: { value: "2" },
        placement_mode: "GROUP_OFFSET_CONTROLLED",
        vertical_offset: { value: "0", unit: "in" },
        horizontal_offset: { value: "0", unit: "in" },
      });
      expect(submitted.interface_b_layout).toMatchObject({
        row_count: 2,
        bolts_per_row: 2,
        placement_mode: "GROUP_OFFSET_CONTROLLED",
        vertical_offset: { value: "-2", unit: "in" },
        horizontal_offset: { value: "-1", unit: "in" },
      });
    });

    fireEvent.change(screen.getByLabelText("Interface B vertical offset"), {
      target: { value: "1" },
    });
    fireEvent.change(screen.getByLabelText("Interface B horizontal offset"), {
      target: { value: "2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Center Interface B bolt group" }));
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.interface_a_layout).toMatchObject({
        vertical_offset: { value: "0" },
        horizontal_offset: { value: "0" },
      });
      expect(submitted.interface_b_layout).toMatchObject({
        row_count: 2,
        bolts_per_row: 2,
        pitch: { value: "2" },
        gauge: { value: "2" },
        placement_mode: "GROUP_OFFSET_CONTROLLED",
        vertical_offset: { value: "0", unit: "in" },
        horizontal_offset: { value: "0", unit: "in" },
      });
    });
  });

  it("distinguishes positive, boundary, and backend-rejected containment clearance", async () => {
    mocks.preview.mockImplementation((request: TeeConnectorRequest) => {
      const response = requestAwarePreview(request);
      if (request.interface_a_layout.vertical_offset?.value === "0.25") {
        response.result.interface_a.placement.clearances.minimum.value = "0";
      }
      if (request.interface_a_layout.vertical_offset?.value === "0.5") {
        response.result.interface_a.placement.clearances.minimum.value = "-0.1";
      }
      if (request.interface_a_layout.vertical_offset?.value === "4") {
        return Promise.reject(new EvaluationTransportError(
          "VALIDATION",
          422,
          "The server rejected the current Interface A offset.",
          {
            detail: {
              code: "CANONICAL_TEE_MAPPING_INVALID",
              message: "Complete-hole clearance -0.2815 in; governing boundary TEE_INTERFACE_A_BRACE_TO_STEM:VERTICAL_POSITIVE; governing bolt A_B_R2_L1.",
            },
          },
        ));
      }
      return Promise.resolve(response);
    });
    render(<TeeConnectorWorkspace />);
    await screen.findByTestId("tee-viewer");
    expect(screen.getAllByText("+0.7185 in", { selector: "dd" }).length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Interface A vertical offset"), {
      target: { value: "0.5" },
    });
    await waitFor(() => {
      expect(screen.getByRole("region", { name: "Interface A computed clearances" }))
        .toHaveTextContent("-0.1 in");
    });

    fireEvent.change(screen.getByLabelText("Interface A vertical offset"), {
      target: { value: "0.25" },
    });
    expect(await screen.findByText(/0\.0000 in — complete hole is exactly at the physical containment boundary/u)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Interface A vertical offset"), {
      target: { value: "4" },
    });
    expect(await screen.findByText("Current governing geometry clearance -0.2815 in")).toBeInTheDocument();
    expect(screen.getByText(/Move the group inward \(down\) by at least 0\.2815 in/u)).toBeInTheDocument();
    expect(screen.queryByText(/code-required minimum.*0\.2815/iu)).not.toBeInTheDocument();
  });

  it("keeps minimum physical group counts independent and fails closed per interface", async () => {
    render(<TeeConnectorWorkspace />);
    const viewer = await screen.findByTestId("tee-viewer");

    fireEvent.change(screen.getByLabelText("Brace ↔ Tee Stem bolts per row"), {
      target: { value: "1" },
    });
    await waitFor(() => { expect(viewer).toHaveAttribute("data-a-bolts", "2"); });
    expect(viewer).toHaveAttribute("data-b-bolts", "4");
    let submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
    expect(submitted.interface_a_layout).toMatchObject({ row_count: 2, bolts_per_row: 1 });
    expect(submitted.interface_b_layout).toMatchObject({ row_count: 2, bolts_per_row: 2 });

    fireEvent.change(screen.getByLabelText("Tee Flange ↔ Support rows"), {
      target: { value: "3" },
    });
    await waitFor(() => { expect(viewer).toHaveAttribute("data-b-bolts", "6"); });
    expect(viewer).toHaveAttribute("data-a-bolts", "2");

    fireEvent.change(screen.getByLabelText("Brace ↔ Tee Stem bolts per row"), {
      target: { value: "2" },
    });
    fireEvent.change(screen.getByLabelText("Brace ↔ Tee Stem rows"), {
      target: { value: "1" },
    });
    await waitFor(() => {
      submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.interface_a_layout).toMatchObject({ row_count: 1, bolts_per_row: 2 });
    });
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(screen.getAllByText(/Calculation Not Supported/u).length).toBeGreaterThan(0);
  });

  it("treats brace inclination as an engineering edit distinct from profile roll", async () => {
    render(<TeeConnectorWorkspace />);
    const viewer = await screen.findByTestId("tee-viewer");
    expect(screen.getByLabelText("Brace inclination")).toHaveValue(0);
    expect(screen.getByLabelText("Profile roll about member axis")).toHaveValue("ROTATION_0");
    const run = screen.getByRole("button", { name: "Run Design Check" });
    fireEvent.click(run);
    await waitFor(() => { expect(mocks.evaluate).toHaveBeenCalledTimes(1); });

    fireEvent.change(screen.getByLabelText("Brace inclination"), {
      target: { value: "27.5" },
    });
    expect(screen.getByText(/Design results are stale/)).toBeInTheDocument();
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.brace_inclination_degrees).toBe("27.5");
      expect(screen.getByText("27.5°")).toBeInTheDocument();
    });
    expect(viewer).toBeInTheDocument();
    expect(mocks.viewerMount).toHaveBeenCalledTimes(1);

    fireEvent.change(screen.getByLabelText("Profile roll about member axis"), {
      target: { value: "ROTATION_90" },
    });
    await waitFor(() => {
      const submitted = mocks.preview.mock.calls.at(-1)?.[0] as TeeConnectorRequest;
      expect(submitted.brace_inclination_degrees).toBe("27.5");
      expect(submitted.connected_member_profile.profile_orientation).toBe("ROTATION_90");
    });
  });

  it("keeps the R6 last-valid scene when backend-authoritative inclination is invalid", async () => {
    mocks.preview.mockImplementation((request: TeeConnectorRequest) => {
      if (request.brace_inclination_degrees === "60") {
        return Promise.reject(new EvaluationTransportError(
          "VALIDATION",
          422,
          "The server rejected the rotated Interface A geometry.",
          "The complete round hole disk is not contained in its source patch.",
        ));
      }
      return Promise.resolve(requestAwarePreview(request));
    });
    render(<TeeConnectorWorkspace />);
    const viewer = await screen.findByTestId("tee-viewer");

    fireEvent.change(screen.getByLabelText("Brace inclination"), {
      target: { value: "60" },
    });
    await waitFor(() => {
      expect(screen.getAllByText(/showing last valid preview/u).length).toBeGreaterThan(0);
    });
    expect(viewer).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Brace inclination"), {
      target: { value: "30" },
    });
    await waitFor(() => {
      expect(screen.queryAllByText(/showing last valid preview/u)).toHaveLength(0);
    });
    expect(viewer).toBeInTheDocument();
  });

  it("keeps the last valid scene, exposes backend detail, blocks design, and recovers", async () => {
    mocks.preview.mockImplementation((request: TeeConnectorRequest) => {
      if (
        request.interface_a_layout.bolts_per_row === 3
        && Number(request.connector_dimensions.stem_depth.value) < 6
      ) {
        return Promise.reject(new EvaluationTransportError(
          "VALIDATION",
          422,
          "The server rejected one or more Tee engineering fields.",
          {
            detail: {
              code: "CANONICAL_TEE_MAPPING_INVALID",
              message: "Interface A bolt lines do not fit within the Tee stem depth.",
            },
          },
        ));
      }
      return Promise.resolve(requestAwarePreview(request));
    });
    render(<TeeConnectorWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Load U.S. Tee benchmark" }));
    const viewer = await screen.findByTestId("tee-viewer");
    await waitFor(() => { expect(viewer).toHaveAttribute("data-a-bolts", "4"); });

    fireEvent.change(screen.getByLabelText("Brace ↔ Tee Stem bolts per row"), {
      target: { value: "3" },
    });
    expect(screen.getAllByText(/Preview updating .* showing last valid preview/u).length).toBeGreaterThan(0);
    expect(viewer).toHaveAttribute("data-a-bolts", "4");
    await waitFor(() => {
      expect(screen.getAllByText("Interface A bolt lines do not fit within the Tee stem depth.").length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText(/Current inputs are invalid .* showing last valid preview/u).length).toBeGreaterThan(0);
    expect(viewer).toHaveAttribute("data-a-bolts", "4");
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Stem depth"), { target: { value: "6" } });
    await waitFor(() => { expect(viewer).toHaveAttribute("data-a-bolts", "6"); });
    expect(screen.queryAllByText(/Current inputs are invalid .* showing last valid preview/u)).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled();
  });

  it("retains the R6 last-valid model while showing an exact offset clearance deficit", async () => {
    mocks.preview.mockImplementation((request: TeeConnectorRequest) => {
      if (request.interface_a_layout.vertical_offset?.value === "4") {
        return Promise.reject(new EvaluationTransportError(
          "VALIDATION",
          422,
          "The server rejected the current Interface A offset.",
          {
            detail: {
              code: "CANONICAL_TEE_MAPPING_INVALID",
              message: "Complete-hole clearance -0.2815 in; governing boundary TEE_INTERFACE_A_BRACE_TO_STEM:VERTICAL_POSITIVE; governing bolt A_B_R2_L1.",
            },
          },
        ));
      }
      return Promise.resolve(requestAwarePreview(request));
    });
    render(<TeeConnectorWorkspace />);
    const viewer = await screen.findByTestId("tee-viewer");
    fireEvent.change(screen.getByLabelText("Interface A vertical offset"), {
      target: { value: "4" },
    });

    await waitFor(() => {
      expect(screen.getAllByText(/Complete-hole clearance -0\.2815 in/u).length)
        .toBeGreaterThan(0);
    });
    expect(screen.getByText(/Move the group inward \(down\) by at least 0\.2815 in/u)).toBeInTheDocument();
    expect(screen.getAllByText(/showing last valid preview/iu).length).toBeGreaterThan(0);
    expect(viewer).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
  });

  it("shows structured rejection detail and no model when no valid preview exists", async () => {
    mocks.preview.mockRejectedValueOnce(new EvaluationTransportError(
      "VALIDATION",
      422,
      "The server rejected one or more Tee engineering fields.",
      { detail: { code: "CANONICAL_TEE_MAPPING_INVALID", message: "Interface A has no valid bolt path." } },
    ));
    render(<TeeConnectorWorkspace />);
    expect((await screen.findAllByText("Interface A has no valid bolt path.")).length).toBeGreaterThan(0);
    expect(screen.queryByTestId("tee-viewer")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
  });

  it("shows preview and design service errors with retryable preview behavior", async () => {
    mocks.preview.mockRejectedValueOnce(new Error("preview broke"));
    render(<TeeConnectorWorkspace />);
    expect(await screen.findByText("Unexpected Tee preview handling failure.")).toBeInTheDocument();
    mocks.preview.mockResolvedValueOnce(teePreviewFixture());
    fireEvent.click(screen.getByRole("button", { name: "Retry preview" }));
    const run = await screen.findByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(run).toBeEnabled(); });

    mocks.evaluate.mockRejectedValueOnce(
      new EvaluationTransportError("HTTP", 500, "Controlled design failure.", null),
    );
    fireEvent.click(run);
    expect(await screen.findByText("Controlled design failure.")).toBeInTheDocument();
  });

  it("labels a failed refresh as last-valid and clears it after retry", async () => {
    render(<TeeConnectorWorkspace />);
    const viewer = await screen.findByTestId("tee-viewer");
    await waitFor(() => { expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled(); });
    mocks.preview.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "Preview service unavailable.", null));
    fireEvent.change(screen.getByLabelText("Connector length"), { target: { value: "8.25" } });
    await waitFor(() => {
      expect(screen.getAllByText(/Preview failed .* showing last valid preview/u).length).toBeGreaterThan(0);
    });
    expect(viewer).toBeInTheDocument();
    expect(screen.getByText("Preview service unavailable.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Retry preview" }));
    await waitFor(() => {
      expect(screen.queryAllByText(/Preview failed .* showing last valid preview/u)).toHaveLength(0);
    });
  });

  it("blocks design when a current accepted preview is not design-ready", async () => {
    const preview = teePreviewFixture();
    preview.design_check_ready = false;
    preview.result.design_check_ready = false;
    mocks.preview.mockResolvedValue(preview);
    render(<TeeConnectorWorkspace />);
    expect(await screen.findByText("The backend has not marked both interfaces design-ready.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
  });

  it("wraps an unexpected design error and displays unavailable normal/result placeholders", async () => {
    const preview = teePreviewFixture();
    preview.result.interface_a.normal_component = null;
    preview.result.interface_a.normal_action_supported = false;
    preview.result.interface_a.preview.automatic_demand_result = null;
    mocks.preview.mockResolvedValue(preview);
    mocks.evaluate.mockRejectedValueOnce(new Error("unexpected"));
    render(<TeeConnectorWorkspace />);
    const run = await screen.findByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(run).toBeEnabled(); });
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("Pending").length).toBeGreaterThan(0);
    fireEvent.click(run);
    expect(await screen.findByText("Unexpected Tee design failure.")).toBeInTheDocument();
  });

  it("shows supported interface failure as governing while retaining the Tee limitation", async () => {
    mocks.evaluate.mockResolvedValueOnce(teeDesignFixture("FAIL"));
    render(<TeeConnectorWorkspace />);
    const run = await screen.findByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(run).toBeEnabled(); });
    fireEvent.click(run);
    expect(await screen.findByText("Yes", { exact: true })).toBeInTheDocument();
    expect(screen.getByText(/Tee connector body · Not evaluated/)).toBeInTheDocument();
  });

  it("aborts an in-flight design and ignores a late success after unmount", async () => {
    const pending = deferred<ReturnType<typeof teeDesignFixture>>();
    mocks.evaluate.mockReturnValueOnce(pending.promise);
    const { unmount } = render(<TeeConnectorWorkspace />);
    const run = await screen.findByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(run).toBeEnabled(); });
    fireEvent.click(run);
    const signal = mocks.evaluate.mock.calls[0]?.[1] as AbortSignal;
    unmount();
    expect(signal.aborted).toBe(true);
    pending.resolve(teeDesignFixture());
    await pending.promise;
  });

  it("aborts an in-flight design when an engineering input changes", async () => {
    const pending = deferred<ReturnType<typeof teeDesignFixture>>();
    mocks.evaluate.mockReturnValueOnce(pending.promise);
    render(<TeeConnectorWorkspace />);
    const run = await screen.findByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(run).toBeEnabled(); });
    fireEvent.click(run);
    const signal = mocks.evaluate.mock.calls[0]?.[1] as AbortSignal;

    fireEvent.change(screen.getByLabelText("Connector length"), { target: { value: "8.5" } });
    expect(signal.aborted).toBe(true);
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeInTheDocument();

    pending.resolve(teeDesignFixture());
    await pending.promise;
    await waitFor(() => { expect(screen.getAllByText("No design run").length).toBeGreaterThan(0); });
  });

  it("suppresses an intentional in-flight design abort after cleanup", async () => {
    const pending = deferred<ReturnType<typeof teeDesignFixture>>();
    mocks.evaluate.mockReturnValueOnce(pending.promise);
    const { unmount } = render(<TeeConnectorWorkspace />);
    const run = await screen.findByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(run).toBeEnabled(); });
    fireEvent.click(run);
    unmount();
    pending.reject(new DOMException("cancel", "AbortError"));
    await expect(pending.promise).rejects.toThrow("cancel");
  });
});
