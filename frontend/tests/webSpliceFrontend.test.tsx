import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationTransportError, evaluateWebSplice, previewWebSplice, WEB_SPLICE_DESIGN_PATH, WEB_SPLICE_PREVIEW_PATH } from "../src/api/client";
import * as clientModule from "../src/api/client";
import { loadWebSpliceBenchmark } from "../src/fixtures/webSpliceBenchmarks";
import { buildWebSpliceSceneModel } from "../src/visualization/webSpliceSceneModel";
import { ShearConnectionsWorkspace } from "../src/workspace/ShearConnectionsWorkspace";
import { WebSpliceWorkspace } from "../src/workspace/WebSpliceWorkspace";
import { useWebSplicePreview } from "../src/workspace/webSpliceWorkflow";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import { webSpliceDesignFixture, webSplicePreviewFixture, webSpliceRC2DesignFixture, webSpliceRC2PreviewFixture, webSpliceVisualizationFixture } from "./webSpliceFixtures";

vi.mock("../src/visualization/VisualizationPanel", () => ({ VisualizationPanel: ({ title, model, onAppliedActionValueChange, onSelect }: { title: string; model: { boxes: readonly unknown[]; cylinders: readonly unknown[]; materialAxes: readonly unknown[] }; onAppliedActionValueChange?: (component: string, value: string) => void; onSelect?: (selection: { kind: "MEMBER"; id: string }) => void }) => <div aria-label="mock-web-splice-viewer"><h3>{title}</h3><span>{model.boxes.length} boxes</span><span>{model.cylinders.length} cylinders</span><span>{model.materialAxes.length} material axes</span><button type="button" onClick={() => { onAppliedActionValueChange?.("FX", "5"); }}>Edit axial</button><button type="button" onClick={() => { onAppliedActionValueChange?.("FY", "3"); }}>Edit minor</button><button type="button" onClick={() => { onAppliedActionValueChange?.("FZ", "-7"); }}>Edit major</button><button type="button" onClick={() => { onAppliedActionValueChange?.("MX", "1"); }}>Ignore moment</button><button type="button" onClick={() => { onSelect?.({ kind: "MEMBER", id: "BEAM_A" }); }}>Select beam</button></div> }));

