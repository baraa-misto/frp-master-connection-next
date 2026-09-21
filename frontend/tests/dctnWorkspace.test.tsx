import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, assert, expect, it, vi } from "vitest";
import * as client from "../src/api/dctn3bClient";
import type { DCTNArrangement, DCTN3BRequest as DCTNRequest, DCTN3BResponse as DCTNResponse } from "../src/api/dctnContracts";
import type { SingleBoltSceneModel } from "../src/visualization/sceneModel";
import { DoubleChannelTrussNodeWorkspace } from "../src/workspace/DoubleChannelTrussNodeWorkspace";
import { ShearConnectionsWorkspace } from "../src/workspace/ShearConnectionsWorkspace";
import fixture from "./dctn3bNativeFixtures.json";

const data = fixture as unknown as { request: DCTNRequest; preview: DCTNResponse; design: DCTNResponse; siRequest: DCTNRequest; siPreview: DCTNResponse; arrangements: Record<DCTNArrangement, { request: DCTNRequest; preview: DCTNResponse }> };
const probe = vi.hoisted(() => ({ model: null as SingleBoltSceneModel | null }));
vi.mock("../src/visualization/EngineeringScene", () => ({ default: ({ model }: { model: SingleBoltSceneModel }) => { probe.model = model; return <div data-testid="native-scene"/>; } }));
vi.mock("../src/workspace/SingleBoltEngineeringWorkspace", () => ({ SingleBoltEngineeringWorkspace: () => <div>Unchanged Direct workspace boundary</div> }));
afterEach(() => { vi.restoreAllMocks(); probe.model = null; });
const copy = <T,>(value: T) => structuredClone(value);
const first = <T,>(items: readonly T[]): T => { const value = items[0]; assert(value !== undefined); return value; };

function mocks() {
  const defaults = vi.spyOn(client, "loadDCTN3BDefaults").mockImplementation(a => Promise.resolve(copy(data.arrangements[a].request)));
  const convert = vi.spyOn(client, "convertDCTN3BUnits").mockImplementation((_r, si) => Promise.resolve(copy(si ? data.siRequest : data.request)));
  const send = vi.spyOn(client, "requestDCTN3B").mockImplementation((kind, request) => {
    // Transport/state test: native fixed geometry fixtures, not an alternative
    // engineering solver. Browser/API tests exercise recalculated geometry.
    const response = copy(kind === "design-check" ? data.design : request.unit_system === "SI" ? data.siPreview : data.arrangements[request.arrangement].preview);
    response.result.preview.input.members.forEach((member, index) => { const input = request.members[index]; if (input !== undefined) member.P = copy(input.P); });
    return Promise.resolve(response);
  });
  return { defaults, convert, send };
}

it("mounts the controlled no-body startup and exposes source-required design truthfully", async () => {
  const { send } = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>);
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(within(screen.getByLabelText("DCTN unit system")).getAllByRole("option").map(o => o.textContent)).toEqual(["U.S. Units", "S.I. Units"]);
  expect(within(screen.getByLabelText("DCTN arrangement")).getAllByRole("option")).toHaveLength(5);
  expect(screen.queryByText("316 Stainless Steel")).toBeNull();
  expect(screen.getByLabelText("V Bolt rows along member axis")).toHaveValue("2");
  expect(screen.queryByLabelText("V W/I transverse offset magnitude")).toBeNull();
  await waitFor(() => { expect(probe.model?.cylinders.filter(c => c.kind === "BOLT")).toHaveLength(2); });
  fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
  const result = await screen.findByRole("region", { name: "DCTN design results" });
  expect(within(result).getByRole("heading", { name: "ENGINEERING_REVIEW_REQUIRED" })).toBeInTheDocument();
  expect(result).toHaveTextContent("DCTN_HARDWARE_SOURCE_OR_INSTALLATION_NOT_QUALIFIED");
  expect(result).toHaveTextContent("Global design certified: No.");
  expect(send.mock.lastCall?.[0]).toBe("design-check");
});

