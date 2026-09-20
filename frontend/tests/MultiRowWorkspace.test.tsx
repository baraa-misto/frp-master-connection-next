import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationTransportError } from "../src/api/client";
import type { VisualizationSnapshot } from "../src/api/contracts";
import type {
  MultiRowConnectionRequest,
  MultiRowDesignResponse,
  MultiRowPreviewResponse,
} from "../src/api/multirowContracts";
import { MultiRowVisualizationPanel } from "../src/visualization/MultiRowVisualizationPanel";
import { ShearConnectionsWorkspace } from "../src/workspace/ShearConnectionsWorkspace";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import * as benchmarks from "../src/fixtures/j1Benchmarks";
import {
  previewResponseFixture,
  responseFixture,
  visualizationFixture,
} from "./fixtures";

const mocks = vi.hoisted(() => ({
  singlePreview: vi.fn(),
  singleEvaluate: vi.fn(),
  multiPreview: vi.fn(),
  multiEvaluate: vi.fn(),
}));

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return {
    ...actual,
    previewSingleBolt: mocks.singlePreview,
    evaluateSingleBolt: mocks.singleEvaluate,
    previewMultiRow: mocks.multiPreview,
    evaluateMultiRow: mocks.multiEvaluate,
  };
});

vi.mock("../src/visualization/EngineeringScene", () => ({
  default: ({ model, view, onSelect }: {
    readonly model: import("../src/visualization/sceneModel").SingleBoltSceneModel;
    readonly view: string;
    readonly onSelect: (selection: { kind: "MEMBER" | "BOLT" | "CONTACT"; id: string }) => void;
  }) => {
    const bolts = model.cylinders.filter((value) => value.kind === "BOLT");
    return (
      <div data-testid="mock-engineering-scene" data-view={view} data-bolt-count={bolts.length}>
        Canonical 3D connection
        {bolts.map((bolt) => (
          <button key={bolt.ownerBoltId} type="button" onClick={() => { onSelect({ kind: "BOLT", id: bolt.ownerBoltId }); }}>
            Select {bolt.ownerBoltId}
          </button>
        ))}
      </div>
    );
  },
}));

function translatedDisplay(
  source: VisualizationSnapshot["bolt"],
  boltId: string,
  rowOffset: number,
  lineOffset: number,
): VisualizationSnapshot["bolt"] {
  const display = structuredClone(source);
  display.bolt_location_id = boltId;
  const move = (value: { x: string; y: string; z: string }) => {
    value.y = String(Number(value.y) + rowOffset);
    value.z = String(Number(value.z) + lineOffset);
  };
  move(display.center);
  move(display.stack_start);
  move(display.stack_end);
  display.holes.forEach((hole) => {
    hole.id = `${boltId}:${hole.id}`;
    move(hole.start);
    move(hole.end);
  });
  display.washers.forEach((washer) => {
    washer.id = `${boltId}:${washer.id}`;
    move(washer.start);
    move(washer.end);
  });
  return display;
}

function multirowPreviewFixture(
  rows = 2,
  lines = 2,
  status: "VALID" | "INVALID_GEOMETRY" = "VALID",
): MultiRowPreviewResponse {
  const physical = visualizationFixture();
  const bolts = Array.from({ length: rows }, (_, rowIndex) =>
    Array.from({ length: lines }, (_, lineIndex) => {
      const boltId = `B_R${String(rowIndex + 1)}_L${String(lineIndex + 1)}`;
      return {
        bolt_id: boltId,
        row_id: `ROW_${String(rowIndex + 1)}`,
        bolt_line_id: `BOLT_LINE_${String(lineIndex + 1)}`,
        penetrated_layer_ids: ["layer-A", "layer-B"],
        display: translatedDisplay(physical.bolt, boltId, rowIndex * 2, lineIndex * 2),
      };
    }),
  ).flat();
  return {
    api_transport_schema_version: "0.3.0-draft",
    orchestration_contract_version: "2.5C-RC1",
    preview_schema_version: "0.2.0-draft",
    visualization_schema_version: "0.2.0-draft",
    request_id: "J1-UI-MULTIROW",
    connection_id: "benchmark-assembly",
    geometry_status: status,
    plan_availability: status === "VALID" ? "READY" : "CALCULATION_NOT_SUPPORTED",
    method_applicability: rows > 3 ? "CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE" : "ASCE_PRESCRIPTIVE",
    qualification: rows > 3 ? "SECTION_2_3_2_QUALIFICATION_REQUIRED" : "QUALIFIED_ASCE_PRESCRIPTIVE",
    warnings: status === "VALID"
      ? rows > 3 ? ["MORE_THAN_THREE_ROWS_REQUIRES_SECTION_2_3_2_QUALIFICATION"] : ["F593_TENSILE_SOURCE_DATA_PENDING"]
      : ["INVALID_PHYSICAL_CONNECTION_GEOMETRY:member-a,member-b"],
    preview_fingerprint: "a".repeat(64),
    resistance_evaluated: false,
    design_check_ready: status === "VALID",
    visualization: {
      schema_version: "0.2.0-draft",
      coordinate_system: "INTERFACE_XY_WITH_SIGNED_FORCE_UV",
      source_length_unit: "in",
      boundary: ["0", String(rows * 2 + 2), "-2.5", String(lines * 2 + 0.5)],
      bolts: bolts.map((value, index) => ({
        bolt_id: value.bolt_id,
        row_id: value.row_id,
        bolt_line_id: value.bolt_line_id,
        x: String(Math.floor(index / lines) * 2 + 2),
        y: String(index % lines * 2 - 1),
        bolt_diameter: { value: ".5", unit: "in" },
        hole_diameter: { value: ".563", unit: "in" },
      })),
      row_ids: Array.from({ length: rows }, (_, index) => `ROW_${String(index + 1)}`),
      bolt_line_ids: Array.from({ length: lines }, (_, index) => `BOLT_LINE_${String(index + 1)}`),
      unloaded_free_end_id: "BOUNDARY:UNLOADED_FREE_END",
      row_1_id: "ROW_1",
      pitch: { value: "2", unit: "in" },
      gauge: { value: "2", unit: "in" },
      unloaded_end_e1: { value: "2", unit: "in" },
      loaded_boundary_to_row_1_distance: { value: "2", unit: "in" },
      negative_side_distance: { value: "1.5", unit: "in" },
      positive_side_distance: { value: "1.5", unit: "in" },
      demand_components: [{ value: ".7", unit: "kip" }, { value: "0", unit: "kip" }],
      force_reference: "bolt-1-center",
      global_axes: [["X", ["1", "0"]], ["Y", ["0", "1"]]],
      local_axes: [["u", ["1", "0"]], ["v", ["0", "1"]]],
      layers: [{ layer_id: "layer-A", component_id: "member-a", material_id: "ICE_LOCKED_PULTRUDED_FRP", material_axis_angle_degrees: "0", material_direction: "LONGITUDINAL", thickness: { value: ".375", unit: "in" } }],
      block_paths: [{ path_id: "BLOCK-L", family: "L_LEFT", accepted: true, points: [["0", "-1"], ["4", "-1"], ["4", "-2.5"]] }],
      physical_connection: physical,
      physical_bolts: bolts,
      connection_demand: {
        reference_point_id: "MULTIROW_CONNECTION_DEMAND_REFERENCE",
        origin: physical.bolt.center,
        axis: physical.bolt.axis,
        resultant: { value: ".7", unit: "kip" },
        frame_id: "BOLT_GROUP_LOCAL:bolt-group-1",
      },
      automatic_bolt_demands: [],
    },
    demand_source: "EXPLICIT_RESOLVED_CONNECTION_DEMAND",
    automatic_demand_result: null,
  };
}

