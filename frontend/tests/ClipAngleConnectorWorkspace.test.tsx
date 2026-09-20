import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationTransportError } from "../src/api/client";
import type { ClipAnglePreviewDisplayState } from "../src/workspace/clipAngleWorkflow";
import { ClipAngleConnectorWorkspace } from "../src/workspace/ClipAngleConnectorWorkspace";
import { clipAngleValidationMessage } from "../src/workspace/clipAngleValidation";
import { ShearConnectionsWorkspace } from "../src/workspace/ShearConnectionsWorkspace";
import { clipAngleDesignFixture, clipAnglePreviewFixture } from "./clipAngleFixtures";

const mocks = vi.hoisted(() => ({
  design: vi.fn(),
  retry: vi.fn(),
  workflowState: "CURRENT_VALID",
  workflowResponse: null as ReturnType<typeof clipAnglePreviewFixture> | null,
  workflowError: null as EvaluationTransportError | null,
  workflowInvalidDetail: undefined as string | null | undefined,
}));

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return { ...actual, evaluateClipAngle: mocks.design };
});

vi.mock("../src/workspace/clipAngleWorkflow", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/workspace/clipAngleWorkflow")>();
  return {
    ...actual,
    useClipAnglePreview: () => ({
      state: mocks.workflowState,
      response: mocks.workflowResponse,
      error: mocks.workflowError,
      invalidDetail: mocks.workflowInvalidDetail === undefined
        ? (mocks.workflowError === null ? null : "Controlled workflow detail")
        : mocks.workflowInvalidDetail,
      outdated: mocks.workflowState !== "CURRENT_VALID",
      acceptedRevision: mocks.workflowState === "CURRENT_VALID" ? 0 : null,
      retry: mocks.retry,
    }),
  };
});

vi.mock("../src/workspace/SingleBoltEngineeringWorkspace", () => ({
  SingleBoltEngineeringWorkspace: () => <div>Direct reference workspace sentinel</div>,
}));

vi.mock("../src/workspace/TeeConnectorWorkspace", () => ({
  TeeConnectorWorkspace: () => <div>Tee workspace sentinel</div>,
}));

vi.mock("../src/visualization/VisualizationPanel", () => ({
  VisualizationPanel: ({ model, title, onSelect, onAppliedActionValueChange }: {
    readonly model: import("../src/visualization/sceneModel").SingleBoltSceneModel;
    readonly title: string;
    readonly onSelect: (value: { readonly kind: "MEMBER" | "BOLT" | "CONTACT"; readonly id: string }) => void;
    readonly onAppliedActionValueChange: (component: "FX" | "MX", value: string) => void;
  }) => (
    <div data-testid="clip-viewer" data-boxes={model.boxes.length} data-bolts={model.cylinders.filter((value) => value.kind === "BOLT").length}>
      <span>{title}</span>
      <button type="button" onClick={() => { onSelect({ kind: "CONTACT", id: "CLIP_ANGLE_INTERFACE_A_CONTACT" }); }}>Select clip contact</button>
      <button type="button" onClick={() => { onAppliedActionValueChange("FX", "2"); }}>Edit clip force</button>
      <button type="button" onClick={() => { onAppliedActionValueChange("MX", "4"); }}>Edit clip moment</button>
    </div>
  ),
}));