it("keeps LAST VALID geometry, hides stale arrows and checks, and recovers automatically", async () => {
  const { send } = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>); await screen.findByText("CURRENT BACKEND PREVIEW");
  fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); await screen.findByRole("region", { name: "DCTN design results" });
  const calls = send.mock.calls.length;
  fireEvent.change(screen.getByLabelText("V Axial P"), { target: { value: "" } });
  expect(screen.getByText("LAST VALID PREVIEW — CURRENT INPUTS UNVERIFIED")).toBeInTheDocument();
  expect(probe.model?.appliedArrows).toEqual([]);
  expect(screen.queryByRole("region", { name: "DCTN design results" })).toBeNull();
  expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
  expect(send.mock.calls).toHaveLength(calls);
  fireEvent.change(screen.getByLabelText("V Axial P"), { target: { value: "-4" } });
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(first(probe.model?.appliedArrows ?? []).signedValue).toBe(-4);
  expect(first(probe.model?.appliedArrows ?? []).axis.z).toBe(-1);
  expect(first(send.mock.lastCall?.[1].members ?? []).P.value).toBe("-4");
});

it.each(["invalid", "network", "non_error"])("retains last-valid on %s preview and does not call it current", async mode => {
  const { send } = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>); await screen.findByText("CURRENT BACKEND PREVIEW");
  if (mode === "invalid") send.mockResolvedValueOnce({ ...data.preview, geometry_status: "INVALID_GEOMETRY", geometry_invalid_reasons: ["DCTN_INVALID_GEOMETRY:TEST_COLLISION"] });
  else send.mockRejectedValueOnce(mode === "network" ? new Error("network unavailable") : "failure");
  fireEvent.change(screen.getByLabelText("V Axial P"), { target: { value: "2" } });
  await screen.findByRole("alert");
  expect(screen.getByText("LAST VALID PREVIEW — CURRENT INPUTS UNVERIFIED")).toBeInTheDocument();
  expect(probe.model?.appliedArrows).toEqual([]);
});

it("ignores an older response arriving after a newer edit", async () => {
  const { send } = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>); await screen.findByText("CURRENT BACKEND PREVIEW");
  let resolveOld: ((response: DCTNResponse) => void) | undefined;
  send.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }));
  fireEvent.change(screen.getByLabelText("V Axial P"), { target: { value: "2" } });
  await waitFor(() => { expect(resolveOld).toBeDefined(); });
  fireEvent.change(screen.getByLabelText("V Axial P"), { target: { value: "3" } });
  await screen.findByText("CURRENT BACKEND PREVIEW");
  await act(async () => { resolveOld?.(data.preview); await Promise.resolve(); });
  expect(first(probe.model?.appliedArrows ?? []).signedValue).toBe(3);
});

