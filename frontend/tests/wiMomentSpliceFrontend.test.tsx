import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  EvaluationTransportError,
  evaluateWIMomentSplice,
  previewWIMomentSplice,
  WI_MOMENT_SPLICE_DESIGN_PATH,
  WI_MOMENT_SPLICE_PREVIEW_PATH,
} from "../src/api/client";
import * as clientModule from "../src/api/client";
import { loadWIMomentSpliceBenchmark } from "../src/fixtures/wiMomentSpliceBenchmarks";
import { buildWIMomentSpliceSceneModel } from "../src/visualization/wiMomentSpliceSceneModel";
import { MomentConnectionsWorkspace } from "../src/workspace/MomentConnectionsWorkspace";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import { WIMomentSpliceWorkspace } from "../src/workspace/WIMomentSpliceWorkspace";
import { useWIMomentSplicePreview } from "../src/workspace/wiMomentSpliceWorkflow";
import {
  wiMomentSpliceDesignFixture,
  wiMomentSplicePreviewFixture,
  wiMomentSpliceVisualizationFixture,
} from "./wiMomentSpliceFixtures";

vi.mock("../src/visualization/VisualizationPanel", () => ({
  VisualizationPanel: ({ title, model, onAppliedActionValueChange, onSelect }: {
    title: string;
    model: { boxes: readonly unknown[]; cylinders: readonly unknown[]; materialAxes: readonly unknown[]; appliedArrows: readonly unknown[] };
    onAppliedActionValueChange?: (component: string, value: string) => void;
    onSelect?: (selection: { kind: "MEMBER"; id: string }) => void;
  }) => <div aria-label="mock-wi-moment-splice-viewer">
    <h3>{title}</h3><span>{model.boxes.length} boxes</span><span>{model.cylinders.length} cylinders</span>
    <span>{model.materialAxes.length} material axes</span><span>{model.appliedArrows.length} action arrows</span>
    <button type="button" onClick={() => { onAppliedActionValueChange?.("FX", "30"); }}>Edit axial</button>
    <button type="button" onClick={() => { onAppliedActionValueChange?.("FZ", "-15"); }}>Edit shear</button>
    <button type="button" onClick={() => { onAppliedActionValueChange?.("MY", "125"); }}>Edit moment</button>
    <button type="button" onClick={() => { onAppliedActionValueChange?.("FY", "9"); }}>Ignore unsupported action</button>
    <button type="button" onClick={() => { onSelect?.({ kind: "MEMBER", id: "BEAM_A" }); }}>Select beam</button>
  </div>,
}));