function change(label: string, value: string): void {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

describe("Stage 3.3A unified single clip-angle workspace", () => {
  beforeEach(() => {
    mocks.design.mockReset();
    mocks.retry.mockReset();
    mocks.workflowState = "CURRENT_VALID";
    mocks.workflowResponse = clipAnglePreviewFixture();
    mocks.workflowError = null;
    mocks.workflowInvalidDetail = undefined;
  });

  it("adds the controlled connection type without changing Direct or Tee defaults", () => {
    render(<ShearConnectionsWorkspace />);
    expect(screen.getByText("Direct reference workspace sentinel")).toBeInTheDocument();
    change("Connection type", "FRP_TEE");
    expect(screen.getByText("Tee workspace sentinel")).toBeInTheDocument();
    change("Connection type", "SINGLE_CLIP_ANGLE");
    expect(screen.getByRole("heading", { name: /Single FRP Clip Angle/iu })).toBeInTheDocument();
  });

  it("exposes all controlled connector, member, fastener, load, and independent group edits", () => {
    render(<ClipAngleConnectorWorkspace />);
    expect(screen.getByTestId("clip-viewer")).toHaveAttribute("data-boxes", "6");
    expect(screen.getByTestId("clip-viewer")).toHaveAttribute("data-bolts", "8");

    fireEvent.click(screen.getByRole("button", { name: "Load G1 SI" }));
    expect(screen.getByLabelText("Connected-leg width")).toHaveValue("101.6");
    fireEvent.click(screen.getByRole("button", { name: "Load G1 U.S." }));
    expect(screen.getByLabelText("Connected-leg width")).toHaveValue("4");

    change("Connected role", "BEAM");
    change("Connected profile family", "ANGLE");
    change("Leg Y", "5");
    change("Selected physical surface", "LEG_Z_OUTER");
    change("Connected profile roll", "ROTATION_90");
    change("Connected-member inclination", "25");
    fireEvent.click(screen.getByLabelText("Apply end trim clearance"));
    change("End clearance to clip-angle support leg", "0.25");
    fireEvent.click(screen.getByLabelText("Apply end trim clearance"));

    for (const family of ["CHANNEL", "WIDE_FLANGE_I", "RECTANGULAR_HOLLOW_SECTION", "FLAT_PLATE"]) {
      change("Connected profile family", family);
    }
    change("Supporting member", "W_BEAM_FLANGE");
    change("Support contact face", "FLANGE_NEG_OUTER");
    const fieldValues: readonly (readonly [string, string])[] = [
      ["Support member / view length", "18"],
      ["Support depth", "9"],
      ["Support flange width", "9"],
      ["Support web thickness", "0.6"],
      ["Support flange thickness", "0.8"],
      ["Connected-leg width", "4.5"],
      ["Support-leg width", "4.25"],
      ["Clip-angle thickness", "0.55"],
      ["Connector length", "9"],
      ["Connector longitudinal position", "1"],
      ["Bolt diameter", "0.625"],
      ["Hole diameter", "0.688"],
      ["Force X", "1"],
      ["Force Y", "2"],
      ["Force Z", "4"],
      ["Moment X", "1"],
      ["Moment Y", "2"],
      ["Moment Z", "3"],
      ["Reference X", "1"],
      ["Reference Y", "2"],
      ["Reference Z", "3"],
    ];
    for (const [label, value] of fieldValues) change(label, value);
    change("Clip-angle hand", "NEGATIVE_S_SIDE");
    change("Clip-angle length anchor", "POSITIVE_L_END");

    const interfaceA = "Connected Member ↔ Clip-Angle Connected Leg";
    const interfaceB = "Clip-Angle Support Leg ↔ Support";
    change(`${interfaceA} rows`, "3");
    change(`${interfaceA} bolts per row`, "1");
    change(`${interfaceA} Pitch`, "1.5");
    change(`${interfaceA} Gauge`, "1.25");
    const centerButtons = screen.getAllByRole("button", { name: "Center bolt group" });
    const centerA = centerButtons[0];
    const centerB = centerButtons[1];
    if (centerA === undefined || centerB === undefined) throw new Error("Two center controls required.");
    fireEvent.click(centerA);
    change(`${interfaceA} length offset`, "0.5");
    change(`${interfaceA} width offset`, "-0.25");
    change(`${interfaceA} placement method`, "EDGE_DISTANCE_CONTROLLED");
    change(`${interfaceA} Heel edge distance`, "0.8");
    change(`${interfaceA} Free-edge distance`, "0.8");
    change(`${interfaceA} Negative end distance`, "2.5");
    change(`${interfaceA} Positive end distance`, "2.5");

    change(`${interfaceB} placement method`, "GROUP_OFFSET_CONTROLLED");
    change(`${interfaceB} length offset`, "0.25");
    change(`${interfaceB} width offset`, "0.25");
    change(`${interfaceB} placement method`, "EDGE_DISTANCE_CONTROLLED");

    fireEvent.click(screen.getByRole("button", { name: "Select clip contact" }));
    fireEvent.click(screen.getByRole("button", { name: "Edit clip force" }));
    fireEvent.click(screen.getByRole("button", { name: "Edit clip moment" }));
    expect(screen.getByText("Region-specific LW/CW/TT basis")).toBeInTheDocument();
    expect(screen.getAllByText("0.4685 in").length).toBeGreaterThan(0);
  }, 15000);

  it("runs design explicitly, marks it stale on engineering edits, and handles failures", async () => {
    mocks.design.mockResolvedValueOnce(clipAngleDesignFixture());
    const { unmount } = render(<ClipAngleConnectorWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(mocks.design).toHaveBeenCalledTimes(1); });
    await waitFor(() => { expect(screen.getAllByText("Fail").length).toBeGreaterThan(0); });
    change("Bolt diameter", "0.6");
    expect(screen.getAllByText(/stale/iu).length).toBeGreaterThan(0);
    unmount();

    mocks.design.mockRejectedValueOnce(new Error("unexpected"));
    render(<ClipAngleConnectorWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(screen.getByText("Unexpected clip-angle design failure.")).toBeInTheDocument(); });

    mocks.design.mockRejectedValueOnce(
      new EvaluationTransportError("HTTP", 500, "Controlled design error.", null),
    );
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(screen.getByText("Controlled design error.")).toBeInTheDocument(); });
  });

  it("blocks invalid local geometry and surfaces every preview-state boundary", () => {
    const states: readonly ClipAnglePreviewDisplayState[] = [
      "PREVIEW_PENDING",
      "CURRENT_INVALID_SHOWING_LAST_VALID",
      "PREVIEW_FAILED_SHOWING_LAST_VALID",
      "NO_VALID_PREVIEW",
    ];
    for (const state of states) {
      mocks.workflowState = state;
      mocks.workflowResponse = state === "NO_VALID_PREVIEW"
        ? ({ ...clipAnglePreviewFixture(), result: { ...clipAnglePreviewFixture().result, visualization: null } })
        : clipAnglePreviewFixture();
      const { unmount } = render(<ClipAngleConnectorWorkspace />);
      expect(screen.getByRole("status")).toBeInTheDocument();
      unmount();
    }

    mocks.workflowState = "NO_VALID_PREVIEW";
    mocks.workflowResponse = null;
    const empty = render(<ClipAngleConnectorWorkspace />);
    expect(screen.getByText("No current clip-angle result.")).toBeInTheDocument();
    expect(screen.getAllByText("Awaiting backend-authoritative clearances.")).toHaveLength(2);
    empty.unmount();

    mocks.workflowState = "CURRENT_VALID";
    mocks.workflowResponse = clipAnglePreviewFixture();
    const { rerender } = render(<ClipAngleConnectorWorkspace />);
    change("Connected-leg width", "0");
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(screen.getByText("Physical dimensions must be finite and greater than zero.")).toBeInTheDocument();
    rerender(<ClipAngleConnectorWorkspace />);

    mocks.workflowError = new EvaluationTransportError("NETWORK", null, "offline", null);
    rerender(<ClipAngleConnectorWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Retry preview" }));
    expect(mocks.retry).toHaveBeenCalledTimes(1);
  });

  it("keeps design limitations current while explicit readiness gates design", () => {
    const bodyLimited = clipAnglePreviewFixture();
    bodyLimited.result.design_check_ready = false;
    bodyLimited.design_check_ready = false;
    bodyLimited.result.interface_b.normal_action_supported = false;
    bodyLimited.result.interface_b.normal_component.value = "1";
    bodyLimited.result.interface_a.demand.method_applicability = (
      "CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE"
    );
    bodyLimited.result.interface_a.demand.qualification = (
      "SECTION_2_3_2_QUALIFICATION_REQUIRED"
    );
    mocks.workflowResponse = bodyLimited;

    render(<ClipAngleConnectorWorkspace />);

    expect(screen.getByRole("status")).toHaveTextContent("Current backend geometry");
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(screen.getByText("Limited by current method/action")).toBeInTheDocument();
    expect(screen.getByText("Calculated Outside Prescriptive Scope")).toBeInTheDocument();
    expect(screen.getByText("Section 2 3 2 Qualification Required")).toBeInTheDocument();
    expect(screen.getAllByText("Not evaluated").length).toBeGreaterThan(0);
    expect(screen.queryByText(/Current geometry invalid/iu)).not.toBeInTheDocument();
  });

  it("shows only the backend physical reason for a true invalid last-valid state", () => {
    mocks.workflowState = "CURRENT_INVALID_SHOWING_LAST_VALID";
    mocks.workflowInvalidDetail = "CONNECTED_MEMBER_CLIP_ANGLE_INTERFERENCE";
    mocks.workflowResponse = clipAnglePreviewFixture();

    render(<ClipAngleConnectorWorkspace />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Current geometry invalid — showing last valid preview",
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "CONNECTED_MEMBER_CLIP_ANGLE_INTERFERENCE",
    );
    expect(screen.getByTestId("clip-viewer")).toBeInTheDocument();
    expect(screen.getByText("Single clip-angle connector body · Not evaluated"))
      .toBeInTheDocument();
  });

  it("covers fail-closed validation, SI display, unsupported normal action, and canceled design", async () => {
    const invalidCounts = structuredClone(clipAnglePreviewFixture());
    const request = (await import("../src/fixtures/clipAngleBenchmarks")).loadClipAngleC2Benchmark("US_CUSTOMARY");
    request.interface_a_layout.row_count = 0;
    expect(clipAngleValidationMessage(request)).toBe(
      "Each bolt group requires at least one row and one bolt per row.",
    );
    request.interface_a_layout.row_count = 2;
    request.connected_member_end_trim_enabled = true;
    request.connected_member_end_clearance = null;
    expect(clipAngleValidationMessage(request)).toBe(
      "Enabled member-end trim requires a clearance.",
    );

    invalidCounts.result.interface_a.normal_action_supported = false;
    invalidCounts.result.interface_a.normal_component.unit = "kN";
    const metricBolt = invalidCounts.result.interface_a.demand.scenarios[0]?.per_bolt[0];
    if (metricBolt === undefined) throw new Error("Controlled per-bolt result required.");
    metricBolt.total_force_magnitude.unit = "kN";
    invalidCounts.result.interface_a.placement.clearances.heel.unit = "mm";
    invalidCounts.result.interface_a.placement.clearances.free_edge.unit = "mm";
    invalidCounts.result.interface_a.placement.clearances.positive_length_end.unit = "mm";
    invalidCounts.result.interface_a.placement.clearances.negative_length_end.unit = "mm";
    invalidCounts.result.interface_a.placement.clearances.minimum.unit = "mm";
    mocks.workflowResponse = invalidCounts;
    const controlled = render(<ClipAngleConnectorWorkspace />);
    expect(screen.getAllByText(/kN/u).length).toBeGreaterThan(0);

    invalidCounts.result.interface_a.demand.scenarios = [];
    controlled.rerender(<ClipAngleConnectorWorkspace />);
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("Not evaluated").length).toBeGreaterThan(0);

    let resolveDesign!: (value: ReturnType<typeof clipAngleDesignFixture>) => void;
    mocks.design.mockReturnValueOnce(new Promise((resolve) => { resolveDesign = resolve; }));
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    change("Bolt diameter", "0.55");
    resolveDesign(clipAngleDesignFixture());
    await waitFor(() => { expect(screen.queryByText("Running design check…")).not.toBeInTheDocument(); });
    controlled.unmount();

    let rejectDesign!: (reason: unknown) => void;
    mocks.workflowResponse = clipAnglePreviewFixture();
    mocks.design.mockReturnValueOnce(new Promise((_resolve, reject) => { rejectDesign = reject; }));
    const canceled = render(<ClipAngleConnectorWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    change("Hole diameter", "0.6");
    rejectDesign(new Error("canceled after edit"));
    await waitFor(() => { expect(screen.queryByText("Unexpected clip-angle design failure.")).not.toBeInTheDocument(); });
    canceled.unmount();

    mocks.workflowError = new EvaluationTransportError("NETWORK", null, "fallback detail", null);
    mocks.workflowInvalidDetail = null;
    render(<ClipAngleConnectorWorkspace />);
    expect(screen.getByText("fallback detail")).toBeInTheDocument();
  });
});
