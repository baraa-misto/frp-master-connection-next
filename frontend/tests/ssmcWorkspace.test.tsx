import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, assert, expect, it, vi } from "vitest";
import * as client from "../src/api/ssmcClient";
import type { SSMCAnalyticalRequest, SSMCAnalyticalResponse, SSMCRequest, SSMCResponse } from "../src/api/ssmcClient";
import type { SingleBoltSceneModel } from "../src/visualization/sceneModel";
import { StairStringerMiterWorkspace } from "../src/workspace/StairStringerMiterWorkspace";
import { MomentConnectionsWorkspace } from "../src/workspace/MomentConnectionsWorkspace";
import fixture from "./ssmcNativeFixtures.json";

const data = fixture as unknown as { us: { request: SSMCRequest; response: SSMCResponse }; si: { request: SSMCRequest; response: SSMCResponse } };
const probe = vi.hoisted(() => ({ model: null as SingleBoltSceneModel | null }));
vi.mock("../src/visualization/EngineeringScene", () => ({ default: ({ model }: { model: SingleBoltSceneModel }) => { probe.model = model; return <div data-testid="ssmc-scene"/>; } }));
vi.mock("../src/workspace/WIMomentSpliceWorkspace", () => ({ WIMomentSpliceWorkspace: () => <div>Unchanged initial moment workspace</div> }));
afterEach(() => { vi.restoreAllMocks(); probe.model = null; });
const copy = <T,>(v: T) => structuredClone(v);
function response(request: SSMCRequest) {
  const result = copy(request.unit_system === "SI" ? data.si.response : data.us.response);
  result.request_id = request.request_id; result.result.input = copy(request);
  return result;
}
function analyticalResponse(request: SSMCAnalyticalRequest): SSMCAnalyticalResponse {
  return {
    contract: "SSMC-3-ANALYTICAL-RC1", method: "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1", whole_connection_status: "ENGINEERING_REVIEW_REQUIRED",
    result: {
      contract: "SSMC-3-ANALYTICAL-RC1", method: "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1", whole_connection_status: "ENGINEERING_REVIEW_REQUIRED",
      request, existing_demand: response(request.physical).result, applicability_status: "ELIGIBLE", applicability_reasons: [],
      checks: [{ owner: "MITER_WEB_PLATE", path_id: "HORIZONTAL_WEB_GROUP:PIN", mode: "PIN_BEARING", status: "SOURCE_REQUIRED", reason: "TEST_SOURCE_REQUIRED", demand_N: 1, source_id: null, qualification_id: null }],
      blockers: ["PLATE_PRODUCT_QUALIFICATION_REQUIRED"], numerical_failures: [], action_reaction: [{ group_id: "HORIZONTAL_WEB_GROUP" }], member_cut_demands: [], cuts: { cuts: [], finite_coverage_proven: false, status: "ENGINEERING_REVIEW_REQUIRED" },
    },
  };
}
function mocks() {
  const load = vi.spyOn(client, "loadSSMC").mockResolvedValue(copy(data.us.request));
  const send = vi.spyOn(client, "evaluateSSMC").mockImplementation(r => Promise.resolve(response(r)));
  const convert = vi.spyOn(client, "convertSSMC").mockImplementation((_r, si) => Promise.resolve(copy(si ? data.si.request : data.us.request)));
  const design = vi.spyOn(client, "evaluateSSMCAnalytical").mockImplementation(r => Promise.resolve(analyticalResponse(r)));
  return { load, send, convert, design };
}
const current = () => screen.findByText("CURRENT BACKEND PREVIEW");
function edit(label: string, value: string) { fireEvent.change(screen.getByLabelText(new RegExp("^" + label.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&") + "$", "iu")), { target: { value } }); }
function completeDeclaration() {
  edit("Combination ID", "COMBO-1"); edit("Combination source", "Issued factored schedule"); edit("Actions already factored", "YES");
  edit("Time-effect category", "OTHER_LIVE"); edit("Time-effect reference", "Issued time schedule");
  edit("External actions at faying interface", "YES"); edit("Independent bolt-axis force (N)", "0"); edit("Independent out-of-plane moment (N-mm)", "0");
  for (const label of ["Imposed separation", "Non-contact gap", "Friction or preload credit", "Miter bearing credit"]) edit(label, "NO");
}
async function renderBeforeInitialPreview() {
  const { send } = mocks();
  send.mockImplementationOnce(() => new Promise<SSMCResponse>(() => undefined));
  render(<StairStringerMiterWorkspace/>);
  await waitFor(() => { expect(send).toHaveBeenCalledTimes(1); });
  return send;
}
async function awaitCurrentRequest(send: ReturnType<typeof mocks>["send"], check: (request: SSMCRequest) => void) {
  await waitFor(() => {
    const request = send.mock.lastCall?.[0];
    assert(request);
    check(request);
  });
  await current();
}

it("adds one Moment workspace without changing the initial selection or exposing stainless", async () => {
  const { design } = mocks(); render(<MomentConnectionsWorkspace/>);
  expect(screen.getByText("Unchanged initial moment workspace")).toBeInTheDocument();
  const selector = screen.getByLabelText("Connection type");
  expect(within(selector).getByRole("group", { name: "Stair connections" })).toContainElement(screen.getByRole("option", { name: "Stair Stringer Miter Connection" }));
  expect(within(selector).getByRole("group", { name: "Beam moment connections" })).not.toContainElement(screen.getByRole("option", { name: "Stair Stringer Miter Connection" }));
  fireEvent.change(screen.getByLabelText("Connection type"), { target: { value: "STAIR_STRINGER_MITER_CONNECTION" } });
  await current();
  expect(screen.queryByText("316 Stainless Steel")).toBeNull();
  expect(within(screen.getByLabelText("SSMC unit system")).getAllByRole("option")).toHaveLength(2);
  expect(screen.getByText(/Analytical method accepted/u)).toBeInTheDocument();
  await waitFor(() => { expect(probe.model?.cylinders.filter(c => c.kind === "BOLT")).toHaveLength(8); });
  for (const label of ["Geometry", "Demand", "Planar group response", "Complete response", "Plate resistance", "Member local transfer", "Hardware", "Qualification", "Design"]) expect(screen.getByText(label, { selector: "dt" })).toBeInTheDocument();
  expect(screen.getByText("Required missing coverage / failures")).toBeInTheDocument();
  expect(screen.getByLabelText("Design Status")).toHaveTextContent("STALE");
  expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
  completeDeclaration();
  fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
  await waitFor(() => { expect(design).toHaveBeenCalledTimes(1); });
  expect(screen.getByLabelText("Design Status")).toHaveTextContent("ENGINEERING_REVIEW_REQUIRED");
  expect(screen.getByLabelText("Qualification and source blockers")).toHaveTextContent("PLATE_PRODUCT_QUALIFICATION_REQUIRED");
  expect(screen.getByLabelText("Geometry / Model Status")).toHaveTextContent("VALID");
  fireEvent.change(selector, { target: { value: "WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE" } });
  expect(screen.queryByLabelText("SSMC inputs")).toBeNull();
  expect(screen.getByText("Unchanged initial moment workspace")).toBeInTheDocument();
});

it.each([
  ["CHANNEL", "CHANNEL", "-35", "NEG_Y", "2", "2"],
  ["CHANNEL", "W_I", "35", "POS_Y", "3", "2"],
  ["W_I", "CHANNEL", "-40", "POS_Y", "2", "3"],
  ["W_I", "W_I", "40", "NEG_Y", "3", "3"],
] as const)("sends public %s/%s physical inputs through the analytical route", async (horizontal, inclined, angle, side, horizontalRows, inclinedRows) => {
  const { send, design } = mocks(); render(<StairStringerMiterWorkspace/>); await current();
  edit("horizontal section form", horizontal); edit("inclined section form", inclined); edit("Signed inclination (deg)", angle);
  edit("Plate side", side); edit("horizontal_group rows", horizontalRows); edit("inclined_group rows", inclinedRows);
  edit("N", "-8"); edit("V", "4"); edit("M", "-20");
  await current(); completeDeclaration();
  fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
  await waitFor(() => { expect(design).toHaveBeenCalledTimes(1); });
  const request = design.mock.lastCall?.[0]; assert(request);
  expect([request.physical.horizontal.form, request.physical.inclined.form, request.physical.theta_deg, request.physical.plate.side]).toEqual([horizontal, inclined, angle, side]);
  expect([request.physical.horizontal_group.rows, request.physical.inclined_group.rows]).toEqual([Number(horizontalRows), Number(inclinedRows)]);
  expect([request.physical.N.value, request.physical.V.value, request.physical.M.value]).toEqual(["-8", "4", "-20"]);
  expect(request.action).toMatchObject({ basis: "FACTORED_LRFD", combination_id: "COMBO-1", time_effect_category: "OTHER_LIVE", already_factored: true });
  expect(request.physical.source_reference).toBe(""); expect(request.physical.fastener.source_reference).toBe("");
  expect(send.mock.calls.every(call => call[1] === "preview")).toBe(true);
});

it.each(["PASS", "FAIL", "ENGINEERING_REVIEW_REQUIRED", "SOURCE_REQUIRED", "NOT_APPLICABLE"] as const)("renders authoritative %s and mixed child status without client precedence", async status => {
  const { send, design } = mocks();
  design.mockImplementation(request => {
    const result = analyticalResponse(request);
    result.whole_connection_status = status; result.result.whole_connection_status = status;
    result.result.checks.push({ owner: "INCLINED_STRINGER", path_id: "I1", mode: "PULL_THROUGH", status: "NOT_APPLICABLE", reason: "SERVER_PROOF", demand_N: 0, source_id: null, qualification_id: null });
    return Promise.resolve(result);
  });
  render(<StairStringerMiterWorkspace/>); await current(); completeDeclaration();
  expect(screen.getByLabelText("Design Status")).toHaveTextContent("STALE");
  fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
  await waitFor(() => { expect(screen.getByLabelText("Design Status")).toHaveTextContent(status); });
  expect(screen.getByLabelText("Qualification and source blockers")).toHaveTextContent("PLATE_PRODUCT_QUALIFICATION_REQUIRED");
  expect(screen.getByText("SERVER_PROOF")).toBeInTheDocument();
  expect(screen.getByText("TEST_SOURCE_REQUIRED")).toBeInTheDocument();
  expect(screen.getByLabelText("Geometry / Model Status")).toHaveTextContent("VALID");
  fireEvent.click(screen.getByRole("button", { name: "Front" }));
  expect(screen.getByLabelText("Design Status")).toHaveTextContent(status);
  const count = send.mock.calls.length;
  edit("Combination ID", "COMBO-2");
  expect(screen.getByLabelText("Design Status")).toHaveTextContent("STALE");
  expect(screen.getByLabelText("Geometry / Model Status")).toHaveTextContent("VALID");
  expect(send.mock.calls).toHaveLength(count);
});

it("preserves last valid geometry, hides stale arrows/design and recovers through an awaited preview", async () => {
  const { send } = mocks(); render(<StairStringerMiterWorkspace/>); await current();
  edit("N", "8"); await current(); expect(probe.model?.appliedArrows[0]?.signedValue).toBe(8);
  completeDeclaration(); fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); await waitFor(() => { expect(screen.getByLabelText("Design Status")).toHaveTextContent("ENGINEERING_REVIEW_REQUIRED"); });
  const count = send.mock.calls.length;
  edit("N", "");
  expect(screen.getByText("LAST VALID PREVIEW — CURRENT INPUTS UNVERIFIED")).toBeInTheDocument();
  expect(probe.model?.appliedArrows).toEqual([]);
  expect(screen.getByText(/Design is stale/u)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
  expect(send.mock.calls).toHaveLength(count);
  edit("N", "-8"); await current(); expect(probe.model?.appliedArrows[0]?.signedValue).toBe(-8);
  send.mockRejectedValueOnce(new Error("SSMC_POLYGON_INVALID")); edit("Plate Horizontal overlap", "0");
  await screen.findByRole("alert"); expect(probe.model?.appliedArrows).toEqual([]);
  edit("Plate Horizontal overlap", "8"); await current();
});

it("does not expose source or strength overrides and clears untrusted references on edit", async () => {
  const send = await renderBeforeInitialPreview();
  expect(screen.queryByLabelText("SSMC source reference")).toBeNull();
  expect(screen.queryByLabelText("SSMC hardware source reference")).toBeNull();
  edit("N", "8");
  await awaitCurrentRequest(send, request => {
    expect(request.N.value).toBe("8");
    expect(request.source_reference).toBe("");
    expect(request.fastener.source_reference).toBe("");
  });
});

it("edits every member and plate geometry field without linking or repair", async () => {
  const send = await renderBeforeInitialPreview();
  for (const [label, value] of [
    ["horizontal section form", "W_I"], ["inclined section form", "W_I"], ["Signed inclination (deg)", "35"], ["Plate side", "POS_Y"],
    ["Horizontal Length", "25"], ["Horizontal Depth", "11"], ["Horizontal Width", "5"], ["Horizontal Web thickness", "0.6"], ["Horizontal Flange thickness", "0.6"],
    ["Inclined Length", "26"], ["Inclined Depth", "12"], ["Inclined Width", "6"], ["Inclined Web thickness", "0.7"], ["Inclined Flange thickness", "0.7"],
    ["Plate Thickness", "0.6"], ["Plate Horizontal overlap", "9"], ["Plate Inclined overlap", "10"], ["Plate Horizontal depth", "5"], ["Plate Inclined depth", "6"], ["Plate Normal gap", "0.25"], ["Plate Corner radius", "0.1"], ["Plate Chamfer", "0.2"],
  ]) { assert(label !== undefined && value !== undefined); edit(label, value); }
  await awaitCurrentRequest(send, request => {
    expect(request.theta_deg).toBe("35"); expect(request.plate.side).toBe("POS_Y");
    expect(request.horizontal.form).toBe("W_I"); expect(request.inclined.form).toBe("W_I");
    expect([request.horizontal.length.value, request.horizontal.depth.value, request.horizontal.width.value, request.horizontal.web_thickness.value, request.horizontal.flange_thickness.value]).toEqual(["25", "11", "5", "0.6", "0.6"]);
    expect([request.inclined.length.value, request.inclined.depth.value, request.inclined.width.value, request.inclined.web_thickness.value, request.inclined.flange_thickness.value]).toEqual(["26", "12", "6", "0.7", "0.7"]);
    expect([request.plate.thickness.value, request.plate.horizontal_overlap.value, request.plate.inclined_overlap.value, request.plate.horizontal_depth.value, request.plate.inclined_depth.value, request.plate.normal_gap.value, request.plate.corner_radius.value, request.plate.chamfer.value]).toEqual(["0.6", "9", "10", "5", "6", "0.25", "0.1", "0.2"]);
  });
});

it("edits both bolt groups independently without cross-group linking", async () => {
  const send = await renderBeforeInitialPreview();
  for (const [label, value] of [
    ["horizontal_group rows", "3"], ["Horizontal group First from cut", "2"], ["Horizontal group Pitch", "1.5"], ["Horizontal group Gauge", "1.75"], ["Horizontal group Transverse offset", "0.1"],
    ["inclined_group rows", "3"], ["Inclined group First from cut", "2.25"], ["Inclined group Pitch", "1.6"], ["Inclined group Gauge", "1.8"], ["Inclined group Transverse offset", "-0.1"],
  ]) { assert(label !== undefined && value !== undefined); edit(label, value); }
  for (const group of ["horizontal_group", "inclined_group"] as const) for (const flag of ["ordinary_snug_tight", "slots", "equal_translational_stiffness"] as const) fireEvent.click(screen.getByLabelText(group + " " + flag));
  await awaitCurrentRequest(send, request => {
    expect([request.horizontal_group.rows, request.horizontal_group.first_from_cut.value, request.horizontal_group.pitch.value, request.horizontal_group.gauge.value, request.horizontal_group.transverse_offset.value]).toEqual([3, "2", "1.5", "1.75", "0.1"]);
    expect([request.inclined_group.rows, request.inclined_group.first_from_cut.value, request.inclined_group.pitch.value, request.inclined_group.gauge.value, request.inclined_group.transverse_offset.value]).toEqual([3, "2.25", "1.6", "1.8", "-0.1"]);
    for (const group of ["horizontal_group", "inclined_group"] as const) for (const flag of ["ordinary_snug_tight", "slots", "equal_translational_stiffness"] as const) expect(request[group][flag]).toBe(!data.us.request[group][flag]);
  });
});

it("edits every hardware and action field without silent repair", async () => {
  const send = await renderBeforeInitialPreview();
  for (const [label, value] of [
    ["Bolt Diameter", "0.625"], ["Bolt Hole diameter", "0.688"], ["Hardware Washer diameter", "1.5"], ["Hardware Washer thickness", "0.2"], ["Hardware Head across flats", "0.9"], ["Hardware Head height", "0.4"], ["Hardware Nut across flats", "0.9"], ["Hardware Nut height", "0.6"], ["Hardware End extension", "0.3"], ["Thread location", "INCLUDED"], ["N", "8"], ["V", "4"], ["M", "20"],
  ]) { assert(label !== undefined && value !== undefined); edit(label, value); }
  await awaitCurrentRequest(send, request => {
    expect([request.fastener.diameter.value, request.fastener.hole_diameter.value]).toEqual(["0.625", "0.688"]);
    expect([request.fastener.hardware.washer_diameter.value, request.fastener.hardware.washer_thickness.value, request.fastener.hardware.head_across_flats.value, request.fastener.hardware.head_height.value, request.fastener.hardware.nut_across_flats.value, request.fastener.hardware.nut_height.value, request.fastener.hardware.end_extension.value]).toEqual(["1.5", "0.2", "0.9", "0.4", "0.9", "0.6", "0.3"]);
    expect(request.fastener.threads).toBe("INCLUDED");
    expect([request.N.value, request.V.value, request.M.value]).toEqual(["8", "4", "20"]);
  });
});

it("converts through the backend and preserves native exact trace rather than formatting inputs", async () => {
  const { convert, design } = mocks(); render(<StairStringerMiterWorkspace/>); await current();
  edit("SSMC unit system", "SI"); await waitFor(() => { expect(screen.getByLabelText("SSMC unit system")).toHaveValue("SI"); }); await current();
  expect(convert.mock.lastCall?.[1]).toBe(true);
  expect(screen.getByLabelText("Bolt Hole Diameter")).toHaveValue("14.3002");
  expect(screen.getByText("Exact engineering trace / references / machine codes")).toBeInTheDocument();
  completeDeclaration(); fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
  await waitFor(() => { expect(design).toHaveBeenCalledTimes(1); });
  expect(design.mock.lastCall?.[0].physical).toMatchObject({ unit_system: "SI", N: data.si.request.N, V: data.si.request.V, M: data.si.request.M });
  expect(screen.getByLabelText("Design Status")).toHaveTextContent("ENGINEERING_REVIEW_REQUIRED");
  edit("SSMC unit system", "US"); await waitFor(() => { expect(screen.getByLabelText("SSMC unit system")).toHaveValue("US"); }); await current();
  expect(convert.mock.lastCall?.[1]).toBe(false);
  expect(screen.getByLabelText("Design Status")).toHaveTextContent("STALE");
});

it("keeps a prior design stale even when edited inputs are restored", async () => {
  const { design } = mocks(); render(<StairStringerMiterWorkspace/>); await current(); completeDeclaration();
  fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
  await waitFor(() => { expect(design).toHaveBeenCalledTimes(1); });
  expect(screen.getByLabelText("Design Status")).toHaveTextContent("ENGINEERING_REVIEW_REQUIRED");
  edit("Combination ID", "TEMP"); edit("Combination ID", "COMBO-1");
  expect(screen.getByLabelText("Design Status")).toHaveTextContent("STALE");
  const originalN = data.us.request.N.value;
  edit("N", "17"); edit("N", originalN); await current();
  expect(screen.getByLabelText("Design Status")).toHaveTextContent("STALE");
});

it("ignores stale preview and analytical design completions after newer input", async () => {
  const { send, design } = mocks(); render(<StairStringerMiterWorkspace/>); await current();
  let resolveOld: ((r: SSMCResponse) => void) | undefined;
  send.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }));
  edit("N", "2"); await waitFor(() => { expect(resolveOld).toBeDefined(); });
  edit("N", "3"); await current();
  await act(async () => { resolveOld?.(data.us.response); await Promise.resolve(); });
  expect(probe.model?.appliedArrows[0]?.signedValue).toBe(3);
  let resolveOldDesign: ((r: SSMCAnalyticalResponse) => void) | undefined;
  design.mockImplementationOnce(() => new Promise(resolve => { resolveOldDesign = resolve; }));
  completeDeclaration();
  fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
  edit("N", "4"); await current();
  const oldRequest = design.mock.lastCall?.[0]; assert(oldRequest);
  await act(async () => { resolveOldDesign?.(analyticalResponse(oldRequest)); await Promise.resolve(); });
  expect(screen.getByLabelText("Design Status")).toHaveTextContent("STALE");
  expect(probe.model?.appliedArrows[0]?.signedValue).toBe(4);
});

it("reports load failures, retries, and reports operation failures without discarding valid geometry", async () => {
  const { load, design, convert } = mocks(); load.mockRejectedValueOnce(new Error("offline"));
  render(<StairStringerMiterWorkspace/>); await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Retry" })); await current();
  completeDeclaration(); design.mockRejectedValueOnce(new Error("design offline")); fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
  await screen.findByText("Error: design offline");
  convert.mockRejectedValueOnce(new Error("conversion offline")); edit("SSMC unit system", "SI"); await screen.findByText("Error: conversion offline");
  expect(screen.getByLabelText("SSMC unit system")).toHaveValue("US");
});

it("ignores pending defaults after unmount and preserves no-input state on intentional abort", async () => {
  const { load } = mocks(); let done: ((r: SSMCRequest) => void) | undefined;
  load.mockImplementationOnce(() => new Promise(resolve => { done = resolve; }));
  const view = render(<StairStringerMiterWorkspace/>); view.unmount();
  await act(async () => { done?.(data.us.request); await Promise.resolve(); });
  load.mockRejectedValueOnce(new DOMException("stop", "AbortError")); render(<StairStringerMiterWorkspace/>);
  await act(async () => { await Promise.resolve(); }); expect(screen.queryByRole("alert")).toBeNull();
});

it("ignores aborted preview and operation errors and stale unit conversion", async () => {
  const { send, convert } = mocks(); render(<StairStringerMiterWorkspace/>); await current();
  send.mockRejectedValueOnce(new DOMException("stop", "AbortError")); edit("N", "9");
  await waitFor(() => { expect(send.mock.lastCall?.[0].N.value).toBe("9"); });
  expect(screen.queryByRole("alert")).toBeNull();
  edit("N", "10"); await current();
  convert.mockRejectedValueOnce(new DOMException("stop", "AbortError")); edit("SSMC unit system", "SI");
  await waitFor(() => { expect(screen.getByLabelText("SSMC unit system")).not.toBeDisabled(); });
  expect(screen.queryByRole("alert")).toBeNull();
  let rejectOld: ((e: Error) => void) | undefined;
  convert.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectOld = reject; }));
  edit("SSMC unit system", "SI"); edit("N", "11"); await current();
  await act(async () => { rejectOld?.(new Error("stale conversion failure")); await Promise.resolve(); });
  expect(screen.queryByRole("alert")).toBeNull();
  let resolveOld: ((r: SSMCRequest) => void) | undefined;
  convert.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }));
  edit("SSMC unit system", "SI"); edit("N", "12"); await current();
  await act(async () => { resolveOld?.(data.si.request); await Promise.resolve(); });
  expect(screen.getByLabelText("N")).toHaveValue("12");
  expect(screen.getByLabelText("SSMC unit system")).toHaveValue("US");
});
