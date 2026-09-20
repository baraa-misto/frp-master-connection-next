import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";

import { EvaluationTransportError } from "../src/api/client";
import { BeamConcretePairedAngleWorkspace } from "../src/workspace/BeamConcretePairedAngleWorkspace";
import { ShearConnectionsWorkspace } from "../src/workspace/ShearConnectionsWorkspace";
import type { BeamConcretePreviewState } from "../src/workspace/beamConcretePairedAngleWorkflow";
import { beamConcreteDesignFixture, beamConcretePreviewFixture } from "./beamConcretePairedAngleFixtures";

const mocks = vi.hoisted<{
  design: Mock<(request: unknown, signal: AbortSignal) => Promise<ReturnType<typeof beamConcreteDesignFixture>>>;
  response: ReturnType<typeof beamConcretePreviewFixture> | null;
  state: BeamConcretePreviewState;
  error: EvaluationTransportError | null;
  detail: string | null;
  retry: ReturnType<typeof vi.fn>;
  clipboardWrite: Mock<(text: string) => Promise<void>>;
  createObjectUrl: Mock<(obj: Blob | MediaSource) => string>;
  revokeObjectUrl: Mock<(url: string) => void>;
  anchorClick: Mock<() => void>;
}>(() => ({ design: vi.fn(), response: null, state: "CURRENT_VALID", error: null, detail: null, retry: vi.fn(), clipboardWrite: vi.fn<(text: string) => Promise<void>>(), createObjectUrl: vi.fn<(obj: Blob | MediaSource) => string>(() => "blob:handoff"), revokeObjectUrl: vi.fn<(url: string) => void>(), anchorClick: vi.fn<() => void>() }));

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return { ...actual, evaluateBeamConcretePairedAngle: mocks.design };
});
vi.mock("../src/workspace/beamConcretePairedAngleWorkflow", () => ({
  useBeamConcretePairedAnglePreview: () => ({ state: mocks.state, response: mocks.response, error: mocks.error, invalidDetail: mocks.detail, retry: mocks.retry }),
}));
vi.mock("../src/visualization/VisualizationPanel", () => ({
  VisualizationPanel: ({ onAppliedActionValueChange }: { readonly onAppliedActionValueChange?: (component: "FX" | "FY" | "FZ" | "MX", value: string) => void }) => <div data-testid="beam-concrete-viewer">Wall / beam / paired-angle / anchor scene<button type="button" onClick={() => { onAppliedActionValueChange?.("FZ", "-5"); }}>Edit major arrow</button><button type="button" onClick={() => { onAppliedActionValueChange?.("FX", "9"); }}>Edit minor arrow</button><button type="button" onClick={() => { onAppliedActionValueChange?.("FY", "3"); }}>Edit axial arrow</button><button type="button" onClick={() => { onAppliedActionValueChange?.("MX", "7"); }}>Edit ignored moment arrow</button></div>,
}));

