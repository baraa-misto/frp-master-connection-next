import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationTransportError } from "../src/api/client";
import { clearanceWitness } from "./directGeometryIssueFixtures";
import f3Faces from "./fixtures/directF3EngineeringFaces.json";
import f593Resolution from "./fixtures/f593_f4_resolution.json";
import type { VisualizationSnapshot } from "../src/api/contracts";
import type {
  MultiRowConnectionRequest,
  DirectEngineeringFace,
  MultiRowDesignResponse,
  MultiRowPreviewResponse,
} from "../src/api/multirowContracts";
import { MultiRowVisualizationPanel } from "../src/visualization/MultiRowVisualizationPanel";
import { ShearConnectionsWorkspace } from "../src/workspace/ShearConnectionsWorkspace";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import * as benchmarks from "../src/fixtures/j1Benchmarks";
import { mat1Snapshot, setMAT1Active, setMAT1Conditions } from "../src/state/mat1Session";
import {
  previewResponseFixture,
  visualizationFixture,
} from "./fixtures";

const mocks = vi.hoisted(() => ({
  singlePreview: vi.fn(),
  singleEvaluate: vi.fn(),
  multiPreview: vi.fn(),
  multiEvaluate: vi.fn(),
}));
function requiredElement(element: Element | null | undefined): Element {
  if (element === null || element === undefined) throw new Error("Expected diagnostic control");
  return element;
}

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
      layers: [{ layer_id: "layer-A", component_id: "member-a", material_id: "ICE_LOCKED_PULTRUDED_FRP", material_axis_angle_degrees: "0", material_direction: "LONGITUDINAL", thickness: { value: ".375", unit: "in" } }, { layer_id: "layer-B", component_id: "member-b", material_id: "ICE_LOCKED_PULTRUDED_FRP", material_axis_angle_degrees: "90", material_direction: "TRANSVERSE", thickness: { value: ".375", unit: "in" } }],
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
  await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
  fireEvent.click(screen.getByRole("button", { name: "Legacy J1 regression fixture — U.S." }));
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

// OR1-07: Direct automatically uses member-end force. A harmless layout round
// trip requests a fresh preview in tests that formerly clicked a demand toggle.
function activateNormalAutomaticDemand(): void {
  const toggle = screen.queryByRole("button", { name: "Automatic from member-end force" });
  if (toggle !== null) {
    fireEvent.click(toggle);
    return;
  }
  const rows = screen.getByLabelText<HTMLInputElement>("Row count");
  const original = rows.value;
  fireEvent.change(rows, { target: { value: String(Number(original) + 1) } });
  fireEvent.change(rows, { target: { value: original } });
}

