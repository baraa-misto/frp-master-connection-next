import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import { afterEach, assert, expect, it, vi } from "vitest";
import * as client from "../src/api/columnMomentBaseClient";
import type { ColumnMomentBaseRequest, ColumnMomentBaseResponse } from "../src/api/columnMomentBaseContracts";
import { ColumnMomentBaseWorkspace } from "../src/workspace/ColumnMomentBaseWorkspace";
import { finiteColumnMomentBaseInputs, useColumnMomentBasePreview } from "../src/workspace/columnMomentBaseWorkflow";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import { buildColumnMomentBaseScene } from "../src/visualization/columnMomentBaseSceneModel";
import data from "./fixtures/columnMomentBase.json";

interface Fixture {request:ColumnMomentBaseRequest;preview:ColumnMomentBaseResponse;design:ColumnMomentBaseResponse}
const fixture=(qualified=false)=>structuredClone((qualified?data.QUALIFIED:data.WI12_FOUR_XY) as unknown as Fixture);
vi.mock("../src/visualization/VisualizationPanel",()=>({VisualizationPanel:()=> <div aria-label="base45-negative-viewer"/>}));
afterEach(()=>{vi.restoreAllMocks();vi.useRealTimers();});
function deferred<T>(){let resolve!:(v:T)=>void;let reject!:(v:unknown)=>void;const promise=new Promise<T>((yes,no)=>{resolve=yes;reject=no;});return{promise,resolve,reject};}
function mocks(){const f=fixture();vi.spyOn(client,"loadColumnMomentBasePreset").mockResolvedValue(f.request);vi.spyOn(client,"requestColumnMomentBase").mockImplementation(k=>Promise.resolve(k==="preview"?f.preview:f.design));return f;}

it("retries bootstrap and preview network failures without replacing physical inputs",async()=>{
  const f=mocks();vi.mocked(client.loadColumnMomentBasePreset).mockRejectedValueOnce(new Error("bootstrap offline"));
  render(<ColumnMomentBaseWorkspace/>);expect(await screen.findByRole("alert")).toHaveTextContent("bootstrap offline");
  fireEvent.click(screen.getByText("Retry preset"));await screen.findByLabelText("base45-negative-viewer");
  vi.mocked(client.requestColumnMomentBase).mockRejectedValueOnce(new Error("preview offline"));
  fireEvent.change(screen.getByLabelText("Column Width"),{target:{value:"13"}});
  expect(await screen.findByRole("alert")).toHaveTextContent("preview offline");
  expect(screen.getByText("LAST VALID PREVIEW — CURRENT PREVIEW UNAVAILABLE")).toBeInTheDocument();
  vi.mocked(client.requestColumnMomentBase).mockResolvedValueOnce(f.preview);
  fireEvent.click(screen.getByText("Retry preview"));
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(screen.getByLabelText("Column Width")).toHaveValue("13");
});

it.each(["Column profile / placement","Finite concrete pedestal","Column-end actions","X positive base angle","X negative base angle","Y positive base angle","Y negative base angle","Assembly qualification"])("binds every editable scalar/source in %s",async group=>{
  vi.useFakeTimers();mocks();render(<ColumnMomentBaseWorkspace/>);await act(async()=>{await Promise.resolve();await Promise.resolve();});
  const section=screen.getByText(group).closest("details");assert(section);
  const inputs=section.querySelectorAll<HTMLInputElement>("input");
  expect(inputs.length).toBeGreaterThan(0);
  for(const input of inputs){
    const value=input.type==="number"?"3":Number.isFinite(Number(input.value))&&input.value!==""?String(Number(input.value)+0.1):"TEST_ONLY_TEXT";
    fireEvent.change(input,{target:{value}});
    expect(input).toHaveValue(input.type==="number"?3:value);
  }
});

it("retains geometry for layout selection and replaces only on explicit constructive preset",async()=>{
  vi.useFakeTimers();const f=mocks();render(<ColumnMomentBaseWorkspace/>);await act(async()=>{await Promise.resolve();await Promise.resolve();});
  fireEvent.change(screen.getByLabelText("X positive base angle member thread condition"),{target:{value:"INCLUDED"}});
  fireEvent.change(screen.getByLabelText("Active connector layout"),{target:{value:"TWO_X"}});
  expect(screen.queryByLabelText("Y positive base angle Length")).toBeNull();
  fireEvent.change(screen.getByLabelText("Active connector layout"),{target:{value:"TWO_Y"}});
  expect(screen.queryByLabelText("X positive base angle Length")).toBeNull();
  fireEvent.change(screen.getByLabelText("Column shape"),{target:{value:"SRS"}});
  await act(async()=>{await Promise.resolve();});
  expect(client.loadColumnMomentBasePreset).toHaveBeenLastCalledWith("SRS","TWO_Y",false,expect.any(AbortSignal));
  expect(screen.getByLabelText("Column Width")).toHaveValue(f.request.column.width.value);
});

