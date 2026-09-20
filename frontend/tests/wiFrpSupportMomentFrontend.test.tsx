import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../src/api/wiFrpSupportMomentClient";
import * as historical from "../src/api/client";
import { supportFaces, type SupportMode, type WIFrpSupportMomentPreview, type WIFrpSupportMomentResponse } from "../src/api/wiFrpSupportMomentContracts";
import { loadWIFrpSupportMomentPreset } from "../src/fixtures/wiFrpSupportMomentBenchmarks";
import { buildFastenerPresentations } from "../src/visualization/fastenerPresentation";
import { buildWIFrpSupportMomentScene } from "../src/visualization/wiFrpSupportMomentSceneModel";
import { MomentConnectionsWorkspace } from "../src/workspace/MomentConnectionsWorkspace";
import { WIFrpSupportMomentWorkspace } from "../src/workspace/WIFrpSupportMomentWorkspace";
import { useWIFrpSupportMomentPreview } from "../src/workspace/wiFrpSupportMomentWorkflow";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import { frpSupportMomentVisibleFailures } from "../src/workspace/wiFrpSupportMomentFailures";
import { frpDesignFixture, frpPreviewFixture } from "./wiFrpSupportMomentFixtures";

vi.mock("../src/visualization/VisualizationPanel", () => ({
  VisualizationPanel: ({ model, onAppliedActionValueChange, onSelect }: {
    model: ReturnType<typeof buildWIFrpSupportMomentScene>;
    onAppliedActionValueChange: (component: string, value: string) => void;
    onSelect: (selection: { kind: "MEMBER"; id: string }) => void;
  }) => <div aria-label="frp-moment-test-viewer"><span>{model.boxes.length} solids</span><span>{model.materialAxes.length} regions</span>{["FX", "FZ", "MY", "MX"].map(c => <button key={c} onClick={() => { onAppliedActionValueChange(c, "-30"); }}>Edit {c}</button>)}<button onClick={() => { onSelect({ kind: "MEMBER", id: "FRP_SUPPORT" }); }}>Select support</button></div>,
}));
const modes = Object.keys(supportFaces) as SupportMode[];
const response = (v: unknown, status = 200) => new Response(JSON.stringify(v), { status });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); });

describe("Stage 4.3 five-support canonical scene and source-free presets", () => {
  it.each(modes)("draws %s actual through-bolts, regions, references and contact faces", mode => {
    const p = frpPreviewFixture(mode).result, m = buildWIFrpSupportMomentScene(p);
    const us = loadWIFrpSupportMomentPreset(mode, "US_CUSTOMARY"), si = loadWIFrpSupportMomentPreset(mode, "SI");
    expect(us.support.mode).toBe(mode); expect(us.support.face).toBe(supportFaces[mode][0]);
    expect(si.gap).toEqual({ value: "12.7", unit: "mm" });
    expect(si.top.support_fastener.hole_diameter).toEqual({ value: "14.3002", unit: "mm" });
    expect(us.response_source_reference).toBe(""); expect(us.local_zone_source_reference).toBe("");
    expect(us.top).toEqual(us.bottom); expect(us.top).not.toBe(us.bottom);
    expect(m.cylinders.filter(c => c.kind === "BOLT")).toHaveLength(28);
    expect(m.cylinders.filter(c => c.kind === "WASHER")).toHaveLength(56);
    expect(m.cylinders.some(c => c.hardwareConfiguration === "EXTERIOR_NUT_WASHER_ANCHOR")).toBe(false);
    expect(m.materialAxes).toHaveLength(p.geometry.display_parts.length);
    expect(m.materialAxes.every(a => a.presentation !== null)).toBe(true);
    expect(m.materialAxes.filter(a => a.componentId === "FRP_SUPPORT").length).toBeGreaterThan(0);
    expect(m.zones).toHaveLength(4); expect(m.zones.every(z => z.selectedContact)).toBe(true);
    expect(m.markers).toHaveLength(14); expect(m.appliedArrows).toHaveLength(3);
    expect(m.appliedArrows.every(a => a.origin.x === .5 && a.origin.z === 0)).toBe(true);
    expect(m.boundsRadius).toBeGreaterThan(m.fitRadius);
    const assemblies = buildFastenerPresentations(m.cylinders);
    expect(assemblies).toHaveLength(28);
    for (const a of assemblies) {
      expect(a.shank.exactHardware).toBeDefined();
      expect(a.head.start).toEqual(a.shank.exactHardware?.headStart);
      expect(a.nut.end).toEqual(a.shank.exactHardware?.nutEnd);
      expect(a.renderedHardware).toHaveLength(2);
    }
  });

  it("retains signed arrows, zero suppression, metric display and missing-hardware rejection", () => {
    const p = structuredClone(frpPreviewFixture().result);
    p.input.actions.axial.value = "-20"; p.joint_right_hand_action.force.x.value = "-20";
    p.input.actions.major_shear.value = "10"; p.joint_right_hand_action.force.y.value = "10";
    p.input.actions.structural_major_moment.value = "-100"; p.joint_right_hand_action.moment.z.value = "100";
    p.joint_right_hand_action.reference.x.value = "12.7"; p.joint_right_hand_action.reference.x.unit = "mm";
    let m = buildWIFrpSupportMomentScene(p);
    expect(m.appliedArrows[0]).toMatchObject({ axis: { x: -1 }, axialLoadingSense: "COMPRESSION", origin: { x: .5 } });
    expect(m.appliedArrows[1]?.axis.z).toBe(1); expect(m.appliedArrows[2]?.axis.y).toBe(-1);
    for (const q of Object.values(p.input.actions)) q.value = "0";
    m = buildWIFrpSupportMomentScene(p); expect(m.appliedArrows).toEqual([]);
    const absent = { ...p, geometry: { ...p.geometry, hardware_envelopes: [] } };
    expect(() => buildWIFrpSupportMomentScene(absent)).toThrow("hardware envelope");
    const noMaterial = { ...p, geometry: { ...p.geometry, display_parts: p.geometry.display_parts.map(x => ({ ...x, material_region: null })) } };
    expect(buildWIFrpSupportMomentScene(noMaterial).materialAxes).toEqual([]);
    const unbound = { ...p, geometry: { ...p.geometry, display_parts: p.geometry.display_parts.map(x => x.material_region === null ? x : ({ ...x, material_region: { ...x.material_region, component_id: "UNBOUND" } })) } };
    expect(buildWIFrpSupportMomentScene(unbound).materialAxes.every(a => a.presentation === null)).toBe(true);
  });
});