it("links D1/D2 section on activation without linking placement, force or length", async () => {
  const { send } = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>); await screen.findByText("CURRENT BACKEND PREVIEW");
  fireEvent.change(screen.getByLabelText("DCTN arrangement"), { target: { value: "ONE_INCLINED" } });
  await screen.findByLabelText("D1 section form");
  fireEvent.change(screen.getByLabelText("D1 section form"), { target: { value: "W_I" } });
  await screen.findByLabelText("D1 Flange width");
  fireEvent.change(screen.getByLabelText("DCTN arrangement"), { target: { value: "TWO_INCLINED" } });
  await screen.findByLabelText("D2 section form");
  expect(screen.getByLabelText("D2 section form")).toHaveValue("W_I");
  expect(screen.queryByLabelText(/direction [XYZ]/i)).toBeNull();
  expect(screen.getByLabelText("D1 Inclination angle (deg)")).toHaveValue("126.86989764584402");
  expect(screen.getByLabelText("D2 Inclination angle (deg)")).toHaveValue("53.13010235415599");
  fireEvent.change(screen.getByLabelText("D1 Inclination angle (deg)"), { target: { value: "145" } });
  expect(screen.getByLabelText("D2 Inclination angle (deg)")).toHaveValue("53.13010235415599");
  fireEvent.change(screen.getByLabelText("D2 Inclination angle (deg)"), { target: { value: "50" } });
  expect(screen.getByLabelText("D1 Inclination angle (deg)")).toHaveValue("145");
  fireEvent.change(screen.getByLabelText("D2 Flange width"), { target: { value: "5" } });
  expect(screen.getByLabelText("D1 Flange width")).toHaveValue("5");
  fireEvent.change(screen.getByLabelText("D1 Length"), { target: { value: "30" } });
  expect(screen.getByLabelText("D2 Length")).toHaveValue("24");
  fireEvent.change(screen.getByLabelText("D2 Axial P"), { target: { value: "4" } });
  expect(screen.getByLabelText("D1 Axial P")).toHaveValue("1");
  await waitFor(() => {
    expect(send.mock.lastCall?.[1].arrangement).toBe("TWO_INCLINED");
    expect(send.mock.lastCall?.[1].members.map(m => m.slot)).toEqual(["D1", "D2"]);
    expect(send.mock.lastCall?.[1].members.map(m => m.inclination_deg)).toEqual(["145", "50"]);
    expect(send.mock.lastCall?.[1].members.map(m => m.P.value)).toEqual(["1", "4"]);
  });
  fireEvent.change(screen.getByLabelText("DCTN arrangement"), { target: { value: "VERTICAL_TWO_INCLINED" } });
  await waitFor(() => {
    expect(send.mock.lastCall?.[1].arrangement).toBe("VERTICAL_TWO_INCLINED");
    expect(send.mock.lastCall?.[1].members.map(m => m.slot)).toEqual(["V", "D1", "D2"]);
  });
  expect(screen.getByLabelText("D1 Flange width")).toHaveValue("5");
  expect(screen.getByLabelText("D2 Flange width")).toHaveValue("5");
  fireEvent.change(screen.getByLabelText("DCTN arrangement"), { target: { value: "VERTICAL_ONLY" } });
  await waitFor(() => {
    expect(screen.queryByLabelText("D1 Flange width")).toBeNull();
    expect(screen.queryByLabelText("D2 Flange width")).toBeNull();
    expect(send.mock.lastCall?.[1].arrangement).toBe("VERTICAL_ONLY");
    expect(send.mock.lastCall?.[1].members.map(m => m.slot)).toEqual(["V"]);
  });
});

it("clears source bindings on engineering edits, retains explicit source entry, and uses native unit conversion", async () => {
  const { send, convert } = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>); await screen.findByText("CURRENT BACKEND PREVIEW");
  for (const label of ["V material_source_reference", "V local_path_source_reference", "Channel material source reference", "Shared Channel local-path source reference", "Hardware source reference"]) fireEvent.change(screen.getByLabelText(label), { target: { value: "SOURCE" } });
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(send.mock.lastCall?.[1].fastener.source_reference).toBe("SOURCE");
  fireEvent.change(screen.getByLabelText("V Bolt rows along member axis"), { target: { value: "1" } });
  expect(screen.getByLabelText("V Row pitch")).toBeDisabled();
  expect(screen.getByLabelText("Hardware source reference")).toHaveValue("");
  await screen.findByText("CURRENT BACKEND PREVIEW");
  fireEvent.change(screen.getByLabelText("DCTN unit system"), { target: { value: "SI" } });
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(convert.mock.lastCall?.[1]).toBe(true);
  expect(screen.getByLabelText("Bolt Hole Diameter")).toHaveValue("14.3002");
});

