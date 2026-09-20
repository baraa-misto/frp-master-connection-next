import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  COLUMN_BASE_WEB_ANGLE_DESIGN_PATH,
  COLUMN_BASE_WEB_ANGLE_PREVIEW_PATH,
  EvaluationTransportError,
  evaluateColumnBaseWebAngle,
  previewColumnBaseWebAngle,
} from "../src/api/client";
import * as clientModule from "../src/api/client";
import type {
  ColumnBaseHistoricalComponentTransfer,
  ColumnBasePreviewResponse,
  ColumnBaseSignedComponentTransfer,
} from "../src/api/columnBaseWebAngleContracts";
import { loadColumnBaseWebAngleBenchmark } from "../src/fixtures/columnBaseWebAngleBenchmarks";
import { ColumnBaseWebAngleWorkspace } from "../src/workspace/ColumnBaseWebAngleWorkspace";
import { ShearConnectionsWorkspace } from "../src/workspace/ShearConnectionsWorkspace";
import { useColumnBaseWebAnglePreview } from "../src/workspace/columnBaseWebAngleWorkflow";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import { columnBaseDesignFixture, columnBasePreviewFixture } from "./columnBaseWebAngleFixtures";

vi.mock("../src/visualization/VisualizationPanel", () => ({
  VisualizationPanel: ({ title, model, onAppliedActionValueChange }: { title: string; model: { boxes: readonly unknown[]; cylinders: readonly unknown[]; materialAxes: readonly unknown[] }; onAppliedActionValueChange?: (component: string, value: string) => void }) => <div aria-label="mock-column-base-viewer"><h3>{title}</h3><span>{model.boxes.length} boxes</span><span>{model.cylinders.length} cylinders</span><span>{model.materialAxes.length} material axes</span><button type="button" onClick={() => { onAppliedActionValueChange?.("FX", "7"); }}>Edit FX</button><button type="button" onClick={() => { onAppliedActionValueChange?.("FY", "2"); }}>Edit FY</button><button type="button" onClick={() => { onAppliedActionValueChange?.("FZ", "25"); }}>Edit FZ</button><button type="button" onClick={() => { onAppliedActionValueChange?.("MX", "1"); }}>Ignore MX</button></div>,
}));

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("Stage 3.5C controlled benchmark and API boundary", () => {
  beforeEach(() => { vi.stubGlobal("fetch", vi.fn()); });
  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it("loads independent fresh exact U.S. and SI successor defaults", () => {
    const us = loadColumnBaseWebAngleBenchmark("US_CUSTOMARY");
    const si = loadColumnBaseWebAngleBenchmark("SI");
    expect(us).toMatchObject({ orchestration_contract_version: "3.7A-RC1", assembly: "DOUBLE_BASE_ANGLES", single_side: "+T_C", signed_axial_force: { value: "-20", unit: "kip" }, connection_plane_shear: { value: "4", unit: "kip" }, connection_normal_shear: { value: "0", unit: "kip" } });
    expect(us).not.toHaveProperty("user_moment");
    expect(si.concrete.s_dimension).toEqual({ value: "914.4", unit: "mm" });
    expect(si.web_hole_diameter).toEqual({ value: "14.3002", unit: "mm" });
    expect(si.signed_axial_force).toEqual({ value: "-88.96443230521", unit: "kN" });
    if (us.column_profile.profile_family !== "WIDE_FLANGE_I") throw new Error("Controlled W/I fixture required.");
    us.column_profile.dimensions.depth.value = "99";
    const fresh = loadColumnBaseWebAngleBenchmark("US_CUSTOMARY");
    if (fresh.column_profile.profile_family !== "WIDE_FLANGE_I") throw new Error("Controlled W/I fixture required.");
    expect(fresh.column_profile.dimensions.depth.value).toBe("10");
  });

  it("posts preview and design only to the strict same-origin endpoints", async () => {
    const fetchMock = vi.mocked(fetch);
    const request = loadColumnBaseWebAngleBenchmark("US_CUSTOMARY");
    const controller = new AbortController();
    fetchMock.mockResolvedValueOnce(response(columnBasePreviewFixture()));
    await expect(previewColumnBaseWebAngle(request, controller.signal)).resolves.toMatchObject({ request_id: request.request_id });
    expect(fetchMock).toHaveBeenNthCalledWith(1, COLUMN_BASE_WEB_ANGLE_PREVIEW_PATH, expect.objectContaining({ method: "POST", credentials: "same-origin", signal: controller.signal }));
    fetchMock.mockResolvedValueOnce(response(columnBaseDesignFixture()));
    await expect(evaluateColumnBaseWebAngle(request, controller.signal)).resolves.toMatchObject({ external_design_required: true });
    expect(fetchMock).toHaveBeenNthCalledWith(2, COLUMN_BASE_WEB_ANGLE_DESIGN_PATH, expect.objectContaining({ method: "POST" }));
  });

  it("rejects malformed successful preview and design responses", async () => {
    const preview = columnBasePreviewFixture() as unknown as Record<string, unknown>;
    for (const body of [null, {}, { ...preview, api_transport_schema_version: "bad" }, { ...preview, orchestration_contract_version: "bad" }, { ...preview, preview_schema_version: "bad" }, { ...preview, resistance_evaluated: true }, { ...preview, external_design_required: false }, { ...preview, engineering_fingerprint: null }, { ...preview, result: null }]) {
      vi.mocked(fetch).mockResolvedValueOnce(response(body));
      await expect(previewColumnBaseWebAngle(loadColumnBaseWebAngleBenchmark("US_CUSTOMARY"), new AbortController().signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    }
    const design = columnBaseDesignFixture() as unknown as Record<string, unknown>;
    for (const body of [null, {}, { ...design, orchestration_contract_version: "bad" }, { ...design, required_check_status: "PASS" }, { ...design, ordinary_pass_allowed: true }, { ...design, external_design_required: false }, { ...design, result_fingerprint: null }, { ...design, result: null }]) {
      vi.mocked(fetch).mockResolvedValueOnce(response(body));
      await expect(evaluateColumnBaseWebAngle(loadColumnBaseWebAngleBenchmark("US_CUSTOMARY"), new AbortController().signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    }
  });

  it("classifies validation, HTTP, network, and intentional abort boundaries", async () => {
    const request = loadColumnBaseWebAngleBenchmark("US_CUSTOMARY");
    vi.mocked(fetch).mockResolvedValueOnce(response({ detail: "invalid" }, 422));
    await expect(previewColumnBaseWebAngle(request, new AbortController().signal)).rejects.toMatchObject({ kind: "VALIDATION", status: 422 });
    vi.mocked(fetch).mockResolvedValueOnce(response({ detail: "failed" }, 503));
    await expect(evaluateColumnBaseWebAngle(request, new AbortController().signal)).rejects.toMatchObject({ kind: "HTTP", status: 503 });
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("offline"));
    await expect(previewColumnBaseWebAngle(request, new AbortController().signal)).rejects.toMatchObject({ kind: "NETWORK" });
    const abort = new DOMException("aborted", "AbortError");
    vi.mocked(fetch).mockRejectedValueOnce(abort);
    await expect(evaluateColumnBaseWebAngle(request, new AbortController().signal)).rejects.toBe(abort);
  });
});

describe("Stage 3.5C latest-response-wins preview workflow", () => {
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

  it("accepts immediate valid preview and blocks local invalid input", async () => {
    const spy = vi.spyOn(clientModule, "previewColumnBaseWebAngle").mockResolvedValueOnce(columnBasePreviewFixture());
    const request = loadColumnBaseWebAngleBenchmark("US_CUSTOMARY");
    const valid = renderHook(() => useColumnBaseWebAnglePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(valid.result.current.state).toBe("CURRENT_VALID"); });
    valid.unmount();
    const blocked = renderHook(() => useColumnBaseWebAnglePreview({ request, revision: 1, immediate: false, validationMessage: "invalid" }));
    expect(blocked.result.current).toMatchObject({ state: "NO_VALID_PREVIEW", invalidDetail: "invalid" });
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("retains the last valid model across invalid, failed, retry, and local-invalid states", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(clientModule, "previewColumnBaseWebAngle");
    spy.mockResolvedValueOnce(columnBasePreviewFixture());
    let revision = 0;
    let validationMessage: string | null = null;
    const request = loadColumnBaseWebAngleBenchmark("US_CUSTOMARY");
    const hook = renderHook(() => useColumnBaseWebAnglePreview({ request, revision, immediate: revision === 0, validationMessage }));
    await act(async () => { await Promise.resolve(); });
    expect(hook.result.current.state).toBe("CURRENT_VALID");
    spy.mockResolvedValueOnce(columnBasePreviewFixture("INVALID_GEOMETRY")); revision = 1; hook.rerender();
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(hook.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    spy.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "offline", null)); revision = 2; hook.rerender();
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(hook.result.current.state).toBe("PREVIEW_FAILED_SHOWING_LAST_VALID");
    spy.mockResolvedValueOnce(columnBasePreviewFixture()); act(() => { hook.result.current.retry(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(hook.result.current.state).toBe("CURRENT_VALID");
    validationMessage = "locally invalid"; revision = 3; hook.rerender();
    expect(hook.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
  });

  it("fails closed when the server supplies no invalid-geometry detail", async () => {
    const invalid = { ...columnBasePreviewFixture("INVALID_GEOMETRY"), geometry_invalid_reasons: [] };
    vi.spyOn(clientModule, "previewColumnBaseWebAngle").mockResolvedValueOnce(invalid);
    const request = loadColumnBaseWebAngleBenchmark("US_CUSTOMARY");
    const hook = renderHook(() => useColumnBaseWebAnglePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(hook.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(hook.result.current.invalidDetail).toBeNull();
  });

  it("normalizes unexpected/validation failures and ignores aborts and superseded responses", async () => {
    const request = loadColumnBaseWebAngleBenchmark("US_CUSTOMARY");
    const spy = vi.spyOn(clientModule, "previewColumnBaseWebAngle").mockRejectedValueOnce(new Error("unexpected"));
    const unexpected = renderHook(() => useColumnBaseWebAnglePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(unexpected.result.current.state).toBe("NO_VALID_PREVIEW"); });
    expect(unexpected.result.current.error?.message).toMatch(/Unexpected column-base/iu);
    unexpected.unmount();
    spy.mockRejectedValueOnce(new EvaluationTransportError("VALIDATION", 422, "invalid", null));
    const invalid = renderHook(() => useColumnBaseWebAnglePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(invalid.result.current.state).toBe("NO_VALID_PREVIEW"); });
    invalid.unmount();
    spy.mockRejectedValueOnce(new DOMException("aborted", "AbortError"));
    const aborted = renderHook(() => useColumnBaseWebAnglePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(aborted.result.current.state).toBe("PREVIEW_PENDING"); });
    aborted.unmount();

    let resolveOld: (value: ReturnType<typeof columnBasePreviewFixture>) => void = () => undefined;
    spy.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve; }));
    spy.mockResolvedValueOnce(columnBasePreviewFixture());
    const latest = renderHook((revision: number) => useColumnBaseWebAnglePreview({ request, revision, immediate: true, validationMessage: null }), { initialProps: 0 });
    latest.rerender(1);
    await waitFor(() => { expect(latest.result.current.state).toBe("CURRENT_VALID"); });
    resolveOld(columnBasePreviewFixture());
    await act(async () => { await Promise.resolve(); });
    expect(latest.result.current.response?.request_id).toBe("STAGE-3.7A-WIDE_FLANGE_I-US_CUSTOMARY");
  });
});

describe("Stage 3.5C unified workspace", () => {
  beforeEach(() => {
    vi.spyOn(clientModule, "previewColumnBaseWebAngle").mockResolvedValue(columnBasePreviewFixture());
    vi.spyOn(clientModule, "evaluateColumnBaseWebAngle").mockResolvedValue(columnBaseDesignFixture());
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
  });
  afterEach(() => { vi.restoreAllMocks(); });

  it("registers the Column connections group and mounts the exact selector option", async () => {
    render(<ShearConnectionsWorkspace />);
    const option = screen.getByRole("option", { name: "Column connection — Single/double base angles to concrete" });
    expect(option.closest("optgroup")?.label).toBe("Column connections");
    fireEvent.change(screen.getByLabelText("Connection type"), { target: { value: "COLUMN_BASE_WEB_ANGLES_CONCRETE" } });
    expect(await screen.findByRole("heading", { name: "Column connection — Single/double base angles to concrete" })).toBeInTheDocument();
  });

  it("renders the complete double default, three force fields, no moment fields, and owner transfer distinction", async () => {
    render(<ColumnBaseWebAngleWorkspace />);
    expect(await screen.findByLabelText("mock-column-base-viewer")).toHaveTextContent("8 boxes");
    expect(screen.getByLabelText("Base-angle assembly")).toHaveValue("DOUBLE_BASE_ANGLES");
    expect(screen.getByLabelText("Single-angle side")).toBeDisabled();
    expect(screen.getByLabelText("Axial force (+ uplift / - compression)")).toHaveValue("-20");
    expect(screen.getByLabelText("Connection-plane shear")).toHaveValue("4");
    expect(screen.getByLabelText("Connection-normal shear")).toHaveValue("0");
    expect(screen.getByText(/Shears are signed along backend-authored S_C and T_C/iu)).toBeInTheDocument();
    expect(screen.queryByLabelText(/moment/iu)).not.toBeInTheDocument();
    expect(screen.getByText("Column Local Transfer").parentElement).toHaveTextContent("Signed axial action: -20 kip");
    expect(screen.getByText("Column Local Transfer").parentElement).toHaveTextContent("Design magnitude: 20 kip (100%)");
    expect(screen.getByText("Column Local Transfer").parentElement).toHaveTextContent("Material axis: LW · signed direction -LW");
    expect(screen.getByText("Column Local Transfer").parentElement).toHaveTextContent("Mode: Compression");
    expect(screen.getByText("Base-Angle System").parentElement).toHaveTextContent("Angle +: -10 kip (50%)");
    expect(screen.getByText("Base-Angle System").parentElement).toHaveTextContent("Vertical-leg axis: CW · signed direction -CW");
    expect(screen.getByText("Foundation Reaction").parentElement).toHaveTextContent("Axial reaction counted once: -20 kip");
    expect(screen.getByText("Concrete has no FRP LW/CW/TT material axes.")).toBeInTheDocument();
  });

  it("presents uplift signed actions, half branches, one foundation reaction, and explicit limits", async () => {
    const base = columnBasePreviewFixture();
    const transfer = base.result.component_transfer;
    if (!("axial_mode" in transfer) || base.result.visualization === null) throw new Error("Controlled R2 fixture required.");
    const force = (value: string) => ({ value, unit: "kip", canonical_value: value, canonical_unit: "kip" });
    const uplift = {
      ...base,
      result: {
        ...base.result,
        component_transfer: {
          ...transfer,
          axial_mode: "UPLIFT" as const,
          column_signed_axial_action: force("20"),
          column_signed_material_direction: "+LW" as const,
          base_angle_system_signed_axial_action: force("20"),
          base_angle_vertical_leg_signed_material_direction: "+CW" as const,
          positive_angle_signed_axial_action: force("10"),
          negative_angle_signed_axial_action: force("10"),
          foundation_signed_axial_action: force("20"),
        },
        combined_foundation_wrench: { ...base.result.combined_foundation_wrench, force_s_t_l: { ...base.result.combined_foundation_wrench.force_s_t_l, longitudinal: force("20") } },
        limitations: [
          ["COLUMN_END_BEARING_FOR_UPLIFT", "NOT_REQUIRED"],
          ["BASE_ANGLE_CW_BODY_AND_HEEL_UPLIFT_TRANSFER", "NOT_EVALUATED"],
          ["BASE_ANGLE_HORIZONTAL_LEG_UPLIFT_PRYING", "NOT_EVALUATED"],
          ["ANCHOR_TENSION_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"],
          ["CONCRETE_UPLIFT_ANCHORAGE_LIMIT_STATES", "EXTERNAL_DESIGN_REQUIRED"],
        ] as const,
        visualization: { ...base.result.visualization, applied_force_s_t_l: { ...base.result.visualization.applied_force_s_t_l, longitudinal: force("20") } },
      },
    };
    vi.mocked(clientModule.previewColumnBaseWebAngle).mockResolvedValue(uplift);
    render(<ColumnBaseWebAngleWorkspace />);
    expect(await screen.findByText("Mode: Uplift/Tension")).toBeInTheDocument();
    expect(screen.getByText("Column Local Transfer").parentElement).toHaveTextContent("Signed axial action: +20 kip");
    expect(screen.getByText("Base-Angle System").parentElement).toHaveTextContent("Angle +: +10 kip (50%)");
    expect(screen.getByText("Base-Angle System").parentElement).toHaveTextContent("Angle -: +10 kip (50%)");
    expect(screen.getByText("Foundation Reaction").parentElement).toHaveTextContent("Axial reaction counted once: +20 kip");
    expect(screen.getByText(/column-end bearing NOT_REQUIRED.*body\/heel.*prying NOT_EVALUATED.*anchor tension.*concrete uplift/iu)).toBeInTheDocument();
  });

  it("switches between single positive/negative and double without duplicate state", async () => {
    render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("mock-column-base-viewer");
    fireEvent.change(screen.getByLabelText("Base-angle assembly"), { target: { value: "SINGLE_BASE_ANGLE" } });
    expect(screen.getByLabelText("Single-angle side")).not.toBeDisabled();
    fireEvent.change(screen.getByLabelText("Single-angle side"), { target: { value: "-T_C" } });
    await waitFor(() => { expect(clientModule.previewColumnBaseWebAngle).toHaveBeenLastCalledWith(expect.objectContaining({ assembly: "SINGLE_BASE_ANGLE", single_side: "-T_C" }), expect.any(AbortSignal)); });
    fireEvent.change(screen.getByLabelText("Base-angle assembly"), { target: { value: "DOUBLE_BASE_ANGLES" } });
    expect(screen.getByLabelText("Single-angle side")).toBeDisabled();
  });

  it("keeps sidebar and arrow edits in one request state and marks design stale", async () => {
    render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("mock-column-base-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(clientModule.evaluateColumnBaseWebAngle).toHaveBeenCalledTimes(1); });
    fireEvent.click(screen.getByRole("button", { name: "Edit FX" }));
    fireEvent.click(screen.getByRole("button", { name: "Edit FY" }));
    fireEvent.click(screen.getByRole("button", { name: "Edit FZ" }));
    fireEvent.click(screen.getByRole("button", { name: "Ignore MX" }));
    expect(screen.getByLabelText("Connection-plane shear")).toHaveValue("7");
    expect(screen.getByLabelText("Connection-normal shear")).toHaveValue("2");
    expect(screen.getByLabelText("Axial force (+ uplift / - compression)")).toHaveValue("25");
    expect(screen.getByText(/Design results are stale/iu)).toBeInTheDocument();
  });

  it("routes every editable geometry and hardware field through the one canonical request state", async () => {
    render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("mock-column-base-viewer");
    const decimalLabels = [
      "Column depth", "Flange width", "Web thickness", "Flange thickness", "Column display height",
      "Base S dimension", "Base T dimension", "Base depth",
      "Vertical-leg width", "Horizontal-leg width", "Angle thickness", "Angle length",
      "Bolt pitch", "Bolt gauge", "Group centroid height", "Bolt diameter", "Hole diameter",
      "Anchor pitch", "Anchor gauge", "Group centroid offset T",
      "Anchor diameter", "Anchor hole diameter", "Specified embedment", "Washer outside diameter", "Washer thickness",
      "Axial force (+ uplift / - compression)", "Connection-plane shear", "Connection-normal shear",
    ];
    for (const label of decimalLabels) {
      const field = screen.getByLabelText(label);
      fireEvent.change(field, { target: { value: (field as HTMLInputElement).value === "2" ? "2.1" : "2" } });
    }
    for (const label of ["Bolt rows", "Bolts per row", "Anchor rows", "Anchors per row"]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: "3" } });
    }
    fireEvent.click(screen.getByRole("button", { name: "Load 3.7A U.S." }));
    expect(screen.getByLabelText("Column depth")).toHaveValue("10");
    expect(clientModule.previewColumnBaseWebAngle).toHaveBeenCalled();
  });

  it("exports the exact backend handoff, runs design, and loads SI without frontend calculation", async () => {
    const createObjectURL = vi.fn(() => "blob:test");
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("mock-column-base-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Copy JSON" }));
    // eslint-disable-next-line @typescript-eslint/unbound-method -- jsdom clipboard mock is intentionally asserted as a detached spy
    await waitFor(() => { expect(navigator.clipboard.writeText).toHaveBeenCalledWith('{"schema_version":"3.7A-RC1"}'); });
    fireEvent.click(screen.getByRole("button", { name: "Download JSON" }));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(screen.getAllByText("Fail").length).toBeGreaterThan(0); });
    fireEvent.click(screen.getByRole("button", { name: "Load 3.7A SI" }));
    expect(screen.getByLabelText("Axial force (+ uplift / - compression)")).toHaveValue("-88.96443230521");
  });

  it("fails closed locally for nonpositive geometry and nonfinite forces while accepting signed axial values", async () => {
    render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("mock-column-base-viewer");
    fireEvent.change(screen.getByLabelText("Column depth"), { target: { value: "0" } });
    expect(screen.getAllByText(/dimensions must be positive/iu)).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Column depth"), { target: { value: "10" } });
    fireEvent.change(screen.getByLabelText("Axial force (+ uplift / - compression)"), { target: { value: "20" } });
    expect(screen.getByLabelText("mock-column-base-viewer")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Axial force (+ uplift / - compression)"), { target: { value: "0" } });
    expect(screen.queryByText(/nonnegative compression magnitude/iu)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Connection-plane shear"), { target: { value: "not-a-number" } });
    expect(screen.getAllByText(/force fields must be finite/iu)).toHaveLength(2);
  });

  it("reports design transport and unexpected response failures without accepting stale completion", async () => {
    vi.mocked(clientModule.evaluateColumnBaseWebAngle).mockRejectedValueOnce(new EvaluationTransportError("HTTP", 503, "design offline", null));
    const first = render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("mock-column-base-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(await screen.findByText("design offline")).toBeInTheDocument();
    first.unmount();

    vi.mocked(clientModule.evaluateColumnBaseWebAngle).mockRejectedValueOnce(new Error("unexpected"));
    const second = render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("mock-column-base-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(await screen.findByText("Unexpected column-base design-check failure.")).toBeInTheDocument();
    second.unmount();

    let resolveDesign: (value: ReturnType<typeof columnBaseDesignFixture>) => void = () => undefined;
    vi.mocked(clientModule.evaluateColumnBaseWebAngle).mockImplementationOnce(() => new Promise((resolve) => { resolveDesign = resolve; }));
    render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("mock-column-base-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    fireEvent.change(screen.getByLabelText("Connection-plane shear"), { target: { value: "6" } });
    resolveDesign(columnBaseDesignFixture());
    await act(async () => { await Promise.resolve(); });
    expect(screen.queryByText("Fail")).not.toBeInTheDocument();
  });

  it("ignores an intentional design abort after a preview-affecting edit", async () => {
    vi.mocked(clientModule.evaluateColumnBaseWebAngle).mockImplementationOnce((_request, signal) => new Promise((_resolve, reject) => { signal.addEventListener("abort", () => { reject(new DOMException("aborted", "AbortError")); }); }));
    render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("mock-column-base-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    fireEvent.change(screen.getByLabelText("Connection-plane shear"), { target: { value: "8" } });
    await act(async () => { await Promise.resolve(); });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("presents pending, no-valid, retained-invalid, and retained-request-failure preview states", async () => {
    vi.mocked(clientModule.previewColumnBaseWebAngle).mockImplementationOnce(() => new Promise(() => undefined));
    const pending = render(<ColumnBaseWebAngleWorkspace />);
    expect(screen.getAllByText("Preview updating")).toHaveLength(3);
    expect(screen.getByText("No current column-base result.")).toBeInTheDocument();
    pending.unmount();

    vi.mocked(clientModule.previewColumnBaseWebAngle).mockResolvedValueOnce(columnBasePreviewFixture("INVALID_GEOMETRY"));
    const noValid = render(<ColumnBaseWebAngleWorkspace />);
    expect(await screen.findAllByText("No valid backend preview")).toHaveLength(2);
    expect(screen.getByText("Canonical column-base model unavailable")).toBeInTheDocument();
    noValid.unmount();

    vi.mocked(clientModule.previewColumnBaseWebAngle).mockResolvedValueOnce(columnBasePreviewFixture()).mockResolvedValueOnce(columnBasePreviewFixture("INVALID_GEOMETRY")).mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "offline", null));
    render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("mock-column-base-viewer");
    fireEvent.change(screen.getByLabelText("Connection-plane shear"), { target: { value: "5" } });
    expect(await screen.findAllByText("Current geometry invalid — showing last valid preview")).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Connection-plane shear"), { target: { value: "6" } });
    expect(await screen.findAllByText("Preview unavailable — showing last valid preview")).toHaveLength(2);
  });

  it("renders the single-angle 100% branch and retained combined-only handoff limitation", async () => {
    const base = columnBasePreviewFixture();
    const firstGroup = base.result.anchor_groups[0];
    if (firstGroup === undefined) throw new Error("Controlled anchor group required.");
    const single = {
      ...base,
      result: {
        ...base.result,
        assembly: "SINGLE_BASE_ANGLE" as const,
        component_transfer: {
          ...base.result.component_transfer,
          axial_mode: "UPLIFT" as const,
          column_signed_axial_action: { value: "20", unit: "kip", canonical_value: "20", canonical_unit: "kip" },
          column_signed_material_direction: "+LW" as const,
          base_angle_system_signed_axial_action: { value: "20", unit: "kip", canonical_value: "20", canonical_unit: "kip" },
          base_angle_vertical_leg_signed_material_direction: "+CW" as const,
          positive_angle_signed_axial_action: null,
          negative_angle_signed_axial_action: null,
          single_angle_signed_axial_action: { value: "20", unit: "kip", canonical_value: "20", canonical_unit: "kip" },
          foundation_signed_axial_action: { value: "20", unit: "kip", canonical_value: "20", canonical_unit: "kip" },
        },
        anchor_groups: [{ ...firstGroup, branch_wrench: null }, ...base.result.anchor_groups.slice(1)],
      },
    };
    vi.mocked(clientModule.previewColumnBaseWebAngle).mockResolvedValueOnce(columnBasePreviewFixture()).mockResolvedValue(single);
    render(<ColumnBaseWebAngleWorkspace />);
    await screen.findByLabelText("mock-column-base-viewer");
    fireEvent.change(screen.getByLabelText("Base-angle assembly"), { target: { value: "SINGLE_BASE_ANGLE" } });
    expect(await screen.findByText("Single angle: +20 kip (100%)")).toBeInTheDocument();
    expect(screen.getByText("Base Angle").parentElement).toHaveTextContent("Single angle: +20 kip (100%)");
    expect(screen.getByText(/Branch allocation NOT_EVALUATED/iu)).toBeInTheDocument();
  });

  it("renders historical transfer variants and the successor zero-action fallback", async () => {
    const base = columnBasePreviewFixture();
    const force = (value: string) => ({
      value,
      unit: "kip",
      canonical_value: value,
      canonical_unit: "kip",
    });
    const historicalTransfer = {
      column_web_axial_demand: force("20"),
      column_web_fraction: "1",
      column_web_material_direction: "LW",
      angle_system_axial_demand: force("20"),
      angle_system_fraction: "1",
      angle_vertical_leg_material_direction: "CW",
      positive_angle_axial_demand: force("10"),
      negative_angle_axial_demand: force("10"),
      single_angle_axial_demand: null,
      branch_fraction: "0.5",
      foundation_axial_action: force("20"),
      component_design_demands_summed_for_equilibrium: false,
    } satisfies ColumnBaseHistoricalComponentTransfer;
    const historicalDouble = {
      ...base,
      orchestration_contract_version: "3.5C-RC1" as const,
      result: { ...base.result, component_transfer: historicalTransfer },
    };
    vi.mocked(clientModule.previewColumnBaseWebAngle).mockResolvedValue(historicalDouble);
    const double = render(<ColumnBaseWebAngleWorkspace />);
    expect((await screen.findByText("Base-Angle Pair")).parentElement).toHaveTextContent(
      "System axial design demand: 20 kip (100%)",
    );

    const historicalSingle = {
      ...historicalDouble,
      result: {
        ...historicalDouble.result,
        assembly: "SINGLE_BASE_ANGLE" as const,
        component_transfer: {
          ...historicalTransfer,
          positive_angle_axial_demand: null,
          negative_angle_axial_demand: null,
          single_angle_axial_demand: force("20"),
          branch_fraction: "1",
        },
      },
    };
    vi.mocked(clientModule.previewColumnBaseWebAngle).mockResolvedValue(historicalSingle);
    fireEvent.change(screen.getByLabelText("Base-angle assembly"), {
      target: { value: "SINGLE_BASE_ANGLE" },
    });
    expect((await screen.findByText("Base Angle")).parentElement).toHaveTextContent(
      "System axial design demand: 20 kip (100%)",
    );
    double.unmount();

    const signedHistoricalTransfer = {
      axial_mode: "COMPRESSION",
      column_web_signed_axial_action: force("-20"),
      column_web_design_magnitude: force("20"),
      column_web_fraction: "1",
      column_web_material_direction: "LW",
      column_web_signed_material_direction: "-LW",
      angle_system_signed_axial_action: force("-20"),
      angle_system_design_magnitude: force("20"),
      angle_system_fraction: "1",
      angle_vertical_leg_material_direction: "CW",
      angle_vertical_leg_signed_material_direction: "-CW",
      positive_angle_signed_axial_action: force("-10"),
      negative_angle_signed_axial_action: force("-10"),
      single_angle_signed_axial_action: null,
      branch_fraction: "0.5",
      foundation_signed_axial_action: force("-20"),
      component_design_demands_summed_for_equilibrium: false,
    } satisfies ColumnBaseSignedComponentTransfer;
    vi.mocked(clientModule.previewColumnBaseWebAngle).mockResolvedValue({
      ...base,
      orchestration_contract_version: "3.5C-R2-RC1",
      result: { ...base.result, component_transfer: signedHistoricalTransfer },
    });
    const signedCompression = render(<ColumnBaseWebAngleWorkspace />);
    expect((await screen.findByText("Column Web Local Transfer")).parentElement).toHaveTextContent("Mode: Compression");
    expect(screen.getByText("Base-Angle Pair").parentElement).toHaveTextContent("Angle +: -10 kip (50%)");
    signedCompression.unmount();

    vi.mocked(clientModule.previewColumnBaseWebAngle).mockResolvedValue({
      ...base,
      orchestration_contract_version: "3.5C-R2-RC1",
      result: {
        ...base.result,
        assembly: "SINGLE_BASE_ANGLE",
        component_transfer: {
          ...signedHistoricalTransfer,
          axial_mode: "UPLIFT",
          column_web_signed_axial_action: force("20"),
          column_web_signed_material_direction: "+LW",
          angle_system_signed_axial_action: force("20"),
          angle_vertical_leg_signed_material_direction: "+CW",
          positive_angle_signed_axial_action: null,
          negative_angle_signed_axial_action: null,
          single_angle_signed_axial_action: force("20"),
          branch_fraction: "1",
          foundation_signed_axial_action: force("20"),
        },
      },
    });
    const signedUplift = render(<ColumnBaseWebAngleWorkspace />);
    expect((await screen.findByText("Mode: Uplift/Tension")).parentElement).toHaveTextContent("Signed axial action: +20 kip");
    fireEvent.change(screen.getByLabelText("Base-angle assembly"), { target: { value: "SINGLE_BASE_ANGLE" } });
    expect(await screen.findByText("Base Angle")).toBeInTheDocument();
    expect(screen.getByText("Single angle: +20 kip (100%)")).toBeInTheDocument();
    signedUplift.unmount();

    vi.mocked(clientModule.previewColumnBaseWebAngle).mockResolvedValue({
      ...base,
      orchestration_contract_version: "3.5C-R2-RC1",
      result: {
        ...base.result,
        component_transfer: {
          ...signedHistoricalTransfer,
          axial_mode: "ZERO",
          column_web_signed_axial_action: force("0"),
          column_web_design_magnitude: force("0"),
          column_web_signed_material_direction: "LW",
          angle_system_signed_axial_action: force("0"),
          angle_system_design_magnitude: force("0"),
          angle_vertical_leg_signed_material_direction: "CW",
          positive_angle_signed_axial_action: force("0"),
          negative_angle_signed_axial_action: force("0"),
          foundation_signed_axial_action: force("0"),
        },
      },
    });
    const signedZero = render(<ColumnBaseWebAngleWorkspace />);
    expect(await screen.findByText("Mode: Zero")).toBeInTheDocument();
    signedZero.unmount();

    const transfer = base.result.component_transfer;
    if (!("axial_mode" in transfer)) throw new Error("Controlled R2 fixture required.");
    const fallbackZero = {
      ...base,
      orchestration_contract_version: undefined,
      result: {
        ...base.result,
        component_transfer: {
          ...transfer,
          axial_mode: "ZERO" as const,
          column_signed_axial_action: force("0"),
          column_design_magnitude: force("0"),
          column_signed_material_direction: "LW" as const,
          base_angle_system_signed_axial_action: force("0"),
          base_angle_system_design_magnitude: force("0"),
          base_angle_vertical_leg_signed_material_direction: "CW" as const,
          positive_angle_signed_axial_action: force("0"),
          negative_angle_signed_axial_action: force("0"),
          foundation_signed_axial_action: force("0"),
        },
      },
    } as unknown as ColumnBasePreviewResponse;
    vi.mocked(clientModule.previewColumnBaseWebAngle).mockResolvedValue(fallbackZero);
    render(<ColumnBaseWebAngleWorkspace />);
    expect(await screen.findByText("Mode: Zero")).toBeInTheDocument();
    expect(screen.getByLabelText("mock-column-base-viewer")).toBeInTheDocument();
  });
});
