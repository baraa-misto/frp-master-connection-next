import { afterEach, assert, expect, it, vi } from "vitest";
import * as client from "../src/api/columnMomentBaseClient";
import type { ColumnMomentBaseRequest, ColumnMomentBaseResponse } from "../src/api/columnMomentBaseContracts";
import data from "./fixtures/columnMomentBase.json";

interface Fixture {request:ColumnMomentBaseRequest;preview:ColumnMomentBaseResponse;design:ColumnMomentBaseResponse}
const fixtures=data as unknown as Record<string,Fixture>;
const fixture=(name="WI12_FOUR_XY")=>{const f=fixtures[name];assert(f);return structuredClone(f);};
const json=(v:unknown,status=200)=>new Response(JSON.stringify(v),{status,headers:{"Content-Type":"application/json"}});
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});

it.each(Object.keys(fixtures))("accepts exact native %s preview/design and conversion transport",async name=>{
  const f=fixture(name),signal=new AbortController().signal;
  const spy=vi.fn().mockResolvedValueOnce(json(f.request)).mockResolvedValueOnce(json(f.preview)).mockResolvedValueOnce(json(f.design)).mockResolvedValueOnce(json(f.request));
  vi.stubGlobal("fetch",spy);
  const si=f.request.column.width.unit==="mm";
  expect(await client.loadColumnMomentBasePreset(name,f.request.layout,si,signal)).toEqual(f.request);
  expect(await client.requestColumnMomentBase("preview",f.request,signal)).toEqual(f.preview);
  expect(await client.requestColumnMomentBase("design-check",f.request,signal)).toEqual(f.design);
  expect(await client.convertColumnMomentBaseUnits(f.request,si,signal)).toEqual(f.request);
  expect(spy.mock.calls.map(c=>(c[1] as RequestInit).method)).toEqual(["GET","POST","POST","POST"]);
});
it("rejects malformed contracts and separates HTTP/network/JSON/abort",async()=>{
  const f=fixture(),signal=new AbortController().signal,fetcher=vi.fn();vi.stubGlobal("fetch",fetcher);
  for(const v of [null,[],{}, {...f.preview,request_id:"other"},{...f.preview,ordinary_pass_allowed:true},{...f.preview,resistance_evaluated:true},{...f.preview,result:{preview:{},design:null}},{...f.preview,result:{...f.preview.result,preview:{...f.preview.result.preview,geometry:{...f.preview.result.preview.geometry,member_hardware_envelopes:[]}}}}]){
    fetcher.mockResolvedValueOnce(json(v));await expect(client.requestColumnMomentBase("preview",f.request,signal)).rejects.toMatchObject({kind:"RESPONSE"});
  }
  fetcher.mockResolvedValueOnce(json({}));await expect(client.loadColumnMomentBasePreset("WI12","TWO_X",true,signal)).rejects.toMatchObject({kind:"RESPONSE"});
  fetcher.mockResolvedValueOnce(json({}));await expect(client.convertColumnMomentBaseUnits(f.request,true,signal)).rejects.toMatchObject({kind:"RESPONSE"});
  for(const [status,kind] of [[422,"VALIDATION"],[503,"HTTP"]] as const){fetcher.mockResolvedValueOnce(json({},status));await expect(client.requestColumnMomentBase("design-check",f.request,signal)).rejects.toMatchObject({kind});}
  fetcher.mockResolvedValueOnce(new Response("invalid JSON"));await expect(client.requestColumnMomentBase("preview",f.request,signal)).rejects.toMatchObject({kind:"RESPONSE"});
  fetcher.mockRejectedValueOnce(new TypeError("offline"));await expect(client.loadColumnMomentBasePreset("WI12","FOUR_XY",false,signal)).rejects.toMatchObject({kind:"NETWORK"});
  const error=new DOMException("abort","AbortError");fetcher.mockRejectedValueOnce(error);await expect(client.requestColumnMomentBase("preview",f.request,signal)).rejects.toBe(error);
  expect(client.isColumnMomentBaseRequest({...f.request,column:{...f.request.column,width:{value:"NaN",unit:"in"}}})).toBe(false);
});
