import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../src/api/wiWallMomentClient";
import * as historicalClient from "../src/api/client";
import type { WIWallMomentPreview, WIWallMomentResponse } from "../src/api/wiWallMomentContracts";
import { loadWIWallMomentBenchmark } from "../src/fixtures/wiWallMomentBenchmarks";
import { buildWIWallMomentScene } from "../src/visualization/wiWallMomentSceneModel";
import { WIWallMomentWorkspace } from "../src/workspace/WIWallMomentWorkspace";
import { MomentConnectionsWorkspace } from "../src/workspace/MomentConnectionsWorkspace";
import { useWIWallMomentPreview } from "../src/workspace/wiWallMomentWorkflow";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import { wallDesignFixture, wallPreviewFixture } from "./wiWallMomentFixtures";

vi.mock("../src/visualization/VisualizationPanel", () => ({
  VisualizationPanel: ({ model, onAppliedActionValueChange, onSelect }: {
    model: ReturnType<typeof buildWIWallMomentScene>;
    onAppliedActionValueChange: (component: string, value: string) => void;
    onSelect: (selection: { kind:"MEMBER"; id:string }) => void;
  }) => <div aria-label="wall-moment-test-viewer"><span>{model.boxes.length} solids</span><span>{model.materialAxes.length} material regions</span><span>{model.cylinders.length} cylinders</span><span>{model.appliedArrows.length} actions</span>{["FX","FZ","MY","MX"].map(component => <button key={component} onClick={() => {onAppliedActionValueChange(component,"-30");}}>Edit {component}</button>)}<button onClick={() => {onSelect({kind:"MEMBER",id:"POSITIVE_WEB_ANGLE"});}}>Select web angle</button></div>,
}));
const response = (value: unknown, status = 200) => new Response(JSON.stringify(value),{status});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); });

describe("Stage 4.2 exact fixture and canonical scene", () => {
  it("loads independent exact U.S./SI requests without a qualified production source", () => {
    const us=loadWIWallMomentBenchmark("US_CUSTOMARY"), si=loadWIWallMomentBenchmark("SI");
    expect(us.actions).toEqual({axial:{value:"20",unit:"kip"},major_shear:{value:"-10",unit:"kip"},structural_major_moment:{value:"100",unit:"kip-in"}});
    expect(si.top.fastener.hole_diameter).toEqual({value:"14.3002",unit:"mm"});
    expect(si.actions.structural_major_moment).toEqual({value:"11298.48290276167",unit:"kN-mm"});
    expect(us.top.connector_source_reference).toBe("");
    expect(us.positive_web.provider_id).toBe("FRP");
    expect(us.top.fastener.nominal_shear_stress).toBeNull();
    us.top.geometry.length.value="9";
    expect(us.bottom.geometry.length.value).toBe("8");
    expect(loadWIWallMomentBenchmark("US_CUSTOMARY").top.geometry.length.value).toBe("8");
  });

  it("binds wall/beam/four angles, exterior endpoints, 11 regions, references and signed arrows", () => {
    const value=wallPreviewFixture().result;
    const model=buildWIWallMomentScene(value);
    expect(model.boxes).toHaveLength(12);
    expect(new Set(model.boxes.map(p=>p.ownerId)).size).toBe(6);
    expect(model.cylinders.filter(p=>p.kind==="BOLT")).toHaveLength(28);
    expect(model.cylinders.filter(p=>p.kind==="HOLE")).toHaveLength(28);
    expect(model.cylinders.filter(p=>p.kind==="BOLT" && p.hardwareConfiguration==="EXTERIOR_NUT_WASHER_ANCHOR")).toHaveLength(16);
    expect(model.materialAxes).toHaveLength(11);
    expect(model.materialAxes.some(a=>a.componentId==="CONCRETE_WALL")).toBe(false);
    expect(model.materialAxes.every(a=>a.presentation!==null)).toBe(true);
    expect(model.markers).toHaveLength(14);
    expect(model.appliedArrows.map(a=>[a.component,a.axis])).toEqual([["FX",{x:1,y:0,z:0}],["FZ",{x:-0,y:-0,z:-1}],["MY",{x:-0,y:1,z:-0}]]);
    for (const basis of model.materialAxes) {
      const a=basis.lengthwise,b=basis.crosswise,t=basis.throughThickness;
      expect([a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x].map(Math.abs)).toEqual([t.x,t.y,t.z].map(Math.abs));
      expect((a.y*b.z-a.z*b.y)*t.x+(a.z*b.x-a.x*b.z)*t.y+(a.x*b.y-a.y*b.x)*t.z).toBe(1);
    }
    expect(model.appliedArrows.every(a=>a.origin.x===0.5 && a.origin.y===0 && a.origin.z===0)).toBe(true);
    expect(model.positiveArrows).toHaveLength(3);
    expect(model.fitRadius).toBeGreaterThan(0);
    expect(model.boundsRadius).toBeGreaterThan(model.fitRadius);
  });

  it("preserves backend signs, suppresses zero actions, and draws exact metric quantities", () => {
    const value=structuredClone(wallPreviewFixture().result);
    value.applied_actions.axial.value="-20"; value.joint_right_hand_action.force.x.value="-20";
    value.applied_actions.major_shear.value="10"; value.joint_right_hand_action.force.y.value="10";
    value.applied_actions.structural_major_moment.value="-100"; value.joint_right_hand_action.moment.z.value="100";
    value.joint_right_hand_action.reference.x.value="12.7"; value.joint_right_hand_action.reference.x.unit="mm";
    let model=buildWIWallMomentScene(value);
    expect(model.appliedArrows[0]).toMatchObject({axis:{x:-1,y:-0,z:-0},axialLoadingSense:"COMPRESSION",origin:{x:0.5,y:-0,z:0}});
    expect(model.appliedArrows[1]?.axis.z).toBe(1);
    expect(model.appliedArrows[2]?.axis.y).toBe(-1);
    for (const q of Object.values(value.applied_actions)) q.value="0";
    model=buildWIWallMomentScene(value);
    expect(model.appliedArrows).toEqual([]);
    const detached={...value,geometry:{...value.geometry,parts:value.geometry.parts.map(p=>p.material_region===null?p:{...p,material_region:{...p.material_region,component_id:"UNBOUND"}})}};
    expect(buildWIWallMomentScene(detached).materialAxes.every(a=>a.presentation===null)).toBe(true);
  });
});

