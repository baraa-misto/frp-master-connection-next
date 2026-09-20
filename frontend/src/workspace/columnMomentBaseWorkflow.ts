import { useCallback, useEffect, useRef, useState } from "react";
import type { ColumnMomentBaseRequest, ColumnMomentBaseResponse } from "../api/columnMomentBaseContracts";
import { requestColumnMomentBase } from "../api/columnMomentBaseClient";
import { isIntentionalAbort, PREVIEW_DEBOUNCE_MS } from "./previewWorkflow";

export function columnMomentBaseEngineeringKey(request:ColumnMomentBaseRequest):string {
  // UI staleness key only, NOT an engineering fingerprint or quantity transform.
  const copy=structuredClone(request);
  copy.request_id="";
  copy.column.view_length={value:"",unit:copy.column.view_length.unit};
  return JSON.stringify(copy);
}
export function clearColumnMomentBaseQualifications(request:ColumnMomentBaseRequest):void {
  request.response_source_reference="";request.column_zone_source_reference="";
  for(const c of [request.x_positive,request.x_negative,request.y_positive,request.y_negative]){
    c.angle.connector_source_reference="";c.angle.attachment_source_reference="";
    c.normal_response_source_reference="";c.fastener_source_reference="";
  }
}
export function finiteColumnMomentBaseInputs(value:unknown):boolean {
  if(typeof value==="number")return Number.isFinite(value);
  if(value!==null&&typeof value==="object"){
    if("value" in value)return typeof value.value==="string"&&value.value.trim()!==""&&Number.isFinite(Number(value.value));
    return Object.values(value).every(finiteColumnMomentBaseInputs);
  }
  return true;
}
export function useColumnMomentBasePreview(request:ColumnMomentBaseRequest,revision:number,invalid:string|null) {
  const [response,setResponse]=useState<ColumnMomentBaseResponse|null>(null);
  const [accepted,setAccepted]=useState<number|null>(null);
  const [failure,setFailure]=useState<{revision:number;message:string;kind:"geometry"|"request"}|null>(null);
  const [retryCount,setRetryCount]=useState(0);
  const sequence=useRef(0);
  useEffect(()=>{
    const current=++sequence.current,controller=new AbortController();
    let disposed=false;
    let timer:ReturnType<typeof setTimeout>|null=null;
    if(invalid!==null)return()=>{disposed=true;controller.abort();};
    const execute=async()=>{
      try{
        const next=await requestColumnMomentBase("preview",request,controller.signal);
        if(disposed||current!==sequence.current)return;
        if(next.geometry_status!=="VALID")setFailure({revision,message:next.geometry_invalid_reasons.join("; ")||next.geometry_status,kind:"geometry"});
        else{setResponse(next);setAccepted(revision);setFailure(null);}
      }catch(error){if(!disposed&&current===sequence.current&&!isIntentionalAbort(error))setFailure({revision,message:error instanceof Error?error.message:"Preview failed.",kind:"request"});}
    };
    if(revision===0)void execute();else timer=setTimeout(()=>{void execute();},PREVIEW_DEBOUNCE_MS);
    return()=>{disposed=true;if(timer!==null)clearTimeout(timer);controller.abort();};
  },[request,revision,invalid,retryCount]);
  const error=invalid??(failure?.revision===revision?failure.message:null);
  const current=error===null&&accepted===revision;
  const invalidInputs=invalid!==null||(failure?.revision===revision&&failure.kind==="geometry");
  return {response,current,error,invalidInputs,state:current?"Current backend preview":error===null?"Updating preview — last valid model":"Current input unavailable/invalid — showing last valid model",retry:useCallback(()=>{setRetryCount(v=>v+1);},[])};
}
