import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import * as client from "../src/api/angleColumnMomentBaseClient";
import type { AngleBaseRequest, AngleBaseResponse } from "../src/api/angleColumnMomentBaseContracts";
import { AngleColumnMomentBaseWorkspace } from "../src/workspace/AngleColumnMomentBaseWorkspace";
import { finiteAngleBaseInputs, useAngleColumnMomentBasePreview } from "../src/workspace/angleColumnMomentBaseWorkflow";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import data from "./fixtures/angleColumnMomentBase.json";

interface Fixture {request:AngleBaseRequest;preview:AngleBaseResponse;design:AngleBaseResponse}
const fixture=(qualified=false)=>structuredClone((qualified?data.qualified_test_only:data.equal_us) as unknown as Fixture);
vi.mock("../src/visualization/VisualizationPanel",()=>({VisualizationPanel:()=> <div aria-label="base44-negative-viewer"/>}));
afterEach(()=>{vi.restoreAllMocks();vi.useRealTimers();});
function deferred<T>(){let resolve!:(v:T)=>void;let reject!:(v:unknown)=>void;const promise=new Promise<T>((yes,no)=>{resolve=yes;reject=no;});return{promise,resolve,reject};}
function mocks(){const f=fixture();vi.spyOn(client,"loadAngleBasePreset").mockResolvedValue(f.request);vi.spyOn(client,"requestAngleBase").mockImplementation(k=>Promise.resolve(k==="preview"?f.preview:f.design));return f;}

it.each([false,true])("bootstrap unmount rejects late %s without blank/error replacement",async rejects=>{
  const pending=deferred<AngleBaseRequest>();vi.spyOn(client,"loadAngleBasePreset").mockReturnValue(pending.promise);
  const view=render(<AngleColumnMomentBaseWorkspace/>);view.unmount();
  await act(async()=>{if(rejects)pending.reject(new Error("late"));else pending.resolve(fixture().request);await Promise.resolve();});
  expect(screen.queryByRole("alert")).toBeNull();
});
it("bootstrap non-Error failure has a readable fallback",async()=>{
  vi.spyOn(client,"loadAngleBasePreset").mockRejectedValue("offline");render(<AngleColumnMomentBaseWorkspace/>);
  expect(await screen.findByRole("alert")).toHaveTextContent("Preset request failed.");
});

it.each([new Error("explicit preset failure"),"offline",new DOMException("cancelled","AbortError")])("handles preset failure and intentional abort independently: %s",async failure=>{
  mocks();render(<AngleColumnMomentBaseWorkspace/>);await screen.findByLabelText("base44-negative-viewer");
  vi.mocked(client.loadAngleBasePreset).mockRejectedValueOnce(failure);
  await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Unequal / U.S."}));await Promise.resolve();});
  if(failure instanceof DOMException)expect(screen.queryByRole("alert")).toBeNull();
  else expect(screen.getByRole("alert")).toHaveTextContent(failure instanceof Error?failure.message:"Preset request failed.");
});

it.each([false,true])("preset supersession ignores late result/error %s and retains current edits",async rejects=>{
  const f=mocks();render(<AngleColumnMomentBaseWorkspace/>);await screen.findByLabelText("base44-negative-viewer");
  const pending=deferred<AngleBaseRequest>();vi.mocked(client.loadAngleBasePreset).mockReturnValueOnce(pending.promise);
  fireEvent.click(screen.getByRole("button",{name:"Unequal / U.S."}));
  fireEvent.change(screen.getByLabelText("Column view length"),{target:{value:"21"}});
  await act(async()=>{if(rejects)pending.reject(new Error("late"));else pending.resolve(f.request);await Promise.resolve();});
  expect(screen.getByLabelText("Column view length")).toHaveValue("21");expect(screen.queryByRole("alert")).toBeNull();
});

it.each([new Error("explicit design failure"),"offline",new DOMException("cancelled","AbortError")])("keeps design errors distinct and ignores abort: %s",async failure=>{
  mocks();render(<AngleColumnMomentBaseWorkspace/>);await screen.findByLabelText("base44-negative-viewer");
  vi.mocked(client.requestAngleBase).mockRejectedValueOnce(failure);
  await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));await Promise.resolve();});
  if(failure instanceof DOMException)expect(screen.queryByRole("alert")).toBeNull();
  else expect(screen.getByRole("alert")).toHaveTextContent(failure instanceof Error?failure.message:"Design check failed.");
  expect(screen.queryByLabelText("Stage 4.4 design results")).toBeNull();
});

