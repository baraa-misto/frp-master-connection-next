import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";

import { EvaluationTransportError } from "../src/api/client";
import { DirectSideLapConcreteWorkspace } from "../src/workspace/DirectSideLapConcreteWorkspace";
import { ShearConnectionsWorkspace } from "../src/workspace/ShearConnectionsWorkspace";
import type { DirectSideLapPreviewState } from "../src/workspace/directSideLapConcreteWorkflow";
import {
  directSideLapDesignFixture,
  directSideLapPreviewFixture,
} from "./directSideLapConcreteFixtures";

const mocks = vi.hoisted<{
  design: Mock;
  response: ReturnType<typeof directSideLapPreviewFixture> | null;
  state: DirectSideLapPreviewState;
  error: EvaluationTransportError | null;
  detail: string | null;
  retry: ReturnType<typeof vi.fn>;
  clipboard: Mock;
}>(() => ({ design: vi.fn(), response: null, state: "CURRENT_VALID", error: null, detail: null, retry: vi.fn(), clipboard: vi.fn() }));

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return { ...actual, evaluateDirectSideLapConcrete: mocks.design };
});
vi.mock("../src/workspace/directSideLapConcreteWorkflow", () => ({
  useDirectSideLapConcretePreview: () => ({ state: mocks.state, response: mocks.response, error: mocks.error, invalidDetail: mocks.detail, retry: mocks.retry }),
}));
vi.mock("../src/visualization/VisualizationPanel", () => ({
  VisualizationPanel: ({ onAppliedActionValueChange, onSelect }: { readonly onAppliedActionValueChange?: (component: "FX" | "FY" | "FZ" | "MX", value: string) => void; readonly onSelect?: (value: { kind: "MEMBER"; id: string }) => void }) => <div data-testid="direct-side-lap-viewer"><button type="button" onClick={() => { onAppliedActionValueChange?.("FZ", "-5"); }}>Edit Major arrow</button><button type="button" onClick={() => { onAppliedActionValueChange?.("FY", "2"); }}>Edit Minor arrow</button><button type="button" onClick={() => { onAppliedActionValueChange?.("FX", "3"); }}>Edit Axial arrow</button><button type="button" onClick={() => { onAppliedActionValueChange?.("MX", "9"); }}>Ignore moment arrow</button><button type="button" onClick={() => { onSelect?.({ kind: "MEMBER", id: "selected-member" }); }}>Select member</button></div>,
}));