function change(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

describe("Stage 3.5A beam-to-concrete paired clip-angle workspace", () => {
  beforeEach(() => {
    mocks.design.mockReset(); mocks.retry.mockReset(); mocks.clipboardWrite.mockReset().mockResolvedValue(undefined); mocks.createObjectUrl.mockClear(); mocks.revokeObjectUrl.mockClear(); mocks.anchorClick.mockClear();
    mocks.response = beamConcretePreviewFixture(); mocks.state = "CURRENT_VALID"; mocks.error = null; mocks.detail = null;
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: mocks.clipboardWrite } });
    vi.spyOn(URL, "createObjectURL").mockImplementation(mocks.createObjectUrl);
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(mocks.revokeObjectUrl);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(mocks.anchorClick);
  });

  it("adds one distinct selector option while preserving the Direct default", () => {
    render(<ShearConnectionsWorkspace />);
    expect(screen.getByLabelText("Connection type")).toHaveValue("DIRECT_REFERENCE");
    change("Connection type", "BEAM_CONCRETE_PAIRED_ANGLE");
    expect(screen.getByRole("heading", { name: "Beam connection — Paired clip angles to concrete wall" })).toBeInTheDocument();
  });

  it("mounts the complete shear-only workspace, scene, handoff, and limitation surface", () => {
    render(<BeamConcretePairedAngleWorkspace />);
    for (const section of ["General / Case", "Connected Member", "Concrete Wall", "Paired Clip-Angle Connector", "Connected Member ↔ Paired Clip Angles", "Mirrored Wall Anchor Groups", "External Anchor Geometry", "Loads", "Wall / Anchor Design Handoff", "Materials / Fasteners", "Geometry / Design Results", "Advanced / Diagnostics"]) {
      expect(screen.getByText(section)).toBeInTheDocument();
    }
    expect(screen.getByTestId("beam-concrete-viewer")).toBeInTheDocument();
    expect(screen.getByLabelText("Major shear")).toHaveValue("-4");
    expect(screen.getByLabelText("Minor shear")).toHaveValue("0");
    expect(screen.getByLabelText("Axial force")).toHaveValue("0");
    expect(screen.queryByLabelText(/Moment/iu)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Eccentricity-induced transfer moment/iu).length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText(/Concrete and external-anchor capacity/iu)).toBeInTheDocument();
  });

  it("switches across the six shared profiles while preserving wall and anchor state", () => {
    render(<BeamConcretePairedAngleWorkspace />);
    const family = screen.getByLabelText("Concrete-wall connected profile family");
    expect(Array.from((family as HTMLSelectElement).options).map((item) => item.value)).toEqual([
      "FLAT_PLATE", "ANGLE", "CHANNEL", "WIDE_FLANGE_I",
      "RECTANGULAR_HOLLOW_SECTION", "SOLID_RECTANGULAR_SECTION",
    ]);
    change("Wall width", "50");
    change("Wall anchor rows", "2");
    change("Concrete-wall connected profile family", "FLAT_PLATE");
    expect(screen.getByLabelText("Thickness")).toHaveValue("0.5");
    change("Concrete-wall connected profile family", "ANGLE");
    expect(screen.getByLabelText("Leg Y")).toHaveValue("6");
    change("Concrete-wall connected profile family", "CHANNEL");
    expect(screen.getByLabelText("Web thickness")).toHaveValue("0.5");
    change("Concrete-wall connected profile family", "RECTANGULAR_HOLLOW_SECTION");
    expect(screen.getAllByLabelText("Wall thickness").map((item) => (item as HTMLInputElement).value)).toContain("0.5");
    change("Concrete-wall connected profile family", "SOLID_RECTANGULAR_SECTION");
    expect(screen.getAllByLabelText("Wall thickness")).toHaveLength(1);
    change("Concrete-wall connected profile surface", "Y_NEG_FACE");
    expect(screen.getByLabelText("Concrete-wall connected profile surface")).toHaveValue("Y_NEG_FACE");
    change("Concrete-wall connected profile roll", "ROTATION_90");
    expect(screen.getByLabelText("Concrete-wall connected profile roll")).toHaveValue("ROTATION_90");
    change("Wall anchors per row", "2");
    expect(screen.getByLabelText("Wall width")).toHaveValue("50");
    expect(screen.getByLabelText("Wall anchor rows")).toHaveValue(2);
    expect(screen.getByLabelText("Wall anchors per row")).toHaveValue(2);
  });

  it("edits the controlled geometry from one state and synchronizes arrow and shear input", () => {
    render(<BeamConcretePairedAngleWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Load R2 SI" }));
    expect(screen.getByLabelText("Wall width")).toHaveValue("1219.2");
    fireEvent.click(screen.getByRole("button", { name: "Load R2 U.S." }));
    const edits = [
      ["Member / view length", "18"], ["Depth", "11"], ["Flange width", "9"], ["Web thickness", "0.6"], ["Flange thickness", "0.6"], ["Member end gap", "0.75"],
      ["Wall width", "50"], ["Wall height", "52"], ["Wall thickness", "10"], ["Connection origin H", "1"], ["Connection origin V", "-1"],
      ["Connected-leg width", "4.5"], ["Wall-leg width", "4.5"], ["Angle thickness", "0.625"], ["Angle length", "9"],
      ["Common beam rows", "3"], ["Common beam bolts per row", "1"], ["Common beam pitch", "2.5"], ["Common beam gauge", "1.5"], ["Common beam heel edge distance", "1.25"], ["Common beam free edge distance", "1.25"], ["Common beam negative end distance", "2"], ["Common beam positive end distance", "2"],
      ["Common bolt diameter", "0.625"], ["Common hole diameter", "0.688"], ["Wall anchor rows", "3"], ["Wall anchors per row", "1"], ["Wall anchor pitch", "2.5"], ["Wall anchor gauge", "1.5"], ["Group centroid ±H", "3.5"], ["Group centroid V", "0.5"],
      ["Anchor diameter", "0.625"], ["Clip-angle anchor hole", "0.688"], ["Specified coordination embedment", "5"], ["Washer outside diameter", "1.25"], ["Washer thickness", "0.125"], ["Major shear", "-6"], ["Minor shear", "2"], ["Axial force", "1"],
    ] as const;
    for (const [label, value] of edits) change(label, value);
    fireEvent.click(screen.getByRole("button", { name: "Edit major arrow" }));
    expect(screen.getByLabelText("Major shear")).toHaveValue("-5");
    fireEvent.click(screen.getByRole("button", { name: "Edit minor arrow" }));
    expect(screen.getByLabelText("Minor shear")).toHaveValue("9");
    fireEvent.click(screen.getByRole("button", { name: "Edit axial arrow" }));
    expect(screen.getByLabelText("Axial force")).toHaveValue("3");
    fireEvent.click(screen.getByRole("button", { name: "Edit ignored moment arrow" }));
    expect(screen.getByLabelText("Major shear")).toHaveValue("-5");
    expect(screen.getByLabelText("Minor shear")).toHaveValue("9");
    expect(screen.getByLabelText("Axial force")).toHaveValue("3");
  });

  it("copies and downloads the full-precision backend-authored handoff", async () => {
    render(<BeamConcretePairedAngleWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Copy JSON" }));
    await waitFor(() => { expect(mocks.clipboardWrite.mock.calls).toEqual([[mocks.response?.result.external_anchor_handoff_json]]); });
    expect(screen.getByText(/Copied full-precision/iu)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Download JSON" }));
    expect(mocks.createObjectUrl.mock.calls).toHaveLength(1);
    expect(mocks.anchorClick.mock.calls).toHaveLength(1);
    expect(mocks.revokeObjectUrl.mock.calls).toEqual([["blob:handoff"]]);
  });

  it("renders combined-layout Minor action without fabricated branch cards", () => {
    mocks.response = beamConcretePreviewFixture();
    mocks.response = {
      ...mocks.response,
      result: {
        ...mocks.response.result,
        handoff_mode: "COMBINED_LAYOUT",
        branch_allocation_status: "NOT_EVALUATED",
        positive_wall_group: { ...mocks.response.result.positive_wall_group, wrench: null },
        negative_wall_group: { ...mocks.response.result.negative_wall_group, wrench: null },
      },
    };
    render(<BeamConcretePairedAngleWorkspace />);
    expect(screen.getByText(/Combined layout — branch allocation NOT_EVALUATED/iu)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Paired branch allocation" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Positive wall-anchor group" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Negative wall-anchor group" })).not.toBeInTheDocument();
  });

  it("runs design only explicitly and marks the accepted result stale after an edit", async () => {
    mocks.design.mockResolvedValueOnce(beamConcreteDesignFixture());
    render(<BeamConcretePairedAngleWorkspace />);
    expect(mocks.design).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(mocks.design).toHaveBeenCalledTimes(1); });
    expect(screen.getAllByText("Fail").length).toBeGreaterThan(0);
    change("Member end gap", "0.6");
    expect(screen.getAllByText(/stale/iu).length).toBeGreaterThan(0);
  });

  it("preserves last-valid display, retry, no-preview, local invalidity, and design errors", () => {
    mocks.state = "CURRENT_INVALID_SHOWING_LAST_VALID"; mocks.detail = "ANCHOR_CENTER_OUTSIDE_FINITE_WALL";
    const view = render(<BeamConcretePairedAngleWorkspace />);
    expect(screen.getAllByText(/showing last valid preview/iu).length).toBeGreaterThan(0);
    mocks.state = "PREVIEW_FAILED_SHOWING_LAST_VALID"; mocks.error = new EvaluationTransportError("NETWORK", null, "offline", null); mocks.detail = null;
    view.rerender(<BeamConcretePairedAngleWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Retry preview" }));
    expect(mocks.retry).toHaveBeenCalledTimes(1);
    mocks.state = "NO_VALID_PREVIEW"; mocks.response = null; mocks.error = null;
    view.rerender(<BeamConcretePairedAngleWorkspace />);
    expect(screen.getByText("Canonical beam-to-concrete model unavailable")).toBeInTheDocument();
    expect(screen.getByText("No current beam-to-concrete result.")).toBeInTheDocument();
    view.unmount();

    mocks.response = beamConcretePreviewFixture(); mocks.state = "CURRENT_VALID";
    mocks.design.mockRejectedValueOnce(new Error("unexpected"));
    render(<BeamConcretePairedAngleWorkspace />);
    change("Member end gap", "-1");
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(screen.getByText("Member end gap must be nonnegative.")).toBeInTheDocument();
  });

  it("covers every local wall/embedment validation and pending preview label", () => {
    const view = render(<BeamConcretePairedAngleWorkspace />);
    change("Wall width", "not-a-number");
    expect(screen.getByText(/must be finite decimal values/iu)).toBeInTheDocument();
    change("Wall width", "0");
    expect(screen.getByText("Concrete wall dimensions must be positive.")).toBeInTheDocument();
    change("Wall width", "48");
    change("Specified coordination embedment", "0");
    expect(screen.getByText("External anchor embedment must be positive.")).toBeInTheDocument();
    mocks.state = "PREVIEW_PENDING";
    mocks.response = null;
    view.rerender(<BeamConcretePairedAngleWorkspace />);
    expect(screen.getAllByText("Preview updating").length).toBeGreaterThan(0);
    view.unmount();
  });

  it("ignores superseded design responses and intentional abort failures", async () => {
    let resolveFirst: (value: ReturnType<typeof beamConcreteDesignFixture>) => void = () => undefined;
    mocks.design.mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }));
    render(<BeamConcretePairedAngleWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    change("Member end gap", "0.6");
    resolveFirst(beamConcreteDesignFixture());
    await waitFor(() => { expect(screen.getAllByText(/No design run|Run Design Check/iu).length).toBeGreaterThan(0); });

    mocks.design.mockImplementationOnce((_request: unknown, signal: AbortSignal) => new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => { reject(new DOMException("aborted", "AbortError")); });
    }));
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    change("Member end gap", "0.7");
    await waitFor(() => { expect(screen.queryByText(/Unexpected design-check failure/iu)).not.toBeInTheDocument(); });
  });

  it("shows the preserved transport error from an explicit design failure", async () => {
    mocks.design.mockRejectedValueOnce(new EvaluationTransportError("HTTP", 503, "design unavailable", null));
    const view = render(<BeamConcretePairedAngleWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(screen.getByText("design unavailable")).toBeInTheDocument(); });
    view.unmount();
    mocks.design.mockRejectedValueOnce(new Error("untyped failure"));
    render(<BeamConcretePairedAngleWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(screen.getByText("Unexpected design-check failure.")).toBeInTheDocument(); });
  });
});
