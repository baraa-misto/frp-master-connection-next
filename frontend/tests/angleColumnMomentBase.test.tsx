import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../src/api/angleColumnMomentBaseClient";
import * as historical from "../src/api/client";
import type { AngleBaseRequest, AngleBaseResponse } from "../src/api/angleColumnMomentBaseContracts";
import { buildAngleColumnMomentBaseScene } from "../src/visualization/angleColumnMomentBaseSceneModel";
import { buildFastenerPresentations } from "../src/visualization/fastenerPresentation";
import { AngleColumnMomentBaseWorkspace } from "../src/workspace/AngleColumnMomentBaseWorkspace";
import { MomentConnectionsWorkspace } from "../src/workspace/MomentConnectionsWorkspace";
import { angleBaseEngineeringKey, clearAngleBaseQualifications, finiteAngleBaseInputs, useAngleColumnMomentBasePreview } from "../src/workspace/angleColumnMomentBaseWorkflow";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import data from "./fixtures/angleColumnMomentBase.json";

describe("Stage 4.4 owner-review current versus last-valid scene",()=>{
  const edits=[["Axial N — positive uplift","30","actions.axial.value"],["Column Leg X","9","column.leg_x.value"],["Leg 1 base angle Length","6.5","leg_1.angle.geometry.length.value"],["Leg 1 base angle Member bolts across","1","leg_1.angle.member_pattern.across"],["Leg 1 base angle Member bolts along","1","leg_1.angle.member_pattern.along"],["Leg 1 base angle Member bolts Gauge","2.5","leg_1.angle.member_pattern.gauge.value"],["Leg 1 base angle Member bolts Pitch","1.5","leg_1.angle.member_pattern.pitch.value"],["Leg 1 base angle Member bolts centroid offset","3.25","leg_1.angle.member_pattern.center.value"],["Leg 1 base angle Foundation attachments across","1","leg_1.angle.support_pattern.across"],["Leg 1 base angle Foundation attachments along","1","leg_1.angle.support_pattern.along"],["Leg 1 base angle Foundation attachments Gauge","2.5","leg_1.angle.support_pattern.gauge.value"],["Leg 1 base angle Foundation attachments Pitch","1.5","leg_1.angle.support_pattern.pitch.value"],["Leg 1 base angle Foundation attachments centroid offset","3.25","leg_1.angle.support_pattern.center.value"],["Leg 1 base angle Member bolt diameter","0.45","leg_1.angle.fastener.bolt_diameter.value"],["Leg 1 base angle Member hole diameter","0.6","leg_1.angle.fastener.hole_diameter.value"],["Leg 1 base angle Foundation Nominal Diameter","0.45","leg_1.angle.anchors.nominal_diameter.value"],["Leg 1 base angle Foundation Hole Diameter","0.6","leg_1.angle.anchors.hole_diameter.value"],["Leg 2 base angle Length","6.5","leg_2.angle.geometry.length.value"],["Leg 2 base angle Member bolts across","1","leg_2.angle.member_pattern.across"],["Leg 2 base angle Member bolts along","1","leg_2.angle.member_pattern.along"],["Leg 2 base angle Member bolts Gauge","2.5","leg_2.angle.member_pattern.gauge.value"],["Leg 2 base angle Member bolts Pitch","1.5","leg_2.angle.member_pattern.pitch.value"],["Leg 2 base angle Member bolts centroid offset","3.25","leg_2.angle.member_pattern.center.value"],["Leg 2 base angle Foundation attachments across","1","leg_2.angle.support_pattern.across"],["Leg 2 base angle Foundation attachments along","1","leg_2.angle.support_pattern.along"],["Leg 2 base angle Foundation attachments Gauge","2.5","leg_2.angle.support_pattern.gauge.value"],["Leg 2 base angle Foundation attachments Pitch","1.5","leg_2.angle.support_pattern.pitch.value"],["Leg 2 base angle Foundation attachments centroid offset","3.25","leg_2.angle.support_pattern.center.value"],["Leg 2 base angle Member bolt diameter","0.45","leg_2.angle.fastener.bolt_diameter.value"],["Leg 2 base angle Member hole diameter","0.6","leg_2.angle.fastener.hole_diameter.value"],["Leg 2 base angle Foundation Nominal Diameter","0.45","leg_2.angle.anchors.nominal_diameter.value"],["Leg 2 base angle Foundation Hole Diameter","0.6","leg_2.angle.anchors.hole_diameter.value"]] as const;
  it.each(edits)("binds accepted response after valid %s edit",async(label,value,path)=>{
    vi.useFakeTimers();const {requestSpy}=mocks();render(<AngleColumnMomentBaseWorkspace/>);
    await act(async()=>{await Promise.resolve();await Promise.resolve();});
    const old=sceneProbe.model;
    // Transport binding oracle: use a distinct captured backend snapshot. The API
    // regression/browser matrix separately proves the actual edited physical cases.
    const next=fixture("unequal_us").preview;
    requestSpy.mockResolvedValueOnce(next);
    fireEvent.change(screen.getByLabelText(label),{target:{value}});
    expect(screen.getByText(/LAST VALID PREVIEW — UPDATING/)).toBeInTheDocument();
    expect(sceneProbe.model?.boxes).toEqual(old?.boxes);
    expect(sceneProbe.model?.cylinders).toEqual(old?.cylinders);
    expect(sceneProbe.model?.appliedArrows).toEqual([]);
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    const sent=requestSpy.mock.calls.at(-1)?.[1];
    const entered=path.split(".").reduce<unknown>((v,k)=>(v as Record<string,unknown>)[k],sent);
    expect(String(entered)).toBe(value);
    expect(sceneProbe.model).toEqual(buildAngleColumnMomentBaseScene(next.result.preview));
    expect(screen.getByLabelText("Stage 4.4 preview state")).toHaveAttribute("data-preview-state","current");
    expect(screen.getByLabelText("Stage 4.4 preview state")).toHaveAttribute("data-preview-fingerprint",next.engineering_fingerprint);
    expect(requestSpy.mock.calls.every(c=>c[0]==="preview")).toBe(true);
  });

  it("retains only labeled last-valid hardware, hides actions, rejects late replies and recovers",async()=>{
    vi.useFakeTimers();const {f,requestSpy}=mocks();render(<AngleColumnMomentBaseWorkspace/>);
    await act(async()=>{await Promise.resolve();await Promise.resolve();});
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    await act(async()=>{await Promise.resolve();});
    const original=sceneProbe.model;
    const bad={...f.preview,geometry_status:"INVALID_GEOMETRY",geometry_invalid_reasons:["MEMBER_BOLT_PATH:OUTSIDE_SELECTED_LEG_SURFACE","COLUMN_HOLE_WASHER_NOT_ON_EXPOSED_MATCHING_LEG"]};
    requestSpy.mockResolvedValueOnce(bad);
    fireEvent.change(screen.getByLabelText("Column Leg X"),{target:{value:"4"}});
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    expect(screen.getByText("LAST VALID PREVIEW — CURRENT INPUTS INVALID")).toBeInTheDocument();
    expect(screen.getByLabelText("Stage 4.4 preview state")).toHaveTextContent("COLUMN_HOLE_WASHER_NOT_ON_EXPOSED_MATCHING_LEG");
    expect(screen.getByLabelText("Column Leg X")).toHaveValue("4");
    expect(sceneProbe.model?.boxes).toEqual(original?.boxes);
    expect(sceneProbe.model?.cylinders).toEqual(original?.cylinders);
    expect(sceneProbe.model?.appliedArrows).toEqual([]);
    expect(sceneProbe.model?.positiveArrows).toEqual([]);
    expect(screen.getByRole("button",{name:"Run Design Check"})).toBeDisabled();
    expect(screen.queryByLabelText("Stage 4.4 design results")).toBeNull();
    // A stale action-editor callback cannot change the current input.
    fireEvent.click(screen.getByText("Edit FZ"));
    expect(screen.getByLabelText("Axial N — positive uplift")).toHaveValue("-20");
    let resolveOld!:(r:AngleBaseResponse)=>void;
    requestSpy.mockImplementationOnce(()=>new Promise(yes=>{resolveOld=yes;}));
    fireEvent.change(screen.getByLabelText("Axial N — positive uplift"),{target:{value:"30"}});
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    expect(sceneProbe.model?.appliedArrows).toEqual([]);
    const latest=fixture("unequal_us").preview;
    requestSpy.mockResolvedValueOnce(latest);
    fireEvent.change(screen.getByLabelText("Column Leg X"),{target:{value:"8"}});
    fireEvent.change(screen.getByLabelText("Shear Vx"),{target:{value:"-7"}});
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    expect(sceneProbe.model).toEqual(buildAngleColumnMomentBaseScene(latest.result.preview));
    const newest=sceneProbe.model;
    await act(async()=>{resolveOld(bad);await Promise.resolve();});
    expect(sceneProbe.model).toBe(newest);
    expect(screen.getByLabelText("Stage 4.4 preview state")).toHaveAttribute("data-preview-state","current");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(requestSpy.mock.calls.at(-1)?.[1].actions.shear_x.value).toBe("-7");
    expect(requestSpy.mock.calls.filter(c=>c[0]==="design-check")).toHaveLength(1);
  });

  it("marks transport failure as unavailable, never geometry invalid, and invalid view input hides design",async()=>{
    vi.useFakeTimers();const {f,requestSpy}=mocks();render(<AngleColumnMomentBaseWorkspace/>);
    await act(async()=>{await Promise.resolve();await Promise.resolve();});
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    await act(async()=>{await Promise.resolve();});
    requestSpy.mockRejectedValueOnce(new Error("offline"));
    fireEvent.change(screen.getByLabelText("Column view length"),{target:{value:"21"}});
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    expect(screen.getByText("LAST VALID PREVIEW — CURRENT PREVIEW UNAVAILABLE")).toBeInTheDocument();
    expect(screen.queryByLabelText("Stage 4.4 design results")).toBeNull();
    expect(sceneProbe.model?.appliedArrows).toEqual([]);
    requestSpy.mockResolvedValueOnce(f.preview);
    fireEvent.click(screen.getByText("Retry preview"));
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    expect(screen.getByLabelText("Stage 4.4 design results")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Column view length"),{target:{value:""}});
    expect(screen.getByText("LAST VALID PREVIEW — CURRENT INPUTS INVALID")).toBeInTheDocument();
    expect(screen.queryByLabelText("Stage 4.4 design results")).toBeNull();
  });
});


interface Fixture {request:AngleBaseRequest;preview:AngleBaseResponse;design:AngleBaseResponse}
const fixtures=data as unknown as Record<keyof typeof data,Fixture>;
const fixture=(name:keyof typeof data="equal_us")=>structuredClone(fixtures[name]);
const json=(v:unknown,status=200)=>new Response(JSON.stringify(v),{status});
const sceneProbe=vi.hoisted(()=>({model:null as ReturnType<typeof buildAngleColumnMomentBaseScene>|null}));
vi.mock("../src/visualization/VisualizationPanel",()=>({
  VisualizationPanel:({model,onAppliedActionValueChange,onSelect}:{model:ReturnType<typeof buildAngleColumnMomentBaseScene>;onAppliedActionValueChange:(c:string,v:string)=>void;onSelect:(s:{kind:"MEMBER";id:string})=>void})=>{sceneProbe.model=model;return <div aria-label="base44-test-viewer"><span>{model.cylinders.length} hardware parts</span>{["FX","FY","FZ","MX","MY","MZ"].map(c=><button key={c} onClick={()=>{onAppliedActionValueChange(c,"-9");}}>Edit {c}</button>)}<button onClick={()=>{onSelect({kind:"MEMBER",id:"LEG_2_BASE_ANGLE"});}}>Select leg 2</button></div>;},
}));
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();vi.useRealTimers();});