describe("Stage 4.2 strict native-response client", () => {
  it("posts the explicit routes with abort signals and no automatic resistance request", async () => {
    const fetcher=vi.fn().mockResolvedValueOnce(response(wallPreviewFixture())).mockResolvedValueOnce(response(wallDesignFixture()));
    vi.stubGlobal("fetch",fetcher);
    const request=loadWIWallMomentBenchmark("US_CUSTOMARY"), signal=new AbortController().signal;
    expect((await client.previewWIWallMoment(request,signal)).resistance_evaluated).toBe(false);
    expect((await client.designWIWallMoment(request,signal)).result.native_governing_check_ids).toEqual(["FIRST_ROW:TOP_FLANGE_ANGLE"]);
    expect(fetcher).toHaveBeenNthCalledWith(1,"/api/v1/calculations/wi-beam-concrete-wall-moment/preview",expect.objectContaining({method:"POST",credentials:"same-origin",signal,body:JSON.stringify(request)}));
    expect(fetcher).toHaveBeenNthCalledWith(2,"/api/v1/calculations/wi-beam-concrete-wall-moment/design-check",expect.objectContaining({method:"POST"}));
  });

  it("rejects malformed nested render data and separates HTTP, network, JSON and abort failures", async () => {
    const fetcher=vi.fn(); vi.stubGlobal("fetch",fetcher);
    const request=loadWIWallMomentBenchmark("US_CUSTOMARY"), signal=new AbortController().signal;
    const good=wallPreviewFixture();
    const badValues=[null,[],{}, {...good,request_id:"wrong"}, {...good,api_transport_schema_version:"wrong"}, {...good,contract:"old"}, {...good,ordinary_pass_allowed:true}, {...good,whole_connection_status:"PASS"}, {...good,resistance_evaluated:true}, {...good,geometry_status:0}, {...good,result:{...good.result,joint_right_hand_action:{}}}, {...good,result:{...good.result,geometry:{...good.result.geometry,parts:[{}]}}}, {...good,result:{...good.result,applied_actions:{axial:{value:"NaN",unit:"kip"}}}}];
    for (const body of badValues) { fetcher.mockResolvedValueOnce(response(body)); await expect(client.previewWIWallMoment(request,signal)).rejects.toMatchObject({kind:"RESPONSE"}); }
    fetcher.mockResolvedValueOnce(response({detail:"invalid"},422)); await expect(client.designWIWallMoment(request,signal)).rejects.toMatchObject({kind:"VALIDATION",status:422});
    fetcher.mockResolvedValueOnce(response({},503)); await expect(client.previewWIWallMoment(request,signal)).rejects.toMatchObject({kind:"HTTP",status:503});
    fetcher.mockResolvedValueOnce(new Response("invalid json")); await expect(client.previewWIWallMoment(request,signal)).rejects.toMatchObject({kind:"RESPONSE"});
    fetcher.mockRejectedValueOnce(new TypeError("offline")); await expect(client.previewWIWallMoment(request,signal)).rejects.toMatchObject({kind:"NETWORK"});
    const abort=new DOMException("aborted","AbortError"); fetcher.mockRejectedValueOnce(abort); await expect(client.designWIWallMoment(request,signal)).rejects.toBe(abort);
  });
});