describe("Stage 4.3 strict transport", () => {
  it.each(modes)("validates both %s real response contracts and explicit routes", async mode => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(frpPreviewFixture(mode))).mockResolvedValueOnce(response(frpDesignFixture(mode)));
    vi.stubGlobal("fetch", fetcher);
    const r = loadWIFrpSupportMomentPreset(mode, "US_CUSTOMARY"), signal = new AbortController().signal;
    expect((await client.previewWIFrpSupportMoment(r, signal)).resistance_evaluated).toBe(false);
    expect((await client.designWIFrpSupportMoment(r, signal)).result.native_governing_check_ids).toContain("FIRST_ROW:TOP_FLANGE_ANGLE");
    expect(fetcher).toHaveBeenNthCalledWith(1, "/api/v1/calculations/wi-beam-frp-support-moment/preview", expect.objectContaining({ body: JSON.stringify(r), signal }));
    expect(fetcher).toHaveBeenNthCalledWith(2, "/api/v1/calculations/wi-beam-frp-support-moment/design-check", expect.objectContaining({ method: "POST" }));
  });
  it("rejects malformed/untrusted envelopes and distinguishes network, abort, JSON and HTTP errors", async () => {
    const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
    const r = loadWIFrpSupportMomentPreset("WI_FLANGE", "US_CUSTOMARY"), signal = new AbortController().signal, good = frpPreviewFixture();
    const bad = [null, [], {}, { ...good, request_id: "wrong" }, { ...good, contract: "4.2-RC1" }, { ...good, ordinary_pass_allowed: true }, { ...good, resistance_evaluated: true }, { ...good, geometry_status: 0 }, { ...good, result: { ...good.result, joint_right_hand_action: {} } }, { ...good, result: { ...good.result, input: { ...good.result.input, actions: { axial: { value: "NaN", unit: "kip" } } } } }, { ...good, result: { ...good.result, geometry: { ...good.result.geometry, hardware_envelopes: [] } } }];
    for (const body of bad) { fetcher.mockResolvedValueOnce(response(body)); await expect(client.previewWIFrpSupportMoment(r, signal)).rejects.toMatchObject({ kind: "RESPONSE" }); }
    for (const [status, kind] of [[422, "VALIDATION"], [503, "HTTP"]] as const) { fetcher.mockResolvedValueOnce(response({}, status)); await expect(client.designWIFrpSupportMoment(r, signal)).rejects.toMatchObject({ kind }); }
    fetcher.mockResolvedValueOnce(new Response("not JSON")); await expect(client.previewWIFrpSupportMoment(r, signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    fetcher.mockRejectedValueOnce(new TypeError("offline")); await expect(client.previewWIFrpSupportMoment(r, signal)).rejects.toMatchObject({ kind: "NETWORK" });
    const abort = new DOMException("abort", "AbortError"); fetcher.mockRejectedValueOnce(abort); await expect(client.designWIFrpSupportMoment(r, signal)).rejects.toBe(abort);
  });
});

