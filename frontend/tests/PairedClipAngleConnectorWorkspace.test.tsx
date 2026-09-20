import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationTransportError } from "../src/api/client";
import { PairedClipAngleConnectorWorkspace } from "../src/workspace/PairedClipAngleConnectorWorkspace";
import { ShearConnectionsWorkspace } from "../src/workspace/ShearConnectionsWorkspace";
import type { PairedClipAnglePreviewDisplayState } from "../src/workspace/pairedClipAngleWorkflow";
import {
  pairedClipAngleDesignFixture,
  pairedClipAnglePreviewFixture,
} from "./pairedClipAngleFixtures";

const mocks = vi.hoisted<{
  design: ReturnType<typeof vi.fn>;
  workflowResponse: ReturnType<typeof pairedClipAnglePreviewFixture> | null;
  workflowState: PairedClipAnglePreviewDisplayState;
  workflowError: EvaluationTransportError | null;
  workflowInvalidDetail: string | null;
  retry: ReturnType<typeof vi.fn>;
}>(() => ({
  design: vi.fn(),
  workflowResponse: null as ReturnType<typeof pairedClipAnglePreviewFixture> | null,
  workflowState: "CURRENT_VALID",
  workflowError: null as EvaluationTransportError | null,
  workflowInvalidDetail: null as string | null,
  retry: vi.fn(),
}));

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return { ...actual, evaluatePairedClipAngle: mocks.design };
});

vi.mock("../src/workspace/pairedClipAngleWorkflow", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/workspace/pairedClipAngleWorkflow")>();
  return {
    ...actual,
    usePairedClipAnglePreview: () => ({
      state: mocks.workflowState,
      response: mocks.workflowResponse,
      error: mocks.workflowError,
      invalidDetail: mocks.workflowInvalidDetail,
      outdated: mocks.workflowState !== "CURRENT_VALID",
      acceptedRevision: mocks.workflowState === "CURRENT_VALID" ? 0 : null,
      retry: mocks.retry,
    }),
  };
});

vi.mock("../src/visualization/VisualizationPanel", () => ({
  VisualizationPanel: ({ onAppliedActionValueChange }: {
    readonly onAppliedActionValueChange?: (component: "FX" | "MZ", value: string) => void;
  }) => <div data-testid="paired-viewer">Paired viewer<button type="button" onClick={() => { onAppliedActionValueChange?.("FX", "1.25"); }}>Edit paired force</button><button type="button" onClick={() => { onAppliedActionValueChange?.("MZ", "2.5"); }}>Edit paired moment</button></div>,
}));

