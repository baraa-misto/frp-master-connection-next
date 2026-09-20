import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, assert, describe, expect, it, vi } from "vitest";
import * as client from "../src/api/columnMomentBaseClient";
import type { ColumnMomentBaseRequest, ColumnMomentBaseResponse } from "../src/api/columnMomentBaseContracts";
import { ColumnMomentBaseWorkspace } from "../src/workspace/ColumnMomentBaseWorkspace";
import { MomentConnectionsWorkspace } from "../src/workspace/MomentConnectionsWorkspace";
import { buildColumnMomentBaseScene } from "../src/visualization/columnMomentBaseSceneModel";
import { buildFastenerPresentations } from "../src/visualization/fastenerPresentation";
import { columnMomentBaseEngineeringKey, clearColumnMomentBaseQualifications, finiteColumnMomentBaseInputs } from "../src/workspace/columnMomentBaseWorkflow";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import data from "./fixtures/columnMomentBase.json";

interface Fixture {request:ColumnMomentBaseRequest;preview:ColumnMomentBaseResponse;design:ColumnMomentBaseResponse}
const fixtures=data as unknown as Record<string,Fixture>;
const fixture=(key="WI12_FOUR_XY"):Fixture=>{const f=fixtures[key];assert(f);return structuredClone(f);};
const probe=vi.hoisted(()=>({model:null as ReturnType<typeof buildColumnMomentBaseScene>|null}));
vi.mock("../src/visualization/VisualizationPanel",()=>({
  VisualizationPanel:({model,onAppliedActionValueChange,onSelect}:{model:ReturnType<typeof buildColumnMomentBaseScene>;onAppliedActionValueChange:(k:string,v:string)=>void;onSelect:(s:{kind:"MEMBER";id:string})=>void})=>{
    probe.model=model;
    return <div aria-label="test-scene">{["FX","FY","FZ","MX","MY","MZ"].map(k=><button key={k} onClick={()=>{onAppliedActionValueChange(k,"-7");}}>Edit {k}</button>)}<button onClick={()=>{onSelect({kind:"MEMBER",id:"X_POS"});}}>Select X</button></div>;
  },
}));
vi.mock("../src/workspace/WIMomentSpliceWorkspace",()=>({WIMomentSpliceWorkspace:()=> <p>Historical moment splice</p>}));
afterEach(()=>{vi.restoreAllMocks();vi.useRealTimers();vi.unstubAllGlobals();probe.model=null;});
const flush=async()=>{await act(async()=>{await Promise.resolve();await Promise.resolve();});};
const advance=async()=>{await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});};
function mocks(key="WI12_FOUR_XY"){
  const f=fixture(key);
  const load=vi.spyOn(client,"loadColumnMomentBasePreset").mockResolvedValue(f.request);
  const send=vi.spyOn(client,"requestColumnMomentBase").mockImplementation(kind=>Promise.resolve(kind==="preview"?f.preview:f.design));
  return {f,load,send};
}

