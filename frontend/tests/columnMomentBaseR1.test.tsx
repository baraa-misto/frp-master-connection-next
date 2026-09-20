import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, assert, expect, it, vi } from "vitest";
import * as client from "../src/api/columnMomentBaseClient";
import type { ColumnMomentBaseRequest, ColumnMomentBaseResponse } from "../src/api/columnMomentBaseContracts";
import { ColumnMomentBaseWorkspace } from "../src/workspace/ColumnMomentBaseWorkspace";
import { buildColumnMomentBaseScene } from "../src/visualization/columnMomentBaseSceneModel";
import type { SingleBoltSceneModel } from "../src/visualization/sceneModel";
import data from "./fixtures/columnMomentBase.json";

// Exercise the real panel, labels and inspector. Only WebGL mounting is replaced;
// the exact model sent to its arrow renderer is inspected independently below.
const probe=vi.hoisted(()=>({model:null as SingleBoltSceneModel|null}));
vi.mock("../src/visualization/EngineeringScene",()=>({default:({model}:{model:SingleBoltSceneModel})=>{probe.model=model;return <div/>;}}));
afterEach(()=>{vi.restoreAllMocks();probe.model=null;});
const fields=[["FX","shear_x","force","x","Shear Vx"],["FY","shear_y","force","y","Shear Vy"],["FZ","axial","force","z","Axial N — positive uplift"],["MX","moment_x","moment","x","Moment Mx"],["MY","moment_y","moment","y","Moment My"]] as const;
const modes=(["WI12","RHS8","SRS8"] as const).flatMap(p=>(["TWO_X","TWO_Y","FOUR_XY"] as const).map(layout=>({p,layout})));
const fixture=(p:string,layout:string)=>structuredClone((data as unknown as Record<string,{request:ColumnMomentBaseRequest;preview:ColumnMomentBaseResponse}>)[p+"_"+layout]);

it.each(modes.flatMap(mode=>fields.map(entry=>({...mode,entry}))))("R1 real signed viewer/inspector matrix $p $layout $entry",async({p,layout,entry})=>{
  const f=fixture(p,layout);assert(f);
  vi.spyOn(client,"loadColumnMomentBasePreset").mockResolvedValue(f.request);
  const send=vi.spyOn(client,"requestColumnMomentBase").mockImplementation((_kind,request)=>{
    const p=f.preview.result.preview;
    return Promise.resolve({...f.preview,result:{...f.preview.result,preview:{...p,input:request,column_on_base:{...p.column_on_base,force:{x:request.actions.shear_x,y:request.actions.shear_y,z:request.actions.axial},moment:{x:request.actions.moment_x,y:request.actions.moment_y,z:request.actions.applied_torque_z}}}}});
  });
  render(<ColumnMomentBaseWorkspace/>);await screen.findByText("CURRENT BACKEND PREVIEW");
  for(const [component,field,,axis,title] of [entry]){
    for(const value of ["4","-4","0"]){
      fireEvent.change(screen.getByLabelText(title),{target:{value}});
      await screen.findByText("CURRENT BACKEND PREVIEW");
      expect(screen.getByLabelText(title)).toHaveValue(value);
      expect(send.mock.lastCall?.[1].actions[field].value).toBe(value);
      const label="Edit Column "+component.slice(0,1)+component.slice(1).toLowerCase()+" applied load value";
      const arrow=probe.model?.appliedArrows.find(a=>a.component===component);
      if(value==="0"){expect(arrow).toBeUndefined();expect(screen.queryByRole("button",{name:label})).toBeNull();}
      else{
        assert(arrow);expect(arrow.signedValue).toBe(Number(value));
        expect(arrow.axis[axis]).toBe(Math.sign(Number(value)));
        expect(Object.entries(arrow.axis).filter(([k])=>k!==axis).every(([,v])=>v===0)).toBe(true);
        expect(arrow.frameId).toBe("BASE_XYZ");expect(arrow.origin).toEqual(probe.model?.markers.find(m=>m.id==="COLUMN_END_CENTROID")?.position);
        expect(screen.getByRole("button",{name:label})).toHaveTextContent(value==="4"?"+4.00":"−4.00");
        expect(screen.getByText(component+": "+value+" "+f.request.actions[field].unit)).toBeInTheDocument();
      }
      // The input and returned wrench share native units; no reaction substitution.
      const native=f.preview.result.preview;
      expect(buildColumnMomentBaseScene(native).frames[0]?.id).toBe("BASE_XYZ");
    }
  }
},15000);

it("R1 independent controls, no nominal-size UI, count-aware spacing and reactivation",async()=>{
  const f=fixture("WI12","FOUR_XY");assert(f);
  for(const name of ["x_positive","x_negative","y_positive","y_negative"] as const){
    f.request[name].angle.member_pattern.across=2;f.request[name].angle.member_pattern.along=1;
    f.request[name].angle.support_pattern.across=1;f.request[name].angle.support_pattern.along=1;
  }
  const load=vi.spyOn(client,"loadColumnMomentBasePreset").mockResolvedValue(f.request);
  vi.spyOn(client,"requestColumnMomentBase").mockResolvedValue(f.preview);
  render(<ColumnMomentBaseWorkspace/>);await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(within(screen.getByLabelText("Unit system")).getAllByRole("option").map(x=>x.textContent)).toEqual(["U.S. Units","S.I. Units"]);
  expect(within(screen.getByLabelText("Column shape")).getAllByRole("option").map(x=>x.textContent)).toEqual(["W/I Shape Column","Hollow Rectangular Tube","Solid Rectangular Tube"]);
  expect(screen.queryByText(/Load (WI12|RHS8|SRS8)/)).toBeNull();
  expect(screen.queryByLabelText("Section preset")).toBeNull();
  expect(screen.getByLabelText("X positive base angle Member bolts across")).toHaveValue(2);
  expect(screen.getByText(/New angles use 2 × 1 member bolts/)).toHaveTextContent("Zero tangential offset centers each angle on its selected column face.");
  expect(screen.getByLabelText("X positive base angle Member bolts Pitch")).toBeDisabled();
  expect(screen.getByLabelText("X positive base angle Foundation attachments Gauge")).toBeDisabled();
  expect(screen.getByLabelText("X positive base angle Foundation attachments Pitch")).toBeDisabled();
  fireEvent.change(screen.getByLabelText("X positive base angle Member bolts along"),{target:{value:"2"}});
  expect(screen.getByLabelText("X positive base angle Member bolts Pitch")).toBeEnabled();
  fireEvent.change(screen.getByLabelText("X positive base angle Foundation attachments across"),{target:{value:"2"}});
  expect(screen.getByLabelText("X positive base angle Foundation attachments Gauge")).toBeEnabled();
  fireEvent.change(screen.getByLabelText("Active connector layout"),{target:{value:"TWO_Y"}});
  fireEvent.change(screen.getByLabelText("Column shape"),{target:{value:"RHS"}});
  await act(async()=>{await Promise.resolve();});
  expect(load).toHaveBeenLastCalledWith("RHS","TWO_Y",false,expect.any(AbortSignal));
});