const response = (body: unknown, status = 200): Response => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("Stage 3.6A exact benchmark and scene", () => {
  it("loads independent U.S./SI defaults without a moment or flange/single-plate option", () => {
    const us = loadWebSpliceBenchmark("US_CUSTOMARY");
    const si = loadWebSpliceBenchmark("SI");
    expect(us).toMatchObject({ orchestration_contract_version: "3.6A-RC1", beam_end_gap: { value: "0.5", unit: "in" }, transfer_force: { axial_force: { value: "0", unit: "kip" }, major_shear: { value: "-10", unit: "kip" }, minor_shear: { value: "0", unit: "kip" } } });
    expect(si).toMatchObject({ beam_end_gap: { value: "12.7", unit: "mm" }, hole_diameter: { value: "14.3002", unit: "mm" }, transfer_force: { major_shear: { value: "-44.482216152605", unit: "kN" } } });
    expect(us.splice_plate).toMatchObject({ count: 2, locked_identical: true });
    expect(us.flange_splice_enabled).toBe(false);
    us.beam.depth.value = "99";
    expect(loadWebSpliceBenchmark("US_CUSTOMARY").beam.depth.value).toBe("10");
  });

  it("builds two beams, two plates, eight distinct through bolts, eight material regions, the gap, and signed arrows", () => {
    const model = buildWebSpliceSceneModel(webSpliceVisualizationFixture());
    expect(model.boxes).toHaveLength(8);
    expect(model.boxes.filter((item) => item.ownerId.startsWith("BEAM_"))).toHaveLength(6);
    expect(model.boxes.filter((item) => item.ownerId.includes("SPLICE_PLATE"))).toHaveLength(2);
    expect(model.cylinders.filter((item) => item.kind === "BOLT")).toHaveLength(8);
    expect(new Set(model.cylinders.filter((item) => item.kind === "BOLT").map((item) => item.ownerBoltId)).size).toBe(8);
    expect(model.materialAxes).toHaveLength(8);
    expect(model.markers[0]).toMatchObject({ id: "WEB_SPLICE_JOINT", position: { x: 0, y: 0, z: 0 } });
    expect(model.appliedArrows).toHaveLength(1);
    expect(model.appliedArrows[0]).toMatchObject({ component: "FZ", signedValue: -10, axis: { x: 0, y: 0, z: -1 } });
    expect(model.boundsRadius).toBeGreaterThan(9);
  });

  it("reverses every signed arrow, suppresses zeros, supports SI, and tolerates an unbound region", () => {
    const visualization = structuredClone(webSpliceVisualizationFixture());
    visualization.applied_force_l_v_t.l.value = "5";
    visualization.applied_force_l_v_t.v.value = "7";
    visualization.applied_force_l_v_t.t.value = "-3";
    let model = buildWebSpliceSceneModel(visualization);
    expect(model.appliedArrows.map((item) => [item.component, item.axis])).toEqual([["FX", { x: 1, y: 0, z: 0 }], ["FZ", { x: 0, y: 0, z: 1 }], ["FY", { x: 0, y: -1, z: 0 }]]);
    visualization.applied_force_l_v_t.l.value = "-5";
    model = buildWebSpliceSceneModel(visualization);
    expect(model.appliedArrows[0]).toMatchObject({ component: "FX", axis: { x: -1, y: 0, z: 0 }, axialLoadingSense: "COMPRESSION" });
    visualization.applied_force_l_v_t.l.value = "0";
    visualization.applied_force_l_v_t.v.value = "0";
    visualization.applied_force_l_v_t.t.value = "0";
    visualization.beam_end_planes_l[0].unit = "mm";
    const firstRegion = visualization.material_regions[0];
    if (firstRegion === undefined) throw new Error("Controlled material region required.");
    const modified = {
      ...visualization,
      material_regions: [
        { ...firstRegion, component_id: "UNKNOWN", region_id: "UNKNOWN_REGION" },
        ...visualization.material_regions.slice(1),
      ],
    };
    model = buildWebSpliceSceneModel(modified);
    expect(model.appliedArrows).toEqual([]);
    expect(model.unitSystem).toBe("SI");
    expect(model.materialAxes[0]).toMatchObject({ componentId: "UNKNOWN", componentLabel: "UNKNOWN", origin: { x: 0, y: 0, z: 0 }, presentation: null });
  });
});

describe("Stage 3.6A strict transport", () => {
  beforeEach(() => { vi.stubGlobal("fetch", vi.fn()); });
  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it("posts only the two strict same-origin routes", async () => {
    const request = loadWebSpliceBenchmark("US_CUSTOMARY");
    const signal = new AbortController().signal;
    vi.mocked(fetch).mockResolvedValueOnce(response(webSplicePreviewFixture())).mockResolvedValueOnce(response(webSpliceDesignFixture()));
    await expect(previewWebSplice(request, signal)).resolves.toMatchObject({ request_id: request.request_id });
    await expect(evaluateWebSplice(request, signal)).resolves.toMatchObject({ ordinary_pass_allowed: false });
    expect(fetch).toHaveBeenNthCalledWith(1, WEB_SPLICE_PREVIEW_PATH, expect.objectContaining({ method: "POST", credentials: "same-origin", signal }));
    expect(fetch).toHaveBeenNthCalledWith(2, WEB_SPLICE_DESIGN_PATH, expect.objectContaining({ method: "POST" }));
  });

  it("rejects malformed success responses and classifies validation/http/network/abort", async () => {
    const request = loadWebSpliceBenchmark("US_CUSTOMARY");
    const signal = new AbortController().signal;
    for (const body of [null, {}, { ...webSplicePreviewFixture(), api_transport_schema_version: "bad" }, { ...webSplicePreviewFixture(), orchestration_contract_version: "bad" }, { ...webSplicePreviewFixture(), preview_schema_version: "bad" }, { ...webSplicePreviewFixture(), resistance_evaluated: true }, { ...webSplicePreviewFixture(), ordinary_pass_allowed: true }, { ...webSplicePreviewFixture(), engineering_fingerprint: null }, { ...webSplicePreviewFixture(), result: null }]) { vi.mocked(fetch).mockResolvedValueOnce(response(body)); await expect(previewWebSplice(request, signal)).rejects.toMatchObject({ kind: "RESPONSE" }); }
    for (const body of [null, {}, { ...webSpliceDesignFixture(), orchestration_contract_version: "bad" }, { ...webSpliceDesignFixture(), ordinary_pass_allowed: true }, { ...webSpliceDesignFixture(), result_fingerprint: null }, { ...webSpliceDesignFixture(), result: null }]) { vi.mocked(fetch).mockResolvedValueOnce(response(body)); await expect(evaluateWebSplice(request, signal)).rejects.toMatchObject({ kind: "RESPONSE" }); }
    vi.mocked(fetch).mockResolvedValueOnce(response({ detail: "invalid" }, 422)); await expect(previewWebSplice(request, signal)).rejects.toMatchObject({ kind: "VALIDATION", status: 422 });
    vi.mocked(fetch).mockResolvedValueOnce(response({ detail: "failed" }, 503)); await expect(evaluateWebSplice(request, signal)).rejects.toMatchObject({ kind: "HTTP", status: 503 });
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("offline")); await expect(previewWebSplice(request, signal)).rejects.toMatchObject({ kind: "NETWORK" });
    const abort = new DOMException("aborted", "AbortError"); vi.mocked(fetch).mockRejectedValueOnce(abort); await expect(evaluateWebSplice(request, signal)).rejects.toBe(abort);
  });
});