it("reports initial bootstrap failure and supports a clean retry", async () => {
  const { defaults } = mocks(); defaults.mockRejectedValueOnce(new Error("offline"));
  render(<DoubleChannelTrussNodeWorkspace/>);
  await screen.findByRole("button", { name: "Retry defaults" });
  fireEvent.click(screen.getByRole("button", { name: "Retry defaults" }));
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(defaults).toHaveBeenCalledTimes(2);
});

it("edits every physical input without changing the no-body contract", async () => {
  const { send } = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>); await screen.findByText("CURRENT BACKEND PREVIEW");
  fireEvent.change(screen.getByLabelText("V section form"), { target: { value: "W_I" } });
  const labels = ["Channel Length", "Channel Depth", "Channel Flange Width", "Channel Web Thickness", "Channel Flange Thickness", "V Length", "V Depth", "V Flange width", "V Web thickness", "V Flange Thickness", "V Member Horizontal Location", "V Member Vertical Location", "V First bolt row from member end", "V Row pitch", "V W/I transverse offset magnitude", "Bolt Diameter", "Bolt Hole Diameter", "Hardware Washer Diameter", "Hardware Washer Thickness", "Hardware Head Across Flats", "Hardware Head Height", "Hardware Nut Across Flats", "Hardware Nut Height", "Hardware End Extension"];
  const edits = labels.map((label) => {
    const input = screen.getByLabelText<HTMLInputElement>(label);
    return { input, raw: String(Number(input.value) + 0.01) };
  });
  act(() => {
    for (const { input, raw } of edits) fireEvent.change(input, {target:{value:raw}});
    fireEvent.change(screen.getByLabelText("DCTN thread location"), {target:{value:"INCLUDED"}});
    fireEvent.click(screen.getByRole("checkbox", {name:"Snug-tight installation"}));
  });
  for (const { input, raw } of edits) expect(input).toHaveValue(raw);
  await waitFor(() => {
    const latest = send.mock.lastCall?.[1];
    expect(latest?.members[0]?.section.form).toBe("W_I");
    expect(latest?.fastener.threads_excluded).toBe(false);
    expect(latest?.fastener.snug_tight).toBe(false);
    expect(latest?.members[0]?.pattern.wi_offset.value).toBe("1.01");
  });
  fireEvent.change(screen.getByLabelText("V section form"), {target:{value:"SOLID_RECTANGLE"}});
  await waitFor(() => {
    expect(screen.queryByLabelText("V Web thickness")).toBeNull();
    expect(screen.queryByLabelText("V Flange Thickness")).toBeNull();
    expect(send.mock.lastCall?.[1].members[0]?.section.form).toBe("SOLID_RECTANGLE");
  });
  expect(screen.queryByText("316 Stainless Steel")).toBeNull();
});

it.each(["error", "non_error", "abort"])("reports a %s configuration failure without replacing accepted geometry", async kind => {
  const { convert } = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>); await screen.findByText("CURRENT BACKEND PREVIEW");
  const before = probe.model;
  convert.mockRejectedValueOnce(kind === "error" ? new Error("unit service unavailable") : kind === "abort" ? new DOMException("cancelled", "AbortError") : "unavailable");
  fireEvent.change(screen.getByLabelText("DCTN unit system"), {target:{value:"SI"}});
  await waitFor(() => { expect(screen.getByLabelText("DCTN unit system")).toBeEnabled(); });
  if (kind === "abort") expect(screen.queryByRole("alert")).toBeNull();
  else expect(await screen.findByRole("alert")).toHaveTextContent(kind === "error" ? "unit service unavailable" : "Configuration unavailable.");
  expect(probe.model?.boxes).toEqual(before?.boxes);
  expect(screen.getByLabelText("DCTN unit system")).toHaveValue("US");
});