const response = (body: unknown, status = 200): Response => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("Stage 4.1A benchmark and canonical scene", () => {
  it("loads cloned exact U.S./SI contracts with only the authorized W/I major-axis topology", () => {
    const us = loadWIMomentSpliceBenchmark("US_CUSTOMARY");
    const si = loadWIMomentSpliceBenchmark("SI");
    expect(us).toMatchObject({ orchestration_contract_version: "4.1A-RC1", profile_family: "WIDE_FLANGE_I", beams_locked_identical: true, beam_end_gap: { value: "0.5", unit: "in" } });
    expect(us.flange_geometry).toMatchObject({ outer_plate_count_per_flange: 1, inner_strip_count_per_flange: 2, locked_top_bottom_identical: true, locked_inner_symmetric: true });
    expect(si.actions.major_moment_t).toEqual({ value: "11298.48290276167", unit: "kN-mm" });
    expect(si.beam_end_gap).toEqual({ value: "12.7", unit: "mm" });
    us.beam.depth.value = "99";
    expect(loadWIMomentSpliceBenchmark("US_CUSTOMARY").beam.depth.value).toBe("10");
  });

  it("renders two physical beams, two web plates, six flange plates, 24 bolt/hole paths, all material regions, and signed force/moment arrows", () => {
    const model = buildWIMomentSpliceSceneModel(wiMomentSpliceVisualizationFixture());
    expect(model.boxes).toHaveLength(14);
    expect(model.boxes.filter((item) => item.id.includes("FLANGE_SPLICE_PLATE"))).toHaveLength(6);
    expect(model.cylinders.filter((item) => item.kind === "BOLT")).toHaveLength(24);
    expect(model.cylinders.filter((item) => item.kind === "HOLE")).toHaveLength(24);
    expect(model.materialAxes).toHaveLength(14);
    expect(model.appliedArrows.map((item) => item.component)).toEqual(["FX", "FZ", "MY"]);
    expect(model.appliedArrows.map((item) => [item.axis.x, item.axis.y, item.axis.z])).toEqual([[1, 0, 0], [-0, -0, -1], [0, 1, 0]]);
    expect(model.boundsRadius).toBeGreaterThan(10);
  });

  it("reverses signed actions, suppresses zeros, identifies SI, and safely presents an unbound material region", () => {
    const value = structuredClone(wiMomentSpliceVisualizationFixture("SI"));
    value.applied_force_l_v_t.l.value = "-1";
    value.applied_force_l_v_t.v.value = "2";
    value.applied_force_l_v_t.t.value = "-3";
    value.applied_moment_l_v_t.t.value = "-4";
    const first = value.material_regions[0];
    if (first === undefined) throw new Error("Controlled material region required.");
    const modified = { ...value, material_regions: [{ ...first, component_id: "UNKNOWN", region_id: "UNKNOWN" }, ...value.material_regions.slice(1)] };
    let model = buildWIMomentSpliceSceneModel(modified);
    expect(model.unitSystem).toBe("SI");
    expect(model.appliedArrows.map((item) => item.component)).toEqual(["FX", "FZ", "FY", "MY"]);
    expect(model.appliedArrows.map((item) => [item.axis.x, item.axis.y, item.axis.z])).toEqual([[-1, -0, -0], [0, 0, 1], [-0, -1, -0], [0, -1, 0]]);
    expect(model.appliedArrows[0]).toMatchObject({ axialLoadingSense: "COMPRESSION" });
    expect(model.materialAxes[0]).toMatchObject({ componentId: "UNKNOWN", origin: { x: 0, y: 0, z: 0 }, presentation: null });
    value.applied_force_l_v_t.l.value = "0"; value.applied_force_l_v_t.v.value = "0"; value.applied_force_l_v_t.t.value = "0"; value.applied_moment_l_v_t.t.value = "0";
    model = buildWIMomentSpliceSceneModel(modified);
    expect(model.appliedArrows).toEqual([]);
  });
});