describe("Stage 4.5 actual backend scene captures",()=>{
  it.each(Object.keys(fixtures).filter(k=>k.includes("_TWO_")||k.endsWith("_FOUR_XY")))("binds real layers and exterior hardware for %s",key=>{
    const f=fixture(key),p=f.preview.result.preview,m=buildColumnMomentBaseScene(p);
    expect(m.snapshotVersion).toBe("4.5-RC1");
    expect(m.boxes.filter(b=>b.ownerId==="COLUMN").length).toBeGreaterThan(0);
    expect(m.cylinders.filter(b=>b.kind==="BOLT"&&b.hardwareConfiguration==="THROUGH_BOLT")).toHaveLength(p.geometry.member_bolts.length);
    expect(new Set(m.cylinders.map(b=>b.id)).size).toBe(m.cylinders.length);
    expect(m.materialAxes.every(a=>a.presentation!==null)).toBe(true);
    expect(m.materialAxes.filter(a=>a.componentId==="COLUMN").every(a=>a.lengthwise.z===1)).toBe(true);
    expect(m.appliedArrows).toHaveLength(5);
    expect(m.appliedArrows.find(a=>a.component==="FZ")?.axialLoadingSense).toBe("COMPRESSION");
    expect(m.appliedArrows.every(a=>a.origin.z===0)).toBe(true);
    expect(m.perBoltDemandArrows).toEqual([]);
    for(const a of buildFastenerPresentations(m.cylinders)){
      expect(a.renderedHardware).toHaveLength(a.shank.hardwareConfiguration==="THROUGH_BOLT"?2:1);
      if(a.shank.hardwareConfiguration==="THROUGH_BOLT")expect(a.head.start).toEqual(a.shank.exactHardware?.headStart);
    }
  });
  it("retains SI native geometry, signed reversal and missing-hardware rejection",()=>{
    for(const name of ["RHS10X8","SRS10X8"]){
      const a=buildColumnMomentBaseScene(fixture(name+"_FOUR_XY").preview.result.preview);
      const b=buildColumnMomentBaseScene(fixture(name+"_SI").preview.result.preview);
      expect(b.boxes).toEqual(a.boxes);
      // Native physical endpoints are identical. Drawing-only quantity projection
      // uses the accepted viewer's Number/mm path; it is not a Decimal oracle.
      expect(b.cylinders.map(c=>[c.id,c.start,c.end,c.penetratedLayerIds])).toEqual(a.cylinders.map(c=>[c.id,c.start,c.end,c.penetratedLayerIds]));
      const geometry=fixture(name+"_SI").preview.result.preview.geometry;
      for(const bolt of geometry.member_bolts){
        const envelope=geometry.member_hardware_envelopes.find(e=>e.bolt_id===bolt.hardware_id);
        const drawing=b.cylinders.find(c=>c.id===bolt.hardware_id);
        assert(envelope);assert(drawing);
        expect(drawing.diameter).toBe(Number(bolt.diameter.value)/25.4);
        expect(b.cylinders.find(c=>c.id===bolt.hardware_id+":HOLE")?.diameter).toBe(Number(bolt.hole_diameter.value)/25.4);
        expect(drawing.exactHardware?.headAcrossFlats).toBe(Number(envelope.head_across_flats.value)/(envelope.head_across_flats.unit==="mm"?25.4:1));
        expect(drawing.exactHardware?.headStart).toEqual(a.cylinders.find(c=>c.id===bolt.hardware_id)?.exactHardware?.headStart);
      }
    }
    const p=fixture().preview.result.preview;
    for(const q of [p.column_on_base.force.x,p.column_on_base.force.y,p.column_on_base.force.z,p.column_on_base.moment.x,p.column_on_base.moment.y,p.column_on_base.moment.z])q.value=String(-Number(q.value));
    const m=buildColumnMomentBaseScene(p);
    expect(m.appliedArrows.find(a=>a.component==="FZ")?.axialLoadingSense).toBe("TENSION");
    expect(m.appliedArrows.find(a=>a.component==="MY")?.axis.y).toBe(-1);
    expect(buildColumnMomentBaseScene(fixture("ZERO").preview.result.preview).appliedArrows).toEqual([]);
    expect(()=>buildColumnMomentBaseScene({...p,geometry:{...p.geometry,member_hardware_envelopes:[]}})).toThrow("member hardware");
    expect(()=>buildColumnMomentBaseScene({...p,geometry:{...p.geometry,foundation_washers:[]}})).toThrow("foundation washer");
  });
});