describe("Stage 3.6B RC2 result contract and engineering presentation", () => {
  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it("accepts the paired RC2 preview/design transport while retaining historical 3.6A", async () => {
    vi.stubGlobal("fetch", vi.fn());
    const request = loadWebSpliceBenchmark("US_CUSTOMARY", "3.6B-RC2");
    vi.mocked(fetch).mockResolvedValueOnce(response(webSpliceRC2PreviewFixture())).mockResolvedValueOnce(response(webSpliceRC2DesignFixture()));
    await expect(previewWebSplice(request, new AbortController().signal)).resolves.toMatchObject({ orchestration_contract_version: "3.6B-RC2", preview_schema_version: "0.2.0-draft" });
    await expect(evaluateWebSplice(request, new AbortController().signal)).resolves.toMatchObject({ orchestration_contract_version: "3.6B-RC2", ordinary_pass_allowed: false });
    expect(loadWebSpliceBenchmark("US_CUSTOMARY").orchestration_contract_version).toBe("3.6A-RC1");
  });

  it("shows the body interaction, Slice 4 advisory, qualification, disclaimer, and source-pending double shear only after design", async () => {
    vi.spyOn(clientModule, "previewWebSplice").mockResolvedValue(webSpliceRC2PreviewFixture());
    vi.spyOn(clientModule, "evaluateWebSplice").mockResolvedValue(webSpliceRC2DesignFixture());
    render(<WebSpliceWorkspace />);
    await screen.findByLabelText("mock-web-splice-viewer");
    expect(screen.getByText("Run Design Check to calculate the rational interaction.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(await screen.findByText("Rational linear interaction")).toBeInTheDocument();
    expect(screen.getByText(/Narrow Plate Validation Caution/iu)).toBeInTheDocument();
    expect(screen.getByText(/Section 2.3.2/iu)).toBeInTheDocument();
    expect(screen.getByText("Source-authorized Fnv required")).toBeInTheDocument();
    expect(screen.getByText(/engineering review\/report disclaimer required/iu)).toBeInTheDocument();
    expect(screen.getByText("2", { selector: "dd" })).toBeInTheDocument();
  });

  it("presents unavailable rational-body fields and a source-authorized common-bolt capacity", async () => {
    const baseDesign = webSpliceRC2DesignFixture();
    const body = baseDesign.result.plate_body_interaction;
    const bolt = baseDesign.result.double_shear_results?.[0];
    if (body === undefined || bolt === undefined) throw new Error("Controlled RC2 design fixture required.");
    const design = { ...baseDesign, result: {
      ...baseDesign.result,
      plate_body_interaction: {
        ...body,
        slice4_advisories: [],
        governing_section_id: null,
        governing_fiber_id: null,
        governing_signed_normal_stress: null,
        governing_signed_shear_stress: null,
        normal_utilization: null,
        shear_utilization: null,
        rational_utilization: null,
      },
      double_shear_results: [{
        ...bolt,
        per_plane_design_capacity: { value: "10", unit: "kip" },
        two_plane_design_capacity: { value: "20", unit: "kip" },
        utilization: "0.5",
      }],
    } } satisfies typeof baseDesign;
    const basePreview = webSpliceRC2PreviewFixture();
    const previewResult = { ...basePreview.result };
    Reflect.deleteProperty(previewResult, "clear_body_plan");
    const preview = { ...basePreview, result: previewResult } satisfies typeof basePreview;
    vi.spyOn(clientModule, "previewWebSplice").mockResolvedValue(preview);
    vi.spyOn(clientModule, "evaluateWebSplice").mockResolvedValue(design);
    render(<WebSpliceWorkspace />);
    await screen.findByLabelText("mock-web-splice-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(await screen.findByText("Unavailable")).toBeInTheDocument();
    expect(screen.getByText("None")).toBeInTheDocument();
    expect(screen.getAllByText("Not evaluated").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText(/20 kip \/ 0\.5/iu)).toBeInTheDocument();
  });

  it("falls back safely when evaluated result identifiers or component utilizations are absent", async () => {
    const baseDesign = webSpliceRC2DesignFixture();
    const body = baseDesign.result.plate_body_interaction;
    const bolt = baseDesign.result.double_shear_results?.[0];
    if (body === undefined || bolt === undefined) throw new Error("Controlled RC2 design fixture required.");
    const design = { ...baseDesign, result: {
      ...baseDesign.result,
      plate_body_interaction: {
        ...body,
        governing_fiber_id: null,
        normal_utilization: null,
        shear_utilization: null,
      },
      double_shear_results: [{
        ...bolt,
        per_plane_design_capacity: { value: "10", unit: "kip" },
        two_plane_design_capacity: { value: "20", unit: "kip" },
        utilization: null,
      }],
    } } satisfies typeof baseDesign;
    vi.spyOn(clientModule, "previewWebSplice").mockResolvedValue(webSpliceRC2PreviewFixture());
    vi.spyOn(clientModule, "evaluateWebSplice").mockResolvedValue(design);
    render(<WebSpliceWorkspace />);
    await screen.findByLabelText("mock-web-splice-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(await screen.findByText(/Section A Clear Boundary \/\s*$/iu)).toBeInTheDocument();
    expect(screen.getByText(/— \/ — \/ 0\.398/iu)).toBeInTheDocument();
    expect(screen.getByText(/20 kip \/ —/iu)).toBeInTheDocument();
  });
});

describe("Stage 3.6A latest-response-wins workflow and workspace", () => {
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

  it("covers current, invalid, failed, retry, and local-invalid states", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(clientModule, "previewWebSplice").mockResolvedValueOnce(webSplicePreviewFixture());
    const request = loadWebSpliceBenchmark("US_CUSTOMARY");
    let revision = 0; let validationMessage: string | null = null;
    const hook = renderHook(() => useWebSplicePreview({ request, revision, immediate: revision === 0, validationMessage }));
    await act(async () => { await Promise.resolve(); }); expect(hook.result.current.state).toBe("CURRENT_VALID");
    spy.mockResolvedValueOnce(webSplicePreviewFixture("INVALID_GEOMETRY")); revision = 1; hook.rerender(); await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); }); expect(hook.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
    spy.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "offline", null)); revision = 2; hook.rerender(); await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); }); expect(hook.result.current.state).toBe("PREVIEW_FAILED_SHOWING_LAST_VALID");
    spy.mockResolvedValueOnce(webSplicePreviewFixture()); act(() => { hook.result.current.retry(); }); await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); }); expect(hook.result.current.state).toBe("CURRENT_VALID");
    validationMessage = "locally invalid"; revision = 3; hook.rerender(); expect(hook.result.current.state).toBe("CURRENT_INVALID_SHOWING_LAST_VALID");
  });

  it("normalizes unexpected/validation/abort failures and no-last-valid invalidity", async () => {
    const request = loadWebSpliceBenchmark("US_CUSTOMARY");
    const spy = vi.spyOn(clientModule, "previewWebSplice").mockRejectedValueOnce(new Error("unexpected"));
    const unexpected = renderHook(() => useWebSplicePreview({ request, revision: 0, immediate: true, validationMessage: null })); await waitFor(() => { expect(unexpected.result.current.state).toBe("NO_VALID_PREVIEW"); }); expect(unexpected.result.current.error?.message).toContain("Unexpected web-splice"); unexpected.unmount();
    spy.mockRejectedValueOnce(new EvaluationTransportError("VALIDATION", 422, "invalid", null)); const invalid = renderHook(() => useWebSplicePreview({ request, revision: 0, immediate: true, validationMessage: null })); await waitFor(() => { expect(invalid.result.current.state).toBe("NO_VALID_PREVIEW"); }); invalid.unmount();
    spy.mockRejectedValueOnce(new DOMException("aborted", "AbortError")); const aborted = renderHook(() => useWebSplicePreview({ request, revision: 0, immediate: true, validationMessage: null })); await waitFor(() => { expect(aborted.result.current.state).toBe("PREVIEW_PENDING"); }); aborted.unmount();
    spy.mockResolvedValueOnce({ ...webSplicePreviewFixture("INVALID_GEOMETRY"), geometry_invalid_reasons: [] }); const empty = renderHook(() => useWebSplicePreview({ request, revision: 0, immediate: true, validationMessage: null })); await waitFor(() => { expect(empty.result.current.state).toBe("NO_VALID_PREVIEW"); }); expect(empty.result.current.invalidDetail).toBeNull();
  });

  it("registers the Beam option and mounts the complete workspace without single-plate, flange-splice, or moment controls", async () => {
    vi.spyOn(clientModule, "previewWebSplice").mockResolvedValue(webSplicePreviewFixture());
    vi.spyOn(clientModule, "evaluateWebSplice").mockResolvedValue(webSpliceDesignFixture());
    render(<ShearConnectionsWorkspace />);
    const option = screen.getByRole("option", { name: "Beam connection — Symmetric double web splice plates" }); expect(option.closest("optgroup")?.label).toBe("Beam connections");
    fireEvent.change(screen.getByLabelText("Connection type"), { target: { value: "SYMMETRIC_DOUBLE_WEB_SPLICE" } });
    expect(await screen.findByRole("heading", { name: "Beam connection — Symmetric double FRP web splice plates" })).toBeInTheDocument();
    expect(screen.getByLabelText("Beam-end gap")).toHaveValue("0.5");
    expect(screen.getByLabelText("Axial force (+ tension / - compression)")).toHaveValue("0");
    expect(screen.getByLabelText("Major shear")).toHaveValue("-10");
    expect(screen.getByLabelText("Minor shear")).toHaveValue("0");
    expect(screen.queryByLabelText(/moment/iu)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/single plate/iu)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/flange splice/iu)).not.toBeInTheDocument();
    expect(await screen.findByLabelText("mock-web-splice-viewer")).toHaveTextContent("8 boxes");
  });

  it("keeps one load state across sidebar/arrow edits, marks design stale, loads SI, validates locally, and runs explicit design", async () => {
    vi.spyOn(clientModule, "previewWebSplice").mockResolvedValue(webSplicePreviewFixture());
    const designSpy = vi.spyOn(clientModule, "evaluateWebSplice").mockResolvedValue(webSpliceDesignFixture());
    render(<WebSpliceWorkspace />); await screen.findByLabelText("mock-web-splice-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); await waitFor(() => { expect(designSpy).toHaveBeenCalledTimes(1); }); expect(screen.getByText("Local checks on last design run").parentElement).toHaveTextContent("1");
    designSpy.mockResolvedValueOnce({ ...webSpliceDesignFixture(), supported_local_checks_executed: false, local_check_ids: [] });
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); await screen.findByText("No accepted mapping");
    fireEvent.click(screen.getByRole("button", { name: "Edit axial" })); expect(screen.getByLabelText("Axial force (+ tension / - compression)")).toHaveValue("5"); expect(screen.getByText(/Design results are stale/iu)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit minor" })); expect(screen.getByLabelText("Minor shear")).toHaveValue("3");
    fireEvent.click(screen.getByRole("button", { name: "Edit major" })); expect(screen.getByLabelText("Major shear")).toHaveValue("-7");
    fireEvent.click(screen.getByRole("button", { name: "Ignore moment" })); expect(screen.queryByLabelText(/moment/iu)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Select beam" }));
    fireEvent.click(screen.getByRole("button", { name: "Load 3.6B SI" })); expect(screen.getByLabelText("Beam-end gap")).toHaveValue("12.7");
    fireEvent.click(screen.getByRole("button", { name: "Load 3.6B U.S." })); expect(screen.getByLabelText("Beam-end gap")).toHaveValue("0.5");
    fireEvent.change(screen.getByLabelText("Beam-end gap"), { target: { value: "0" } }); expect(screen.getAllByText(/must be positive decimals/iu)).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Beam-end gap"), { target: { value: "0.5" } });
    fireEvent.change(screen.getByLabelText("Rows"), { target: { value: "0" } }); expect(screen.getAllByText(/must be positive integers/iu)).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Rows"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Axial force (+ tension / - compression)"), { target: { value: "not-finite" } }); expect(screen.getAllByText(/must be finite signed decimals/iu)).toHaveLength(2);
  });

  it("binds every geometry and fastener editor to the one request state", async () => {
    vi.spyOn(clientModule, "previewWebSplice").mockResolvedValue(webSplicePreviewFixture());
    render(<WebSpliceWorkspace />); await screen.findByLabelText("mock-web-splice-viewer");
    for (const label of ["Beam depth", "Flange width", "Web thickness", "Flange thickness", "Display length each side", "Plate length", "Plate height", "Plate thickness", "Vertical pitch", "Longitudinal gauge", "Group-centroid offset", "Major shear", "Minor shear", "Bolt diameter", "Hole diameter"]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: "5" } });
      expect(screen.getByLabelText(label)).toHaveValue("5");
    }
    fireEvent.change(screen.getByLabelText("Rows"), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText("Bolts per row"), { target: { value: "3" } });
    expect(screen.getByLabelText("Rows")).toHaveValue(3);
    expect(screen.getByLabelText("Bolts per row")).toHaveValue(3);
  });

  it("normalizes design errors and ignores a superseded design response", async () => {
    vi.spyOn(clientModule, "previewWebSplice").mockResolvedValue(webSplicePreviewFixture());
    const designSpy = vi.spyOn(clientModule, "evaluateWebSplice");
    designSpy.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "design offline", null));
    render(<WebSpliceWorkspace />); await screen.findByLabelText("mock-web-splice-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(await screen.findByText("design offline")).toBeInTheDocument();
    designSpy.mockRejectedValueOnce(new Error("unexpected"));
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(await screen.findByText("Unexpected web-splice design failure.")).toBeInTheDocument();

    let resolveDesign: ((value: ReturnType<typeof webSpliceDesignFixture>) => void) | undefined;
    designSpy.mockImplementationOnce(() => new Promise((resolve) => { resolveDesign = resolve; }));
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    expect(screen.getByRole("button", { name: "Running design check…" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Load 3.6B SI" }));
    await act(async () => { resolveDesign?.(webSpliceDesignFixture()); await Promise.resolve(); });
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeInTheDocument();
    expect(screen.queryByText("Not Evaluated")).not.toBeInTheDocument();

    let rejectDesign: ((error: Error) => void) | undefined;
    designSpy.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectDesign = reject; }));
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    fireEvent.click(screen.getByRole("button", { name: "Load 3.6B U.S." }));
    await act(async () => { rejectDesign?.(new Error("superseded")); await Promise.resolve(); });
    expect(screen.queryByText("superseded")).not.toBeInTheDocument();
  });

  it("presents invalid, failed-last-valid, and no-valid preview states with retry", async () => {
    const spy = vi.spyOn(clientModule, "previewWebSplice")
      .mockResolvedValueOnce(webSplicePreviewFixture())
      .mockResolvedValueOnce(webSplicePreviewFixture("INVALID_GEOMETRY"))
      .mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "preview offline", null))
      .mockResolvedValueOnce(webSplicePreviewFixture());
    const view = render(<WebSpliceWorkspace />);
    expect((await screen.findAllByText("Current backend preview")).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Beam-end gap"), { target: { value: "0.6" } });
    expect((await screen.findAllByText("Current geometry invalid — showing last valid preview")).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Beam-end gap"), { target: { value: "0.7" } });
    expect((await screen.findAllByText("Preview unavailable — showing last valid preview")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Retry preview" }));
    expect((await screen.findAllByText("Current backend preview")).length).toBeGreaterThan(0);
    view.unmount();

    spy.mockReset().mockResolvedValueOnce(webSplicePreviewFixture("INVALID_GEOMETRY"));
    render(<WebSpliceWorkspace />);
    expect((await screen.findAllByText("No valid backend preview")).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Canonical web-splice model unavailable" })).toBeInTheDocument();
  });
});
