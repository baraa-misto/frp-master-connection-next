import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CHANNEL_MOMENT_SPLICE_DESIGN_PATH, CHANNEL_MOMENT_SPLICE_PREVIEW_PATH, EvaluationTransportError, evaluateChannelMomentSplice, previewChannelMomentSplice } from "../src/api/client";
import * as clientModule from "../src/api/client";
import { loadChannelMomentSpliceBenchmark } from "../src/fixtures/channelMomentSpliceBenchmarks";
import { buildChannelMomentSpliceSceneModel } from "../src/visualization/channelMomentSpliceSceneModel";
import { ChannelMomentSpliceWorkspace } from "../src/workspace/ChannelMomentSpliceWorkspace";
import { MomentConnectionsWorkspace } from "../src/workspace/MomentConnectionsWorkspace";
import { useChannelMomentSplicePreview } from "../src/workspace/channelMomentSpliceWorkflow";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import { channelMomentSpliceDesignFixture, channelMomentSplicePreviewFixture, channelMomentSpliceVisualizationFixture } from "./channelMomentSpliceFixtures";

vi.mock("../src/visualization/VisualizationPanel", () => ({
  VisualizationPanel: ({ title, model, onAppliedActionValueChange, onSelect }: {
    title: string;
    model: { boxes: readonly unknown[]; cylinders: readonly unknown[]; materialAxes: readonly unknown[]; appliedArrows: readonly unknown[]; markers: readonly unknown[] };
    onAppliedActionValueChange?: (component: string, value: string) => void;
    onSelect?: (selection: { kind: "MEMBER"; id: string }) => void;
  }) => <div aria-label="mock-channel-moment-splice-viewer"><h3>{title}</h3><span>{model.boxes.length} boxes</span><span>{model.cylinders.length} cylinders</span><span>{model.materialAxes.length} material axes</span><span>{model.appliedArrows.length} action arrows</span><span>{model.markers.length} markers</span><button type="button" onClick={() => { onAppliedActionValueChange?.("FX", "30"); }}>Edit Channel axial</button><button type="button" onClick={() => { onAppliedActionValueChange?.("FZ", "-15"); }}>Edit Channel shear</button><button type="button" onClick={() => { onAppliedActionValueChange?.("MY", "125"); }}>Edit Channel moment</button><button type="button" onClick={() => { onAppliedActionValueChange?.("MX", "999"); }}>Ignore generated torsion edit</button><button type="button" onClick={() => { onSelect?.({ kind: "MEMBER", id: "OPENING_WEB_SPLICE_PLATE" }); }}>Select opening plate</button></div>,
}));