describe("Stage 2.4C-R1 unified connection workspace", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(f593Resolution)))));
    mocks.singlePreview.mockReset();
    mocks.singleEvaluate.mockReset();
    mocks.multiPreview.mockReset();
    mocks.multiEvaluate.mockReset();
    mocks.singlePreview.mockResolvedValue(previewResponseFixture());
    mocks.multiPreview.mockResolvedValue(multirowPreviewFixture());
  });

  afterEach(() => {
    setMAT1Active(false);
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("binds normal thread confirmation to catalog selectors before any example load", async () => {
    render(<ShearConnectionsWorkspace />);
    activateNormalAutomaticDemand();
    await waitFor(() => { expect(mocks.multiPreview).toHaveBeenCalled(); });
    expect(screen.queryByText(/controlled ASTM F593 catalog tensile-strength table/u)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Shear-plane threads"), {target:{value:"INCLUDED"}});
    expect(mat1Snapshot().fastenerSelections["multi-row"]).toMatchObject({kind:"CATALOG",shear_thread_status:"INCLUDED"});
    expect(screen.getByLabelText("Shear-plane threads")).toHaveValue("INCLUDED");
    fireEvent.change(screen.getByLabelText("Shear-plane threads"), {target:{value:"UNKNOWN"}});
    expect(mat1Snapshot().fastenerSelections["multi-row"]).toMatchObject({kind:"CATALOG",shear_thread_status:"UNKNOWN"});
  });

  it("loads normal Direct examples in both unit systems without opening legacy fixtures", async () => {
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: "Load Direct example — U.S." }));
    expect(screen.getByLabelText<HTMLSelectElement>("Unit system").value).toBe("US_CUSTOMARY");
    fireEvent.click(screen.getByRole("button", { name: "Load Direct example — SI" }));
    expect(screen.getByLabelText<HTMLSelectElement>("Unit system").value).toBe("SI");
    expect(screen.getByLabelText<HTMLInputElement>("Leg y").value).toBe("101.6");
    expect(screen.getByText(/historical J1 regression fixture may not satisfy current Direct physical-validation rules/)).not.toBeVisible();
  });

  it("explains missing shared conditions before requesting a Direct design", async () => {
    setMAT1Active(true);
    setMAT1Conditions({ ...mat1Snapshot().conditions, load_case_name: "", time_effect_category: "" });
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(screen.getAllByText(/Enter a load-case name/)[0]).toBeVisible();
    act(() => { setMAT1Conditions({ ...mat1Snapshot().conditions, load_case_name: "LC-1", sustained_temperature: { value: "", unit: "degF" } }); });
    expect(screen.getAllByText(/Select the load classification/)[0]).toBeVisible();
    act(() => { setMAT1Conditions({ ...mat1Snapshot().conditions, sustained_temperature: { value: "72", unit: "degF" }, maximum_temperature: { value: "", unit: "degF" } }); });
    expect(screen.getAllByText(/Select the load classification/)[0]).toBeVisible();
    act(() => { setMAT1Conditions({ ...mat1Snapshot().conditions, maximum_temperature: { value: "72", unit: "degF" } }); });
    expect(screen.getAllByText(/Select the load classification/)[0]).toBeVisible();
    expect(mocks.multiEvaluate).not.toHaveBeenCalled();
  });

  it("previews a compatible Direct layout and applies it only on explicit command", async () => {
    await openUnifiedMultirow();
    const before = screen.getByLabelText<HTMLInputElement>("Leg y");
    const original = before.value;
    const candidate = multirowPreviewFixture();
    candidate.geometry_status = "VALID";
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(candidate), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Suggest compatible geometry" }));
    expect(await screen.findByText(/Proposed geometry for the current/)).toBeInTheDocument();
    expect(screen.getByLabelText("Leg y")).toHaveValue(original);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Apply proposed geometry" }));
    expect(screen.queryByText(/Proposed geometry for the current/)).not.toBeInTheDocument();
    expect(screen.getByLabelText<HTMLInputElement>("Leg y").value).toBe(original);
  });

  it("separates a necessary SI member resize from placement and requires explicit acceptance", async () => {
    render(<ShearConnectionsWorkspace />);
    fireEvent.change(screen.getByLabelText("Unit system"), { target: { value: "SI" } });
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "3" } });
    const invalid = multirowPreviewFixture(3, 1, "INVALID_GEOMETRY");
    const valid = multirowPreviewFixture(3, 1);
    const fetchMock = vi.fn().mockImplementationOnce(() => Promise.resolve(new Response(JSON.stringify(invalid))))
      .mockImplementationOnce(() => Promise.resolve(new Response(JSON.stringify(invalid))))
      .mockImplementationOnce(() => Promise.resolve(new Response(JSON.stringify(invalid))))
      .mockImplementation(() => Promise.resolve(new Response(JSON.stringify(valid))));
    vi.stubGlobal("fetch", fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Suggest compatible geometry" }));
    await screen.findByText("Member size change required");
    expect(screen.getByLabelText("Leg y")).toHaveValue("101.6");
    fireEvent.click(screen.getByRole("button", { name: "Accept member size change and apply" }));
    expect(screen.getByLabelText("Leg y")).toHaveValue("203.2");
    expect(screen.queryByText("Member size change required")).not.toBeInTheDocument();
  });

  it("turns network failure into an actionable suggestion message", async () => {
    await openUnifiedMultirow();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    fireEvent.click(screen.getByRole("button", { name: "Suggest compatible geometry" }));
    expect(await screen.findByText(/Confirm the local backend is running, then try again/)).toHaveTextContent("Unable to preview a compatible layout");
  });

  it("identifies the current unsupported action at the design button", async () => {
    const preview = multirowPreviewFixture();
    preview.design_check_ready = false;
    preview.warnings = ["DIRECT_INDEPENDENT_MEMBER_END_MOMENT_NOT_SUPPORTED"];
    mocks.multiPreview.mockResolvedValue(preview);
    render(<ShearConnectionsWorkspace />);
    activateNormalAutomaticDemand();
    await waitFor(() => { expect(screen.getByRole("button", { name: "Run Design Check" })).toHaveAttribute("title", expect.stringContaining("independent member-end moment")); });
    expect(screen.getByRole("region", { name: "UNSUPPORTED ACTION" })).toBeVisible();
  });

  it("uses final checks with separate source and qualification evidence", async () => {
    const design = automaticDesignFixture();
    const integration = design.automatic_group_mode_integration;
    if (integration === null) throw new Error("Integration required");
    integration.incomplete_required_check_ids = ["MATERIAL_SOURCE:layer-A", "SECTION_2_3_2", "BOLT_SHEAR:B_R1_L1"];
    const scenario = integration.scenario_results[0];
    const check = scenario?.supported_results[0];
    if (scenario === undefined || check === undefined) throw new Error("Final check required");
    scenario.supported_results.push({ ...check, result_id: "SOURCE_PENDING", layer_id: null, bolt_id: null, row_id: null, bolt_line_id: null, path_id: null, numerical_comparison: "NOT_EVALUATED", availability: "SOURCE_DATA_PENDING" });
    mocks.multiPreview.mockResolvedValue(automaticPreviewFixture());
    mocks.multiEvaluate.mockResolvedValue(design);
    render(<ShearConnectionsWorkspace />);
    activateNormalAutomaticDemand();
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);
    await screen.findByRole("heading", { name: "Calculated supported checks" });
    expect(screen.getByRole("region", { name: "QUALIFICATION REQUIRED" })).toHaveTextContent("MATERIAL_SOURCE:layer-A");
    expect(screen.getByRole("region", { name: "SOURCE REQUIRED" })).toHaveTextContent("BOLT_SHEAR:B_R1_L1");
    expect(screen.getAllByText("Connection").length).toBeGreaterThan(0);
  });

  it("keeps Direct geometry unchanged when a proposed layout is dismissed", async () => {
    await openUnifiedMultirow();
    const candidate = multirowPreviewFixture();
    candidate.geometry_status = "VALID";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(candidate), { status: 200 })));
    const original = screen.getByLabelText<HTMLInputElement>("Leg y").value;
    fireEvent.click(screen.getByRole("button", { name: "Suggest compatible geometry" }));
    await screen.findByText(/Proposed geometry for the current/);
    fireEvent.click(screen.getByRole("button", { name: "Dismiss proposal" }));
    expect(screen.queryByText(/Proposed geometry for the current/)).not.toBeInTheDocument();
    expect(screen.getByLabelText<HTMLInputElement>("Leg y").value).toBe(original);
  });

  it("rejects a late compatible-layout response after an engineering input changes", async () => {
    await openUnifiedMultirow();
    let resolveResponse: ((response: Response) => void) | undefined;
    const fetchMock = vi.fn(() => new Promise<Response>((resolve) => { resolveResponse = resolve; }));
    vi.stubGlobal("fetch", fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Suggest compatible geometry" }));
    await waitFor(() => { expect(fetchMock).toHaveBeenCalledTimes(1); });
    fireEvent.change(screen.getByLabelText("Leg y"), { target: { value: "9" } });
    resolveResponse?.(new Response(JSON.stringify(multirowPreviewFixture()), { status: 200 }));
    expect(await screen.findByText(/Inputs changed after the layout preview/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apply proposed geometry" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Leg y")).toHaveValue("9");
  });

  it("reports bounded Direct layout search failure without applying geometry", async () => {
    await openUnifiedMultirow();
    const invalid = multirowPreviewFixture();
    invalid.geometry_status = "INVALID_GEOMETRY";
    invalid.warnings = ["DIRECT_PHYSICAL_CONTAINMENT:B_R2_L1:member-a:TOP_FLANGE:available=0.5; required=1; plane=X. unit=in"];
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(invalid), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Suggest compatible geometry" }));
    await waitFor(() => { expect(fetchMock).toHaveBeenCalledTimes(16); });
    expect(screen.getByText(/No contained layout found in the bounded/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apply proposed geometry" })).not.toBeInTheDocument();
  });

  it("reports Direct layout preview transport errors without silently changing inputs", async () => {
    await openUnifiedMultirow();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("rejected", { status: 503 })));
    fireEvent.click(screen.getByRole("button", { name: "Suggest compatible geometry" }));
    expect(await screen.findByText(/The proposed layout was rejected \(HTTP 503\)/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apply proposed geometry" })).not.toBeInTheDocument();
  });

  it("handles a non-Error layout transport failure without changing geometry", async () => {
    await openUnifiedMultirow();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue("offline"));
    fireEvent.click(screen.getByRole("button", { name: "Suggest compatible geometry" }));
    expect(await screen.findByText("Unable to preview a compatible layout. Confirm the local backend is running, then try again.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apply proposed geometry" })).not.toBeInTheDocument();
  });

  it("uses the physical two-row SI and three-row U.S. layout minima", async () => {
    const view = render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.change(screen.getByLabelText("Unit system"), { target: { value: "SI" } });
    const valid = multirowPreviewFixture();
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(valid), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Suggest compatible geometry" }));
    await screen.findByText(/Proposed geometry for the current/);
    const si = JSON.parse((fetchMock.mock.calls[0]?.[1] as RequestInit).body as string) as MultiRowConnectionRequest;
    expect(si.loaded_boundary_to_row_1_distance.value).toBe("76.2");
    fireEvent.change(screen.getByLabelText("Unit system"), { target: { value: "US_CUSTOMARY" } });
    expect(screen.getByLabelText("Case label")).toHaveValue("Direct layout example — U.S.");
    view.unmount();

    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "3" } });
    const usFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(multirowPreviewFixture(3, 1)), { status: 200 }));
    vi.stubGlobal("fetch", usFetch);
    fireEvent.click(screen.getByRole("button", { name: "Suggest compatible geometry" }));
    await screen.findByText(/Proposed geometry for the current/);
    const us = JSON.parse((usFetch.mock.calls[0]?.[1] as RequestInit).body as string) as MultiRowConnectionRequest;
    expect(us.loaded_boundary_to_row_1_distance.value).toBe("3");
  });

  it.each(["in", "mm"] as const)("groups Direct statuses and selects the canonical geometry issue (%s)", async (unit) => {
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: "Legacy J1 regression fixture — U.S." }));
    const basePreview = multirowPreviewFixture(2, 2, "INVALID_GEOMETRY");
    const witness = unit === "in" ? clearanceWitness : JSON.parse(JSON.stringify(clearanceWitness, (_key, value: unknown) => typeof value === "string" && /^[+-]?(?:\d*\.)?\d+$/u.test(value) ? String(Number(value) * 25.4) : value)) as typeof clearanceWitness;
    if (basePreview.visualization === null) throw new Error("Canonical fixture required");
    basePreview.visualization.source_length_unit = unit;
    const physicalFace = (unit === "in" ? f3Faces.free : JSON.parse(JSON.stringify(f3Faces.free, (_key, value: unknown) => typeof value === "string" && /^[+-]?(?:\d*\.)?\d+$/u.test(value) ? String(Number(value) * 25.4) : value))) as unknown as DirectEngineeringFace;
    const preview = { ...basePreview, direct_engineering_geometry: [
      { ...physicalFace, bolt_id: "B_R1_L1" },
      { ...physicalFace, bolt_id: "B_R2_L1" },
    ], direct_clearance_provenance: [
      { ...witness, valid: true },
      { ...witness, bolt_id: "B_R1_L1" },
      witness,
    ] };
    preview.warnings = [
      `DIRECT_PHYSICAL_CONTAINMENT:B_R2_L1:member-a:TOP_FLANGE:available=${witness.center_to_boundary}; required=${witness.validator_minimum}; plane=0. unit=${unit}`,
      "UNSUPPORTED_MEMBER_MOMENT",
      "F593_TENSILE_SOURCE_DATA_PENDING",
      "EXTRA_DOCUMENTATION_NOTE",
    ];
    mocks.multiPreview.mockResolvedValue(preview);
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    expect(await screen.findByRole("region", { name: "GEOMETRY" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "METHOD REQUIRED" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "SOURCE REQUIRED" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "INFORMATION" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "INFORMATION" })).toHaveClass("information-status");
    fireEvent.click(screen.getByRole("button", { name: /Bolt B_R2_L1.*Show geometry issue/u }));
    expect(screen.getByRole("region", { name: "Physical engineering geometry" })).toBeVisible();
    fireEvent.click(screen.getByText("Advanced Engineering Diagnostics — computational contact patch"));
    expect(screen.getByRole("region", { name: "Canonical geometry issue" })).toBeInTheDocument();
    expect(screen.getByText("Bolt / Interface", { exact: true })).toBeInTheDocument();
  });

  it("previews the three-row Direct SI layout in canonical millimetres", async () => {
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.change(screen.getByLabelText("Unit system"), { target: { value: "SI" } });
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "3" } });
    const candidate = multirowPreviewFixture(3, 1);
    candidate.geometry_status = "VALID";
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(candidate), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Suggest compatible geometry" }));
    expect(await screen.findByText(/Proposed geometry for the current/)).toBeInTheDocument();
    const submitted = JSON.parse((fetchMock.mock.calls[0]?.[1] as RequestInit).body as string) as MultiRowConnectionRequest;
    expect(submitted).toMatchObject({ row_count: 3, source_length_unit: "mm" });
    expect(submitted.loaded_boundary_to_row_1_distance.value).toBe("76.2");
  });

  it("starts with the contained 2 x 1 Direct layout without a legacy preview", async () => {
    render(<ShearConnectionsWorkspace />);
    expect(screen.getByRole("heading", { name: "Direct angle-to-W connection" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Multi-row bolt group" })).not.toBeInTheDocument();
    // OR1-06: the physical Direct starter is two rows.
    expect(screen.getByLabelText("Row count")).toHaveValue(2);
    expect(screen.getByLabelText("Bolts per row")).toHaveValue(1);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    expect(mocks.singlePreview).not.toHaveBeenCalled();
    expect(mocks.multiPreview).not.toHaveBeenCalled();
    mocks.multiPreview.mockResolvedValue(multirowPreviewFixture(1, 1));
    activateNormalAutomaticDemand();
    await waitFor(() => { expect(mocks.multiPreview).toHaveBeenCalled(); });
    const submitted = mocks.multiPreview.mock.calls.at(-1)?.[0] as MultiRowConnectionRequest;
    expect(submitted).toMatchObject({
      row_count: 2, bolts_per_row: 1,
      demand_source: "AUTOMATIC_MEMBER_END_FORCE",
      lap_configuration: "SINGLE_LAP",
      direct_finalization_contract_version: "SHEAR01-DIRECT-F1",
      physical_connection: { lap_configuration: "SINGLE_LAP" },
    });
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
    expect(request.direct_finalization_contract_version).toBe("SHEAR01-DIRECT-F1");
    expect(request.material_pair).toBe("FRP_FRP");
    expect(request.layers.map((layer) => [layer.layer_id, layer.component_id])).toEqual([
      ["layer-A", "member-a"],
      ["layer-B", "member-b"],
    ]);
    expect(request.physical_connection?.geometry_template?.brace_to_column_directed_angle_deg).toBe("45");
    fireEvent.click(screen.getByText("Bolt / Interface", { exact: true }));
    expect(screen.getByText(/Standard physical hole/)).toBeVisible();
    expect(screen.getByText(/0.563 in.*Us Customary Printed/i)).toBeVisible();
    expect(screen.getByRole("heading", { name: "Direct angle-to-W connection viewer" })).toBeVisible();
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

  it("routes Direct 1 x 2 and 1 x 3 through canonical automatic demand", async () => {
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: "Legacy J1 regression fixture — U.S." }));
    mocks.multiPreview.mockImplementation((request: MultiRowConnectionRequest) =>
      Promise.resolve(multirowPreviewFixture(request.row_count, request.bolts_per_row)),
    );
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    // OR1-07: one-row Direct demand is automatic in the normal workflow.
    expect(screen.queryByRole("button", { name: "Explicit resolved connection demand" })).not.toBeInTheDocument();
    activateNormalAutomaticDemand();
    await waitFor(() => {
      expect(mocks.multiPreview.mock.calls.at(-1)?.[0]).toMatchObject({
        row_count: 1, bolts_per_row: 2, demand_source: "AUTOMATIC_MEMBER_END_FORCE",
      });
    });
    await waitFor(() => { expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled(); });
    mocks.multiEvaluate.mockResolvedValue(multirowDesignFixture(1, 2));
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(mocks.multiEvaluate).toHaveBeenCalledTimes(1); });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "3" } });
    await waitFor(() => {
      expect(mocks.multiPreview.mock.calls.at(-1)?.[0]).toMatchObject({
        row_count: 1, bolts_per_row: 3, demand_source: "AUTOMATIC_MEMBER_END_FORCE",
      });
    });
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
    fireEvent.change(screen.getByLabelText("P / Fx"), { target: { value: "0.8" } });
    expect(screen.getAllByText(/Results need to be recalculated/i)[0]).toBeVisible();
    expect(mocks.multiEvaluate).toHaveBeenCalledTimes(1);
  });

  it("requires a project support condition and explicitly marks both owner examples continuous", async () => {
    render(<ShearConnectionsWorkspace />);
    const selector = screen.getByRole("combobox", { name: "Supporting W — longitudinal extent" });
    expect(selector).toHaveValue("UNSPECIFIED");
    expect(screen.getByText(/INPUT NEEDED — Specify whether the supporting W/u)).toBeInTheDocument();
    fireEvent.change(selector, { target: { value: "CONTINUOUS_THROUGH_CONNECTION" } });
    expect(screen.queryByText(/Results need to be recalculated/u)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load Direct example — U.S." }));
    expect(selector).toHaveValue("CONTINUOUS_THROUGH_CONNECTION");
    await waitFor(() => { expect(mocks.multiPreview).toHaveBeenCalled(); });
    expect(mocks.multiPreview.mock.calls.at(-1)?.[0]).toMatchObject({ supporting_w_longitudinal_ends: { condition: "CONTINUOUS_THROUGH_CONNECTION" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Direct example — SI" }));
    expect(selector).toHaveValue("CONTINUOUS_THROUGH_CONNECTION");
  });

  it("keeps a result current after view-only changes and stales it after a real W end edit", async () => {
    mocks.multiEvaluate.mockResolvedValue(multirowDesignFixture());
    await openUnifiedMultirow();
    const design = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(design).toBeEnabled(); });
    fireEvent.click(design);
    await screen.findByRole("heading", { name: /Engineering review required/i });
    fireEvent.change(screen.getByLabelText("Supporting W member view extent above connection"), { target: { value: "20" } });
    await waitFor(() => { expect(design).toBeEnabled(); });
    expect(screen.queryByText(/Results need to be recalculated/u)).not.toBeInTheDocument();
    expect(mocks.multiEvaluate).toHaveBeenCalledTimes(1);
    fireEvent.change(screen.getByRole("combobox", { name: "Supporting W — longitudinal extent" }), { target: { value: "FINITE_POSITIVE_END_ONLY" } });
    expect(screen.getAllByText(/Results need to be recalculated/u)[0]).toBeVisible();
    expect(design).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Distance from connection reference to W end above"), { target: { value: "12" } });
    await waitFor(() => { expect(mocks.multiPreview.mock.calls.at(-1)?.[0]).toMatchObject({ supporting_w_longitudinal_ends: { condition: "FINITE_POSITIVE_END_ONLY", positive_end_distance: { value: "12", unit: "in" } } }); });
    expect(mocks.multiEvaluate).toHaveBeenCalledTimes(1);
  });

  it("shows the backend-authored W continuation cue above the actual canonical viewer", async () => {
    const response: MultiRowPreviewResponse = { ...automaticPreviewFixture(), direct_support_end_authority: { condition: "CONTINUOUS_THROUGH_CONNECTION", component_id: "member-a", length_unit: "in", negative_end_distance: null, positive_end_distance: null, negative_end_member_local_station: null, positive_end_member_local_station: null } };
    mocks.multiPreview.mockResolvedValue(response);
    render(<ShearConnectionsWorkspace />);
    activateNormalAutomaticDemand();
    expect(await screen.findByLabelText("Supporting W real ends and view cuts")).toHaveTextContent("W continues above — view cut");
    expect(screen.getByTestId("mock-engineering-scene")).toBeInTheDocument();
  });

  it("binds custom Direct fastener identity and washer geometry to the current request", async () => {
    mocks.multiEvaluate.mockResolvedValue(multirowDesignFixture());
    await openUnifiedMultirow();
    const design = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(design).toBeEnabled(); });
    fireEvent.click(design);
    await screen.findByRole("heading", { name: /Engineering review required/i });
    fireEvent.click(screen.getByRole("button", { name: "Copy as custom" }));
    fireEvent.change(screen.getByLabelText("Fastener name"), { target: { value: "Project washer assembly" } });
    fireEvent.change(screen.getByLabelText(/Washer outside diameter \(/), { target: { value: "2.25" } });
    fireEvent.change(screen.getByLabelText(/Fnt \(/), { target: { value: "75" } });
    fireEvent.change(screen.getByLabelText("Fnt source basis"), { target: { value: "QA-only supplied test" } });
    expect(screen.getAllByText(/Results need to be recalculated/)[0]).toBeVisible();
    expect(screen.getByRole("heading", { name: "Project washer assembly" })).toBeInTheDocument();
    expect(screen.getByText(/User-supplied Fnt 75 ksi/)).toBeInTheDocument();
    expect(screen.getByText("2.25 in")).toBeInTheDocument();
    expect(screen.getByText(/controlled ASTM F593 catalog tensile-strength table/u)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Fastener"), { target: { value: "DEFAULT" } });
    await screen.findByText("Catalog source resolved");
    expect(screen.queryByText(/controlled ASTM F593 catalog tensile-strength table/u)).not.toBeInTheDocument();
    expect(screen.queryByText(/ASTM F593 tensile-strength source is required/)).not.toBeInTheDocument();
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
    expect(screen.queryByText(/Results need to be recalculated/u)).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Loaded boundary to Row 1"), {
      target: { value: "4" },
    });
    expect(screen.getAllByText(/Results need to be recalculated/u)[0]).toBeVisible();
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
    activateNormalAutomaticDemand();
    await waitFor(() => {
      const latest = mocks.multiPreview.mock.calls.at(-1)?.[0] as MultiRowConnectionRequest;
      expect(latest).toMatchObject({ row_count: 1, bolts_per_row: 1 });
    });
    expect(screen.getByLabelText("Case label")).toHaveValue("Shared connection case");
    await waitFor(() => { expect(screen.getByTestId("mock-engineering-scene")).toHaveAttribute("data-bolt-count", "1"); });
    expect(mocks.singlePreview).not.toHaveBeenCalled();
    expect(screen.queryByRole("heading", { name: /Engineering review required/i })).not.toBeInTheDocument();
  });

  it("selects any physical bolt and exposes row, line, and penetrated layers", async () => {
    await openUnifiedMultirow();
    const previewCalls = mocks.multiPreview.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Select B_R2_L2" }));
    expect(screen.getByLabelText("Selected object")).toHaveTextContent("Bolt · Row 2 · Line 2");
    expect(screen.getByText("Row 2")).toBeVisible();
    expect(screen.getByText("Bolt Line 2")).toBeVisible();
    expect(screen.getAllByText(/Angle Connected Leg.*Supporting W Flange/).length).toBeGreaterThan(0);
    expect(mocks.multiPreview).toHaveBeenCalledTimes(previewCalls);
    expect(mocks.multiEvaluate).not.toHaveBeenCalled();
  });

  it("debounces physical group geometry while retaining automatic member-end provenance", async () => {
    await openUnifiedMultirow();
    await waitFor(() => { expect(mocks.multiPreview).toHaveBeenCalled(); });
    mocks.multiPreview.mockClear();
    vi.useFakeTimers();
    // OR1-07: Direct hides manual row allocations; the backend distributes demand.
    expect(screen.queryByLabelText("Row-demand method")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Spacing between rows"), { target: { value: "2.5" } });
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(mocks.multiPreview).toHaveBeenCalledTimes(1);
    const request = mocks.multiPreview.mock.calls[0]?.[0] as MultiRowConnectionRequest;
    expect(request.pitch.value).toBe("2.5");
    expect(request.demand_source).toBe("AUTOMATIC_MEMBER_END_FORCE");
  });

  it("keeps invalid physical geometry visible and design fail closed", async () => {
    mocks.multiPreview.mockResolvedValue(multirowPreviewFixture(2, 2, "INVALID_GEOMETRY"));
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: "Legacy J1 regression fixture — U.S." }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    await waitFor(() => { expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled(); });
    expect((await screen.findAllByText(/Geometry must be corrected before Design Check/i)).length).toBeGreaterThan(0);
  });

  it("blocks more than three Direct rows before ordinary design", async () => {
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: "Legacy J1 regression fixture — U.S." }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "4" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    expect(screen.getByRole("button", { name: "Run Design Check" })).toHaveAttribute(
      "title", "The Direct Chapter 8 route allows at most three rows and three bolts per row.",
    );
    expect(screen.queryByText(/^Pass$/i)).not.toBeInTheDocument();
  });

  it("handles multi-row preview and design transport failures without invented results", async () => {
    mocks.multiPreview.mockRejectedValue(new EvaluationTransportError("NETWORK", null, "offline"));
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: "Legacy J1 regression fixture — U.S." }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    await screen.findByText("offline");
    mocks.multiPreview.mockImplementation((request: MultiRowConnectionRequest) =>
      Promise.resolve(multirowPreviewFixture(request.row_count, request.bolts_per_row)),
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => { expect(screen.getByTestId("mock-engineering-scene")).toHaveAttribute("data-bolt-count", "2"); });
    mocks.multiEvaluate.mockRejectedValue(new EvaluationTransportError("HTTP", 503, "service unavailable"));
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);
    const firstError = await screen.findByRole("alert");
    expect(firstError).toHaveTextContent("Unable to complete Design Check");
    fireEvent.click(requiredElement(firstError.querySelector("summary")));
    expect(screen.getByText(/service unavailable/)).toBeVisible();
    mocks.multiEvaluate.mockRejectedValue(new EvaluationTransportError("NETWORK", null, "network failure"));
    fireEvent.click(button);
    const secondError = await screen.findByRole("alert");
    fireEvent.click(requiredElement(secondError.querySelector("summary")));
    expect(screen.getByText(/network failure/)).toBeVisible();
  });

  it("preserves SI common state in the multi-row request", async () => {
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: "Legacy J1 regression fixture — SI" }));
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

  it("runs Direct 1 x 1 through the same F1 design and status route", async () => {
    mocks.multiPreview.mockResolvedValue(multirowPreviewFixture(1, 1));
    mocks.multiEvaluate.mockResolvedValue(automaticDesignFixture());
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: "Legacy J1 regression fixture — U.S." }));
    activateNormalAutomaticDemand();
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);
    await waitFor(() => { expect(mocks.multiEvaluate).toHaveBeenCalledTimes(1); });
    const submitted = mocks.multiEvaluate.mock.calls[0]?.[0] as MultiRowConnectionRequest;
    expect(submitted).toMatchObject({ row_count: 1, bolts_per_row: 1, lap_configuration: "SINGLE_LAP" });
    expect(mocks.singleEvaluate).not.toHaveBeenCalled();
  });

  it("edits physical Direct group controls without exposing manual engineering internals", async () => {
    await openUnifiedMultirow(2, 2);
    fireEvent.change(screen.getByLabelText("Loaded boundary to Row 1"), { target: { value: "2.1" } });
    fireEvent.change(screen.getByLabelText("Negative side distance"), { target: { value: "1.6" } });
    fireEvent.change(screen.getByLabelText("Positive side distance"), { target: { value: "1.7" } });
    expect(screen.queryByLabelText("Connected material pair")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("FRP LW-axis angle")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Source calculation")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Force-line offset")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Row-demand method")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Bolt-axis tension required")).not.toBeInTheDocument();
    await waitFor(() => {
      const request = mocks.multiPreview.mock.calls.at(-1)?.[0] as MultiRowConnectionRequest;
      expect(request.loaded_boundary_to_row_1_distance.value).toBe("2.1");
      expect(request.demand_source).toBe("AUTOMATIC_MEMBER_END_FORCE");
    });
  }, 15000);

  it("keeps unsupported Direct axis-tension controls hidden while preview is pending", async () => {
    mocks.multiPreview.mockImplementation(() => new Promise(() => undefined));
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    // OR1-07: a user cannot claim an unimplemented tension/prying load path.
    expect(screen.queryByLabelText("Bolt-axis tension required")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Bolt · Row 1 · Line 1 axis tension")).not.toBeInTheDocument();
  });

  it("fails closed for invalid Direct multi-row counts and physical dimensions", async () => {
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

    activateNormalAutomaticDemand();
    await waitFor(() => {
      const submitted = mocks.multiPreview.mock.calls.at(-1)?.[0] as MultiRowConnectionRequest;
      expect(submitted.demand_source).toBe("AUTOMATIC_MEMBER_END_FORCE");
      expect(submitted.signed_force_x).toBeUndefined();
    });
    // OR1-07: Direct has one automatic route for one or multiple rows.
    expect(screen.queryByRole("button", { name: "Explicit resolved connection demand" })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "1" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "1" } });
    await waitFor(() => {
      expect(mocks.multiPreview.mock.calls.at(-1)?.[0]).toMatchObject({
        row_count: 1, bolts_per_row: 1, demand_source: "AUTOMATIC_MEMBER_END_FORCE",
      });
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
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: "Legacy J1 regression fixture — U.S." }));
    activateNormalAutomaticDemand();
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "3" } });
    expect(screen.queryByLabelText("Row 3 direct force")).not.toBeInTheDocument();
    await waitFor(() => {
      const submitted = mocks.multiPreview.mock.calls.at(-1)?.[0] as MultiRowConnectionRequest;
      expect(submitted.demand_source).toBe("AUTOMATIC_MEMBER_END_FORCE");
      expect(submitted.automatic_action_source_id).toBe("action-1");
      expect(submitted.signed_force_x).toBeUndefined();
      expect(submitted.provenance.load_combination).toBeTruthy();
    });
    expect(screen.queryByLabelText("Bolt-axis tension required")).not.toBeInTheDocument();
  });

  it("labels an explicitly complete backend QA fixture GREEN", async () => {
    const complete = automaticDesignFixture();
    const integration = complete.automatic_group_mode_integration;
    if (integration === null) throw new Error("Automatic integration fixture is required.");
    integration.required_check_ids = integration.scenario_results[0]?.supported_results.map((item) => item.result_id) ?? [];
    integration.unsupported_required_check_ids = [];
    integration.incomplete_required_check_ids = [];
    integration.failed_check_ids = [];
    integration.qualification = "QUALIFIED_ASCE_PRESCRIPTIVE";
    integration.numerical_comparison = "PASS";
    integration.overall_disposition = "PASS";
    mocks.multiPreview.mockImplementation((request: MultiRowConnectionRequest) =>
      Promise.resolve(request.demand_source === "AUTOMATIC_MEMBER_END_FORCE" ? automaticPreviewFixture() : multirowPreviewFixture(request.row_count, request.bolts_per_row)),
    );
    mocks.multiEvaluate.mockResolvedValue(complete);
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: /Legacy J1 regression fixture .* U\.S\./u }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    activateNormalAutomaticDemand();
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);
    expect((await screen.findAllByText("GREEN — complete pass")).length).toBeGreaterThan(0);
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
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: /Legacy J1 regression fixture .* U\.S\./u }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    activateNormalAutomaticDemand();

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
    expect(screen.getAllByText("YELLOW — incomplete design").length).toBeGreaterThan(0);
    expect(screen.getByText("Calculated supported checks")).toBeVisible();
    fireEvent.click(requiredElement(document.querySelector(".results-technical-audit > summary")));
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
    expect(screen.getAllByText(/Results need to be recalculated/u)[0]).toBeVisible();
    expect(screen.getAllByText("Results need to be recalculated").length).toBeGreaterThan(0);
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

  it("renders both physical layers when backend scenarios share a method ID", async () => {
    const design = automaticDesignFixture();
    const integration = design.automatic_group_mode_integration;
    const first = integration?.scenario_results[0];
    if (integration === null || first === undefined) throw new Error("Group-mode fixture is required.");
    integration.scenario_results.push({
      ...first,
      input_fingerprint: "4".repeat(64),
      result_fingerprint: "5".repeat(64),
    });
    mocks.multiPreview.mockImplementation((request: MultiRowConnectionRequest) =>
      Promise.resolve(request.demand_source === "AUTOMATIC_MEMBER_END_FORCE"
        ? automaticPreviewFixture() : multirowPreviewFixture(request.row_count, request.bolts_per_row)),
    );
    mocks.multiEvaluate.mockResolvedValue(design);
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    try {
      render(<ShearConnectionsWorkspace />);
      await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
      fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "3" } });
      fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
      await waitFor(() => { expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled(); });
      fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
      await waitFor(() => { expect(screen.getAllByRole("heading", { name: "Asce Prescribed" })).toHaveLength(2); });
      expect(error.mock.calls.some(([message]) => String(message).includes("same key"))).toBe(false);
    } finally {
      error.mockRestore();
    }
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
      warnings: [{ code: "ECCENTRIC_SHEAROUT_LINE_RESULTANT_NOT_PARALLEL_TO_CONNECTION_FORCE", trace: [] }],
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
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: /Legacy J1 regression fixture .* U\.S\./u }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    activateNormalAutomaticDemand();
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);

    await screen.findByRole("heading", { name: "Fail" });
    expect(screen.getAllByText("Fail").length).toBeGreaterThan(1);
    expect(screen.getAllByText(/Line Resultant Not Parallel To Connection Force/u).length).toBeGreaterThan(1);
    expect(screen.getAllByText(/Line Force Reversal Not Supported/u).length).toBeGreaterThan(1);
    expect(screen.getAllByText("Calculation not supported").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Not required — parent exemption").length).toBeGreaterThan(0);
    fireEvent.click(requiredElement(document.querySelector(".results-technical-audit > summary")));
    expect(screen.getByText("Inherited legacy Stage 2.4B")).toBeVisible();
    expect(screen.getByText(/parallel_n:-444\.8/u)).toBeVisible();
    expect(screen.getByText(/Eccentric first-row net tension is not supported/u)).toBeVisible();
  });

  it("renders a nested Direct one-row native result with RED precedence and separate blockers", async () => {
    const design = automaticDesignFixture();
    const integration = design.automatic_group_mode_integration;
    if (integration === null) throw new Error("Automatic integration fixture is required.");
    integration.direct_single_row_result = {
      contract_version: "SHEAR01-DIRECT-F1-R1-SINGLE-ROW",
      source_scenario_id: "FULL_ROW_ROW_1",
      checks: [{
        result_id: "SINGLE_ROW_NET_TENSION:layer-A",
        limit_state: "SINGLE_ROW_NET_TENSION",
        equation_method: "ASCE_EQ_8_7A_8_7C",
        source_locator: "ASCE/SEI 74-23 Section 8.3.2",
        layer_id: "layer-A",
        bolt_id: null,
        bolt_line_id: null,
        demand: { value: "7", unit: "kip" },
        design_resistance: { value: "3", unit: "kip" },
        utilization: "2.33333333333333333333333333333333",
        numerical_comparison: "FAIL",
        availability: "CALCULATED",
        qualification: "ENGINEERING_REVIEW_REQUIRED",
        required: true,
        reason: "Numerical check executed; qualification is separate",
        equation_trace: { knt: "0.325" },
      }, {
        result_id: "SINGLE_ROW_SHEAR_OUT:layer-B:BOLT_LINE_1",
        limit_state: "SINGLE_ROW_SHEAR_OUT",
        equation_method: "ASCE_EQ_8_8",
        source_locator: "ASCE/SEI 74-23 Section 8.3.2",
        layer_id: "layer-B",
        bolt_id: "B_R1_L1",
        bolt_line_id: "BOLT_LINE_1",
        demand: null,
        design_resistance: null,
        utilization: null,
        numerical_comparison: "NOT_EVALUATED",
        availability: "CALCULATION_NOT_SUPPORTED",
        qualification: "ENGINEERING_REVIEW_REQUIRED",
        required: true,
        reason: "Residual moment requires an accepted section demand",
        equation_trace: null,
      }],
      required_check_ids: ["SINGLE_ROW_NET_TENSION:layer-A", "SINGLE_ROW_SHEAR_OUT:layer-B:BOLT_LINE_1"],
      incomplete_required_check_ids: ["SINGLE_ROW_SHEAR_OUT:layer-B:BOLT_LINE_1"],
      failed_check_ids: ["SINGLE_ROW_NET_TENSION:layer-A"],
      numerical_comparison: "FAIL",
      overall_disposition: "FAIL",
      result_fingerprint: "4".repeat(64),
    };
    mocks.multiPreview.mockImplementation((request: MultiRowConnectionRequest) =>
      Promise.resolve(request.demand_source === "AUTOMATIC_MEMBER_END_FORCE"
        ? automaticPreviewFixture()
        : multirowPreviewFixture(request.row_count, request.bolts_per_row)),
    );
    mocks.multiEvaluate.mockResolvedValue(design);
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: /Legacy J1 regression fixture .* U\.S\./u }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    activateNormalAutomaticDemand();
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);
    expect(await screen.findByRole("heading", { name: "Angle and W flange checks" })).toBeVisible();
    expect(screen.getAllByText("Fail").length).toBeGreaterThan(0);
    expect(screen.getByText(/Residual moment requires an accepted section demand/u)).toBeVisible();
    expect(screen.getByText(/Ordinary whole-connection PASS is prohibited/u)).toBeVisible();
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
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: /Legacy J1 regression fixture .* U\.S\./u }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
    activateNormalAutomaticDemand();
    const button = screen.getByRole("button", { name: "Run Design Check" });
    await waitFor(() => { expect(button).toBeEnabled(); });
    fireEvent.click(button);

    await screen.findByText("Calculated supported checks");
    expect(screen.queryByRole("heading", { name: "Eccentric group-mode checks" })).not.toBeInTheDocument();
    expect(screen.getByText("Current Design Check")).toBeVisible();

    const handoffOnly = automaticDesignFixture();
    handoffOnly.automatic_group_mode_integration = null;
    mocks.multiEvaluate.mockResolvedValueOnce(handoffOnly);
    fireEvent.click(button);
    await waitFor(() => {
      expect(mocks.multiEvaluate).toHaveBeenCalledTimes(2);
    });
    expect(screen.queryByRole("heading", { name: "Eccentric group-mode checks" })).not.toBeInTheDocument();
  });

  it("uses member-end action when an optional explicit demand is absent", async () => {
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
      await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
      fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
      activateNormalAutomaticDemand();
      fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "3" } });
      await waitFor(() => {
        const submitted = mocks.multiPreview.mock.calls.at(-1)?.[0] as MultiRowConnectionRequest;
        expect(submitted.demand_source).toBe("AUTOMATIC_MEMBER_END_FORCE");
        expect(submitted.automatic_action_source_id).toBe("action-1");
        expect(submitted.provenance.reference_point).toBe("EXPLICIT_POINT:action-1");
      });
      expect(screen.queryByLabelText("Bolt-axis tension required")).not.toBeInTheDocument();
    } finally {
      benchmark.mockRestore();
    }
  });

  it("blocks design when a valid canonical preview is not backend-design-ready", async () => {
    const response = multirowPreviewFixture();
    response.design_check_ready = false;
    mocks.multiPreview.mockResolvedValue(response);
    render(<ShearConnectionsWorkspace />);
    await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
    fireEvent.click(screen.getByRole("button", { name: "Legacy J1 regression fixture — U.S." }));
    fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Run Design Check" })).toHaveAttribute(
        "title",
        "The current action cannot be calculated. Review the model warnings above.",
      );
    });
  });

  it("preserves legacy non-Direct expert moment and allocation controls for later family binding", async () => {
    const source = benchmarks.loadJ1Benchmark("US_CUSTOMARY");
    const nonDirect = structuredClone(source);
    const member = nonDirect.joint_assembly.members[0];
    if (member === undefined) throw new Error("A member fixture is required.");
    member.material_kind = "STAINLESS_STEEL";
    const benchmark = vi.spyOn(benchmarks, "loadJ1Benchmark").mockImplementation(() => structuredClone(nonDirect));
    mocks.multiPreview.mockImplementation((request: MultiRowConnectionRequest) => {
      const value = multirowPreviewFixture(request.row_count, request.bolts_per_row);
      value.warnings.push("RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY_USED");
      return Promise.resolve(value);
    });
    try {
      render(<ShearConnectionsWorkspace />);
      await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
      fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
      fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "2" } });
      await waitFor(() => { expect(mocks.multiPreview).toHaveBeenCalled(); });
      expect(screen.getAllByText(/controlled ASTM F593 catalog tensile-strength table/u).length).toBeGreaterThan(0);
      expect(screen.getByLabelText("T / Mx")).toBeInTheDocument();
      expect(screen.getByLabelText("CM")).toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("CM"), { target: { value: "" } });
      expect(screen.getByText(/Blank factors require explicit selection/u)).toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("CM"), { target: { value: "1" } });
      fireEvent.change(screen.getByLabelText("CT"), { target: { value: "0.95" } });
      fireEvent.change(screen.getByLabelText("CCH"), { target: { value: "1" } });
      expect(screen.getByLabelText("Washer outside diameter")).toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("Washer outside diameter"), { target: { value: "1.5" } });
      fireEvent.change(screen.getByLabelText("Row-demand method"), { target: { value: "FRACTIONS" } });
      fireEvent.change(screen.getByLabelText("Row 1 fraction"), { target: { value: "0.6" } });
      fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "3" } });
      expect(screen.getByLabelText("Row 3 fraction")).toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("Row-demand method"), { target: { value: "DIRECT_ROW_FORCES" } });
      fireEvent.change(screen.getByLabelText("Row 1 direct force"), { target: { value: "0.4" } });
      fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
      expect(screen.getByLabelText("Row 2 direct force")).toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("Row-demand method"), { target: { value: "ASCE_PRESCRIBED" } });
      expect(screen.queryByLabelText("Row 1 direct force")).not.toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("Source calculation"), { target: { value: "Engineer sheet" } });
      fireEvent.change(screen.getByLabelText("Force-line offset"), { target: { value: "0.2" } });
      fireEvent.click(screen.getByLabelText("Bolt-axis tension required"));
      expect(screen.getByLabelText("Bolt-axis tension required")).toBeChecked();
      const axisTension = screen.queryAllByLabelText(/Bolt · Row .*axis tension$/u);
      expect(axisTension.length).toBeGreaterThan(0);
      const firstAxis = axisTension[0];
      if (firstAxis === undefined) throw new Error("A physical bolt-axis control is required.");
      fireEvent.change(firstAxis, { target: { value: "0.2" } });
      expect(firstAxis).toHaveValue("0.2");
      fireEvent.click(screen.getByLabelText("Bolt-axis tension required"));
      expect(screen.queryAllByLabelText(/Bolt · Row .*axis tension$/u)).toHaveLength(0);
      fireEvent.change(screen.getByLabelText("First-row method"), { target: { value: "ASCE_COMMENTARY_FULL" } });
      fireEvent.change(screen.getByLabelText("Prescribed Lbr"), { target: { value: "1.2" } });
      expect(screen.getByLabelText("First-row method")).toHaveValue("ASCE_COMMENTARY_FULL");
    } finally {
      benchmark.mockRestore();
    }
  });

  it("keeps legacy non-Direct demand warnings and hardware units explicit without an external demand", async () => {
    const nonDirect = structuredClone(benchmarks.loadJ1Benchmark("US_CUSTOMARY"));
    const member = nonDirect.joint_assembly.members[0];
    if (member === undefined) throw new Error("A member fixture is required.");
    member.material_kind = "STAINLESS_STEEL";
    nonDirect.explicit_resolved_demand = null;
    const source = vi.spyOn(benchmarks, "loadJ1Benchmark").mockImplementation(() => structuredClone(nonDirect));
    try {
      render(<ShearConnectionsWorkspace />);
      await screen.findByRole("heading", { name: "Direct angle-to-W connection" });
      expect(screen.getByText("Explicit externally resolved connection demand is required.")).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Automatic from member-end force" }));
      expect(screen.getByText(/Select at least two rows for the accepted automatic multi-row workflow/)).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Explicit resolved connection demand" }));
      fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "2" } });
      fireEvent.change(screen.getByLabelText("Row-demand method"), { target: { value: "DIRECT_ROW_FORCES" } });
      expect(screen.getByLabelText("Row 1 direct force")).toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("Row count"), { target: { value: "3" } });
      expect(screen.getByLabelText("Row 3 direct force")).toBeInTheDocument();
      fireEvent.click(screen.getByLabelText("Bolt-axis tension required"));
      expect(screen.getByLabelText("Bolt-axis tension required")).toBeChecked();
      expect(screen.queryAllByLabelText(/axis tension$/u)).toHaveLength(0);
      fireEvent.click(screen.getByLabelText("Bolt-axis tension required"));
      expect(screen.getByLabelText("Bolt-axis tension required")).not.toBeChecked();
    } finally {
      source.mockRestore();
    }
  });
});