describe("Stage 4.5 preview and shared request state",()=>{
  it("mounts through the selector and exposes canonical owners, not duplicate hardware edits",async()=>{
    vi.useFakeTimers();const {send}=mocks();render(<MomentConnectionsWorkspace/>);
    fireEvent.change(screen.getByLabelText("Connection type"),{target:{value:"WI_RHS_SRS_COLUMN_MOMENT_BASE_CONNECTION"}});
    await flush();
    expect(screen.getByLabelText("Column moment base inputs")).toBeInTheDocument();
    expect(screen.queryByLabelText("X negative base angle Member bolt diameter")).toBeNull();
    expect(screen.getByLabelText("Y negative base angle Member bolt diameter")).toBeInTheDocument();
    expect(screen.queryByLabelText("Stage 4.5 design results")).toBeNull();
    expect(send.mock.calls.every(c=>c[0]==="preview")).toBe(true);
    fireEvent.click(screen.getByText("Select X"));
    expect(screen.getByLabelText("X positive base angle Length")).toBeInTheDocument();
  });
  it.each([
    ["Axial N — positive uplift","30"],["Shear Vx","-8"],["Shear Vy","5"],["Moment Mx","-45"],["Moment My","35"],
    ["Column Width","13"],["Column Depth","13"],["Column Web Thickness","0.6"],["Column Flange Thickness","0.6"],
    ["X positive base angle Member bolts across","1"],["X positive base angle Member bolts Gauge","2.5"],
    ["X positive base angle Tangential extrusion center","0.25"],["X positive base angle Tangential extrusion center","-0.25"],
    ["Y negative base angle Foundation attachments centroid offset","3.25"],
    ["X positive base angle Member Washer Diameter","1.4"],["X negative base angle Length","6.5"],
  ])("preserves last-valid scene during %s edit and binds the latest native result",async(label,value)=>{
    vi.useFakeTimers();const {send}=mocks();render(<ColumnMomentBaseWorkspace/>);await flush();
    const before=probe.model;
    send.mockResolvedValueOnce(fixture("RHS8_FOUR_XY").preview);
    fireEvent.change(screen.getByLabelText(label),{target:{value}});
    expect(screen.getByText(/LAST VALID PREVIEW — UPDATING/)).toBeInTheDocument();
    expect(probe.model?.boxes).toEqual(before?.boxes);
    expect(probe.model?.cylinders).toEqual(before?.cylinders);
    expect(probe.model?.appliedArrows).toEqual([]);
    await advance();
    expect(probe.model).toEqual(buildColumnMomentBaseScene(fixture("RHS8_FOUR_XY").preview.result.preview));
    expect(screen.getByLabelText("Stage 4.5 preview state")).toHaveAttribute("data-preview-state","current");
    expect(send.mock.calls.every(c=>c[0]==="preview")).toBe(true);
  });
  it("keeps invalid LAST VALID explicit, ignores late replies, and recovers without defaults",async()=>{
    vi.useFakeTimers();const {f,send,load}=mocks();render(<ColumnMomentBaseWorkspace/>);await flush();
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));await flush();
    const old=probe.model,bad={...f.preview,geometry_status:"INVALID_GEOMETRY",geometry_invalid_reasons:["PERPENDICULAR_HOLE_COLLISION"],design_check_ready:false};
    send.mockResolvedValueOnce(bad);
    fireEvent.change(screen.getByLabelText("Y positive base angle Member bolts centroid offset"),{target:{value:"3"}});
    await advance();
    expect(screen.getByText("LAST VALID PREVIEW — CURRENT INPUTS INVALID")).toBeInTheDocument();
    expect(probe.model?.boxes).toEqual(old?.boxes);
    expect(probe.model?.positiveArrows).toEqual([]);
    expect(probe.model?.appliedArrows).toEqual([]);
    expect(screen.getByRole("button",{name:"Run Design Check"})).toBeDisabled();
    expect(screen.queryByLabelText("Stage 4.5 design results")).toBeNull();
    fireEvent.click(screen.getByText("Edit FZ"));
    expect(screen.getByLabelText("Axial N — positive uplift")).toHaveValue("-20");
    let resolveOld!:(v:ColumnMomentBaseResponse)=>void;
    send.mockImplementationOnce(()=>new Promise(yes=>{resolveOld=yes;}));
    fireEvent.change(screen.getByLabelText("Shear Vx"),{target:{value:"-8"}});await advance();
    send.mockResolvedValueOnce(fixture("SRS8_FOUR_XY").preview);
    fireEvent.change(screen.getByLabelText("Y positive base angle Member bolts centroid offset"),{target:{value:"6"}});await advance();
    const newest=probe.model;
    await act(async()=>{resolveOld(bad);await Promise.resolve();});
    expect(probe.model).toBe(newest);
    expect(screen.getByLabelText("Stage 4.5 preview state")).toHaveAttribute("data-preview-state","current");
    expect(load).toHaveBeenCalledTimes(1);
    expect(send.mock.calls.filter(c=>c[0]==="design-check")).toHaveLength(1);
  });
  it("only explicit design evaluates and geometry changes clear every incompatible source",async()=>{
    vi.useFakeTimers();const {send}=mocks("QUALIFIED");render(<ColumnMomentBaseWorkspace/>);await flush();
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));await flush();
    expect(screen.getByLabelText("Stage 4.5 design results")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Column Width"),{target:{value:"14"}});await advance();
    const last=send.mock.calls.at(-1);assert(last);const sent=last[1];
    expect(sent.response_source_reference).toBe("");
    expect(sent.column_zone_source_reference).toBe("");
    for(const c of [sent.x_positive,sent.x_negative,sent.y_positive,sent.y_negative]){
      expect(c.angle.connector_source_reference).toBe("");
      expect(c.angle.attachment_source_reference).toBe("");
      expect(c.fastener_source_reference).toBe("");
    }
    expect(screen.queryByLabelText("Stage 4.5 design results")).toBeNull();
    expect(send.mock.calls.filter(c=>c[0]==="design-check")).toHaveLength(1);
  });
  it("uses backend unit conversion, preserving edited physical fields and source text",async()=>{
    vi.useFakeTimers();const {load,send}=mocks("RHS10X8_FOUR_XY");
    const si=fixture("RHS10X8_SI");
    const convert=vi.spyOn(client,"convertColumnMomentBaseUnits").mockResolvedValue(si.request);
    render(<ColumnMomentBaseWorkspace/>);await flush();
    send.mockResolvedValueOnce(si.preview);
    fireEvent.change(screen.getByLabelText("Unit system"),{target:{value:"SI"}});await flush();await advance();
    expect(convert).toHaveBeenCalledOnce();
    expect(load).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("Column Width")).toHaveValue("254");
    expect(screen.getByLabelText("X positive base angle Member hole diameter")).toHaveValue("14.3002");
    expect(screen.queryByLabelText("Y negative base angle Member bolt diameter")).toBeNull();
  });
  it("rejects incomplete numeric input without request and shares arrow/sidebar state",async()=>{
    vi.useFakeTimers();const {send}=mocks();render(<ColumnMomentBaseWorkspace/>);await flush();
    fireEvent.click(screen.getByText("Edit FX"));await advance();
    expect(screen.getByLabelText("Shear Vx")).toHaveValue("-7");
    fireEvent.click(screen.getByText("Edit MZ"));
    const count=send.mock.calls.length;
    fireEvent.change(screen.getByLabelText("Column Width"),{target:{value:""}});
    await advance();
    expect(send).toHaveBeenCalledTimes(count);
    expect(screen.getByText("LAST VALID PREVIEW — CURRENT INPUTS INVALID")).toBeInTheDocument();
    expect(probe.model?.appliedArrows).toEqual([]);
  });
});

it("engineering key excludes view only and qualification clearing covers four leaves",()=>{
  const r=fixture().request,key=columnMomentBaseEngineeringKey(r);
  r.column.view_length.value="31";r.request_id="view";
  expect(columnMomentBaseEngineeringKey(r)).toBe(key);
  r.column.width.value="14";
  expect(columnMomentBaseEngineeringKey(r)).not.toBe(key);
  expect(finiteColumnMomentBaseInputs(r)).toBe(true);
  r.actions.axial.value="NaN";expect(finiteColumnMomentBaseInputs(r)).toBe(false);
  const source=fixture("QUALIFIED").request;
  clearColumnMomentBaseQualifications(source);
  expect(source.response_source_reference).toBe("");
});