describe("Stage 4.4 independent backend transport snapshots",()=>{
  it.each(["equal_us","unequal_us","equal_si","unequal_si","qualified_test_only"] as const)("accepts both exact %s API responses",async name=>{
    const f=fixture(name),signal=new AbortController().signal;
    vi.stubGlobal("fetch",vi.fn().mockResolvedValueOnce(json(f.request)).mockResolvedValueOnce(json(f.preview)).mockResolvedValueOnce(json(f.design)));
    expect(await client.loadAngleBasePreset(name.startsWith("unequal"),name.endsWith("si"),signal)).toEqual(f.request);
    expect(await client.requestAngleBase("preview",f.request,signal)).toEqual(f.preview);
    expect(await client.requestAngleBase("design-check",f.request,signal)).toEqual(f.design);
  });
  it("rejects malformed contracts and reports HTTP/network/JSON/abort separately",async()=>{
    const f=fixture(),signal=new AbortController().signal,fetcher=vi.fn();vi.stubGlobal("fetch",fetcher);
    for(const v of [null,[],{}, {...f.preview,request_id:"other"},{...f.preview,ordinary_pass_allowed:true},{...f.preview,resistance_evaluated:true},{...f.preview,result:{preview:{},design:null}},{...f.preview,result:{...f.preview.result,preview:{...f.preview.result.preview,geometry:{...f.preview.result.preview.geometry,member_hardware_envelopes:[]}}}}]){
      fetcher.mockResolvedValueOnce(json(v));await expect(client.requestAngleBase("preview",f.request,signal)).rejects.toMatchObject({kind:"RESPONSE"});
    }
    fetcher.mockResolvedValueOnce(json({}));await expect(client.loadAngleBasePreset(true,true,signal)).rejects.toMatchObject({kind:"RESPONSE"});
    for(const [status,kind] of [[422,"VALIDATION"],[503,"HTTP"]] as const){fetcher.mockResolvedValueOnce(json({},status));await expect(client.requestAngleBase("design-check",f.request,signal)).rejects.toMatchObject({kind});}
    fetcher.mockResolvedValueOnce(new Response("invalid JSON"));await expect(client.requestAngleBase("preview",f.request,signal)).rejects.toMatchObject({kind:"RESPONSE"});
    fetcher.mockRejectedValueOnce(new TypeError("offline"));await expect(client.loadAngleBasePreset(false,false,signal)).rejects.toMatchObject({kind:"NETWORK"});
    const error=new DOMException("abort","AbortError");fetcher.mockRejectedValueOnce(error);await expect(client.requestAngleBase("preview",f.request,signal)).rejects.toBe(error);
    expect(client.isAngleBaseRequest({...f.request,column:{...f.request.column,leg_x:{value:"NaN",unit:"in"}}})).toBe(false);
  });
});