it.each([new Error("conversion offline"),"offline",new DOMException("cancelled","AbortError")])("unit conversion failure is recoverable and never geometry validity: %s",async failure=>{
  mocks();vi.spyOn(client,"convertColumnMomentBaseUnits").mockRejectedValue(failure);
  render(<ColumnMomentBaseWorkspace/>);await screen.findByLabelText("base45-negative-viewer");
  fireEvent.change(screen.getByLabelText("Unit system"),{target:{value:"SI"}});
  await act(async()=>{await Promise.resolve();});
  if(failure instanceof DOMException)expect(screen.queryByRole("alert")).toBeNull();
  else expect(screen.getByRole("alert")).toHaveTextContent(failure instanceof Error?failure.message:"Unit conversion failed.");
  expect(screen.getByLabelText("Column Width")).toHaveValue("12");
});

it.each([false,true])("late unit response/error cannot overwrite an intervening geometry edit: %s",async rejects=>{
  const f=mocks(),pending=deferred<ColumnMomentBaseRequest>();vi.spyOn(client,"convertColumnMomentBaseUnits").mockReturnValue(pending.promise);
  render(<ColumnMomentBaseWorkspace/>);await screen.findByLabelText("base45-negative-viewer");
  fireEvent.change(screen.getByLabelText("Unit system"),{target:{value:"SI"}});
  fireEvent.change(screen.getByLabelText("Column Depth"),{target:{value:"14"}});
  await act(async()=>{if(rejects)pending.reject(new Error("late conversion"));else pending.resolve(f.request);await Promise.resolve();});
  expect(screen.getByLabelText("Column Depth")).toHaveValue("14");expect(screen.queryByRole("alert")).toBeNull();
});

it("preserves a current design unit identity but never revives an already stale design",async()=>{
  const f=mocks();vi.spyOn(client,"convertColumnMomentBaseUnits").mockResolvedValue(f.request);
  render(<ColumnMomentBaseWorkspace/>);await screen.findByLabelText("base45-negative-viewer");
  fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));await screen.findByLabelText("Stage 4.5 design results");
  fireEvent.change(screen.getByLabelText("Unit system"),{target:{value:"SI"}});await act(async()=>{await Promise.resolve();});
  expect(screen.getByLabelText("Stage 4.5 design results")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Column Width"),{target:{value:"14"}});
  expect(screen.queryByLabelText("Stage 4.5 design results")).toBeNull();
  const changed=structuredClone(f.request);changed.column.width.value="14";
  vi.mocked(client.convertColumnMomentBaseUnits).mockResolvedValueOnce(changed);
  fireEvent.change(screen.getByLabelText("Unit system"),{target:{value:"SI"}});await act(async()=>{await Promise.resolve();});
  expect(screen.queryByLabelText("Stage 4.5 design results")).toBeNull();
});

it("selects solid rectangular and hollow wall-specific fields without adding W/I assumptions",async()=>{
  const f=mocks();render(<ColumnMomentBaseWorkspace/>);await screen.findByLabelText("base45-negative-viewer");
  vi.mocked(client.loadColumnMomentBasePreset).mockResolvedValueOnce(data.SRS8_FOUR_XY.request as unknown as ColumnMomentBaseRequest);
  fireEvent.change(screen.getByLabelText("Column shape"),{target:{value:"SRS"}});
  await screen.findByText("SRS · native lower-end centroid");
  expect(screen.queryByLabelText("Column Wall Thickness")).toBeNull();expect(screen.queryByLabelText("Column Web Thickness")).toBeNull();
  vi.mocked(client.loadColumnMomentBasePreset).mockResolvedValueOnce(data.RHS8_FOUR_XY.request as unknown as ColumnMomentBaseRequest);
  fireEvent.change(screen.getByLabelText("Column shape"),{target:{value:"RHS"}});
  await screen.findByLabelText("Column Wall Thickness");
  expect(client.requestColumnMomentBase).toHaveBeenCalledWith("preview",f.request,expect.any(AbortSignal));
});