const response = (body: unknown, status = 200): Response => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("Stage 4.1B benchmark and canonical scene", () => {
  it("loads independent exact U.S./SI Channel contracts and keeps source-pending fasteners", () => {
    const us = loadChannelMomentSpliceBenchmark("US_CUSTOMARY");
    const si = loadChannelMomentSpliceBenchmark("SI");
    expect(us).toMatchObject({ orchestration_contract_version: "4.1B-RC1", beams_locked_identical: true, beams_same_orientation: true, opening_direction: "+T_CH", beam: { profile_family: "CHANNEL", equal_flange: true, lipped: false, back_to_back: false } });
    expect(us.web_splice_plate).toMatchObject({ count: 2, locked_identical: true });
    expect(us.flange_geometry).toMatchObject({ outer_plate_count_per_flange: 1, inner_plate_count_per_flange: 1, locked_top_bottom_identical: true });
    expect(si.actions.major_moment_t).toEqual({ value: "11298.48290276167", unit: "kN-mm" });
    expect(si.beam.depth).toEqual({ value: "203.2", unit: "mm" });
    us.beam.depth.value = "99";
    expect(loadChannelMomentSpliceBenchmark("US_CUSTOMARY").beam.depth.value).toBe("8");
  });

  it("renders both Channels, all six plates, 24 physical bolt/hole paths, material regions, references, and signed actions", () => {
    const model = buildChannelMomentSpliceSceneModel(channelMomentSpliceVisualizationFixture());
    expect(model.boxes).toHaveLength(12);
    expect(model.boxes.filter((item) => item.id.includes("SPLICE_PLATE"))).toHaveLength(6);
    expect(model.cylinders.filter((item) => item.kind === "BOLT")).toHaveLength(24);
    expect(model.cylinders.filter((item) => item.kind === "HOLE")).toHaveLength(24);
    expect(model.materialAxes).toHaveLength(12);
    expect(model.markers.map((item) => item.id)).toEqual(["CHANNEL_MOMENT_SPLICE_CENTROID", "CHANNEL_MOMENT_SPLICE_SHEAR_CENTER"]);
    expect(model.appliedArrows.map((item) => item.component)).toEqual(["FX", "FZ", "MY", "MX"]);
    expect(model.appliedArrows.map((item) => [item.axis.x, item.axis.y, item.axis.z])).toEqual([[1, 0, 0], [-0, -0, -1], [0, 1, 0], [-1, -0, -0]]);
    expect(model.boundsRadius).toBeGreaterThan(10);
  });

  it("reverses every signed arrow, suppresses zeros, identifies SI, and safely presents an unbound material region", () => {
    const value = structuredClone(channelMomentSpliceVisualizationFixture("SI"));
    value.applied_force_l_v_t.l.value = "-1";
    value.applied_force_l_v_t.v.value = "2";
    value.applied_moment_l_v_t.t.value = "-3";
    value.generated_centroidal_torsion.value = "4";
    const first = value.material_regions[0];
    if (first === undefined) throw new Error("Controlled material region required.");
    const modified = { ...value, material_regions: [{ ...first, component_id: "UNKNOWN", region_id: "UNKNOWN" }, ...value.material_regions.slice(1)] };
    let model = buildChannelMomentSpliceSceneModel(modified);
    expect(model.unitSystem).toBe("SI");
    expect(model.appliedArrows.map((item) => [item.component, item.axis.x, item.axis.y, item.axis.z])).toEqual([["FX", -1, -0, -0], ["FZ", 0, 0, 1], ["MY", -0, -1, -0], ["MX", 1, 0, 0]]);
    expect(model.appliedArrows[0]).toMatchObject({ axialLoadingSense: "COMPRESSION" });
    expect(model.materialAxes[0]).toMatchObject({ componentId: "UNKNOWN", origin: { x: 0, y: 0, z: 0 }, presentation: null });
    value.applied_force_l_v_t.l.value = "0"; value.applied_force_l_v_t.v.value = "0"; value.applied_moment_l_v_t.t.value = "0"; value.generated_centroidal_torsion.value = "0";
    model = buildChannelMomentSpliceSceneModel(modified);
    expect(model.appliedArrows).toEqual([]);
  });
});