it.each([false,true])("engineering edit rejects superseded design completion/error %s",async rejects=>{
  const f=mocks();render(<AngleColumnMomentBaseWorkspace/>);await screen.findByLabelText("base44-negative-viewer");
  const pending=deferred<AngleBaseResponse>();vi.mocked(client.requestAngleBase).mockReturnValueOnce(pending.promise);
  fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
  fireEvent.change(screen.getByLabelText("Axial N — positive uplift"),{target:{value:"5"}});
  await act(async()=>{if(rejects)pending.reject(new Error("old result"));else pending.resolve(f.design);await Promise.resolve();});
  expect(screen.queryByLabelText("Stage 4.4 design results")).toBeNull();expect(screen.queryByRole("alert")).toBeNull();
});

it("blank integer input is invalid, no preview/design, and no NaN display",async()=>{
  const f=mocks();render(<AngleColumnMomentBaseWorkspace/>);await screen.findByLabelText("base44-negative-viewer");
  fireEvent.click(screen.getByText("Leg 1 base angle"));
  expect(screen.getByText("Leg 1 base angle").closest("details")).toHaveClass("sidebar-group-selected");
  fireEvent.click(screen.getByText("Angle column"));
  expect(screen.getByText("Angle column").closest("details")).toHaveClass("sidebar-group-selected");
  fireEvent.change(screen.getByLabelText("Leg 1 base angle Member bolts across"),{target:{value:""}});
  expect(screen.getByLabelText("Leg 1 base angle Member bolts across")).toHaveValue(null);
  expect(screen.getByRole("alert")).toHaveTextContent("finite decimal");
  expect(finiteAngleBaseInputs(NaN)).toBe(false);expect(finiteAngleBaseInputs(f.request)).toBe(true);
});

it("shows explicit not-proven proof states and source-qualified foot breakdown labels",async()=>{
  const f=fixture(true),base=f.preview.result.preview;
  const p={...base,exact_total_transport:false,response:{...base.response,exact_equilibrium:false},transfers:base.transfers.map(t=>({...t,native_core_equilibrium:false})),foundation_breakdowns:base.transfers.map(t=>({domain:{connector_id:t.connector_id},status:"VALID_QUALIFIED_RESPONSE",reasons:["TEST_FOOT_NOTE"],record:{reference:"TEST_FOOT",issuer:"TEST_ISSUER",applicability:"TEST_ONLY",actions:[]},proof:{passed:true}}))};
  vi.spyOn(client,"loadAngleBasePreset").mockResolvedValue(f.request);
  const spy=vi.spyOn(client,"requestAngleBase").mockResolvedValue({...f.preview,result:{preview:p,design:null}});
  render(<AngleColumnMomentBaseWorkspace/>);await screen.findByLabelText("base44-negative-viewer");
  expect(screen.getByText("Total input transport: Not proven")).toBeInTheDocument();
  expect(screen.getByText("Base-response conservation: Not proven")).toBeInTheDocument();
  expect(screen.getAllByText("Core equilibrium: Not proven")).toHaveLength(2);
  expect(screen.getAllByText("Exact parent recovery: Proven")).toHaveLength(2);
  spy.mockResolvedValue({...f.preview,result:{preview:{...p,foundation_breakdowns:p.foundation_breakdowns.map(b=>({...b,proof:{passed:false}}))},design:null}});
  fireEvent.change(screen.getByLabelText("Column view length"),{target:{value:"22"}});
  expect(await screen.findAllByText("Exact parent recovery: Not proven")).toHaveLength(2);
});

it("hook exposes fallback failures and ignores abort/disposed rejection",async()=>{
  vi.useFakeTimers();const f=fixture();const spy=vi.spyOn(client,"requestAngleBase").mockResolvedValue(f.preview);
  let revision=0;const hook=renderHook(()=>useAngleColumnMomentBasePreview(f.request,revision,null));
  await act(async()=>{await Promise.resolve();});
  spy.mockResolvedValueOnce({...f.preview,geometry_status:"INVALID_GEOMETRY",geometry_invalid_reasons:[]});revision++;hook.rerender();
  await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});expect(hook.result.current.error).toBe("INVALID_GEOMETRY");
  spy.mockRejectedValueOnce("offline");revision++;hook.rerender();await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});expect(hook.result.current.error).toBe("Preview failed.");
  spy.mockRejectedValueOnce(new DOMException("cancelled","AbortError"));revision++;hook.rerender();await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});expect(hook.result.current.error).toBeNull();
  const pending=deferred<AngleBaseResponse>();spy.mockReturnValueOnce(pending.promise);revision++;hook.rerender();await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});hook.unmount();
  await act(async()=>{pending.reject(new Error("late"));await Promise.resolve();});expect(hook.result.current.error).toBeNull();
});