it.each(["error", "non_error", "abort"])("does not fabricate checks for a %s design failure", async kind => {
  const { send } = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>); await screen.findByText("CURRENT BACKEND PREVIEW");
  send.mockRejectedValueOnce(kind === "error" ? new Error("design service unavailable") : kind === "abort" ? new DOMException("cancelled", "AbortError") : "unavailable");
  fireEvent.click(screen.getByRole("button", {name:"Run Design Check"}));
  await waitFor(() => { expect(screen.getByRole("button", {name:"Run Design Check"})).toBeEnabled(); });
  if (kind === "abort") expect(screen.queryByRole("alert")).toBeNull();
  else expect(await screen.findByRole("alert")).toHaveTextContent(kind === "error" ? "design service unavailable" : "Design unavailable.");
  expect(screen.queryByRole("region", {name:"DCTN design results"})).toBeNull();
});

it("renders native evaluated and source-required check rows without changing their statuses", async () => {
  const { send } = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>); await screen.findByText("CURRENT BACKEND PREVIEW");
  // Rendering-contract fixtures only; not qualification records or resistance oracles.
  const response = copy(data.design);
  assert(response.result.design !== null);
  const checks = [
    {check_id:"TEST_NATIVE_FAIL",owner_id:"V",status:"FAIL",demand:{value:"2",unit:"kip"},resistance:{value:"1",unit:"kip"},source_reference:"TEST_ONLY",native_trace:null},
    {check_id:"TEST_MISSING",owner_id:"V",status:"SOURCE_REQUIRED",demand:null,resistance:null,source_reference:"",native_trace:null},
  ];
  send.mockResolvedValueOnce({...response,result:{...response.result,design:{...response.result.design,checks,whole_connection_status:"FAIL"}}});
  fireEvent.click(screen.getByRole("button", {name:"Run Design Check"}));
  const result = await screen.findByRole("region", {name:"DCTN design results"});
  expect(result).toHaveTextContent("2 kip / 1 kip");
  expect(result).toHaveTextContent("— / —");
  expect(within(result).getByRole("heading", {name:"FAIL"})).toBeInTheDocument();
  expect(result).toHaveTextContent("DCTN_HARDWARE_SOURCE_OR_INSTALLATION_NOT_QUALIFIED");
});

it("ignores late configuration and design responses after a newer engineering edit", async () => {
  const { convert, send } = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>); await screen.findByText("CURRENT BACKEND PREVIEW");
  let finishUnits: ((value: DCTNRequest) => void) | undefined;
  convert.mockImplementationOnce(() => new Promise(resolve => {finishUnits=resolve;}));
  fireEvent.change(screen.getByLabelText("DCTN unit system"), {target:{value:"SI"}});
  fireEvent.change(screen.getByLabelText("V Axial P"), {target:{value:"2"}});
  await act(async () => {finishUnits?.(data.siRequest); await Promise.resolve();});
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(screen.getByLabelText("DCTN unit system")).toHaveValue("US");
  let finishDesign: ((value: DCTNResponse) => void) | undefined;
  send.mockImplementationOnce(() => new Promise(resolve => {finishDesign=resolve;}));
  fireEvent.click(screen.getByRole("button", {name:"Run Design Check"}));
  fireEvent.change(screen.getByLabelText("V Axial P"), {target:{value:"3"}});
  await act(async () => {finishDesign?.(data.design); await Promise.resolve();});
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(screen.queryByRole("region", {name:"DCTN design results"})).toBeNull();
});

it("reports non-Error bootstrap rejection and ignores completion after unmount", async () => {
  const { defaults } = mocks();
  defaults.mockRejectedValueOnce("offline");
  const view = render(<DoubleChannelTrussNodeWorkspace/>);
  expect(await screen.findByRole("alert")).toHaveTextContent("DCTN defaults unavailable.");
  let resolve: ((value:DCTNRequest)=>void) | undefined;
  defaults.mockImplementationOnce(() => new Promise(done => {resolve=done;}));
  fireEvent.click(screen.getByRole("button",{name:"Retry defaults"}));
  view.unmount();
  await act(async () => {resolve?.(data.request); await Promise.resolve();});
  expect(screen.queryByText("CURRENT BACKEND PREVIEW")).toBeNull();
});