function multirowDesignFixture(rows = 2, lines = 2): MultiRowDesignResponse {
  const preview = multirowPreviewFixture(rows, lines);
  return {
    ...preview,
    preview,
    calculation_result: {
      results: [{
        result_id: "PIN_BEARING:layer-A:B_R1_L1", layer_id: "layer-A", bolt_id: "B_R1_L1", row_id: "ROW_1", bolt_line_id: "BOLT_LINE_1", path_id: null, limit_state: "PIN_BEARING", equation_method: "PIN_BEARING", source_locator: "ASCE/SEI 74-23 Chapter 8", method_applicability: "ASCE_PRESCRIPTIVE", qualification: "ENGINEERING_REVIEW_REQUIRED", availability: "CALCULATED", geometry_status: "VALID", equation_nominal_resistance: { value: "10", unit: "kip" }, connection_adjusted_nominal_resistance: { value: "10", unit: "kip" }, design_resistance: { value: "6", unit: "kip" }, demand: { value: "2.5", unit: "kip" }, utilization: ".4166666667", numerical_comparison: "PASS", factor_trace: { c_delta: "1" }, equation_trace: { equation: "8-5" }, warnings: [],
      }],
      required_check_ids: ["PIN_BEARING:layer-A:B_R1_L1"], calculated_check_ids: ["PIN_BEARING:layer-A:B_R1_L1"], unsupported_check_ids: [], failed_check_ids: [], governing_result_ids: ["PIN_BEARING:layer-A:B_R1_L1"], geometry_status: "VALID", availability: "CALCULATED", method_applicability: "ASCE_PRESCRIPTIVE", qualification: "ENGINEERING_REVIEW_REQUIRED", numerical_comparison: "PASS", overall_disposition: "ENGINEERING_REVIEW_REQUIRED", warnings: [], input_fingerprint: "b".repeat(64), result_fingerprint: "c".repeat(64), versions: { calculation_contract_version: "2.4B-RC2" },
    },
    demand_source: "EXPLICIT_RESOLVED_CONNECTION_DEMAND",
    automatic_demand_result: null,
    automatic_handoff_results: [],
    automatic_group_mode_integration: null,
  };
}

function automaticPreviewFixture(): MultiRowPreviewResponse {
  const preview = multirowPreviewFixture();
  const visualization = preview.visualization;
  if (visualization === null) throw new Error("Automatic visualization fixture is required.");
  const first = visualization.physical_bolts?.[0];
  const second = visualization.physical_bolts?.[1];
  if (first === undefined || second === undefined) {
    throw new Error("Automatic physical bolt fixtures are required.");
  }
  preview.demand_source = "AUTOMATIC_MEMBER_END_FORCE";
  preview.warnings = [
    "MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL",
    "RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY_USED",
  ];
  preview.automatic_demand_result = {
    action_source_id: "action-1",
    member_component_id: "member-a",
    availability: "CALCULATED",
    method_applicability: "ASCE_PRESCRIPTIVE",
    qualification: "QUALIFIED_ASCE_PRESCRIPTIVE",
    warnings: [{
      code: "MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL",
      trace: ["mx:0", "my:0", "mz:1"],
    }],
    input_fingerprint: "d".repeat(64),
    result_fingerprint: "e".repeat(64),
    scenarios: [{
      scenario_id: "ASCE_PRESCRIBED",
      availability: "CALCULATED",
      external_moment: { value: "2.8", unit: "kip-in" },
      residual_moment: { value: "1.4", unit: "kip-in" },
      warnings: [],
    }],
    versions: { calculation_contract_version: "2.5A-RC1" },
  };
  visualization.connection_demand = {
    reference_point_id: "MEMBER_CONNECTED_END:member-a",
    origin: first.display.center,
    axis: first.display.axis,
    resultant: { value: ".7", unit: "kip" },
    frame_id: "BOLT_GROUP_LOCAL:bolt-group-1",
  };
  const demand = {
    direct_u: { value: ".2", unit: "kip" },
    direct_v: { value: "0", unit: "kip" },
    moment_u: { value: ".05", unit: "kip" },
    moment_v: { value: ".1", unit: "kip" },
    total_u: { value: ".25", unit: "kip" },
    total_v: { value: ".1", unit: "kip" },
    total_magnitude: { value: ".2692582404", unit: "kip" },
  };
  visualization.automatic_bolt_demands = [
    {
      bolt_id: first.bolt_id,
      row_id: first.row_id,
      bolt_line_id: first.bolt_line_id,
      origin: first.display.center,
      ...demand,
      total_axis: first.display.axis,
    },
    {
      bolt_id: second.bolt_id,
      row_id: second.row_id,
      bolt_line_id: second.bolt_line_id,
      origin: second.display.center,
      ...demand,
      total_magnitude: { value: "0", unit: "kip" },
      total_axis: null,
    },
  ];
  return preview;
}