function change(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

function lastDesignButton(): HTMLElement {
  return screen.getAllByRole("button", { name: "Run Design Check" }).slice(-1)[0]
    ?? document.body;
}

describe("Stage 3.3B symmetric paired clip-angle workspace", () => {
  beforeEach(() => {
    mocks.design.mockReset();
    mocks.workflowResponse = pairedClipAnglePreviewFixture();
    mocks.workflowState = "CURRENT_VALID";
    mocks.workflowError = null;
    mocks.workflowInvalidDetail = null;
    mocks.retry.mockReset();
  });
  afterEach(() => { vi.restoreAllMocks(); });

  it("renders one unified pair workspace with all controlled sidebar sections and groups", () => {
    render(<PairedClipAngleConnectorWorkspace />);
    expect(screen.getByRole("heading", { name: /Symmetric Paired FRP Clip Angles/iu })).toBeInTheDocument();
    for (const section of ["Connection", "Connected Member", "Supporting Member", "Connector Pair", "Common Member Bolt Group", "Mirrored Support Bolt Groups", "Materials", "Fasteners", "Loads", "Results / Diagnostics"]) {
      expect(screen.getByText(section)).toBeInTheDocument();
    }
    expect(screen.getByTestId("paired-viewer")).toBeInTheDocument();
    expect(screen.getByText("Common Member Through-Bolt Group")).toBeInTheDocument();
    expect(screen.getByText("Positive Support Group")).toBeInTheDocument();
    expect(screen.getByText("Negative Support Group")).toBeInTheDocument();
    expect(screen.getByText(/common metallic double-shear/iu)).toBeInTheDocument();
    expect(screen.getAllByText("Proven")).toHaveLength(2);
  });

  it("is selectable as one distinct governed shear-connection family", () => {
    render(<ShearConnectionsWorkspace />);
    change("Connection type", "SYMMETRIC_PAIRED_CLIP_ANGLES");
    expect(screen.getByRole("heading", { name: /Symmetric Paired FRP Clip Angles/iu })).toBeInTheDocument();
  });

  it("edits the complete controlled pair input surface from one canonical state", () => {
    render(<PairedClipAngleConnectorWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Load G1 SI" }));
    expect(screen.getByLabelText("Common bolt diameter")).toHaveValue("12.7");
    fireEvent.click(screen.getByRole("button", { name: "Load G1 U.S." }));
    change("Paired connected profile family", "WIDE_FLANGE_I");
    change("Paired connected profile surface", "WEB_NEG_FACE");
    change("Paired connected profile family", "CHANNEL");
    change("Paired connected profile family", "FLAT_PLATE");
    change("Width", "7");
    change("Thickness", "0.625");
    change("Member / view length", "10");
    change("Supporting member", "W_BEAM_FLANGE");
    change("Connected-member inclination", "25");
    fireEvent.click(screen.getByLabelText("Apply paired end trim clearance"));
    change("End clearance to paired clip-angle support legs", "0.5");
    fireEvent.click(screen.getByLabelText("Apply paired end trim clearance"));
    for (const [label, value] of [
      ["Support member / view length", "18"], ["Support depth", "9"], ["Support flange width", "11"], ["Support web thickness", "0.6"], ["Support flange thickness", "0.8"],
      ["Connected-leg width", "4.5"], ["Support-leg width", "4.25"], ["Angle thickness", "0.55"], ["Pair length", "9"], ["Pair longitudinal position", "1"],
      ["Common bolt diameter", "0.625"], ["Hole diameter", "0.688"], ["Force X", "0"], ["Force Y", "0"], ["Force Z", "5"], ["Moment X", "1"], ["Moment Y", "0"], ["Moment Z", "0"], ["Reference X", "0"], ["Reference Y", "2.5"], ["Reference Z", "0"],
      ["Common member group Rows", "3"], ["Common member group Bolts per row", "1"], ["Common member group Pitch", "2.5"], ["Common member group Gauge", "1.5"], ["Common member group Heel edge distance", "0.8"], ["Common member group Free edge distance", "0.8"], ["Common member group Negative end distance", "2.5"], ["Common member group Positive end distance", "2.5"],
      ["Mirrored support groups Rows", "3"], ["Mirrored support groups Bolts per row", "1"], ["Mirrored support groups Pitch", "2.5"], ["Mirrored support groups Gauge", "1.5"], ["Mirrored support groups Heel edge distance", "0.8"], ["Mirrored support groups Free edge distance", "0.8"], ["Mirrored support groups Negative end distance", "2.5"], ["Mirrored support groups Positive end distance", "2.5"],
    ] as const) change(label, value);
    fireEvent.click(screen.getByRole("button", { name: "Edit paired force" }));
    fireEvent.click(screen.getByRole("button", { name: "Edit paired moment" }));
    expect(screen.getByLabelText("Force X")).toHaveValue("1.25");
    expect(screen.getByLabelText("Moment Z")).toHaveValue("2.5");
  });

  it("runs design only explicitly, then marks the result stale after an edit", async () => {
    mocks.design.mockResolvedValueOnce(pairedClipAngleDesignFixture());
    render(<PairedClipAngleConnectorWorkspace />);
    expect(mocks.design).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(mocks.design).toHaveBeenCalledTimes(1); });
    await waitFor(() => { expect(screen.getAllByText("Fail").length).toBeGreaterThan(0); });
    change("Common bolt diameter", "0.6");
    expect(screen.getAllByText(/stale/iu).length).toBeGreaterThan(0);
  });

  it("preserves last valid geometry across invalid/error states and exposes retry", () => {
    mocks.workflowState = "CURRENT_INVALID_SHOWING_LAST_VALID";
    mocks.workflowInvalidDetail = "COMMON_MEMBER_THROUGH_BOLT_GROUP:COMPLETE_HOLE_CONTAINMENT_INVALID";
    const { rerender } = render(<PairedClipAngleConnectorWorkspace />);
    expect(screen.getByRole("status")).toHaveTextContent("showing last valid preview");
    expect(screen.getByTestId("paired-viewer")).toBeInTheDocument();
    mocks.workflowState = "PREVIEW_FAILED_SHOWING_LAST_VALID";
    mocks.workflowError = new EvaluationTransportError("NETWORK", null, "offline", null);
    mocks.workflowInvalidDetail = "controlled transport detail";
    rerender(<PairedClipAngleConnectorWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Retry preview" }));
    expect(mocks.retry).toHaveBeenCalledTimes(1);
    mocks.workflowInvalidDetail = null;
    rerender(<PairedClipAngleConnectorWorkspace />);
    expect(screen.getByText("offline")).toBeInTheDocument();
  });

  it("renders pending, empty, unsupported-symmetry, and alternate group result branches", () => {
    mocks.workflowState = "PREVIEW_PENDING";
    const alternate = structuredClone(pairedClipAnglePreviewFixture());
    alternate.result.symmetry_proof = { geometry_proven: false, action_proven: false, equal_sharing_eligible: false, reasons: ["not proven"] };
    alternate.result.common_member_group.demand = null;
    alternate.result.common_member_group.resistance = { automatic_handoff_results: [{ overall_disposition: "FAIL", coverage: "PARTIAL_ECCENTRIC" }] };
    alternate.result.common_member_group.placement.clearances.minimum.unit = "mm";
    const supportBolt = alternate.result.positive_support_group.demand?.scenarios[0]?.per_bolt[0];
    if (supportBolt === undefined) throw new Error("Controlled support demand required.");
    supportBolt.total_force_magnitude.unit = "kN";
    mocks.workflowResponse = alternate;
    const { rerender } = render(<PairedClipAngleConnectorWorkspace />);
    expect(screen.getByRole("status")).toHaveTextContent("Preview updating");
    expect(screen.getAllByText("Not proven").length).toBeGreaterThan(0);
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("Fail").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/mm/u).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/kN/u).length).toBeGreaterThan(0);

    mocks.workflowState = "NO_VALID_PREVIEW";
    mocks.workflowResponse = null;
    rerender(<PairedClipAngleConnectorWorkspace />);
    expect(screen.getByText("Canonical paired clip-angle model unavailable")).toBeInTheDocument();
    expect(screen.getByText("No current paired clip-angle result.")).toBeInTheDocument();
    expect(screen.getAllByText("Pending").length).toBeGreaterThan(0);
  });

  it("blocks design for local invalidity and handles controlled and unexpected design failures", async () => {
    render(<PairedClipAngleConnectorWorkspace />);
    change("Angle thickness", "0");
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(screen.getByText(/finite and positive/iu)).toBeInTheDocument();

    const controlled = render(<PairedClipAngleConnectorWorkspace />);
    mocks.design.mockRejectedValueOnce(new EvaluationTransportError("HTTP", 500, "Controlled pair error.", null));
    fireEvent.click(lastDesignButton());
    await waitFor(() => { expect(screen.getByText("Controlled pair error.")).toBeInTheDocument(); });
    controlled.unmount();

    mocks.design.mockRejectedValueOnce(new Error("unexpected"));
    render(<PairedClipAngleConnectorWorkspace />);
    fireEvent.click(lastDesignButton());
    await waitFor(() => { expect(screen.getByText("Unexpected paired clip-angle design failure.")).toBeInTheDocument(); });
  });

  it("drops superseded design completions and abort-related failures after an engineering edit", async () => {
    let resolveDesign!: (value: ReturnType<typeof pairedClipAngleDesignFixture>) => void;
    mocks.design.mockReturnValueOnce(new Promise((resolve) => { resolveDesign = resolve; }));
    const first = render(<PairedClipAngleConnectorWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(screen.getByRole("button", { name: "Running design check…" })).toBeDisabled();
    change("Common bolt diameter", "0.55");
    resolveDesign(pairedClipAngleDesignFixture());
    await waitFor(() => { expect(screen.queryByText("Running design check…")).not.toBeInTheDocument(); });
    expect(screen.queryByText("Fail")).not.toBeInTheDocument();
    first.unmount();

    let rejectDesign!: (reason: unknown) => void;
    mocks.design.mockReturnValueOnce(new Promise((_resolve, reject) => { rejectDesign = reject; }));
    render(<PairedClipAngleConnectorWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    change("Hole diameter", "0.6");
    rejectDesign(new Error("aborted after edit"));
    await waitFor(() => { expect(screen.queryByText("Unexpected paired clip-angle design failure.")).not.toBeInTheDocument(); });
  });
});
