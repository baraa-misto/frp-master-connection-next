import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, assert, expect, it, vi } from "vitest";
import * as client from "../src/api/ssmcClient";
import type { SSMCRequest, SSMCResponse } from "../src/api/ssmcClient";
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
function mocks() {
  const load = vi.spyOn(client, "loadSSMC").mockResolvedValue(copy(data.us.request));
  const send = vi.spyOn(client, "evaluateSSMC").mockImplementation(r => Promise.resolve(response(r)));
  const convert = vi.spyOn(client, "convertSSMC").mockImplementation((_r, si) => Promise.resolve(copy(si ? data.si.request : data.us.request)));
  return { load, send, convert };
}
const current = () => screen.findByText("CURRENT BACKEND PREVIEW");
function edit(label: string, value: string) { fireEvent.change(screen.getByLabelText(new RegExp("^" + label.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&") + "$", "iu")), { target: { value } }); }

it("adds one Moment workspace without changing the initial selection or exposing stainless", async () => {
  mocks(); render(<MomentConnectionsWorkspace/>);
  expect(screen.getByText("Unchanged initial moment workspace")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Connection type"), { target: { value: "STAIR_STRINGER_MITER_CONNECTION" } });
  await current();
  expect(screen.queryByText("316 Stainless Steel")).toBeNull();
  expect(within(screen.getByLabelText("SSMC unit system")).getAllByRole("option")).toHaveLength(2);
  expect(screen.getByText(/CW basis — unknown cut/u)).toBeInTheDocument();
  await waitFor(() => { expect(probe.model?.cylinders.filter(c => c.kind === "BOLT")).toHaveLength(8); });
  for (const label of ["Geometry", "Demand", "Planar group response", "Complete response", "Plate resistance", "Member local transfer", "Hardware", "Qualification", "Design"]) expect(screen.getByText(label, { selector: "dt" })).toBeInTheDocument();
  expect(screen.getByText("Required missing coverage / failures")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
  await screen.findByText("Current design check: ENGINEERING_REVIEW_REQUIRED");
});

it("preserves last valid geometry, hides stale arrows/design and recovers through an awaited preview", async () => {
  const { send } = mocks(); render(<StairStringerMiterWorkspace/>); await current();
  edit("N", "8"); await current(); expect(probe.model?.appliedArrows[0]?.signedValue).toBe(8);
  fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); await screen.findByText(/Current design check:/u);
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

it("edits every geometry/hardware field without silently linking groups or repairing inputs", async () => {
  const { send } = mocks(); render(<StairStringerMiterWorkspace/>); await current();
  edit("SSMC source reference", "PUBLIC_TEXT"); edit("SSMC hardware source reference", "HARDWARE_TEXT"); await current();
  expect(send.mock.lastCall?.[0].source_reference).toBe("PUBLIC_TEXT");
  expect(send.mock.lastCall?.[0].fastener.source_reference).toBe("HARDWARE_TEXT");
  for (const [label, value] of [
    ["horizontal section form", "W_I"], ["inclined section form", "W_I"], ["Signed inclination (deg)", "35"], ["Plate side", "POS_Y"],
    ["Horizontal Length", "25"], ["Horizontal Depth", "11"], ["Horizontal Width", "5"], ["Horizontal Web thickness", "0.6"], ["Horizontal Flange thickness", "0.6"],
    ["Inclined Length", "26"], ["Inclined Depth", "12"], ["Inclined Width", "6"], ["Inclined Web thickness", "0.7"], ["Inclined Flange thickness", "0.7"],
    ["Plate Thickness", "0.6"], ["Plate Horizontal overlap", "9"], ["Plate Inclined overlap", "10"], ["Plate Horizontal depth", "5"], ["Plate Inclined depth", "6"], ["Plate Normal gap", "0.25"], ["Plate Corner radius", "0.1"], ["Plate Chamfer", "0.2"],
    ["horizontal_group rows", "3"], ["Horizontal group First from cut", "2"], ["Horizontal group Pitch", "1.5"], ["Horizontal group Gauge", "1.75"], ["Horizontal group Transverse offset", "0.1"],
    ["inclined_group rows", "3"], ["Inclined group First from cut", "2.25"], ["Inclined group Pitch", "1.6"], ["Inclined group Gauge", "1.8"], ["Inclined group Transverse offset", "-0.1"],
    ["Bolt Diameter", "0.625"], ["Bolt Hole diameter", "0.688"], ["Hardware Washer diameter", "1.5"], ["Hardware Washer thickness", "0.2"], ["Hardware Head across flats", "0.9"], ["Hardware Head height", "0.4"], ["Hardware Nut across flats", "0.9"], ["Hardware Nut height", "0.6"], ["Hardware End extension", "0.3"], ["Thread location", "INCLUDED"], ["N", "8"], ["V", "4"], ["M", "20"],
  ]) { assert(label !== undefined && value !== undefined); edit(label, value); }
  for (const group of ["horizontal_group", "inclined_group"]) for (const flag of ["ordinary_snug_tight", "slots", "equal_translational_stiffness"]) fireEvent.click(screen.getByLabelText(group + " " + flag));
  await current();
  const r = send.mock.lastCall?.[0]; assert(r);
  expect(r.source_reference).toBe(""); expect(r.fastener.source_reference).toBe("");
  expect(r.horizontal.depth.value).toBe("11"); expect(r.inclined.depth.value).toBe("12");
  expect(r.horizontal_group.first_from_cut.value).toBe("2"); expect(r.inclined_group.first_from_cut.value).toBe("2.25");
  expect(r.horizontal_group.slots).toBe(true); expect(r.inclined_group.equal_translational_stiffness).toBe(false);
  expect(r.M.value).toBe("20"); expect(r.plate.chamfer.value).toBe("0.2");
});

it("converts through the backend and preserves native exact trace rather than formatting inputs", async () => {
  const { convert } = mocks(); render(<StairStringerMiterWorkspace/>); await current();
  edit("SSMC unit system", "SI"); await waitFor(() => { expect(screen.getByLabelText("SSMC unit system")).toHaveValue("SI"); }); await current();
  expect(convert.mock.lastCall?.[1]).toBe(true);
  expect(screen.getByLabelText("Bolt Hole Diameter")).toHaveValue("14.3002");
  expect(screen.getByText("Exact engineering trace / references / machine codes")).toBeInTheDocument();
  edit("SSMC unit system", "US"); await waitFor(() => { expect(screen.getByLabelText("SSMC unit system")).toHaveValue("US"); }); await current();
  expect(convert.mock.lastCall?.[1]).toBe(false);
});

it("ignores stale preview and design completions after newer input", async () => {
  const { send } = mocks(); render(<StairStringerMiterWorkspace/>); await current();
  let resolveOld: ((r: SSMCResponse) => void) | undefined;
  send.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }));
  edit("N", "2"); await waitFor(() => { expect(resolveOld).toBeDefined(); });
  edit("N", "3"); await current();
  await act(async () => { resolveOld?.(data.us.response); await Promise.resolve(); });
  expect(probe.model?.appliedArrows[0]?.signedValue).toBe(3);
  send.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }));
  fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
  edit("N", "4"); await current();
  await act(async () => { resolveOld?.(data.us.response); await Promise.resolve(); });
  expect(screen.queryByText(/Current design check:/u)).toBeNull();
  expect(probe.model?.appliedArrows[0]?.signedValue).toBe(4);
});

it("reports load failures, retries, and reports operation failures without discarding valid geometry", async () => {
  const { load, send, convert } = mocks(); load.mockRejectedValueOnce(new Error("offline"));
  render(<StairStringerMiterWorkspace/>); await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Retry" })); await current();
  send.mockRejectedValueOnce(new Error("design offline")); fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
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