function automaticDesignFixture(): MultiRowDesignResponse {
  const preview = automaticPreviewFixture();
  const supported = multirowDesignFixture().calculation_result?.results[0];
  if (supported === undefined) throw new Error("Supported automatic check fixture is required.");
  const lineCheck = {
    ...supported,
    result_id: "INTERROW:layer-A:BOLT_LINE_1",
    bolt_id: null,
    row_id: null,
    bolt_line_id: "BOLT_LINE_1",
    limit_state: "INTERROW_SHEAR_OUT",
    equation_method: "INTERROW_ASCE_EQ_8_12",
    demand: { value: ".35", unit: "kip" },
    design_resistance: { value: "6", unit: "kip" },
    utilization: ".058333333333",
  };
  return {
    ...preview,
    preview,
    calculation_result: null,
    demand_source: "AUTOMATIC_MEMBER_END_FORCE",
    automatic_demand_result: preview.automatic_demand_result,
    automatic_handoff_results: [{
      coverage: "PARTIAL_ECCENTRIC",
      supported_results: [supported],
      unsupported_required_check_ids: ["FIRST_ROW:layer-A"],
      incomplete_required_check_ids: ["BOLT_TENSION:B_R1_L1"],
      qualification: "ENGINEERING_REVIEW_REQUIRED",
      numerical_comparison: "PASS",
      governing_supported_check_ids: [supported.result_id],
      overall_disposition: "NOT_EVALUATED",
      warnings: [{ code: "ECCENTRIC_FIRST_ROW_NET_TENSION_HANDOFF_NOT_SUPPORTED_RC1", trace: [] }],
      parent_action_transfer_warnings: [
        {
          code: "MEMBER_END_MOMENTS_NOT_TRANSFERRED_BY_CURRENT_DEMAND_MODEL",
          trace: ["mz:1"],
        },
        { code: "OUT_OF_PLANE_FORCE_REQUIRES_EXPLICIT_BOLT_AXIS_DEMAND", trace: [] },
      ],
      result_fingerprint: "f".repeat(64),
      versions: { calculation_contract_version: "2.5B-RC1" },
      legacy_result: null,
    }],
    automatic_group_mode_integration: {
      integration_contract_version: "2.6B-RC1",
      scenario_results: [{
        versions: {
          calculation_contract_version: "2.6A-RC1",
          eccentric_group_mode_engine_version: "0.1.0.dev1",
        },
        scenario_id: "ASCE_PRESCRIBED",
        line_results: [{
          bolt_line_id: "BOLT_LINE_1",
          check_id: lineCheck.result_id,
          contributing_bolt_ids: ["B_R1_L1", "B_R2_L1"],
          line_resultant: {
            u: { value: ".35", unit: "kip" },
            v: { value: "0", unit: "kip" },
          },
          parallel_scalar: { value: ".35", unit: "kip" },
          transverse_scalar: { value: "0", unit: "kip" },
          handoff_status: "AUTHORIZED_RATIONAL_ECCENTRIC_SHEAROUT",
          required_line_demand: { value: ".35", unit: "kip" },
          shear_out_result: lineCheck,
          warnings: [],
          method_id: "RATIONAL_ECCENTRIC_BOLT_LINE_SHEAROUT_HANDOFF",
        }, {
          bolt_line_id: "BOLT_LINE_2",
          check_id: "INTERROW:layer-A:BOLT_LINE_2",
          contributing_bolt_ids: ["B_R1_L2", "B_R2_L2"],
          line_resultant: {
            u: { value: "0", unit: "kip" },
            v: { value: "0", unit: "kip" },
          },
          parallel_scalar: { value: "0", unit: "kip" },
          transverse_scalar: { value: "0", unit: "kip" },
          handoff_status: "NOT_REQUIRED_ZERO_LINE_DEMAND",
          required_line_demand: null,
          shear_out_result: null,
          warnings: [],
          method_id: "RATIONAL_ECCENTRIC_BOLT_LINE_SHEAROUT_HANDOFF",
        }],
        first_row_compatibility: {
          status: "CALCULATION_NOT_SUPPORTED",
          required_check_ids: ["FIRST_ROW:layer-A"],
          warnings: [{
            code: "ECCENTRIC_FIRST_ROW_NET_TENSION_GENERAL_METHOD_NOT_ESTABLISHED_RC1",
            trace: ["check_id:FIRST_ROW:layer-A"],
          }],
        },
        supported_results: [lineCheck],
        required_check_ids: [lineCheck.result_id, "FIRST_ROW:layer-A"],
        not_required_check_ids: ["INTERROW:layer-A:BOLT_LINE_2"],
        unsupported_required_check_ids: ["FIRST_ROW:layer-A"],
        incomplete_required_check_ids: ["BOLT_TENSION:B_R1_L1"],
        failed_check_ids: [],
        qualification: "ENGINEERING_REVIEW_REQUIRED",
        numerical_comparison: "NOT_EVALUATED",
        governing_supported_check_ids: [lineCheck.result_id],
        overall_disposition: "NOT_EVALUATED",
        trace_stages: [
          "DEMAND_ANALYSIS",
          "RESISTANCE_HANDOFF",
          "ECCENTRIC_GROUP_MODE_COMPATIBILITY",
          "RESISTANCE_CALCULATION",
        ],
        source_trace: ["APPLICATION_INTEGRATION"],
        input_fingerprint: "1".repeat(64),
        result_fingerprint: "2".repeat(64),
      }],
      required_check_ids: [lineCheck.result_id, "FIRST_ROW:layer-A"],
      not_required_check_ids: ["INTERROW:layer-A:BOLT_LINE_2"],
      unsupported_required_check_ids: ["FIRST_ROW:layer-A"],
      incomplete_required_check_ids: ["BOLT_TENSION:B_R1_L1"],
      failed_check_ids: [],
      qualification: "ENGINEERING_REVIEW_REQUIRED",
      numerical_comparison: "NOT_EVALUATED",
      governing_supported_check_ids: [lineCheck.result_id],
      overall_disposition: "NOT_EVALUATED",
      trace_layers: [
        "DEMAND_ANALYSIS",
        "RESISTANCE_HANDOFF",
        "ECCENTRIC_GROUP_MODE_COMPATIBILITY",
        "RESISTANCE_CALCULATION",
        "APPLICATION_INTEGRATION",
      ],
      result_fingerprint: "3".repeat(64),
    },
  };
}

async function openUnifiedMultirow(rows = 2, lines = 2) {
  render(<ShearConnectionsWorkspace />);
  await screen.findByRole("heading", { name: "Brace-to-column connection" });
  fireEvent.click(screen.getByRole("button", { name: "Load verified J1 — U.S." }));
  mocks.multiPreview.mockImplementation((request: MultiRowConnectionRequest) =>
    Promise.resolve(multirowPreviewFixture(request.row_count, request.bolts_per_row)),
  );
  fireEvent.change(screen.getByLabelText("Row count"), { target: { value: String(rows) } });
  fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: String(lines) } });
  await waitFor(() => { expect(mocks.multiPreview).toHaveBeenCalled(); });
  await waitFor(() => {
    expect(screen.getByTestId("mock-engineering-scene")).toHaveAttribute(
      "data-bolt-count",
      String(rows * lines),
    );
  });
}