it("keeps unbound material presentation truthful and exposes native failed check IDs",async()=>{
  const f=fixture(true),p=f.preview.result.preview;
  const changed={...p,geometry:{...p.geometry,display_parts:p.geometry.display_parts.map(v=>v.material_region===null?v:{...v,material_region:{...v.material_region,component_id:"UNBOUND"}})}};
  expect(buildColumnMomentBaseScene(changed).materialAxes.every(a=>a.presentation===null)).toBe(true);
  vi.spyOn(client,"loadColumnMomentBasePreset").mockResolvedValue(f.request);
  const d=f.design.result.design;assert(d);
  const design={...f.design,result:{...f.design.result,design:{...d,failed_check_ids:["TEST_NATIVE_FAILED_CHECK"]}}};
  vi.spyOn(client,"requestColumnMomentBase").mockImplementation(k=>Promise.resolve(k==="preview"?f.preview:design));
  render(<ColumnMomentBaseWorkspace/>);await screen.findByLabelText("base45-negative-viewer");
  fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
  expect(await screen.findByText("FAIL · TEST_NATIVE_FAILED_CHECK")).toBeInTheDocument();
});

it.each([false,true])("bootstrap unmount rejects late %s without blank/error replacement",async rejects=>{
  const pending=deferred<ColumnMomentBaseRequest>();vi.spyOn(client,"loadColumnMomentBasePreset").mockReturnValue(pending.promise);
  const view=render(<ColumnMomentBaseWorkspace/>);view.unmount();
  await act(async()=>{if(rejects)pending.reject(new Error("late"));else pending.resolve(fixture().request);await Promise.resolve();});
  expect(screen.queryByRole("alert")).toBeNull();
});
it("bootstrap non-Error failure has a readable fallback",async()=>{
  vi.spyOn(client,"loadColumnMomentBasePreset").mockRejectedValue("offline");render(<ColumnMomentBaseWorkspace/>);
  expect(await screen.findByRole("alert")).toHaveTextContent("Preset request failed.");
});

it.each([new Error("explicit preset failure"),"offline",new DOMException("cancelled","AbortError")])("handles preset failure and intentional abort independently: %s",async failure=>{
  mocks();render(<ColumnMomentBaseWorkspace/>);await screen.findByLabelText("base45-negative-viewer");
  vi.mocked(client.loadColumnMomentBasePreset).mockRejectedValueOnce(failure);
  await act(async()=>{fireEvent.change(screen.getByLabelText("Column shape"),{target:{value:"RHS"}});await Promise.resolve();});
  if(failure instanceof DOMException)expect(screen.queryByRole("alert")).toBeNull();
  else expect(screen.getByRole("alert")).toHaveTextContent(failure instanceof Error?failure.message:"Preset request failed.");
});

it.each([false,true])("preset supersession ignores late result/error %s and retains current edits",async rejects=>{
  const f=mocks();render(<ColumnMomentBaseWorkspace/>);await screen.findByLabelText("base45-negative-viewer");
  const pending=deferred<ColumnMomentBaseRequest>();vi.mocked(client.loadColumnMomentBasePreset).mockReturnValueOnce(pending.promise);
  fireEvent.change(screen.getByLabelText("Column shape"),{target:{value:"RHS"}});
  fireEvent.change(screen.getByLabelText("Column view length"),{target:{value:"21"}});
  await act(async()=>{if(rejects)pending.reject(new Error("late"));else pending.resolve(f.request);await Promise.resolve();});
  expect(screen.getByLabelText("Column view length")).toHaveValue("21");expect(screen.queryByRole("alert")).toBeNull();
});

it.each([new Error("explicit design failure"),"offline",new DOMException("cancelled","AbortError")])("keeps design errors distinct and ignores abort: %s",async failure=>{
  mocks();render(<ColumnMomentBaseWorkspace/>);await screen.findByLabelText("base45-negative-viewer");
  vi.mocked(client.requestColumnMomentBase).mockRejectedValueOnce(failure);
  await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));await Promise.resolve();});
  if(failure instanceof DOMException)expect(screen.queryByRole("alert")).toBeNull();
  else expect(screen.getByRole("alert")).toHaveTextContent(failure instanceof Error?failure.message:"Design check failed.");
  expect(screen.queryByLabelText("Stage 4.5 design results")).toBeNull();
});