describe("Stage 4.4 physical scene binding",()=>{
  it.each(["equal_us","unequal_us","equal_si","unequal_si"] as const)("draws %s real two-leg paths and native material bases",name=>{
    const p=fixture(name).preview.result.preview,m=buildAngleColumnMomentBaseScene(p);
    expect(m.cylinders.filter(c=>c.kind==="BOLT")).toHaveLength(16);
    expect(m.cylinders.filter(c=>c.kind==="WASHER")).toHaveLength(24);
    expect(m.boxes.filter(b=>b.ownerId==="ANGLE_COLUMN")).toHaveLength(2);
    expect(m.boxes.filter(b=>b.ownerId==="LEG_1_BASE_ANGLE")).toHaveLength(2);
    expect(m.boxes.filter(b=>b.ownerId==="LEG_2_BASE_ANGLE")).toHaveLength(2);
    expect(m.boxes.find(b=>b.ownerId==="FOUNDATION")?.ownerRole).toBe("OTHER");
    expect(m.materialAxes).toHaveLength(6);
    expect(m.materialAxes.every(a=>a.presentation!==null)).toBe(true);
    expect(m.materialAxes.filter(a=>a.componentId==="ANGLE_COLUMN").every(a=>a.lengthwise.z===1)).toBe(true);
    expect(m.materialAxes.filter(a=>a.componentId==="LEG_1_BASE_ANGLE").every(a=>a.lengthwise.x===1)).toBe(true);
    expect(m.materialAxes.filter(a=>a.componentId==="LEG_2_BASE_ANGLE").every(a=>a.lengthwise.y===-1)).toBe(true);
    expect(m.appliedArrows).toHaveLength(5);
    expect(m.appliedArrows.find(a=>a.component==="FZ")).toMatchObject({axis:{z:-1},axialLoadingSense:"COMPRESSION"});
    expect(m.appliedArrows.every(a=>a.origin.z===0)).toBe(true);
    expect(m.perBoltDemandArrows).toEqual([]);
    expect(m.boundsRadius).toBeGreaterThan(m.fitRadius);
    for(const a of buildFastenerPresentations(m.cylinders)){
      if(a.shank.hardwareConfiguration==="THROUGH_BOLT"){expect(a.renderedHardware).toHaveLength(2);expect(a.head.start).toEqual(a.shank.exactHardware?.headStart);}
      else{expect(a.renderedHardware).toHaveLength(1);expect(a.renderedHardware[0]?.start.z).toBeGreaterThan(0);}
    }
  });
  it("reverses all signs, suppresses zero, preserves hardware failure and unbound axes",()=>{
    const p=fixture().preview.result.preview;
    for(const q of Object.values(p.input.actions))q.value=String(-Number(q.value));
    let m=buildAngleColumnMomentBaseScene(p);
    expect(m.appliedArrows.find(a=>a.component==="FZ")).toMatchObject({axis:{z:1},axialLoadingSense:"TENSION"});
    expect(m.appliedArrows.find(a=>a.component==="MY")?.axis.y).toBe(-1);
    for(const q of Object.values(p.input.actions))q.value="0";
    expect(buildAngleColumnMomentBaseScene(p).appliedArrows).toEqual([]);
    expect(()=>buildAngleColumnMomentBaseScene({...p,geometry:{...p.geometry,member_hardware_envelopes:[]}})).toThrow("member hardware");
    expect(()=>buildAngleColumnMomentBaseScene({...p,geometry:{...p.geometry,foundation_washers:[]}})).toThrow("foundation washer");
    m=buildAngleColumnMomentBaseScene({...p,geometry:{...p.geometry,display_parts:p.geometry.display_parts.map(v=>v.material_region===null?v:{...v,material_region:{...v.material_region,component_id:"UNBOUND"}})}});
    expect(m.materialAxes.every(a=>a.presentation===null)).toBe(true);
  });
});