describe("Stage 4.3 preview lifecycle", () => {
  it("debounces, retains last valid model and handles retry/local invalid input", async () => {
    vi.useFakeTimers(); const spy = vi.spyOn(client, "previewWIFrpSupportMoment").mockResolvedValue(frpPreviewFixture());
    const r = loadWIFrpSupportMomentPreset("WI_FLANGE", "US_CUSTOMARY"); let revision = 0, invalid: string | null = null;
    const h = renderHook(() => useWIFrpSupportMomentPreview(r, revision, revision === 0, invalid));
    await act(async () => { await Promise.resolve(); }); expect(h.result.current.current).toBe(true);
    const accepted = h.result.current.response;
    spy.mockResolvedValueOnce(frpPreviewFixture("WI_FLANGE", false)); revision++; h.rerender();
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); }); expect(h.result.current.response).toBe(accepted);
    expect(h.result.current.state).toContain("last valid model");
    spy.mockRejectedValueOnce(new Error("offline")); revision++; h.rerender(); await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(h.result.current.error).toBe("offline"); act(() => { h.result.current.retry(); }); await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    expect(h.result.current.current).toBe(true); invalid = "Bad decimal"; revision++; h.rerender(); expect(h.result.current.error).toBe(invalid); h.unmount();
  });
  it("rejects late success/error and intentional abort; initial invalid stays empty", async () => {
    vi.useFakeTimers(); const r = loadWIFrpSupportMomentPreset("WI_FLANGE", "US_CUSTOMARY");
    let resolve: ((v: WIFrpSupportMomentResponse<WIFrpSupportMomentPreview>) => void) | undefined, reject: ((e: unknown) => void) | undefined;
    const spy = vi.spyOn(client, "previewWIFrpSupportMoment").mockImplementationOnce(() => new Promise(yes => { resolve = yes; })).mockResolvedValue(frpPreviewFixture());
    let revision = 0; const h = renderHook(() => useWIFrpSupportMomentPreview(r, revision, true, null)); revision++; h.rerender();
    await act(async () => { await Promise.resolve(); resolve?.(frpPreviewFixture("WI_FLANGE", false)); }); expect(h.result.current.current).toBe(true); expect(spy.mock.calls[0]?.[1].aborted).toBe(true);
    spy.mockImplementationOnce(() => new Promise((_yes, no) => { reject = no; })); revision++; h.rerender(); h.unmount(); await act(async () => { reject?.(new Error("late")); await Promise.resolve(); });
    spy.mockResolvedValueOnce({ ...frpPreviewFixture("WI_FLANGE", false), geometry_invalid_reasons: [] });
    const initial = renderHook(() => useWIFrpSupportMomentPreview(r, revision, true, null)); await act(async () => { await Promise.resolve(); }); expect(initial.result.current.error).toBe("INVALID_GEOMETRY");
    spy.mockRejectedValueOnce("unknown"); revision++; initial.rerender(); await act(async () => { await Promise.resolve(); }); expect(initial.result.current.error).toBe("Preview request failed.");
    spy.mockRejectedValueOnce(new DOMException("abort", "AbortError")); revision++; initial.rerender(); await act(async () => { await Promise.resolve(); }); expect(initial.result.current.error).toBeNull(); initial.unmount();
  });
});