it.each([false,true])("engineering edit rejects superseded design completion/error %s",async rejects=>{
  const f=mocks();render(<ColumnMomentBaseWorkspace/>);await screen.findByLabelText("base45-negative-viewer");
  const pending=deferred<ColumnMomentBaseResponse>();vi.mocked(client.requestColumnMomentBase).mockReturnValueOnce(pending.promise);
  fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
  fireEvent.change(screen.getByLabelText("Axial N — positive uplift"),{target:{value:"5"}});
  await act(async()=>{if(rejects)pending.reject(new Error("old result"));else pending.resolve(f.design);await Promise.resolve();});
  expect(screen.queryByLabelText("Stage 4.5 design results")).toBeNull();expect(screen.queryByRole("alert")).toBeNull();
});

it("blank integer input is invalid, no preview/design, and no NaN display",async()=>{
  const f=mocks();render(<ColumnMomentBaseWorkspace/>);await screen.findByLabelText("base45-negative-viewer");
  fireEvent.click(screen.getByText("X positive base angle"));
  expect(screen.getByText("X positive base angle").closest("details")).toHaveClass("sidebar-group-selected");
  fireEvent.click(screen.getByText("Column profile / placement"));
  expect(screen.getByText("Column profile / placement").closest("details")).toHaveClass("sidebar-group-selected");
  fireEvent.change(screen.getByLabelText("X positive base angle Member bolts across"),{target:{value:""}});
  expect(screen.getByLabelText("X positive base angle Member bolts across")).toHaveValue(null);
  expect(screen.getByRole("alert")).toHaveTextContent("finite decimal");
  expect(finiteColumnMomentBaseInputs(NaN)).toBe(false);expect(finiteColumnMomentBaseInputs(f.request)).toBe(true);
});

it("shows explicit not-proven proof states and source-qualified foot breakdown labels",async()=>{
  const f=fixture(true),base=f.preview.result.preview;
  const p={...base,exact_total_transport:false,response:{...base.response,exact_equilibrium:false},transfers:base.transfers.map(t=>({...t,native_core_equilibrium:false})),foundation_breakdowns:base.transfers.map(t=>({domain:{connector_id:t.connector_id},status:"VALID_QUALIFIED_RESPONSE",reasons:["TEST_FOOT_NOTE"],record:{reference:"TEST_FOOT",issuer:"TEST_ISSUER",applicability:"TEST_ONLY",actions:[]},proof:{passed:true}}))};
  vi.spyOn(client,"loadColumnMomentBasePreset").mockResolvedValue(f.request);
  const spy=vi.spyOn(client,"requestColumnMomentBase").mockResolvedValue({...f.preview,result:{preview:p,design:null}});
  render(<ColumnMomentBaseWorkspace/>);await screen.findByLabelText("base45-negative-viewer");
  expect(screen.getByText("Total input transport: Not proven")).toBeInTheDocument();
  expect(screen.getByText("Base-response conservation: Not proven")).toBeInTheDocument();
  expect(screen.getAllByText("Core equilibrium: Not proven")).toHaveLength(2);
  expect(screen.getAllByText("Exact parent recovery: Proven")).toHaveLength(2);
  spy.mockResolvedValue({...f.preview,result:{preview:{...p,foundation_breakdowns:p.foundation_breakdowns.map(b=>({...b,proof:{passed:false}}))},design:null}});
  fireEvent.change(screen.getByLabelText("Column view length"),{target:{value:"22"}});
  expect(await screen.findAllByText("Exact parent recovery: Not proven")).toHaveLength(2);
});

it("hook exposes fallback failures and ignores abort/disposed rejection",async()=>{
  vi.useFakeTimers();const f=fixture();const spy=vi.spyOn(client,"requestColumnMomentBase").mockResolvedValue(f.preview);
  let revision=0;const hook=renderHook(()=>useColumnMomentBasePreview(f.request,revision,null));
  await act(async()=>{await Promise.resolve();});
  spy.mockResolvedValueOnce({...f.preview,geometry_status:"INVALID_GEOMETRY",geometry_invalid_reasons:[]});revision++;hook.rerender();
  await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});expect(hook.result.current.error).toBe("INVALID_GEOMETRY");
  spy.mockRejectedValueOnce("offline");revision++;hook.rerender();await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});expect(hook.result.current.error).toBe("Preview failed.");
  spy.mockRejectedValueOnce(new DOMException("cancelled","AbortError"));revision++;hook.rerender();await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});expect(hook.result.current.error).toBeNull();
  const pending=deferred<ColumnMomentBaseResponse>();spy.mockReturnValueOnce(pending.promise);revision++;hook.rerender();await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});hook.unmount();
  await act(async()=>{pending.reject(new Error("late"));await Promise.resolve();});expect(hook.result.current.error).toBeNull();
});