function mocks(qualified=false){
  const f=fixture(qualified?"qualified_test_only":"equal_us");
  vi.spyOn(client,"loadAngleBasePreset").mockImplementation((unequal,si)=>Promise.resolve(fixture(`${unequal?"unequal":"equal"}_${si?"si":"us"}`).request));
  const requestSpy=vi.spyOn(client,"requestAngleBase").mockImplementation((kind)=>Promise.resolve(kind==="preview"?f.preview:f.design));
  return {f,requestSpy};
}
describe("Stage 4.4 workspace and request state",()=>{
  it("mounts through the actual moment selector and calculates only explicitly",async()=>{
    vi.spyOn(historical,"previewWIMomentSplice").mockImplementation(()=>new Promise(()=>undefined));
    const {requestSpy}=mocks();
    render(<MomentConnectionsWorkspace/>);
    fireEvent.change(screen.getByLabelText("Connection type"),{target:{value:"ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION"}});
    await screen.findByLabelText("base44-test-viewer");
    expect(requestSpy.mock.calls.every(c=>c[0]==="preview")).toBe(true);
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    await screen.findByLabelText("Stage 4.4 design results");
    expect(screen.getByText(/No evaluated failure returned/)).toBeInTheDocument();
    expect(screen.getByText(/Internal checks: SOURCE_REQUIRED/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Column view length"),{target:{value:"22"}});
    expect(screen.queryByText(/Design is stale/)).toBeNull();
    await screen.findByText("Current backend preview");
    fireEvent.click(screen.getByText("Edit FZ"));
    expect(screen.getByLabelText("Axial N — positive uplift")).toHaveValue("-9");
    expect(screen.getByText(/Design is stale/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Stage 4.4 design results")).toBeNull();
    expect(requestSpy.mock.calls.filter(c=>c[0]==="design-check")).toHaveLength(1);
  });
  it("edits independent groups and every source/control with one canonical load state",async()=>{
    vi.useFakeTimers();const {requestSpy}=mocks();const view=render(<AngleColumnMomentBaseWorkspace/>);
    await act(async()=>{await Promise.resolve();await Promise.resolve();});
    for(const input of view.container.querySelectorAll<HTMLInputElement>(".properties-sidebar input")){
      fireEvent.change(input,{target:{value:input.type==="number"?"3":Number.isFinite(Number(input.value))&&input.value!==""?String(Number(input.value)+.1):"TEST_ONLY"}});
    }
    for(const title of ["Leg 1 base angle","Leg 2 base angle"])fireEvent.change(screen.getByLabelText(`${title} member thread condition`),{target:{value:"INCLUDED"}});
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    for(const c of ["FX","FY","FZ","MX","MY","MZ"]){
      fireEvent.click(screen.getByText(`Edit ${c}`));
      await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    }
    fireEvent.click(screen.getByText("Select leg 2"));
    fireEvent.change(screen.getByLabelText("Leg 1 base angle Length"),{target:{value:"6.2"}});
    expect(screen.getByLabelText("Leg 2 base angle Length")).toHaveValue("6.1");
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    const sent=requestSpy.mock.calls.at(-1)?.[1];
    expect(sent?.response_source_reference).toBe("");
    expect(sent?.leg_1.normal_response_source_reference).toBe("");
    expect(sent?.leg_2.angle.attachment_source_reference).toBe("");
    expect(sent?.actions).toMatchObject({axial:{value:"-9"},shear_x:{value:"-9"},shear_y:{value:"-9"},moment_x:{value:"-9"},moment_y:{value:"-9"},applied_torque_z:{value:"0"}});
    for(const label of ["Equal / SI","Unequal / SI","Unequal / U.S.","Equal / U.S."]){
      fireEvent.click(screen.getByRole("button",{name:label}));
      await act(async()=>{await Promise.resolve();});
    }
    fireEvent.change(screen.getByLabelText("Axial N — positive uplift"),{target:{value:""}});
    expect(screen.getByRole("alert")).toHaveTextContent("finite decimal");
    expect(screen.getByRole("button",{name:"Run Design Check"})).toBeDisabled();
    expect(requestSpy.mock.calls.filter(c=>c[0]==="design-check")).toHaveLength(0);
  },15000);
  it("renders real qualified branch/core/contact and native failed records",async()=>{
    const {f}=mocks(true);
    render(<AngleColumnMomentBaseWorkspace/>);await screen.findByLabelText("base44-test-viewer");
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));await screen.findByLabelText("Stage 4.4 design results");
    expect(screen.getByText(`FAIL · ${f.design.result.design?.failed_check_ids[0]??""}`)).toBeInTheDocument();
    expect(screen.getAllByText(/Core equilibrium: Exact/)).toHaveLength(2);
    expect(screen.getAllByText(/Net connector on foundation/)).toHaveLength(2);
  });
  it("retries bootstrap errors without blank root",async()=>{
    const {f}=mocks();vi.mocked(client.loadAngleBasePreset).mockRejectedValueOnce(new Error("offline"));
    render(<AngleColumnMomentBaseWorkspace/>);await screen.findByRole("alert");fireEvent.click(screen.getByText("Retry preset"));await screen.findByLabelText("base44-test-viewer");
    expect(f.preview.result.preview.branch_allocation_status).toBe("SOURCE_REQUIRED");
  });
  it("stales only engineering input; source text and finite checks remain separate",()=>{
    const r=fixture("qualified_test_only").request,key=angleBaseEngineeringKey(r);
    r.column.view_length.value="100";expect(angleBaseEngineeringKey(r)).toBe(key);
    r.column.thickness.value=".6";expect(angleBaseEngineeringKey(r)).not.toBe(key);
    clearAngleBaseQualifications(r);expect(r.response_source_reference).toBe("");expect(r.leg_2.fastener_source_reference).toBe("");
    expect(finiteAngleBaseInputs(null)).toBe(true);expect(finiteAngleBaseInputs(r)).toBe(true);
    r.actions.axial.value="Infinity";expect(finiteAngleBaseInputs(r)).toBe(false);
  });
});

describe("Stage 4.4 debounce, abort and last-valid race protection",()=>{
  it("retains last valid scene on geometry/request errors and retries",async()=>{
    vi.useFakeTimers();const f=fixture(),spy=vi.spyOn(client,"requestAngleBase").mockResolvedValue(f.preview);
    let revision=0,invalid:string|null=null;
    const hook=renderHook(()=>useAngleColumnMomentBasePreview(f.request,revision,invalid));
    await act(async()=>{await Promise.resolve();});expect(hook.result.current.current).toBe(true);
    const accepted=hook.result.current.response;
    spy.mockResolvedValueOnce({...f.preview,geometry_status:"INVALID_GEOMETRY",geometry_invalid_reasons:["Bad geometry"]});revision++;hook.rerender();
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});expect(hook.result.current.response).toBe(accepted);expect(hook.result.current.error).toBe("Bad geometry");
    spy.mockRejectedValueOnce(new Error("request failed"));revision++;hook.rerender();await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    expect(hook.result.current.error).toBe("request failed");
    act(()=>{hook.result.current.retry();});await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});expect(hook.result.current.current).toBe(true);
    invalid="Bad decimal";revision++;hook.rerender();expect(hook.result.current.error).toBe(invalid);hook.unmount();
  });
  it("rejects late responses and cleans timers/listeners on supersession/unmount",async()=>{
    vi.useFakeTimers();const f=fixture();let resolve:((v:AngleBaseResponse)=>void)|undefined;
    const spy=vi.spyOn(client,"requestAngleBase").mockImplementationOnce(()=>new Promise(yes=>{resolve=yes;})).mockResolvedValue(f.preview);
    let revision=0;const hook=renderHook(()=>useAngleColumnMomentBasePreview(f.request,revision,null));
    revision++;hook.rerender();await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    await act(async()=>{resolve?.({...f.preview,geometry_status:"INVALID_GEOMETRY"});await Promise.resolve();});
    expect(hook.result.current.current).toBe(true);expect(spy.mock.calls[0]?.[2].aborted).toBe(true);
    revision++;hook.rerender();hook.unmount();await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    expect(spy).toHaveBeenCalledTimes(2);
  });
});