describe("Stage 4.1B strict transport", () => {
  beforeEach(() => { vi.stubGlobal("fetch", vi.fn()); });
  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it("posts only the two same-origin routes and accepts strict preview/design responses", async () => {
    const request = loadChannelMomentSpliceBenchmark("US_CUSTOMARY");
    const signal = new AbortController().signal;
    vi.mocked(fetch).mockResolvedValueOnce(response(channelMomentSplicePreviewFixture())).mockResolvedValueOnce(response(channelMomentSpliceDesignFixture()));
    await expect(previewChannelMomentSplice(request, signal)).resolves.toMatchObject({ resistance_evaluated: false, ordinary_pass_allowed: false });
    await expect(evaluateChannelMomentSplice(request, signal)).resolves.toMatchObject({ ordinary_pass_allowed: false });
    expect(fetch).toHaveBeenNthCalledWith(1, CHANNEL_MOMENT_SPLICE_PREVIEW_PATH, expect.objectContaining({ method: "POST", credentials: "same-origin", signal }));
    expect(fetch).toHaveBeenNthCalledWith(2, CHANNEL_MOMENT_SPLICE_DESIGN_PATH, expect.objectContaining({ method: "POST" }));
  });

  it("rejects malformed discriminators and classifies validation, HTTP, network, and abort failures", async () => {
    const request = loadChannelMomentSpliceBenchmark("US_CUSTOMARY");
    const signal = new AbortController().signal;
    for (const body of [null, {}, { ...channelMomentSplicePreviewFixture(), api_transport_schema_version: "bad" }, { ...channelMomentSplicePreviewFixture(), orchestration_contract_version: "bad" }, { ...channelMomentSplicePreviewFixture(), preview_schema_version: "bad" }, { ...channelMomentSplicePreviewFixture(), resistance_evaluated: true }, { ...channelMomentSplicePreviewFixture(), ordinary_pass_allowed: true }, { ...channelMomentSplicePreviewFixture(), engineering_fingerprint: null }, { ...channelMomentSplicePreviewFixture(), result: null }]) {
      vi.mocked(fetch).mockResolvedValueOnce(response(body));
      await expect(previewChannelMomentSplice(request, signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    }
    for (const body of [null, {}, { ...channelMomentSpliceDesignFixture(), api_transport_schema_version: "bad" }, { ...channelMomentSpliceDesignFixture(), orchestration_contract_version: "bad" }, { ...channelMomentSpliceDesignFixture(), ordinary_pass_allowed: true }, { ...channelMomentSpliceDesignFixture(), failed_check_ids: null }, { ...channelMomentSpliceDesignFixture(), unavailable_check_ids: null }, { ...channelMomentSpliceDesignFixture(), result_fingerprint: null }, { ...channelMomentSpliceDesignFixture(), result: null }]) {
      vi.mocked(fetch).mockResolvedValueOnce(response(body));
      await expect(evaluateChannelMomentSplice(request, signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    }
    vi.mocked(fetch).mockResolvedValueOnce(response({ detail: "invalid" }, 422));
    await expect(previewChannelMomentSplice(request, signal)).rejects.toMatchObject({ kind: "VALIDATION", status: 422 });
    vi.mocked(fetch).mockResolvedValueOnce(response({ detail: "failed" }, 503));
    await expect(evaluateChannelMomentSplice(request, signal)).rejects.toMatchObject({ kind: "HTTP", status: 503 });
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("offline"));
    await expect(previewChannelMomentSplice(request, signal)).rejects.toMatchObject({ kind: "NETWORK" });
    const abort = new DOMException("aborted", "AbortError");
    vi.mocked(fetch).mockRejectedValueOnce(abort);
    await expect(evaluateChannelMomentSplice(request, signal)).rejects.toBe(abort);
  });
});

describe("Stage 4.1B live preview and workspace", () => {
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

  it("covers current, last-valid invalid/error, retry, local-invalid, no-preview, and abort states", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(clientModule, "previewChannelMomentSplice").mockResolvedValueOnce(channelMomentSplicePreviewFixture());
    const request = loadChannelMomentSpliceBenchmark("US_CUSTOMARY");
    let revision = 0; let validationMessage: string | null = null;
    const hook = renderHook(() => useChannelMomentSplicePreview({ request, revision, immediate: revision === 0, validationMessage }));
    await act(async () => { await Promise.resolve(); }); expect(hook.result.current.state).toBe("CURRENT_VALID");
    spy.mockResolvedValueOnce(channelMomentSplicePreviewFixture("INVALID_GEOMETRY")); revision = 1; hook.rerender();
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); }); expect(hook.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    spy.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "offline", null)); revision = 2; hook.rerender();
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); }); expect(hook.result.current.state).toBe("PREVIEW_FAILED_SHOWING_LAST_VALID");
    spy.mockResolvedValueOnce(channelMomentSplicePreviewFixture()); act(() => { hook.result.current.retry(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); }); expect(hook.result.current.state).toBe("CURRENT_VALID");
    validationMessage = "locally invalid"; revision = 3; hook.rerender(); expect(hook.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID"); hook.unmount();

    vi.useRealTimers();
    spy.mockRejectedValueOnce(new Error("unexpected"));
    const failed = renderHook(() => useChannelMomentSplicePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(failed.result.current.state).toBe("NO_VALID_PREVIEW"); }); expect(failed.result.current.error?.message).toContain("Unexpected Channel"); failed.unmount();
    spy.mockRejectedValueOnce(new EvaluationTransportError("VALIDATION", 422, "invalid", null));
    const invalid = renderHook(() => useChannelMomentSplicePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(invalid.result.current.state).toBe("NO_VALID_PREVIEW"); }); invalid.unmount();
    spy.mockRejectedValueOnce(new DOMException("aborted", "AbortError"));
    const aborted = renderHook(() => useChannelMomentSplicePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(aborted.result.current.state).toBe("PREVIEW_PENDING"); }); aborted.unmount();
    spy.mockResolvedValueOnce({ ...channelMomentSplicePreviewFixture("INVALID_GEOMETRY"), geometry_invalid_reasons: [] });
    const empty = renderHook(() => useChannelMomentSplicePreview({ request, revision: 0, immediate: true, validationMessage: null }));
    await waitFor(() => { expect(empty.result.current.state).toBe("NO_VALID_PREVIEW"); }); expect(empty.result.current.invalidDetail).toBeNull();
  });

  it("registers the Channel product and renders its backend-authored trace", async () => {
    vi.spyOn(clientModule, "previewWIMomentSplice").mockResolvedValue(channelMomentSplicePreviewFixture() as never);
    vi.spyOn(clientModule, "previewChannelMomentSplice").mockResolvedValue(channelMomentSplicePreviewFixture());
    render(<MomentConnectionsWorkspace />);
    const option = screen.getByRole("option", { name: "Channel Beam Moment Splice" });
    expect(option.closest("optgroup")?.label).toBe("Beam moment connections");
    fireEvent.change(screen.getByLabelText("Connection type"), { target: { value: "CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE" } });
    expect(await screen.findByRole("heading", { name: "Moment connection — Channel beam moment splice" })).toBeInTheDocument();
    expect(await screen.findByLabelText("mock-channel-moment-splice-viewer")).toHaveTextContent("12 boxes");
    expect(screen.getByLabelText("mock-channel-moment-splice-viewer")).toHaveTextContent("48 cylinders");
    expect(screen.getByText("Slice 6 — Top Flange")).toBeInTheDocument();
    expect(screen.getByText("Centroid / shear center").parentElement).toHaveTextContent("Generated centroidal torsion");
    expect(screen.getByText("Back / opening web branches").parentElement).toHaveTextContent("Blind 50/50 web shearNot used");
  });

  it("keeps one action state, runs design explicitly, marks it stale, loads SI, and validates inputs", async () => {
    vi.spyOn(clientModule, "previewChannelMomentSplice").mockResolvedValue(channelMomentSplicePreviewFixture());
    const designSpy = vi.spyOn(clientModule, "evaluateChannelMomentSplice").mockResolvedValue(channelMomentSpliceDesignFixture());
    render(<ChannelMomentSpliceWorkspace />); await screen.findByLabelText("mock-channel-moment-splice-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); await waitFor(() => { expect(designSpy).toHaveBeenCalledTimes(1); });
    expect(await screen.findByText(/BACK_WEB_PLATE_BODY \/ 0\.82/iu)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit Channel axial" })); expect(screen.getByLabelText("Axial force P_L")).toHaveValue("30");
    expect(screen.getByText(/Design results are stale/iu)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit Channel shear" })); expect(screen.getByLabelText("Major shear V_V")).toHaveValue("-15");
    fireEvent.click(screen.getByRole("button", { name: "Edit Channel moment" })); expect(screen.getByLabelText("Major-axis moment M_T")).toHaveValue("125");
    fireEvent.click(screen.getByRole("button", { name: "Ignore generated torsion edit" })); expect(screen.queryByLabelText("User torsion")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Select opening plate" }));
    fireEvent.click(screen.getByRole("button", { name: "Load 4.1B SI" })); expect(screen.getByLabelText("Channel depth")).toHaveValue("203.2");
    fireEvent.click(screen.getByRole("button", { name: "Load 4.1B U.S." })); expect(screen.getByLabelText("Channel depth")).toHaveValue("8");
    fireEvent.change(screen.getByLabelText("Beam-end gap"), { target: { value: "0" } }); expect(screen.getAllByText(/positive decimals/iu)).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Beam-end gap"), { target: { value: "0.5" } });
    fireEvent.change(screen.getByLabelText("Web rows"), { target: { value: "0" } }); expect(screen.getAllByText(/positive integers/iu)).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Web rows"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Major-axis moment M_T"), { target: { value: "bad" } }); expect(screen.getAllByText(/finite signed decimals/iu)).toHaveLength(2);
  });

  it("binds every geometry, action, fastener, count, and explicit shear-center field", async () => {
    vi.spyOn(clientModule, "previewChannelMomentSplice").mockResolvedValue(channelMomentSplicePreviewFixture());
    render(<ChannelMomentSpliceWorkspace />); await screen.findByLabelText("mock-channel-moment-splice-viewer");
    const labels = ["Channel depth", "Flange width", "Web thickness", "Flange thickness", "Display length each side", "Beam-end gap", "Axial force P_L", "Major shear V_V", "Major-axis moment M_T", "Web plate length", "Web plate height", "Web plate thickness", "Web vertical pitch", "Web longitudinal gauge", "Web group-centroid distance", "Web bolt diameter", "Web hole diameter", "Flange plate length", "Flange plate thickness", "Inner plate width", "Transverse gauge", "Flange longitudinal pitch", "Flange group-centroid distance", "Flange bolt diameter", "Flange hole diameter"];
    for (const label of labels) { fireEvent.change(screen.getByLabelText(label), { target: { value: "1.25" } }); expect(screen.getByLabelText(label)).toHaveValue("1.25"); }
    for (const label of ["Web rows", "Web bolts per row", "Bolts per T line"]) { fireEvent.change(screen.getByLabelText(label), { target: { value: "3" } }); expect(screen.getByLabelText(label)).toHaveValue(3); }
    fireEvent.change(screen.getByLabelText("Shear-center source"), { target: { value: "EXPLICIT_VERIFIED_CHANNEL_SHEAR_CENTER_RC1" } });
    expect(screen.getByLabelText("Explicit shear-center T coordinate")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Explicit shear-center T coordinate"), { target: { value: "-2" } });
    fireEvent.change(screen.getByLabelText("Explicit source provenance"), { target: { value: "" } }); expect(screen.getAllByText(/requires both/iu)).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Explicit source provenance"), { target: { value: "verified report" } });
    fireEvent.change(screen.getByLabelText("Shear-center source"), { target: { value: "RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1" } }); expect(screen.queryByLabelText("Explicit source provenance")).not.toBeInTheDocument();
  });

  it("handles pending/superseded design, preview retry, typed and unexpected failures, and server-invalid geometry", async () => {
    const previewSpy = vi.spyOn(clientModule, "previewChannelMomentSplice").mockResolvedValue(channelMomentSplicePreviewFixture());
    let resolveDesign: ((value: ReturnType<typeof channelMomentSpliceDesignFixture>) => void) | undefined;
    const designSpy = vi.spyOn(clientModule, "evaluateChannelMomentSplice").mockImplementationOnce(() => new Promise((resolve) => { resolveDesign = resolve; }));
    const view = render(<ChannelMomentSpliceWorkspace />); await screen.findByLabelText("mock-channel-moment-splice-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); expect(screen.getByRole("button", { name: "Running design check…" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Load 4.1B SI" })); resolveDesign?.(channelMomentSpliceDesignFixture()); await act(async () => { await Promise.resolve(); });
    expect(screen.getByText("Run Design Check", { selector: "dd" })).toBeInTheDocument();
    let rejectSuperseded: ((reason: Error) => void) | undefined;
    designSpy.mockImplementationOnce(() => new Promise((_, reject) => { rejectSuperseded = reject; }));
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    fireEvent.click(screen.getByRole("button", { name: "Load 4.1B U.S." }));
    rejectSuperseded?.(new Error("superseded design failure"));
    await act(async () => { await Promise.resolve(); });
    previewSpy.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "preview offline", null)); fireEvent.change(screen.getByLabelText("Channel depth"), { target: { value: "210" } });
    await waitFor(() => { expect(screen.getAllByText(/showing last valid model/iu).length).toBeGreaterThanOrEqual(2); }, { timeout: PREVIEW_DEBOUNCE_MS + 1000 });
    expect(screen.getByRole("alert")).toHaveTextContent("preview offline"); previewSpy.mockResolvedValueOnce(channelMomentSplicePreviewFixture()); fireEvent.click(screen.getByRole("button", { name: "Retry preview" })); await waitFor(() => { expect(screen.getByText("Current backend preview", { selector: "strong" })).toBeInTheDocument(); });
    designSpy.mockRejectedValueOnce(new EvaluationTransportError("HTTP", 503, "design offline", null)); fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); expect(await screen.findByRole("alert")).toHaveTextContent("design offline");
    view.unmount();

    previewSpy.mockResolvedValueOnce(channelMomentSplicePreviewFixture("INVALID_GEOMETRY")); const invalid = render(<ChannelMomentSpliceWorkspace />); expect((await screen.findAllByText(/No valid backend preview/iu)).length).toBeGreaterThanOrEqual(2); expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled(); invalid.unmount();
    previewSpy.mockResolvedValueOnce(channelMomentSplicePreviewFixture()); designSpy.mockRejectedValueOnce(new Error("unexpected design failure")); render(<ChannelMomentSpliceWorkspace />); await screen.findByLabelText("mock-channel-moment-splice-viewer"); fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); expect(await screen.findByRole("alert")).toHaveTextContent("Unexpected Channel moment-splice design failure");
  });

  it("reports non-exact successor diagnostics without hiding the model", async () => {
    const exact = channelMomentSplicePreviewFixture();
    const nonExact = {
      ...exact,
      result: {
        ...exact.result,
        top_flange: { ...exact.result.top_flange, exact_force_equilibrium: false },
        web_faces: { ...exact.result.web_faces, exact_free_torsion_recovery: false },
        equilibrium: { ...exact.result.equilibrium, whole_connection_six_component_exact: false },
      },
    };
    vi.spyOn(clientModule, "previewChannelMomentSplice").mockResolvedValue(nonExact);
    render(<ChannelMomentSpliceWorkspace />);
    await screen.findByLabelText("mock-channel-moment-splice-viewer");
    expect(screen.getAllByText("No").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Not closed")).toBeInTheDocument();
  });
});