it("declares exactly one additive no-body entry in the existing shear selector", async () => {
  mocks(); render(<ShearConnectionsWorkspace/>);
  expect(screen.getByText("Unchanged Direct workspace boundary")).toBeInTheDocument();
  const selector = screen.getByLabelText("Connection type");
  expect(within(selector).getAllByRole("option",{name:"Double-Channel Truss Node"})).toHaveLength(1);
  fireEvent.change(selector,{target:{value:"DOUBLE_CHANNEL_TRUSS_NODE_CONNECTION"}});
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(screen.queryByText("316 Stainless Steel")).toBeNull();
});

it("renders unresolved native response evidence as unproven, never exact", async () => {
  const {send}=mocks();
  const response=copy(data.preview);
  const preview=response.result.preview;
  assert(preview.historical_preview !== null);
  // Rendering contract only: the native response owns these flags and reasons.
  send.mockResolvedValueOnce({...response,result:{...response.result,preview:{...preview,historical_preview:{...preview.historical_preview,response:{...preview.historical_preview.response,status:"UNQUALIFIED",reasons:["TEST_NATIVE_UNPROVEN"],rows:preview.historical_preview.response.rows.map(row=>({...row,member_force_closes:false,member_moment_closes:false}))}}}}});
  render(<DoubleChannelTrussNodeWorkspace/>);
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(screen.getByText("TEST_NATIVE_UNPROVEN")).toBeInTheDocument();
  expect(screen.getAllByText("Unproven / Unproven")).toHaveLength(2);
});

it("uses invalid status when the native invalid reason list is empty", async () => {
  const {send}=mocks();
  send.mockResolvedValueOnce({...data.preview,geometry_status:"INVALID_GEOMETRY",geometry_invalid_reasons:[]});
  render(<DoubleChannelTrussNodeWorkspace/>);
  expect(await screen.findByRole("alert")).toHaveTextContent("INVALID_GEOMETRY");
  expect(screen.getByText("WAITING FOR VALID GEOMETRY")).toBeInTheDocument();
  expect(screen.getByRole("button",{name:"Run Design Check"})).toBeDisabled();
});

it("ignores intentional preview abort and a rejected obsolete request", async () => {
  const {send}=mocks();
  render(<DoubleChannelTrussNodeWorkspace/>); await screen.findByText("CURRENT BACKEND PREVIEW");
  send.mockRejectedValueOnce(new DOMException("cancelled","AbortError"));
  fireEvent.change(screen.getByLabelText("V Axial P"),{target:{value:"2"}});
  await waitFor(()=>{expect(send).toHaveBeenCalledTimes(2);});
  expect(screen.queryByRole("alert")).toBeNull();
  let rejectOld: ((reason:Error)=>void)|undefined;
  send.mockImplementationOnce(()=>new Promise((_resolve,reject)=>{rejectOld=reject;}));
  fireEvent.change(screen.getByLabelText("V Axial P"),{target:{value:"3"}});
  await waitFor(()=>{expect(rejectOld).toBeDefined();});
  fireEvent.change(screen.getByLabelText("V Axial P"),{target:{value:"4"}});
  await act(async()=>{rejectOld?.(new Error("obsolete"));await Promise.resolve();});
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(screen.queryByRole("alert")).toBeNull();
});

it.each(["reject", "abort"])("ignores %s of a defaults request after unmount", async mode => {
  const {defaults}=mocks();
  let reject:((reason:unknown)=>void)|undefined;
  defaults.mockImplementationOnce(()=>new Promise((_resolve,fail)=>{reject=fail;}));
  const view=render(<DoubleChannelTrussNodeWorkspace/>);
  view.unmount();
  await act(async()=>{reject?.(mode==="abort"?new DOMException("cancelled","AbortError"):new Error("late"));await Promise.resolve();});
  expect(screen.queryByRole("alert")).toBeNull();
});