describe("Stage 4.2 persistent preview and explicit design", () => {
  it("handles debounce, invalid geometry, last-valid, request failure, retry and local invalid inputs", async () => {
    vi.useFakeTimers();
    const spy=vi.spyOn(client,"previewWIWallMoment").mockResolvedValue(wallPreviewFixture());
    const request=loadWIWallMomentBenchmark("US_CUSTOMARY");
    let revision=0, invalid: string|null=null;
    const hook=renderHook(()=>useWIWallMomentPreview(request,revision,revision===0,invalid));
    await act(async()=>{await Promise.resolve();});
    expect(hook.result.current.current).toBe(true);
    const accepted=hook.result.current.response;
    spy.mockResolvedValueOnce(wallPreviewFixture(false)); revision=1; hook.rerender();
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    expect(hook.result.current.state).toBe("Current input invalid — showing last valid model");
    expect(hook.result.current.response).toBe(accepted);
    spy.mockRejectedValueOnce(new Error("offline")); revision=2; hook.rerender();
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    expect(hook.result.current.state).toContain("Preview request failed");
    act(()=>{hook.result.current.retry();});
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    expect(hook.result.current.current).toBe(true);
    invalid="Bad local decimal"; revision=3; hook.rerender();
    expect(hook.result.current.error).toBe(invalid);
    expect(hook.result.current.current).toBe(false);
    hook.unmount();
  });

  it("rejects late/out-of-order responses and aborts old/unmounted requests", async () => {
    vi.useFakeTimers();
    let first: ((r:WIWallMomentResponse<WIWallMomentPreview>)=>void)|undefined;
    const spy=vi.spyOn(client,"previewWIWallMoment").mockImplementationOnce(()=>new Promise(resolve=>{first=resolve;})).mockResolvedValue(wallPreviewFixture());
    const request=loadWIWallMomentBenchmark("US_CUSTOMARY"); let revision=0;
    const hook=renderHook(()=>useWIWallMomentPreview(request,revision,true,null));
    revision=1; hook.rerender(); await act(async()=>{await Promise.resolve();});
    expect(spy.mock.calls[0]?.[1].aborted).toBe(true);
    await act(async()=>{first?.(wallPreviewFixture(false)); await Promise.resolve();});
    expect(hook.result.current.current).toBe(true);
    hook.unmount(); expect(spy.mock.calls[1]?.[1].aborted).toBe(true);
  });

  it("mounts from the Moment selector and displays the native FAIL trace only after Run Design Check", async () => {
    vi.spyOn(historicalClient,"previewWIMomentSplice").mockImplementation(()=>new Promise(()=>undefined));
    const preview=vi.spyOn(client,"previewWIWallMoment").mockResolvedValue(wallPreviewFixture());
    const design=vi.spyOn(client,"designWIWallMoment").mockResolvedValue(wallDesignFixture());
    render(<MomentConnectionsWorkspace/>);
    expect(screen.getByRole("option",{name:"W/I Beam to Concrete Wall Moment Connection"}).closest("optgroup")?.label).toBe("Beam moment connections");
    fireEvent.change(screen.getByLabelText("Connection type"),{target:{value:"WI_BEAM_CONCRETE_WALL_MAJOR_AXIS_MOMENT_CONNECTION"}});
    expect(await screen.findByLabelText("wall-moment-test-viewer")).toHaveTextContent("12 solids");
    expect(design).not.toHaveBeenCalled();
    expect(screen.getByText("Structural wall moment: 105 kip-in")).toBeInTheDocument();
    expect(screen.getByText("0 kip-in · 0 kip-in · -105 kip-in")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    expect(await screen.findByText("EVALUATED_FAILURE_OUTRANKS_MISSING_QUALIFIED_SOURCE")).toBeInTheDocument();
    expect(screen.getByText("Governing native group: FIRST_ROW:TOP_FLANGE_ANGLE")).toBeInTheDocument();
    expect(screen.getAllByText(/PIN_BEARING:TOP_FLANGE_ANGLE/).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading",{name:"Missing sources remain visible"})).toBeInTheDocument();
    fireEvent.click(screen.getByText("Edit FX"));
    expect(screen.getByLabelText("Axial force P_L")).toHaveValue("-30");
    expect(screen.getByText(/Design results are stale/)).toBeInTheDocument();
    expect(design).toHaveBeenCalledTimes(1);
    await waitFor(()=>{expect(preview).toHaveBeenCalledTimes(2);});
    fireEvent.click(screen.getByText("Select web angle"));
  });

  it("edits every sidebar field with locked partners and exposes only P/V/M and source references", async () => {
    vi.useFakeTimers();
    const spy=vi.spyOn(client,"previewWIWallMoment").mockResolvedValue(wallPreviewFixture());
    const design=vi.spyOn(client,"designWIWallMoment");
    const view=render(<WIWallMomentWorkspace/>);
    await act(async()=>{await Promise.resolve();});
    const inputs=Array.from(view.container.querySelectorAll<HTMLInputElement>(".properties-sidebar input"));
    expect(inputs.length).toBeGreaterThan(30);
    for (const input of inputs) {
      const value=input.value;
      fireEvent.change(input,{target:{value: input.type==="number"?"3": value===""?"unregistered":String(Number(value)+0.1)}});
    }
    fireEvent.change(screen.getByLabelText("Flange angles Thread condition"),{target:{value:"INCLUDED"}});
    fireEvent.change(screen.getByLabelText("Web clip angles Thread condition"),{target:{value:"INCLUDED"}});
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    const sent=spy.mock.calls.at(-1)?.[0];
    expect(sent?.top).toEqual(sent?.bottom);
    expect(sent?.positive_web).toEqual(sent?.negative_web);
    expect(sent?.top.fastener.thread_condition).toBe("INCLUDED");
    expect(design).not.toHaveBeenCalled();
    expect(screen.queryByLabelText(/Minor shear/)).toBeNull();
    expect(screen.queryByRole("option",{name:"316SS"})).toBeNull();
    fireEvent.click(screen.getByRole("button",{name:"Load 4.2 SI"}));
    await act(async()=>{await Promise.resolve();});
    expect(screen.getByLabelText("Beam Depth")).toHaveValue("254");
    expect(screen.getByText("Structural wall moment: 11863.41 kN-mm")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:"Load 4.2 U.S."}));
    await act(async()=>{await Promise.resolve();});
    expect(screen.getByLabelText("Beam Depth")).toHaveValue("10");
    fireEvent.click(screen.getByText("Edit FZ")); fireEvent.click(screen.getByText("Edit MY")); fireEvent.click(screen.getByText("Edit MX"));
    expect(screen.getByLabelText("Major shear V_V")).toHaveValue("-30");
    expect(screen.getByLabelText("Structural major moment M_T")).toHaveValue("-30");
  });

  it("shows initial invalid/request-error states and handles intentional and late failures safely", async () => {
    vi.useFakeTimers();
    const invalid={...wallPreviewFixture(false),geometry_invalid_reasons:[]};
    const spy=vi.spyOn(client,"previewWIWallMoment").mockResolvedValueOnce(invalid);
    const request=loadWIWallMomentBenchmark("US_CUSTOMARY"); let revision=0;
    const hook=renderHook(()=>useWIWallMomentPreview(request,revision,true,null));
    await act(async()=>{await Promise.resolve();});
    expect(hook.result.current.state).toBe("No valid preview");
    expect(hook.result.current.error).toBe("INVALID_GEOMETRY");
    spy.mockRejectedValueOnce("unstructured failure"); revision=1; hook.rerender();
    await act(async()=>{await Promise.resolve();});
    expect(hook.result.current.error).toBe("Preview request failed.");
    spy.mockRejectedValueOnce(new DOMException("abort","AbortError")); revision=2; hook.rerender();
    await act(async()=>{await Promise.resolve();});
    expect(hook.result.current.error).toBeNull();
    let reject: ((reason:unknown)=>void)|undefined;
    spy.mockImplementationOnce(()=>new Promise((_resolve,no)=>{reject=no;})); revision=3; hook.rerender(); hook.unmount();
    await act(async()=>{reject?.(new Error("late")); await Promise.resolve();});
  });

  it("renders retry/local-invalid messages and defensive absent optional traces", async () => {
    const preview=vi.spyOn(client,"previewWIWallMoment").mockRejectedValueOnce(new Error("request offline"));
    render(<WIWallMomentWorkspace/>);
    expect(await screen.findByRole("alert")).toHaveTextContent("request offline");
    const value=wallPreviewFixture();
    preview.mockResolvedValue({...value,result:{...value.result,wall_handoff:null,wall_reaction:null,equilibrium:null}});
    fireEvent.click(screen.getByRole("button",{name:"Retry preview"}));
    expect(await screen.findByLabelText("wall-moment-test-viewer")).toBeInTheDocument();
    expect(screen.getByText(/proofs: Unavailable/)).toBeInTheDocument();
    const original=wallDesignFixture();
    const modified={...original,result:{...original.result,native_failed_checks:original.result.native_failed_checks.map(c=>({...c,utilization:null,demand:null,design_resistance:null}))}};
    vi.spyOn(client,"designWIWallMoment").mockResolvedValue(modified);
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    expect(await screen.findByRole("heading",{name:"Required evaluated failures"})).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Axial force P_L"),{target:{value:""}});
    expect(screen.getByRole("alert")).toHaveTextContent("Enter finite decimal values");
    expect(screen.getByRole("button",{name:"Run Design Check"})).toBeDisabled();
  });

  it("reports design failures without crashing and ignores late aborted design results", async () => {
    vi.spyOn(client,"previewWIWallMoment").mockResolvedValue(wallPreviewFixture());
    const design=vi.spyOn(client,"designWIWallMoment").mockRejectedValueOnce(new Error("Design offline")).mockRejectedValueOnce("unstructured failure").mockRejectedValueOnce(new DOMException("abort","AbortError"));
    const view=render(<WIWallMomentWorkspace/>);
    await screen.findByLabelText("wall-moment-test-viewer");
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("Design offline");
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    expect(await screen.findByText("Design request failed.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    await waitFor(()=>{expect(screen.getByRole("button",{name:"Run Design Check"})).toBeEnabled();});
    expect(screen.queryByRole("alert")).toBeNull();
    let resolve: ((value:ReturnType<typeof wallDesignFixture>)=>void)|undefined;
    design.mockImplementationOnce(()=>new Promise(yes=>{resolve=yes;}));
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    expect(screen.getByRole("button",{name:"Running design check…"})).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Axial force P_L"),{target:{value:"21"}});
    await act(async()=>{resolve?.(wallDesignFixture()); await Promise.resolve();});
    expect(screen.queryByRole("heading",{name:"Required evaluated failures"})).toBeNull();
    await waitFor(()=>{expect(screen.getByRole("button",{name:"Run Design Check"})).toBeEnabled();});
    let reject: ((reason:unknown)=>void)|undefined;
    design.mockImplementationOnce(()=>new Promise((_yes,no)=>{reject=no;}));
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    view.unmount();
    await act(async()=>{reject?.(new Error("late")); await Promise.resolve();});
  });
});