describe("Stage 4.3 dedicated workspace", () => {
  it("mounts from the selector and runs design only on explicit action", async () => {
    vi.spyOn(historical, "previewWIMomentSplice").mockImplementation(() => new Promise(() => undefined));
    const preview = vi.spyOn(client, "previewWIFrpSupportMoment").mockResolvedValue(frpPreviewFixture());
    const design = vi.spyOn(client, "designWIFrpSupportMoment").mockResolvedValue(frpDesignFixture());
    render(<MomentConnectionsWorkspace />);
    fireEvent.change(screen.getByLabelText("Connection type"), { target: { value: "WI_BEAM_FRP_SUPPORT_MAJOR_AXIS_MOMENT_CONNECTION" } });
    await screen.findByLabelText("frp-moment-test-viewer"); expect(design).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); await screen.findByText("EVALUATED_FAILURE_OUTRANKS_MISSING_QUALIFIED_SOURCE");
    expect(screen.getByText("Native governing: FIRST_ROW:TOP_FLANGE_ANGLE")).toBeInTheDocument();
    expect(frpSupportMomentVisibleFailures(frpDesignFixture().result).length).toBeGreaterThan(15);
    fireEvent.click(screen.getByText("Edit FX")); expect(screen.getByLabelText("Axial force P_L")).toHaveValue("-30");
    expect(screen.getByText(/Design results are stale/)).toBeInTheDocument(); expect(design).toHaveBeenCalledTimes(1);
    await waitFor(() => { expect(preview).toHaveBeenCalledTimes(2); }); fireEvent.click(screen.getByText("Select support"));
  });
  it("edits every input, keeps locked partners and clears incompatible geometry qualification", async () => {
    vi.useFakeTimers(); const spy = vi.spyOn(client, "previewWIFrpSupportMoment").mockResolvedValue(frpPreviewFixture()); const design = vi.spyOn(client, "designWIFrpSupportMoment");
    const view = render(<WIFrpSupportMomentWorkspace />); await act(async () => { await Promise.resolve(); });
    for (const input of view.container.querySelectorAll<HTMLInputElement>(".properties-sidebar input")) fireEvent.change(input, { target: { value: input.type === "number" ? "3" : Number.isFinite(Number(input.value)) ? String(Number(input.value) + .1) : "TEST_ONLY" } });
    for (const family of ["Flange angles", "Web clip angles"]) for (const group of ["Member bolts", "Support bolts"]) fireEvent.change(screen.getByLabelText(`${family} ${group} thread condition`), { target: { value: "INCLUDED" } });
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); }); const sent = spy.mock.calls.at(-1)?.[0];
    expect(sent?.top).toEqual(sent?.bottom); expect(sent?.positive_web).toEqual(sent?.negative_web); expect(sent?.top.support_fastener.thread_condition).toBe("INCLUDED"); expect(design).not.toHaveBeenCalled();
    for (const mode of modes) { fireEvent.change(screen.getByLabelText("Support configuration"), { target: { value: mode } }); fireEvent.change(screen.getByLabelText("Selected physical face"), { target: { value: supportFaces[mode][1] } }); }
    fireEvent.click(screen.getByRole("button", { name: "Load 4.3 SI" })); await act(async () => { await Promise.resolve(); }); expect(screen.getByLabelText("Beam Depth")).toHaveValue("254");
    fireEvent.change(screen.getByLabelText("Support configuration"), { target: { value: "WI_WEB" } });
    expect(screen.getByLabelText("Support Depth")).toHaveValue("406.4");
    fireEvent.click(screen.getByRole("button", { name: "Load 4.3 U.S." })); await act(async () => { await Promise.resolve(); }); expect(screen.getByLabelText("Beam Depth")).toHaveValue("10");
    for (const c of ["FZ", "MY", "MX"]) fireEvent.click(screen.getByText(`Edit ${c}`)); expect(screen.getByLabelText("Major shear V_V")).toHaveValue("-30");
    fireEvent.change(screen.getByLabelText("Axial force P_L"), { target: { value: "" } }); expect(screen.getByRole("alert")).toHaveTextContent("finite decimal"); expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(screen.queryByRole("option", { name: "316SS" })).toBeNull(); expect(screen.queryByLabelText(/Anchor embedment/)).toBeNull();
  }, 15000);
  it("shows retry, missing optional traces and design transport errors", async () => {
    const spy = vi.spyOn(client, "previewWIFrpSupportMoment").mockRejectedValueOnce(new Error("preview offline")); render(<WIFrpSupportMomentWorkspace />); expect(await screen.findByRole("alert")).toHaveTextContent("preview offline");
    const p = frpPreviewFixture(); spy.mockResolvedValue({ ...p, result: { ...p.result, support_contribution: null, support_reaction: null, equilibrium: null } }); fireEvent.click(screen.getByRole("button", { name: "Retry preview" })); await screen.findByLabelText("frp-moment-test-viewer");
    const design = vi.spyOn(client, "designWIFrpSupportMoment").mockRejectedValueOnce(new Error("design offline")).mockRejectedValueOnce("unknown").mockRejectedValueOnce(new DOMException("abort", "AbortError"));
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); expect(await screen.findByRole("alert")).toHaveTextContent("design offline");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); await screen.findByText("Design request failed.");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); await waitFor(() => { expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled(); }); expect(screen.queryByRole("alert")).toBeNull(); expect(design).toHaveBeenCalledTimes(3);
  });
  it("ignores late design success and unmounted failure, and renders source-only empty failures", async () => {
    vi.spyOn(client, "previewWIFrpSupportMoment").mockResolvedValue(frpPreviewFixture());
    let resolve: ((v: ReturnType<typeof frpDesignFixture>) => void) | undefined;
    let reject: ((e: unknown) => void) | undefined;
    const spy = vi.spyOn(client, "designWIFrpSupportMoment").mockImplementationOnce(() => new Promise(yes => { resolve = yes; }));
    const view = render(<WIFrpSupportMomentWorkspace />); await screen.findByLabelText("frp-moment-test-viewer");
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); expect(screen.getByRole("button", { name: "Running design check…" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Axial force P_L"), { target: { value: "21" } });
    await act(async () => { resolve?.(frpDesignFixture()); await Promise.resolve(); }); expect(screen.queryByRole("heading", { name: "Required evaluated failures" })).toBeNull();
    await waitFor(() => { expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled(); });
    const original = frpDesignFixture();
    spy.mockResolvedValueOnce({ ...original, result: { ...original.result, status: "SOURCE_REQUIRED", native_failed_checks: [], native_governing_check_ids: [], beam_bearings: [], support_local_checks: [] } });
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); await screen.findByText("No evaluated failures returned for this design.");
    expect(screen.getByText(/No native group selected/)).toBeInTheDocument();
    spy.mockResolvedValueOnce({ ...original, result: { ...original.result, native_failed_checks: original.result.native_failed_checks.map(c => ({ ...c, utilization: null, demand: null, design_resistance: null })) } });
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); await screen.findByText("EVALUATED_FAILURE_OUTRANKS_MISSING_QUALIFIED_SOURCE"); expect(screen.getAllByText("Unavailable / See trace").length).toBeGreaterThan(0);
    spy.mockImplementationOnce(() => new Promise((_yes, no) => { reject = no; })); fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); view.unmount();
    await act(async () => { reject?.(new Error("late")); await Promise.resolve(); });
  });
});