describe("Stage 2.4C-R1 unified connection workspace", () => {
  beforeEach(() => {
    mocks.singlePreview.mockReset();
    mocks.singleEvaluate.mockReset();
    mocks.multiPreview.mockReset();
    mocks.multiEvaluate.mockReset();
    mocks.singlePreview.mockResolvedValue(previewResponseFixture());
    mocks.multiPreview.mockResolvedValue(multirowPreviewFixture());
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts at 1 x 1 in the one connection workspace and accepted single-bolt route", async () => {
    render(<ShearConnectionsWorkspace />);
    expect(screen.getByRole("heading", { name: "Connection engineering workspace" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Multi-row bolt group" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Row count")).toHaveValue(1);
    expect(screen.getByLabelText("Bolts per row")).toHaveValue(1);
    await screen.findByRole("heading", { name: "Brace-to-column connection" });
    expect(mocks.singlePreview).toHaveBeenCalledTimes(1);
    expect(mocks.multiPreview).not.toHaveBeenCalled();
  });

  it("changes 1 x 1 to 2 x 1 and 2 x 2 in the same canonical 3D scene", async () => {
    await openUnifiedMultirow(2, 1);
    expect(screen.getByText("Canonical 3D connection")).toBeVisible();
    expect(screen.getByTestId("mock-engineering-scene")).toHaveAttribute("data-bolt-count", "2");
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    await waitFor(() => {
      expect(screen.getByTestId("mock-engineering-scene")).toHaveAttribute("data-bolt-count", "4");
    });
    const request = mocks.multiPreview.mock.calls.at(-1)?.[0] as MultiRowConnectionRequest;
    expect(request.row_count).toBe(2);
    expect(request.bolts_per_row).toBe(2);
    expect(request.physical_connection?.geometry_template?.brace_to_column_directed_angle_deg).toBe("45");
    fireEvent.click(screen.getByText("Bolt / Interface", { exact: true }));
    expect(screen.getByText(/Standard physical hole/)).toBeVisible();
    expect(screen.getByText(/0.563 in.*Us Customary Printed/i)).toBeVisible();
    expect(screen.getByRole("heading", { name: "Brace-to-column connection" })).toBeVisible();
  });

  it("keeps the backend-authored 2D layout secondary and optional", async () => {
    await openUnifiedMultirow();
    const diagnostic = screen.getByText("Bolt layout — optional 2D diagnostic");
    expect(diagnostic.closest("details")).not.toHaveAttribute("open");
    fireEvent.click(diagnostic);
    expect(screen.getByRole("heading", { name: "Multi-row connection viewer" })).toBeVisible();
    expect(screen.getByText("Loaded boundary")).toBeVisible();
    fireEvent.click(screen.getByLabelText("Show accepted block paths"));
    expect(document.querySelector(".multirow-block-path")).not.toBeNull();
  });

  it("scales every 2D bolt and hole independently from backend physical dimensions", () => {
    const response = multirowPreviewFixture();
    const snapshot = response.visualization;
    if (snapshot === null) throw new Error("Multi-row visualization fixture is required.");
    const rendered = render(
      <MultiRowVisualizationPanel
        snapshot={snapshot}
        showBlockPaths={false}
        displayUnitSystem="US_CUSTOMARY"
      />,
    );
    const baselineBolts = [...document.querySelectorAll<SVGCircleElement>(".multirow-bolt")];
    const baselineHoles = [...document.querySelectorAll<SVGCircleElement>(".multirow-hole")];
    expect(baselineBolts).toHaveLength(4);
    expect(baselineHoles).toHaveLength(4);
    const baselineBoltRadius = Number(baselineBolts[0]?.getAttribute("r"));
    const baselineHoleRadius = Number(baselineHoles[0]?.getAttribute("r"));
    expect(baselineHoleRadius / baselineBoltRadius).toBeCloseTo(0.563 / 0.5);

    const changed = structuredClone(snapshot);
    changed.bolts.forEach((bolt) => {
      bolt.bolt_diameter.value = "0.75";
      bolt.hole_diameter.value = "0.875";
    });
    rendered.rerender(
      <MultiRowVisualizationPanel
        snapshot={changed}
        showBlockPaths={false}
        displayUnitSystem="US_CUSTOMARY"
      />,
    );
    const changedBolts = [...document.querySelectorAll<SVGCircleElement>(".multirow-bolt")];
    const changedHoles = [...document.querySelectorAll<SVGCircleElement>(".multirow-hole")];
    expect(changedBolts.every((circle) => Number(circle.getAttribute("r")) === baselineBoltRadius * 1.5)).toBe(true);
    expect(changedHoles.every((circle) => Number(circle.getAttribute("r")) === baselineHoleRadius * (0.875 / 0.563))).toBe(true);
  });

  it("plots corrected backend bolt coordinates against the fixed loaded boundary", () => {
    const response = multirowPreviewFixture();
    const snapshot = response.visualization;
    if (snapshot === null) throw new Error("Multi-row visualization fixture is required.");
    snapshot.boundary = ["-2", "6", "-2.5", "4.5"];
    const firstBolt = snapshot.bolts[0];
    if (firstBolt === undefined) throw new Error("A canonical bolt is required.");
    snapshot.bolts[0] = { ...firstBolt, x: "0" };
    render(
      <MultiRowVisualizationPanel
        snapshot={snapshot}
        showBlockPaths={false}
        displayUnitSystem="US_CUSTOMARY"
      />,
    );
    const boundary = document.querySelector<SVGRectElement>(".multirow-layer-surface");
    const bolt = document.querySelector<SVGCircleElement>(".multirow-bolt");
    if (boundary === null || bolt === null) throw new Error("Canonical 2D geometry is required.");
    const normalized = (
      Number(bolt.getAttribute("cx")) - Number(boundary.getAttribute("x"))
    ) / Number(boundary.getAttribute("width"));
    expect(normalized).toBeCloseTo(0.25, 12);
    expect(screen.getByText("Loaded boundary")).toBeVisible();
  });

  it("fails closed for one row with multiple bolts", async () => {
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Brace-to-column connection" });
    mocks.multiPreview.mockClear();
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    expect(screen.getAllByText(/One row with multiple bolts/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(mocks.multiPreview).not.toHaveBeenCalled();
  });

  it("runs multi-row design only on command and stales it after engineering edits", async () => {
    mocks.multiEvaluate.mockResolvedValue(multirowDesignFixture());
    await openUnifiedMultirow();
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    expect(mocks.multiEvaluate).not.toHaveBeenCalled();
    fireEvent.click(button);
    await screen.findByRole("heading", { name: /Engineering review required/i });
    expect(mocks.multiEvaluate).toHaveBeenCalledTimes(1);
    fireEvent.change(screen.getByLabelText("In-plane Fx"), { target: { value: "0.8" } });
    expect(screen.getByText(/Design results are stale/i)).toBeVisible();
    expect(mocks.multiEvaluate).toHaveBeenCalledTimes(1);
  });

  it("maps loaded-boundary placement exactly, previews it, and stales design without rerunning", async () => {
    mocks.multiEvaluate.mockResolvedValue(multirowDesignFixture());
    await openUnifiedMultirow();
    const designButton = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(designButton).toBeEnabled(); });
    fireEvent.click(designButton);
    await screen.findByRole("heading", { name: /Engineering review required/i });

    mocks.multiPreview.mockClear();
    for (const view of ["3D", "Front", "Top", "Side 1", "Side 2"]) {
      fireEvent.click(screen.getByRole("button", { name: view }));
      expect(screen.getByTestId("mock-engineering-scene")).toHaveAttribute("data-view", view);
    }
    expect(mocks.multiPreview).not.toHaveBeenCalled();
    expect(screen.queryByText(/Design results are stale/u)).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Loaded boundary to Row 1"), {
      target: { value: "4" },
    });
    expect(screen.getByText(/Design results are stale/u)).toBeVisible();
    await waitFor(() => { expect(mocks.multiPreview).toHaveBeenCalled(); });
    const submitted = mocks.multiPreview.mock.calls.at(-1)?.[0] as MultiRowConnectionRequest;
    expect(submitted.loaded_boundary_to_row_1_distance).toEqual({ value: "4", unit: "in" });
    expect(mocks.multiEvaluate).toHaveBeenCalledTimes(1);
  });

  it("switches back to 1 x 1 without losing common fields or reusing multi-row results", async () => {
    mocks.multiEvaluate.mockResolvedValue(multirowDesignFixture());
    await openUnifiedMultirow();
    fireEvent.change(screen.getByLabelText("Case label"), { target: { value: "Shared connection case" } });
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);
    await screen.findByRole("heading", { name: /Engineering review required/i });
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "1" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "1" } });
    await waitFor(() => { expect(mocks.singlePreview.mock.calls.length).toBeGreaterThan(1); });
    expect(screen.getByLabelText("Case label")).toHaveValue("Shared connection case");
    expect(screen.getByTestId("mock-engineering-scene")).toHaveAttribute("data-bolt-count", "1");
    expect(screen.queryByRole("heading", { name: /Engineering review required/i })).not.toBeInTheDocument();
  });

  it("selects any physical bolt and exposes row, line, and penetrated layers", async () => {
    await openUnifiedMultirow();
    const previewCalls = mocks.multiPreview.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Select B_R2_L2" }));
    expect(screen.getByLabelText("Selected object")).toHaveTextContent("Bolt · Row 2 · Line 2");
    expect(screen.getByText("Row 2")).toBeVisible();
    expect(screen.getByText("Bolt Line 2")).toBeVisible();
    expect(screen.getAllByText(/Angle Connected Leg.*W Column Flange/).length).toBeGreaterThan(0);
    expect(mocks.multiPreview).toHaveBeenCalledTimes(previewCalls);
    expect(mocks.multiEvaluate).not.toHaveBeenCalled();
  });

  it("debounces group geometry and maps engineer-defined provenance from the shared demand", async () => {
    await openUnifiedMultirow();
    await waitFor(() => { expect(mocks.multiPreview).toHaveBeenCalled(); });
    mocks.multiPreview.mockClear();
    vi.useFakeTimers();
    fireEvent.change(screen.getByLabelText("Row-demand method"), { target: { value: "FRACTIONS" } });
    fireEvent.change(screen.getByLabelText("Row 1 fraction"), { target: { value: "0.6" } });
    fireEvent.change(screen.getByLabelText("Pitch"), { target: { value: "2.5" } });
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(mocks.multiPreview).toHaveBeenCalledTimes(1);
    const request = mocks.multiPreview.mock.calls[0]?.[0] as MultiRowConnectionRequest;
    expect(request.engineer_allocations[0]?.fraction).toBe("0.6");
    expect(request.pitch.value).toBe("2.5");
    expect(request.provenance.engineer_confirmed).toBe(true);
  });

  it("keeps invalid physical geometry visible and design fail closed", async () => {
    mocks.multiPreview.mockResolvedValue(multirowPreviewFixture(2, 2, "INVALID_GEOMETRY"));
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Brace-to-column connection" });
    fireEvent.click(screen.getByRole("button", { name: "Load verified J1 — U.S." }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    await waitFor(() => { expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled(); });
    expect((await screen.findAllByText(/Invalid multi-row geometry/i)).length).toBeGreaterThan(0);
  });

  it("shows more-than-three-row qualification without an ordinary PASS", async () => {
    await openUnifiedMultirow(4, 2);
    expect(screen.getAllByText(/More than three rows requires Section 2 3 2 qualification/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/^Pass$/i)).not.toBeInTheDocument();
  });

  it("handles multi-row preview and design transport failures without invented results", async () => {
    mocks.multiPreview.mockRejectedValue(new EvaluationTransportError("NETWORK", null, "offline"));
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Brace-to-column connection" });
    fireEvent.click(screen.getByRole("button", { name: "Load verified J1 — U.S." }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    await screen.findByText("offline");
    mocks.multiPreview.mockImplementation((request: MultiRowConnectionRequest) =>
      Promise.resolve(multirowPreviewFixture(request.row_count, request.bolts_per_row)),
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry preview" }));
    await waitFor(() => { expect(screen.getByTestId("mock-engineering-scene")).toHaveAttribute("data-bolt-count", "2"); });
    mocks.multiEvaluate.mockRejectedValue(new EvaluationTransportError("HTTP", 503, "service unavailable"));
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);
    expect(await screen.findByText("service unavailable")).toBeVisible();
    mocks.multiEvaluate.mockRejectedValue(new EvaluationTransportError("NETWORK", null, "network failure"));
    fireEvent.click(button);
    expect(await screen.findByText("network failure")).toBeVisible();
  });

  it("preserves SI common state in the multi-row request", async () => {
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Brace-to-column connection" });
    fireEvent.click(screen.getByRole("button", { name: "Load verified J1 — SI" }));
    mocks.multiPreview.mockImplementation((request: MultiRowConnectionRequest) =>
      Promise.resolve(multirowPreviewFixture(request.row_count, request.bolts_per_row)),
    );
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    await waitFor(() => { expect(mocks.multiPreview).toHaveBeenCalled(); });
    const request = mocks.multiPreview.mock.calls.at(-1)?.[0] as MultiRowConnectionRequest;
    expect(request.display_unit_system).toBe("SI");
    expect(request.source_length_unit).toBe("mm");
    expect(request.physical_connection?.view_extents?.brace_view_length.unit).toBe("mm");
  });

  it("ignores a late multi-row design response after a shared engineering edit", async () => {
    let resolveDesign: ((value: MultiRowDesignResponse) => void) | undefined;
    mocks.multiEvaluate.mockImplementation(() => new Promise((resolve) => { resolveDesign = resolve; }));
    await openUnifiedMultirow();
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);
    fireEvent.change(screen.getByLabelText("Gauge"), { target: { value: "2.2" } });
    act(() => { resolveDesign?.(multirowDesignFixture()); });
    await act(async () => { await Promise.resolve(); });
    expect(screen.queryByRole("heading", { name: /Engineering review required/i })).not.toBeInTheDocument();
  });

  it("keeps the existing 1 x 1 design result meaning", async () => {
    mocks.singleEvaluate.mockResolvedValue(responseFixture());
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Brace-to-column connection" });
    fireEvent.click(screen.getByRole("button", { name: "Load verified J1 — U.S." }));
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);
    await screen.findByRole("heading", { name: /Section 2.3.2 qualification required/i });
    expect(mocks.singleEvaluate).toHaveBeenCalledTimes(1);
    expect(mocks.multiEvaluate).not.toHaveBeenCalled();
  });

  it("edits every multi-row-specific group control in the unified sidebar", async () => {
    await openUnifiedMultirow(2, 2);
    fireEvent.change(screen.getByLabelText("Loaded boundary to Row 1"), { target: { value: "2.1" } });
    fireEvent.change(screen.getByLabelText("Negative side distance"), { target: { value: "1.6" } });
    fireEvent.change(screen.getByLabelText("Positive side distance"), { target: { value: "1.7" } });
    fireEvent.change(screen.getByLabelText("Connected material pair"), { target: { value: "FRP_STEEL" } });
    fireEvent.change(screen.getByLabelText("FRP LW-axis angle"), { target: { value: "30" } });
    fireEvent.change(screen.getByLabelText("Source calculation"), { target: { value: "Engineer sheet E-42" } });
    fireEvent.change(screen.getByLabelText("Force-line offset"), { target: { value: ".25" } });

    fireEvent.change(screen.getByLabelText("Row-demand method"), {
      target: { value: "DIRECT_ROW_FORCES" },
    });
    fireEvent.change(screen.getByLabelText("Row 1 direct force"), { target: { value: ".45" } });
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "3" } });
    expect(screen.getByLabelText("Row 3 direct force")).toHaveValue("0");

    fireEvent.change(screen.getByLabelText("Row-demand method"), { target: { value: "FRACTIONS" } });
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Row 2 fraction"), { target: { value: ".4" } });
    fireEvent.change(screen.getByLabelText("First-row method"), {
      target: { value: "ASCE_COMMENTARY_FULL" },
    });
    fireEvent.change(screen.getByLabelText("Prescribed Lbr"), { target: { value: "1.1" } });
    fireEvent.click(screen.getByLabelText("Bolt-axis tension required"));
    fireEvent.change(screen.getByLabelText("Row-demand method"), { target: { value: "ASCE_PRESCRIBED" } });
    fireEvent.change(screen.getByLabelText("Bolt · Row 1 · Line 1 axis tension"), {
      target: { value: ".1" },
    });
    fireEvent.click(screen.getByLabelText("Bolt-axis tension required"));

    expect(screen.getByLabelText("Connected material pair")).toHaveValue("FRP_STEEL");
    expect(screen.getByLabelText("FRP LW-axis angle")).toHaveValue("30");
    expect(screen.getByLabelText("First-row method")).toHaveValue("ASCE_COMMENTARY_FULL");
    expect(screen.getByLabelText("Prescribed Lbr")).toHaveValue("1.1");
    expect(screen.getByLabelText("Bolt-axis tension required")).not.toBeChecked();
  }, 15000);

  it("fails closed for invalid multi-row counts, dimensions, demand, and factors", async () => {
    await openUnifiedMultirow(2, 2);
    const button = screen.getByRole("button", { name: "Run Design Check" });

    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2.5" } });
    expect(button).toHaveAttribute("title", "Row count must be a positive integer.");
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "0" } });
    expect(button).toHaveAttribute("title", "Bolts per row must be a positive integer.");
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Gauge"), { target: { value: "0" } });
    expect(button).toHaveAttribute("title", "Bolt-group dimensions must be finite and greater than zero.");
    fireEvent.change(screen.getByLabelText("Gauge"), { target: { value: "2" } });

    fireEvent.click(screen.getByRole("button", { name: "Automatic from member-end force" }));
    await waitFor(() => {
      const submitted = mocks.multiPreview.mock.calls.at(-1)?.[0] as MultiRowConnectionRequest;
      expect(submitted.demand_source).toBe("AUTOMATIC_MEMBER_END_FORCE");
      expect(submitted.signed_force_x).toBeUndefined();
    });
    fireEvent.click(screen.getByRole("button", { name: "Explicit resolved connection demand" }));
    fireEvent.change(screen.getByLabelText("In-plane Fx"), { target: { value: "0" } });
    fireEvent.change(screen.getByLabelText("In-plane Fy"), { target: { value: "0" } });
    expect(button).toHaveAttribute(
      "title",
      "The signed externally resolved connection demand must be finite and nonzero.",
    );
    fireEvent.change(screen.getByLabelText("In-plane Fx"), { target: { value: ".7" } });
    fireEvent.change(screen.getByLabelText("CM"), { target: { value: "" } });
    expect(button).toHaveAttribute("title", "Select finite CM, CT, and CCH factors before multi-row preview.");

    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "1" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "1" } });
    await waitFor(() => {
      expect(button).toHaveAttribute("title", "Select finite CM, CT, and CCH factors.");
    });
  });

  it("shows selected-bolt checks matched by bolt, row, and bolt line", async () => {
    const design = multirowDesignFixture();
    const calculation = design.calculation_result;
    if (calculation === null) throw new Error("Multi-row calculation fixture is required.");
    const first = calculation.results[0];
    if (first === undefined) throw new Error("Multi-row result fixture is required.");
    calculation.qualification = "SECTION_2_3_2_QUALIFICATION_REQUIRED";
    calculation.governing_result_ids = [];
    calculation.results = [
      { ...first, result_id: "bolt", bolt_id: "B_R2_L2", row_id: null, bolt_line_id: null },
      { ...first, result_id: "row", bolt_id: null, row_id: "ROW_2", bolt_line_id: null },
      { ...first, result_id: "line", bolt_id: null, row_id: null, bolt_line_id: "BOLT_LINE_2", numerical_comparison: "NOT_EVALUATED", availability: "CALCULATION_NOT_SUPPORTED" },
      { ...first, result_id: "unrelated", bolt_id: "B_R1_L1", row_id: "ROW_1", bolt_line_id: "BOLT_LINE_1" },
      { ...first, result_id: "connection", bolt_id: null, row_id: null, bolt_line_id: null, layer_id: null, path_id: null },
    ];
    mocks.multiEvaluate.mockResolvedValue(design);
    await openUnifiedMultirow();
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);
    await screen.findByRole("heading", { name: /Engineering review required/i });
    fireEvent.click(screen.getByRole("button", { name: "Select B_R2_L2" }));
    const selectedChecks = document.querySelector(".selected-bolt-checks");
    expect(selectedChecks?.querySelectorAll("li")).toHaveLength(3);
    expect(selectedChecks).toHaveTextContent(/Calculation Not Supported.*demand 2\.500 kip/u);
    expect(screen.getByText(/not an ordinary prescriptive PASS/u)).toBeVisible();
    expect(screen.getByText("None")).toBeVisible();
    expect(screen.getAllByText("Connection").length).toBeGreaterThan(0);
  });

  it("uses member-action units for automatic multi-row inputs without frontend force transforms", async () => {
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Brace-to-column connection" });
    fireEvent.click(screen.getByRole("button", { name: "Load verified J1 — U.S." }));
    fireEvent.click(screen.getByRole("button", { name: "Automatic from member-end force" }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Row-demand method"), {
      target: { value: "DIRECT_ROW_FORCES" },
    });
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "3" } });
    expect(screen.getByLabelText("Row 3 direct force")).toHaveValue("0");
    fireEvent.click(screen.getByLabelText("Bolt-axis tension required"));
    expect(screen.queryByLabelText("Bolt · Row 1 · Line 1 axis tension")).not.toBeInTheDocument();
    await waitFor(() => {
      const submitted = mocks.multiPreview.mock.calls.at(-1)?.[0] as MultiRowConnectionRequest;
      expect(submitted.demand_source).toBe("AUTOMATIC_MEMBER_END_FORCE");
      expect(submitted.automatic_action_source_id).toBe("action-1");
      expect(submitted.signed_force_x).toBeUndefined();
      expect(submitted.engineer_allocations[2]?.direct_force?.unit).toBe("kip");
    });
  });

  it("renders backend automatic vectors and fail-closed handoff results only on command", async () => {
    mocks.multiPreview.mockImplementation((request: MultiRowConnectionRequest) =>
      Promise.resolve(
        request.demand_source === "AUTOMATIC_MEMBER_END_FORCE"
          ? automaticPreviewFixture()
          : multirowPreviewFixture(request.row_count, request.bolts_per_row),
      ),
    );
    mocks.multiEvaluate.mockResolvedValue(automaticDesignFixture());
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Brace-to-column connection" });
    fireEvent.click(screen.getByRole("button", { name: /Load verified J1 .* U\.S\./u }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Automatic from member-end force" }));

    const vectorToggle = await screen.findByLabelText("Per-bolt demand vectors");
    expect(vectorToggle).not.toBeChecked();
    expect(screen.queryByRole("list", { name: "Per-bolt demand vector values" })).not.toBeInTheDocument();
    fireEvent.click(vectorToggle);
    expect(screen.getByRole("list", { name: "Per-bolt demand vector values" })).toHaveTextContent(
      /0\.269258 kip/u,
    );
    expect(screen.getByText(/Backend-authored total per-bolt demand vectors/u)).toBeVisible();
    expect(mocks.multiEvaluate).not.toHaveBeenCalled();

    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);
    await screen.findByRole("heading", { name: "Not Evaluated" });
    expect(screen.getByText("Calculated supported checks")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Eccentric group-mode checks" })).toBeVisible();
    expect(screen.getByText(/Authorized scalar 0\.35 kip/u)).toBeVisible();
    expect(screen.getByText("Not required — zero line demand")).toBeVisible();
    expect(screen.getByText(/Eccentric first-row net tension is not supported/u)).toBeVisible();
    expect(screen.getAllByText(/Rational Eccentric Bolt Line Shearout Handoff/u).length).toBe(2);
    expect(screen.getAllByText(/Partial Eccentric/u)).toHaveLength(2);
    const limitation = screen.getByText(/Ordinary whole-connection PASS is prohibited/u);
    expect(limitation).toHaveTextContent(/Unsupported:/u);
    expect(limitation).toHaveTextContent(/Incomplete:/u);
    expect(screen.getByText(/mz:1/u)).toBeVisible();
    expect(screen.getByText(/Out Of Plane Force Requires Explicit Bolt Axis Demand/u)).toBeVisible();
    expect(mocks.multiEvaluate).toHaveBeenCalledTimes(1);

    const complete = automaticDesignFixture();
    const completeHandoff = complete.automatic_handoff_results[0];
    const connectionCheck = completeHandoff?.supported_results[0];
    if (completeHandoff === undefined || connectionCheck === undefined) {
      throw new Error("Complete automatic fixture is required.");
    }
    completeHandoff.unsupported_required_check_ids = [];
    completeHandoff.incomplete_required_check_ids = [];
    completeHandoff.governing_supported_check_ids = [];
    completeHandoff.parent_action_transfer_warnings = [];
    completeHandoff.numerical_comparison = "NOT_EVALUATED";
    completeHandoff.supported_results = [{
      ...connectionCheck,
      layer_id: null,
      bolt_id: null,
      row_id: null,
      bolt_line_id: null,
      path_id: null,
      numerical_comparison: "NOT_EVALUATED",
      availability: "ENGINEERING_REVIEW_REQUIRED",
    }];
    const completeIntegration = complete.automatic_group_mode_integration;
    if (completeIntegration === null) {
      throw new Error("Complete group-mode fixture is required.");
    }
    completeIntegration.unsupported_required_check_ids = [];
    completeIntegration.incomplete_required_check_ids = [];
    completeIntegration.governing_supported_check_ids = [];
    mocks.multiEvaluate.mockResolvedValueOnce(complete);
    fireEvent.click(button);
    await waitFor(() => {
      expect(screen.queryByText(/Ordinary whole-connection PASS is prohibited/u)).not.toBeInTheDocument();
    });
    expect(screen.getAllByText("Connection").length).toBeGreaterThan(0);
    expect(screen.getAllByText("None").length).toBeGreaterThan(0);
    expect(mocks.multiEvaluate).toHaveBeenCalledTimes(2);

    fireEvent.change(screen.getByLabelText("P / Fx"), { target: { value: ".8" } });
    expect(screen.getByText(/Design results are stale/u)).toBeVisible();
    await waitFor(() => {
      expect(mocks.multiPreview.mock.calls.at(-1)?.[0]).toMatchObject({
        demand_source: "AUTOMATIC_MEMBER_END_FORCE",
      });
    });
    expect(mocks.multiEvaluate).toHaveBeenCalledTimes(2);
    fireEvent.change(screen.getByLabelText("P / Fx"), { target: { value: "" } });
    expect(button).toHaveAttribute(
      "title",
      "Automatic member-end actions must be complete finite decimals.",
    );
  });

  it("presents known group-mode failure and every structured line state", async () => {
    const design = automaticDesignFixture();
    const integration = design.automatic_group_mode_integration;
    if (integration === null) throw new Error("Group-mode fixture is required.");
    const scenario = integration.scenario_results[0];
    const supportedLine = scenario?.line_results[0];
    const zeroLine = scenario?.line_results[1];
    const supportedCheck = supportedLine?.shear_out_result;
    if (scenario === undefined || supportedLine === undefined || zeroLine === undefined || supportedCheck === null || supportedCheck === undefined) {
      throw new Error("Group-mode line fixtures are required.");
    }
    const failedCheck = {
      ...supportedCheck,
      numerical_comparison: "FAIL",
      utilization: "1.2",
    };
    const failedLine = { ...supportedLine, shear_out_result: failedCheck };
    const unsupportedLine = {
      ...supportedLine,
      bolt_line_id: "BOLT_LINE_NONPARALLEL",
      check_id: "INTERROW:layer-A:BOLT_LINE_NONPARALLEL",
      handoff_status: "CALCULATION_NOT_SUPPORTED" as const,
      required_line_demand: null,
      shear_out_result: null,
      warnings: [{
        code: "ECCENTRIC_SHEAROUT_LINE_RESULTANT_NOT_PARALLEL_TO_CONNECTION_FORCE",
        trace: [],
      }],
    };
    const reversedLine = {
      ...unsupportedLine,
      bolt_line_id: "BOLT_LINE_REVERSED",
      check_id: "INTERROW:layer-A:BOLT_LINE_REVERSED",
      parallel_scalar: { value: "-.1", unit: "kip" },
      warnings: [{
        code: "ECCENTRIC_SHEAROUT_LINE_FORCE_REVERSAL_NOT_SUPPORTED",
        trace: ["parallel_n:-444.8"],
      }],
    };
    const unsupportedWithoutWarning = {
      ...unsupportedLine,
      bolt_line_id: "BOLT_LINE_UNSUPPORTED",
      check_id: "INTERROW:layer-A:BOLT_LINE_UNSUPPORTED",
      warnings: [],
    };
    const parentExemptLine = {
      ...unsupportedLine,
      bolt_line_id: "BOLT_LINE_EXEMPT",
      check_id: null,
      handoff_status: "NOT_REQUIRED_PARENT_EXEMPTION" as const,
      warnings: [],
    };
    const inheritedLine = {
      ...supportedLine,
      bolt_line_id: "BOLT_LINE_INHERITED",
      check_id: "INTERROW:layer-A:BOLT_LINE_INHERITED",
      handoff_status: "INHERITED_LEGACY_STAGE_2_4B" as const,
    };
    const inheritedWithoutResult = {
      ...inheritedLine,
      bolt_line_id: "BOLT_LINE_INHERITED_PENDING",
      check_id: "INTERROW:layer-A:BOLT_LINE_INHERITED_PENDING",
      shear_out_result: null,
    };
    const inheritedNotEvaluated = {
      ...inheritedLine,
      bolt_line_id: "BOLT_LINE_INHERITED_REVIEW",
      check_id: "INTERROW:layer-A:BOLT_LINE_INHERITED_REVIEW",
      shear_out_result: {
        ...supportedCheck,
        numerical_comparison: "NOT_EVALUATED" as const,
        availability: "ENGINEERING_REVIEW_REQUIRED" as const,
      },
    };
    const authorizedWithoutResult = {
      ...supportedLine,
      bolt_line_id: "BOLT_LINE_AUTHORIZED_PENDING",
      check_id: "INTERROW:layer-A:BOLT_LINE_AUTHORIZED_PENDING",
      shear_out_result: null,
    };
    const authorizedNotEvaluated = {
      ...supportedLine,
      bolt_line_id: "BOLT_LINE_AUTHORIZED_REVIEW",
      check_id: "INTERROW:layer-A:BOLT_LINE_AUTHORIZED_REVIEW",
      shear_out_result: {
        ...supportedCheck,
        numerical_comparison: "NOT_EVALUATED" as const,
        availability: "ENGINEERING_REVIEW_REQUIRED" as const,
      },
    };
    scenario.line_results = [
      failedLine,
      zeroLine,
      unsupportedLine,
      reversedLine,
      unsupportedWithoutWarning,
      parentExemptLine,
      inheritedLine,
      inheritedWithoutResult,
      inheritedNotEvaluated,
      authorizedWithoutResult,
      authorizedNotEvaluated,
    ];
    scenario.supported_results = [failedCheck];
    scenario.failed_check_ids = [failedCheck.result_id];
    scenario.numerical_comparison = "FAIL";
    scenario.overall_disposition = "FAIL";
    integration.failed_check_ids = [failedCheck.result_id];
    integration.numerical_comparison = "FAIL";
    integration.overall_disposition = "FAIL";
    integration.scenario_results.push({
      ...scenario,
      scenario_id: "SOURCE_EXEMPT",
      line_results: [parentExemptLine],
      first_row_compatibility: {
        status: "NOT_REQUIRED_PARENT_EXEMPTION",
        required_check_ids: [],
        warnings: [{
          code: "ECCENTRIC_FIRST_ROW_NET_TENSION_GENERAL_METHOD_NOT_ESTABLISHED_RC1",
          trace: [],
        }],
      },
      supported_results: [],
      required_check_ids: [],
      not_required_check_ids: [],
      unsupported_required_check_ids: [],
      incomplete_required_check_ids: [],
      failed_check_ids: [],
      numerical_comparison: "NOT_EVALUATED",
      governing_supported_check_ids: [],
      overall_disposition: "NOT_EVALUATED",
    });

    mocks.multiPreview.mockImplementation((request: MultiRowConnectionRequest) =>
      Promise.resolve(
        request.demand_source === "AUTOMATIC_MEMBER_END_FORCE"
          ? automaticPreviewFixture()
          : multirowPreviewFixture(request.row_count, request.bolts_per_row),
      ),
    );
    mocks.multiEvaluate.mockResolvedValue(design);
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Brace-to-column connection" });
    fireEvent.click(screen.getByRole("button", { name: /Load verified J1 .* U\.S\./u }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Automatic from member-end force" }));
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);

    await screen.findByRole("heading", { name: "Fail" });
    expect(screen.getAllByText("Fail").length).toBeGreaterThan(1);
    expect(screen.getAllByText(/Line Resultant Not Parallel To Connection Force/u).length).toBeGreaterThan(1);
    expect(screen.getAllByText(/Line Force Reversal Not Supported/u).length).toBeGreaterThan(1);
    expect(screen.getAllByText("Calculation not supported").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Not required — parent exemption").length).toBeGreaterThan(0);
    expect(screen.getByText("Inherited legacy Stage 2.4B")).toBeVisible();
    expect(screen.getByText(/parallel_n:-444\.8/u)).toBeVisible();
    expect(screen.getByText(/Eccentric first-row net tension is not supported/u)).toBeVisible();
  });

  it("keeps zero-residual automatic presentation on the inherited legacy result", async () => {
    const design = automaticDesignFixture();
    const integration = design.automatic_group_mode_integration;
    const handoff = design.automatic_handoff_results[0];
    if (integration === null || handoff === undefined) {
      throw new Error("Legacy automatic fixtures are required.");
    }
    for (const scenario of integration.scenario_results) {
      scenario.first_row_compatibility = {
        status: "INHERITED_LEGACY_STAGE_2_4B",
        required_check_ids: ["FIRST_ROW:layer-A"],
        warnings: [],
      };
      scenario.line_results = scenario.line_results.map((line, index) => ({
        ...line,
        handoff_status: index === 0
          ? "INHERITED_LEGACY_STAGE_2_4B"
          : "NOT_REQUIRED_PARENT_EXEMPTION",
        required_line_demand: line.required_line_demand ?? { value: ".35", unit: "kip" },
        shear_out_result: line.shear_out_result ?? handoff.supported_results[0] ?? null,
      }));
    }
    integration.unsupported_required_check_ids = [];
    integration.incomplete_required_check_ids = [];
    integration.overall_disposition = handoff.overall_disposition;
    integration.numerical_comparison = handoff.numerical_comparison;

    mocks.multiPreview.mockImplementation((request: MultiRowConnectionRequest) =>
      Promise.resolve(
        request.demand_source === "AUTOMATIC_MEMBER_END_FORCE"
          ? automaticPreviewFixture()
          : multirowPreviewFixture(request.row_count, request.bolts_per_row),
      ),
    );
    mocks.multiEvaluate.mockResolvedValue(design);
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Brace-to-column connection" });
    fireEvent.click(screen.getByRole("button", { name: /Load verified J1 .* U\.S\./u }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Automatic from member-end force" }));
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);

    await screen.findByText("Calculated supported checks");
    expect(screen.queryByRole("heading", { name: "Eccentric group-mode checks" })).not.toBeInTheDocument();
    expect(screen.getByText(/Stage 2\.5B supported resistance handoff/u)).toBeVisible();

    const handoffOnly = automaticDesignFixture();
    handoffOnly.automatic_group_mode_integration = null;
    mocks.multiEvaluate.mockResolvedValueOnce(handoffOnly);
    fireEvent.click(button);
    await waitFor(() => {
      expect(mocks.multiEvaluate).toHaveBeenCalledTimes(2);
    });
    expect(screen.queryByRole("heading", { name: "Eccentric group-mode checks" })).not.toBeInTheDocument();
  });

  it("fails closed when an internal explicit demand is absent and uses action fallbacks", async () => {
    const source = benchmarks.loadJ1Benchmark("US_CUSTOMARY");
    const withoutExplicit = structuredClone(source);
    withoutExplicit.explicit_resolved_demand = null;
    const action = withoutExplicit.joint_assembly.member_end_actions[0];
    if (action === undefined) throw new Error("Member-end action fixture is required.");
    action.reference_point = {
      kind: "EXPLICIT_POINT",
      owner_id: null,
      position: { x: "0", y: "0", z: "0", unit: "in" },
    };
    const benchmark = vi.spyOn(benchmarks, "loadJ1Benchmark").mockImplementation(() =>
      structuredClone(withoutExplicit),
    );
    const blockedPreview = previewResponseFixture();
    blockedPreview.design_check_ready = false;
    blockedPreview.design_check_blocking_reasons = ["Backend design readiness is incomplete."];
    mocks.singlePreview.mockResolvedValue(blockedPreview);
    mocks.multiPreview.mockResolvedValue(automaticPreviewFixture());
    try {
      render(<ShearConnectionsWorkspace />);
      await screen.findByRole("heading", { name: "Brace-to-column connection" });
      expect(screen.getByRole("button", { name: "Run Design Check" })).toHaveAttribute(
        "title",
        "Backend design readiness is incomplete.",
      );
      fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
      expect(screen.getByRole("button", { name: "Run Design Check" })).toHaveAttribute(
        "title",
        "Explicit externally resolved connection demand is required for multi-row design.",
      );
      fireEvent.click(screen.getByRole("button", { name: "Automatic from member-end force" }));
      fireEvent.change(screen.getByLabelText("Row-demand method"), {
        target: { value: "DIRECT_ROW_FORCES" },
      });
      fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "3" } });
      fireEvent.click(screen.getByLabelText("Bolt-axis tension required"));
      await waitFor(() => {
        const submitted = mocks.multiPreview.mock.calls.at(-1)?.[0] as MultiRowConnectionRequest;
        expect(submitted.provenance.reference_point).toBe("EXPLICIT_POINT:action-1");
        expect(submitted.engineer_allocations[2]?.direct_force?.unit).toBe("kip");
      });
    } finally {
      benchmark.mockRestore();
    }
  });

  it("blocks design when a valid canonical preview is not backend-design-ready", async () => {
    const response = multirowPreviewFixture();
    response.design_check_ready = false;
    mocks.multiPreview.mockResolvedValue(response);
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Brace-to-column connection" });
    fireEvent.click(screen.getByRole("button", { name: "Load verified J1 — U.S." }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Run Design Check" })).toHaveAttribute(
        "title",
        "The backend has not marked this multi-row arrangement design-ready.",
      );
    });
  });
});