describe("Stage 4.1A strict transport", () => {
  beforeEach(() => { vi.stubGlobal("fetch", vi.fn()); });
  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it("posts only the two same-origin routes and accepts strict preview/design responses", async () => {
    const request = loadWIMomentSpliceBenchmark("US_CUSTOMARY");
    const signal = new AbortController().signal;
    vi.mocked(fetch).mockResolvedValueOnce(response(wiMomentSplicePreviewFixture())).mockResolvedValueOnce(response(wiMomentSpliceDesignFixture()));
    await expect(previewWIMomentSplice(request, signal)).resolves.toMatchObject({ resistance_evaluated: false, ordinary_pass_allowed: false });
    await expect(evaluateWIMomentSplice(request, signal)).resolves.toMatchObject({ ordinary_pass_allowed: false });
    expect(fetch).toHaveBeenNthCalledWith(1, WI_MOMENT_SPLICE_PREVIEW_PATH, expect.objectContaining({ method: "POST", credentials: "same-origin", signal }));
    expect(fetch).toHaveBeenNthCalledWith(2, WI_MOMENT_SPLICE_DESIGN_PATH, expect.objectContaining({ method: "POST" }));
  });

  it("rejects every malformed discriminator and classifies validation, HTTP, network, and abort failures", async () => {
    const request = loadWIMomentSpliceBenchmark("US_CUSTOMARY");
    const signal = new AbortController().signal;
    for (const body of [null, {}, { ...wiMomentSplicePreviewFixture(), api_transport_schema_version: "bad" }, { ...wiMomentSplicePreviewFixture(), orchestration_contract_version: "bad" }, { ...wiMomentSplicePreviewFixture(), preview_schema_version: "bad" }, { ...wiMomentSplicePreviewFixture(), resistance_evaluated: true }, { ...wiMomentSplicePreviewFixture(), ordinary_pass_allowed: true }, { ...wiMomentSplicePreviewFixture(), engineering_fingerprint: null }, { ...wiMomentSplicePreviewFixture(), result: null }]) {
      vi.mocked(fetch).mockResolvedValueOnce(response(body));
      await expect(previewWIMomentSplice(request, signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    }
    for (const body of [null, {}, { ...wiMomentSpliceDesignFixture(), api_transport_schema_version: "bad" }, { ...wiMomentSpliceDesignFixture(), orchestration_contract_version: "bad" }, { ...wiMomentSpliceDesignFixture(), ordinary_pass_allowed: true }, { ...wiMomentSpliceDesignFixture(), failed_check_ids: null }, { ...wiMomentSpliceDesignFixture(), unavailable_check_ids: null }, { ...wiMomentSpliceDesignFixture(), result_fingerprint: null }, { ...wiMomentSpliceDesignFixture(), result: null }]) {
      vi.mocked(fetch).mockResolvedValueOnce(response(body));
      await expect(evaluateWIMomentSplice(request, signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    }
    vi.mocked(fetch).mockResolvedValueOnce(response({ detail: "invalid" }, 422));
    await expect(previewWIMomentSplice(request, signal)).rejects.toMatchObject({ kind: "VALIDATION", status: 422 });
    vi.mocked(fetch).mockResolvedValueOnce(response({ detail: "failed" }, 503));
    await expect(evaluateWIMomentSplice(request, signal)).rejects.toMatchObject({ kind: "HTTP", status: 503 });
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("offline"));
    await expect(previewWIMomentSplice(request, signal)).rejects.toMatchObject({ kind: "NETWORK" });
    const abort = new DOMException("aborted", "AbortError");
    vi.mocked(fetch).mockRejectedValueOnce(abort);
    await expect(evaluateWIMomentSplice(request, signal)).rejects.toBe(abort);
  });
});

describe("Stage 4.1A live preview and workspace", () => {
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

  it("covers current, last-valid invalid/error, retry, local-invalid, no-preview, and abort states", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(clientModule, "previewWIMomentSplice").mockResolvedValueOnce(wiMomentSplicePreviewFixture());
    const request = loadWIMomentSpliceBenchmark("US_CUSTOMARY");
    let revision = 0; let validationMessage: string | null = null;
    const hook = renderHook(() => useWIMomentSplicePreview({ request, revision, immediate: revision === 0, validationMessage }));
    await act(async () => { await Promise.resolve(); }); expect(hook.result.current.state).toBe("CURRENT_VALID");
    spy.mockResolvedValueOnce(wiMomentSplicePreviewFixture("INVALID_GEOMETRY")); revision = 1; hook.rerender();
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); }); expect(hook.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    spy.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "offline", null)); revision = 2; hook.rerender();
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); }); expect(hook.result.current.state).toBe("PREVIEW_FAILED_SHOWING_LAST_VALID");
    spy.mockResolvedValueOnce(wiMomentSplicePreviewFixture()); act(() => { hook.result.current.retry(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); }); expect(hook.result.current.state).toBe("CURRENT_VALID");
    validationMessage = "locally invalid"; revision = 3; hook.rerender(); expect(hook.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    hook.unmount();

    vi.useRealTimers();
    spy.mockRejectedValueOnce(new Error("unexpected"));
    const failed = renderHook(() => useWIMomentSplicePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(failed.result.current.state).toBe("NO_VALID_PREVIEW"); }); expect(failed.result.current.error?.message).toContain("Unexpected W/I"); failed.unmount();
    spy.mockRejectedValueOnce(new EvaluationTransportError("VALIDATION", 422, "invalid", null));
    const invalid = renderHook(() => useWIMomentSplicePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(invalid.result.current.state).toBe("NO_VALID_PREVIEW"); }); invalid.unmount();
    spy.mockRejectedValueOnce(new DOMException("aborted", "AbortError"));
    const aborted = renderHook(() => useWIMomentSplicePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(aborted.result.current.state).toBe("PREVIEW_PENDING"); }); aborted.unmount();
    spy.mockResolvedValueOnce({ ...wiMomentSplicePreviewFixture("INVALID_GEOMETRY"), geometry_invalid_reasons: [] });
    const empty = renderHook(() => useWIMomentSplicePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(empty.result.current.state).toBe("NO_VALID_PREVIEW"); }); expect(empty.result.current.invalidDetail).toBeNull();
  });

  it("registers the Moment category product and renders the complete current preview trace", async () => {
    vi.spyOn(clientModule, "previewWIMomentSplice").mockResolvedValue(wiMomentSplicePreviewFixture());
    render(<MomentConnectionsWorkspace />);
    const option = screen.getByRole("option", { name: "W/I Beam Moment Splice" });
    expect(option.closest("optgroup")?.label).toBe("Beam moment connections");
    fireEvent.change(screen.getByLabelText("Connection type"), { target: { value: "WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE" } });
    expect(await screen.findByRole("heading", { name: "Moment connection — W/I beam moment splice" })).toBeInTheDocument();
    expect(screen.getByLabelText("Beam-end gap")).toHaveValue("0.5");
    expect(screen.getByLabelText("Major-axis moment M_T")).toHaveValue("100");
    expect(screen.queryByLabelText(/minor shear|torsion/iu)).not.toBeInTheDocument();
    expect(await screen.findByLabelText("mock-wi-moment-splice-viewer")).toHaveTextContent("14 boxes");
    expect(screen.getByLabelText("mock-wi-moment-splice-viewer")).toHaveTextContent("48 cylinders");
    expect(screen.getByText("Slice 5 — Top Flange")).toBeInTheDocument();
    expect(screen.getByText("Physical flange bolt planes").parentElement).toHaveTextContent("12");
    expect(screen.getByText(/Rational engineering method/iu)).toBeInTheDocument();
  });

  it("keeps one action state across arrow/sidebar edits, marks design stale, loads SI, validates topology, and runs design explicitly", async () => {
    vi.spyOn(clientModule, "previewWIMomentSplice").mockResolvedValue(wiMomentSplicePreviewFixture());
    const designSpy = vi.spyOn(clientModule, "evaluateWIMomentSplice").mockResolvedValue(wiMomentSpliceDesignFixture());
    render(<WIMomentSpliceWorkspace />); await screen.findByLabelText("mock-wi-moment-splice-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(designSpy).toHaveBeenCalledTimes(1); });
    expect(await screen.findByText(/TOP_OUTER_PLATE_BODY \/ 0\.75/iu)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit axial" })); expect(screen.getByLabelText("Axial force P_L")).toHaveValue("30");
    expect(screen.getByText(/Design results are stale/iu)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit shear" })); expect(screen.getByLabelText("Major shear V_V")).toHaveValue("-15");
    fireEvent.click(screen.getByRole("button", { name: "Edit moment" })); expect(screen.getByLabelText("Major-axis moment M_T")).toHaveValue("125");
    fireEvent.click(screen.getByRole("button", { name: "Ignore unsupported action" })); expect(screen.queryByLabelText("Minor shear")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Select beam" }));
    fireEvent.click(screen.getByRole("button", { name: "Load 4.1A SI" })); expect(screen.getByLabelText("Beam-end gap")).toHaveValue("12.7");
    fireEvent.click(screen.getByRole("button", { name: "Load 4.1A U.S." })); expect(screen.getByLabelText("Beam-end gap")).toHaveValue("0.5");
    fireEvent.change(screen.getByLabelText("Beam-end gap"), { target: { value: "0" } }); expect(screen.getAllByText(/positive decimals/iu)).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Beam-end gap"), { target: { value: "0.5" } });
    fireEvent.change(screen.getByLabelText("Flange bolts per line"), { target: { value: "4" } }); expect(screen.getAllByText(/Stage 4\.1A topology/iu)).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Flange bolts per line"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Major-axis moment M_T"), { target: { value: "not-finite" } }); expect(screen.getAllByText(/finite signed decimals/iu)).toHaveLength(2);
  });

  it("binds every authorized geometry, fastener, action, and bolt-count field to the single request state", async () => {
    vi.spyOn(clientModule, "previewWIMomentSplice").mockResolvedValue(wiMomentSplicePreviewFixture());
    render(<WIMomentSpliceWorkspace />); await screen.findByLabelText("mock-wi-moment-splice-viewer");
    const decimalLabels = [
      "Beam depth", "Flange width", "Web thickness", "Flange thickness", "Display length each side", "Beam-end gap",
      "Axial force P_L", "Major shear V_V", "Major-axis moment M_T",
      "Web plate length", "Web plate height", "Web plate thickness", "Web vertical pitch", "Web longitudinal gauge", "Web group-centroid distance", "Web bolt diameter", "Web hole diameter",
      "Flange plate length", "Flange plate thickness", "Inner strip width", "Flange longitudinal pitch", "Flange group-centroid distance", "Flange bolt diameter", "Flange hole diameter",
    ];
    for (const label of decimalLabels) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: "1.25" } });
      expect(screen.getByLabelText(label)).toHaveValue("1.25");
    }
    for (const label of ["Web rows", "Web bolts per row", "Flange bolts per line"]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: "3" } });
      expect(screen.getByLabelText(label)).toHaveValue(3);
    }
  });

  it("suppresses superseded design completions and exposes pending, typed failure, last-valid, and non-exact diagnostic branches", async () => {
    const previewSpy = vi.spyOn(clientModule, "previewWIMomentSplice").mockResolvedValue(wiMomentSplicePreviewFixture());
    let resolveDesign: ((value: ReturnType<typeof wiMomentSpliceDesignFixture>) => void) | undefined;
    const designSpy = vi.spyOn(clientModule, "evaluateWIMomentSplice").mockImplementationOnce(() => new Promise((resolve) => { resolveDesign = resolve; }));
    render(<WIMomentSpliceWorkspace />); await screen.findByLabelText("mock-wi-moment-splice-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(screen.getByRole("button", { name: "Running design check…" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Load 4.1A SI" }));
    resolveDesign?.(wiMomentSpliceDesignFixture());
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText("Run Design Check", { selector: "dd" })).toBeInTheDocument();

    const exact = wiMomentSplicePreviewFixture();
    const nonExact = { ...exact, result: { ...exact.result, top_flange: { ...exact.result.top_flange, exact_force_equilibrium: false }, equilibrium: { whole_joint_exact: false, beam_a_b_equal_opposite: false } } };
    let rejectSuperseded: ((reason: Error) => void) | undefined;
    designSpy.mockImplementationOnce(() => new Promise((_, reject) => { rejectSuperseded = reject; }));
    previewSpy.mockResolvedValueOnce(nonExact);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    fireEvent.click(screen.getByRole("button", { name: "Load 4.1A U.S." }));
    rejectSuperseded?.(new Error("superseded design failure"));
    await act(async () => { await Promise.resolve(); });
    expect((await screen.findAllByText("No")).length).toBeGreaterThanOrEqual(3);

    previewSpy.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "preview offline", null));
    fireEvent.change(screen.getByLabelText("Beam depth"), { target: { value: "11" } });
    await waitFor(() => { expect(screen.getAllByText(/Preview unavailable — showing last valid model/iu).length).toBeGreaterThanOrEqual(2); }, { timeout: PREVIEW_DEBOUNCE_MS + 1000 });
    expect(screen.getByRole("alert")).toHaveTextContent("preview offline");
    previewSpy.mockResolvedValueOnce(wiMomentSplicePreviewFixture());
    fireEvent.click(screen.getByRole("button", { name: "Retry preview" }));
    await waitFor(() => { expect(screen.getByText("Current backend preview", { selector: "strong" })).toBeInTheDocument(); });

    designSpy.mockRejectedValueOnce(new EvaluationTransportError("HTTP", 503, "design offline", null));
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("design offline");
  });

  it("shows server-invalid geometry, last-valid preview failure/retry, and design failures without fabricating results", async () => {
    const previewSpy = vi.spyOn(clientModule, "previewWIMomentSplice").mockResolvedValueOnce(wiMomentSplicePreviewFixture("INVALID_GEOMETRY"));
    const designSpy = vi.spyOn(clientModule, "evaluateWIMomentSplice");
    const invalid = render(<WIMomentSpliceWorkspace />);
    expect((await screen.findAllByText(/No valid backend preview/iu)).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    invalid.unmount();

    previewSpy.mockResolvedValueOnce(wiMomentSplicePreviewFixture());
    designSpy.mockRejectedValueOnce(new Error("unexpected design failure"));
    render(<WIMomentSpliceWorkspace />); await screen.findByLabelText("mock-wi-moment-splice-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unexpected W/I moment-splice design failure");
  });
});