describe("Stage 4.3 failure trace does not recompute governing status", () => {
  it("retains every provider/attachment/bolt/region/source failure and defensive reason", () => {
    const d = frpDesignFixture().result;
    const provider = d.connector_results[2], attachment = d.attachment_results[0], bolt = d.common_web_bolts[0], local = d.beam_local_checks[0], support = d.support_bolts[0], zone = d.local_zone;
    if (provider?.detail?.instep == null || attachment === undefined || bolt === undefined || local === undefined || support === undefined || zone === null) throw new Error("Native fixture incomplete");
    const failing = { ...d, native_failed_checks: d.native_failed_checks.map(c => ({ ...c, result_id: "NO_COLON" })),
      connector_results: [
        { ...provider, core_fingerprint: "UNMATCHED", status: "FAIL", detail: { ...provider.detail, instep: { ...provider.detail.instep, passed: false }, body: { ...provider.detail.body, status: "FAIL" } } },
        { ...provider, status: "FAIL", detail: null },
      ], attachment_results: [{ ...attachment, check: { ...attachment.check, status: "FAIL" } }],
      common_web_bolts: [{ ...bolt, status: "FAIL" }], beam_local_checks: [{ ...local, scope_status: "FAIL" }],
      support_bolts: [{ ...support, status: "FAIL" }], support_local_checks: d.support_local_checks.map(c=>({...c,status:"FAIL"})), local_zone: { ...zone, status: "FAIL" },
    };
    const rows = frpSupportMomentVisibleFailures(failing);
    expect(rows.some(c => c.component === "UNMATCHED")).toBe(true);
    expect(rows.some(c => c.checkId === "Connector provider")).toBe(true);
    expect(rows.some(c => c.checkId === "QUALIFIED_LOCAL_SUPPORT_ZONE")).toBe(true);
    expect(rows.some(c => c.checkId === "NO_COLON")).toBe(true);
    const empty = { ...d, connector_results: [], attachment_results: [], beam_local_checks: [], beam_bearings: [], support_bolts: [], support_local_checks: [], common_web_bolts: [], native_failed_checks: [], local_zone: null };
    expect(frpSupportMomentVisibleFailures(empty)[0]?.reason).toContain("no individual failure record");
    expect(frpSupportMomentVisibleFailures({ ...empty, status: "SOURCE_REQUIRED" })).toEqual([]);
  });
});