function change(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

describe("Stage 3.5B direct side-lap workspace", () => {
  beforeEach(() => {
    mocks.design.mockReset(); mocks.retry.mockReset(); mocks.clipboard.mockReset().mockResolvedValue(undefined);
    mocks.response = directSideLapPreviewFixture(); mocks.state = "CURRENT_VALID"; mocks.error = null; mocks.detail = null;
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: mocks.clipboard } });
  });

  it("groups the stable direct side-lap option exactly once under Beam connections", () => {
    render(<ShearConnectionsWorkspace />);
    const selector = screen.getByLabelText("Connection type");
    expect(selector).toHaveValue("DIRECT_REFERENCE");
    const groups = Array.from(selector.querySelectorAll("optgroup")).map((group) => ({
      label: group.label,
      values: Array.from(group.querySelectorAll("option")).map((option) => option.value),
    }));
    expect(groups.find((group) => group.label === "Brace/beam connections")?.values).not.toContain(
      "DIRECT_SIDE_LAP_CONCRETE",
    );
    expect(groups.find((group) => group.label === "Beam connections")?.values).toEqual([
      "SYMMETRIC_DOUBLE_WEB_SPLICE",
      "BEAM_CONCRETE_PAIRED_ANGLE",
      "DIRECT_SIDE_LAP_CONCRETE",
    ]);
    expect(selector.querySelectorAll('option[value="DIRECT_SIDE_LAP_CONCRETE"]')).toHaveLength(1);
    change("Connection type", "DIRECT_SIDE_LAP_CONCRETE");
    expect(screen.getByRole("heading", { name: "Brace/beam connection — Direct side-lap Angle/Channel to concrete wall" })).toBeInTheDocument();
  });

  it("mounts finite wall, overlap, direct anchors, forces, handoff, and limitations", () => {
    render(<DirectSideLapConcreteWorkspace />);
    for (const title of ["General / Case", "Connected Member", "Concrete Wall / Free End", "Direct Wall Anchor Group", "External Anchor Geometry", "Applied Forces", "External Handoff"]) expect(screen.getByText(title)).toBeInTheDocument();
    expect(screen.getByTestId("direct-side-lap-viewer")).toBeInTheDocument();
    expect(screen.getByLabelText("Side-lap length")).toHaveValue("12");
    expect(screen.getByLabelText("Anchor group distance behind wall free end")).toHaveValue("6");
    expect(screen.queryByLabelText(/moment/iu)).not.toBeInTheDocument();
    expect(screen.getByText(/Concrete, anchors, pull-through/iu)).toBeInTheDocument();
  });

  it("never moves anchors on lap edit and moves them only on explicit center", () => {
    render(<DirectSideLapConcreteWorkspace />);
    change("Side-lap length", "18");
    expect(screen.getByLabelText("Anchor group distance behind wall free end")).toHaveValue("6");
    fireEvent.click(screen.getByRole("button", { name: "Center anchor group in overlap" }));
    expect(screen.getByLabelText("Anchor group distance behind wall free end")).toHaveValue("9");
  });

  it("switches Channel/Angle profile state and keeps shared wall, anchors, and loads", () => {
    render(<DirectSideLapConcreteWorkspace />);
    change("Wall run behind free end", "52"); change("Major shear (+S)", "-6");
    change("Direct side-lap profile family", "ANGLE");
    expect(screen.getByLabelText("Selected Angle leg to wall")).toBeInTheDocument();
    expect(screen.getByLabelText("Wall run behind free end")).toHaveValue("52");
    expect(screen.getByLabelText("Major shear (+S)")).toHaveValue("-6");
    change("Selected Angle leg to wall", "LEG_Z_OUTER");
    expect(screen.getByLabelText("Selected Angle leg to wall")).toHaveValue("LEG_Z_OUTER");
  });

  it("edits every strict geometry/anchor field and loads exact U.S./SI benchmarks", () => {
    render(<DirectSideLapConcreteWorkspace />);
    for (const label of [
      "Depth", "Flange width", "Web thickness", "Flange thickness",
      "Member projection beyond wall", "Wall run behind free end", "Wall transverse width",
      "Wall thickness", "Anchor pitch", "Anchor gauge",
      "Anchor group distance behind wall free end", "Anchor group transverse offset",
      "Anchor diameter", "FRP anchor hole", "Specified embedment",
      "Washer outside diameter", "Washer thickness", "Axial force (+L)",
      "Major shear (+S)", "Minor shear (+N)",
    ]) change(label, "2");
    change("Direct anchor rows", "3");
    change("Direct anchors per row", "2");
    expect(screen.getByLabelText("Direct anchor rows")).toHaveValue(3);
    expect(screen.getByLabelText("Direct anchors per row")).toHaveValue(2);
    fireEvent.click(screen.getByRole("button", { name: "Load 3.5B SI" }));
    expect(screen.getByLabelText("Side-lap length")).toHaveValue("304.8");
    fireEvent.click(screen.getByRole("button", { name: "Load 3.5B U.S." }));
    expect(screen.getByLabelText("Side-lap length")).toHaveValue("12");
    fireEvent.click(screen.getByRole("button", { name: "Select member" }));
  });

  it("uses one load state for sidebar and arrow editing and never exposes moment input", () => {
    render(<DirectSideLapConcreteWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Edit Major arrow" }));
    fireEvent.click(screen.getByRole("button", { name: "Edit Minor arrow" }));
    fireEvent.click(screen.getByRole("button", { name: "Edit Axial arrow" }));
    fireEvent.click(screen.getByRole("button", { name: "Ignore moment arrow" }));
    expect(screen.getByLabelText("Major shear (+S)")).toHaveValue("-5");
    expect(screen.getByLabelText("Minor shear (+N)")).toHaveValue("2");
    expect(screen.getByLabelText("Axial force (+L)")).toHaveValue("3");
  });

  it("runs design only explicitly and marks it stale after preview-affecting edits", async () => {
    mocks.design.mockResolvedValueOnce(directSideLapDesignFixture());
    render(<DirectSideLapConcreteWorkspace />);
    expect(mocks.design).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(mocks.design).toHaveBeenCalledTimes(1); });
    change("Side-lap length", "13");
    expect(screen.getByText(/Design results are stale/iu)).toBeInTheDocument();
  });

  it("copies full-precision handoff and preserves last-valid/invalid workflow", async () => {
    render(<DirectSideLapConcreteWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Copy handoff JSON" }));
    await waitFor(() => { expect(mocks.clipboard).toHaveBeenCalledWith(mocks.response?.result.external_anchor_handoff_json); });
    mocks.state = "CURRENT_INVALID_SHOWING_LAST_VALID"; mocks.detail = "ANCHOR_OUTSIDE_PHYSICAL_SIDE_LAP_OVERLAP";
    render(<DirectSideLapConcreteWorkspace />);
    expect(screen.getAllByText(/showing last valid preview/iu).length).toBeGreaterThan(0);
  });

  it("downloads the immutable handoff through a temporary object URL", () => {
    const create = vi.fn(() => "blob:direct-side-lap");
    const revoke = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: create });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revoke });
    render(<DirectSideLapConcreteWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Download handoff JSON" }));
    expect(create).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
    expect(revoke).toHaveBeenCalledWith("blob:direct-side-lap");
    click.mockRestore();
  });

  it("fails local invalid fields closed and exposes retry for transport failure", () => {
    const view = render(<DirectSideLapConcreteWorkspace />);
    change("Side-lap length", "0");
    expect(screen.getByText(/must be positive/iu)).toBeInTheDocument();
    mocks.state = "PREVIEW_FAILED_SHOWING_LAST_VALID"; mocks.error = new EvaluationTransportError("NETWORK", null, "offline", null);
    view.rerender(<DirectSideLapConcreteWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Retry preview" }));
    expect(mocks.retry).toHaveBeenCalledTimes(1);
  });

  it("distinguishes nonfinite geometry, invalid group counts, pending, and no-valid states", () => {
    const view = render(<DirectSideLapConcreteWorkspace />);
    change("Wall thickness", "not-finite");
    expect(screen.getByText(/finite decimal/iu)).toBeInTheDocument();
    change("Wall thickness", "8");
    change("Direct anchor rows", "0");
    expect(screen.getByText(/rows and anchors per row/iu)).toBeInTheDocument();
    change("Side-lap length", "not-finite");
    fireEvent.click(screen.getByRole("button", { name: "Center anchor group in overlap" }));

    mocks.response = null; mocks.state = "PREVIEW_PENDING"; mocks.detail = null;
    view.rerender(<DirectSideLapConcreteWorkspace />);
    expect(screen.getAllByText("Preview updating")).toHaveLength(2);
    expect(screen.getByText("No current direct side-lap result.")).toBeInTheDocument();
    mocks.state = "NO_VALID_PREVIEW"; mocks.detail = "No accepted geometry";
    view.rerender(<DirectSideLapConcreteWorkspace />);
    expect(screen.getByText("No valid backend preview")).toBeInTheDocument();
    expect(screen.getByText("Canonical direct side-lap model unavailable")).toBeInTheDocument();
  });

  it("renders controlled and unexpected design errors without automatic retries", async () => {
    mocks.design.mockRejectedValueOnce(new EvaluationTransportError("HTTP", 500, "controlled"));
    const controlled = render(<DirectSideLapConcreteWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(screen.getByText("controlled")).toBeInTheDocument(); });
    controlled.unmount();

    mocks.design.mockRejectedValueOnce("unexpected");
    render(<DirectSideLapConcreteWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => {
      expect(screen.getByText("Unexpected direct side-lap design failure.")).toBeInTheDocument();
    });
  });

  it("aborts and ignores a superseded design response after an input edit", async () => {
    let resolve!: (value: ReturnType<typeof directSideLapDesignFixture>) => void;
    const pending = new Promise<ReturnType<typeof directSideLapDesignFixture>>((done) => { resolve = done; });
    mocks.design.mockReturnValueOnce(pending);
    render(<DirectSideLapConcreteWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(screen.getByRole("button", { name: "Running design check…" })).toBeDisabled();
    change("Side-lap length", "13");
    resolve(directSideLapDesignFixture());
    await waitFor(() => { expect(screen.queryByText("Running design check…")).not.toBeInTheDocument(); });
    expect(screen.queryByText(/Unexpected direct side-lap design failure/iu)).not.toBeInTheDocument();
  });

  it("aborts the active design request during unmount", async () => {
    let aborted = false;
    mocks.design.mockImplementationOnce((_request, signal: AbortSignal) => new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => {
        aborted = true;
        reject(new DOMException("cancelled", "AbortError"));
      });
    }));
    const view = render(<DirectSideLapConcreteWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    view.unmount();
    await waitFor(() => { expect(aborted).toBe(true); });
  });
});
