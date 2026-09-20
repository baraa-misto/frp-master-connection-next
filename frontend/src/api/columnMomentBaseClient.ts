import { EvaluationTransportError } from "./client";
import type { ColumnMomentBaseRequest, ColumnMomentBaseResponse } from "./columnMomentBaseContracts";

type Guard = (v: unknown) => boolean;
const record = (v: unknown): v is Record<string,unknown> => v !== null && typeof v === "object" && !Array.isArray(v);
const text: Guard = v => typeof v === "string";
const bool: Guard = v => typeof v === "boolean";
const finite: Guard = v => typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v));
const array = (g: Guard): Guard => v => Array.isArray(v) && v.every(g);
const nullable = (g: Guard): Guard => v => v === null || g(v);
const shape = (fields: Record<string,Guard>): Guard => v => record(v) && Object.entries(fields).every(([k,g])=>g(v[k]));
const q=shape({value:finite,unit:text});
const vec=shape({x:q,y:q,z:q}), lvt=shape({l:q,v:q,t:q});
const wrench=shape({reference:vec,force:vec,moment:vec});
const axis: Guard = v => Array.isArray(v) && v.length===3 && v.every(finite);
const material=nullable(shape({component_id:text,region_id:text,lw_axis:axis,cw_axis:axis,tt_axis:axis}));
const part=shape({part_id:text,box:shape({component_id:text,role:text,center_l_v_t:lvt,size_l_v_t:lvt}),material_region:material});
const bolt=shape({hardware_id:text,group_id:text,start:vec,end:vec,diameter:q,hole_diameter:q,layers:array(text),blind:bool});
const envelope=shape({bolt_id:text,source:text,shank_start:vec,shank_end:vec,head_start:vec,head_end:vec,nut_start:vec,nut_end:vec,head_washer_start:vec,head_washer_end:vec,nut_washer_start:vec,nut_washer_end:vec,washer_diameter:q,head_across_flats:q,nut_across_flats:q});
const hardware=shape({washer_diameter:q,washer_thickness:q,head_across_flats:q,head_height:q,nut_across_flats:q,nut_height:q,end_extension:q,geometry_source:text});
const pattern=shape({across:Number.isInteger,along:Number.isInteger,gauge:q,pitch:q,center:q});
const connector=shape({extrusion_center:q,member_hardware:hardware,normal_response_source_reference:text,fastener_source_reference:text,
  angle:shape({geometry:shape({length:q,member_leg:q,support_leg:q,thickness:q,inside_radius:q,heel_end_reliefs:v=>Array.isArray(v)&&v.length===2&&v.every(q)}),member_pattern:pattern,support_pattern:pattern,
    fastener:shape({bolt_diameter:q,hole_diameter:q,source_authority_id:text,thread_condition:v=>v==="INCLUDED"||v==="EXCLUDED",nominal_shear_stress:v=>v===null}),
    anchors:shape({nominal_diameter:q,hole_diameter:q,specified_embedment:q,washer_outside_diameter:q,washer_thickness:q}),connector_source_reference:text,attachment_source_reference:text,material_id:v=>v==="ICE_LOCKED_PULTRUDED_FRP",provider_id:v=>v==="FRP"})});
export const isColumnMomentBaseRequest: Guard=shape({request_id:text,contract:v=>v==="4.5-RC1",layout:v=>v==="TWO_X"||v==="TWO_Y"||v==="FOUR_XY",column:shape({family:v=>v==="WI"||v==="RHS"||v==="SRS",width:q,depth:q,web_thickness:q,flange_thickness:q,wall_thickness:q,offset_x:q,offset_y:q,view_length:q,material_id:v=>v==="ICE_LOCKED_PULTRUDED_FRP"}),foundation:shape({width_x:q,width_y:q,depth:q}),x_positive:connector,x_negative:connector,y_positive:connector,y_negative:connector,actions:shape({axial:q,shear_x:q,shear_y:q,moment_x:q,moment_y:q,applied_torque_z:q}),response_source_reference:text,column_zone_source_reference:text});
const preview=shape({product:v=>v==="WI_RHS_SRS_COLUMN_MOMENT_BASE_CONNECTION",contract:v=>v==="4.5-RC1",input:isColumnMomentBaseRequest,
  geometry:shape({status:text,reasons:array(text),parts:array(part),display_parts:array(part),member_bolts:array(bolt),foundation_attachments:array(bolt),foundation_washers:array(bolt),member_hardware_envelopes:array(envelope),column_centroid:vec,angles:array(shape({connector_id:text,heel:vec,member_reference_global:vec,support_reference_global:vec,frame:shape({a:axis,b:axis,c:axis})}))}),
  column_on_base:wrench,required_total_foundation_action:wrench,opposite_foundation_reaction:wrench,branch_allocation_status:text,
  response:shape({status:text,reasons:array(text),exact_equilibrium:nullable(bool),qualified:bool}),
  transfers:array(shape({connector_id:text,core:shape({request:shape({member_action:wrench}),heel:wrench,connector_on_support:wrench,fingerprint:text}),connector_on_foundation:wrench,foundation_reaction:wrench,foundation_at_report:wrench,native_core_equilibrium:bool,member_out_of_plane_f_c_m_a_m_b:array(q)})),
  direct_column_contact:nullable(wrench),assembled_foundation_action:nullable(wrench),assembled_force_residual:nullable(vec),assembled_moment_residual:nullable(vec),
  foundation_breakdowns:array(shape({domain:shape({connector_id:text}),status:text,reasons:array(text),record:nullable(shape({reference:text,issuer:text,applicability:text,actions:Array.isArray})),proof:nullable(shape({passed:bool}))})),
  exact_total_transport:bool,engineering_fingerprint:text,disclaimer:text,resistance_evaluated:v=>v===false,foundation_strength_status:text,overall_column_status:text,classification_status:text,
});
const design=shape({status:text,status_reason:text,failed_check_ids:array(text),missing_sources:array(text),scope_statuses:array(v=>Array.isArray(v)&&v.length===2&&v.every(text)),
  member_bolts:array(shape({check_id:text,connector_id:text,bolt_id:text,status:text,reason:text,shear_magnitude:nullable(q),total_tension_including_prying:nullable(q)})),
  local_checks:array(shape({check_id:text,connector_id:text,layer_id:text,bolt_id:nullable(text),status:text,method:text,demand:nullable(q),resistance:nullable(q),applicability:text,material_direction:text})),
  connector_results:array(shape({core_fingerprint:text,status:text,reason:text,detail:nullable(shape({body:shape({status:text}),instep:nullable(shape({method:text,passed:bool,utilization:finite,demand:q,factors:shape({design_resistance:q})}))}))})),
  member_attachment_results:array(shape({connector_id:text,check:shape({status:text})})),
  local_zone:nullable(shape({status:text,reasons:array(text),required_coverage:array(text)})),result_fingerprint:text});
const endpoint="/api/v1/calculations/wi-rhs-srs-column-moment-base";
async function exchange(url:string,signal:AbortSignal,request?:ColumnMomentBaseRequest):Promise<unknown> {
  let response:Response;
  try {response=await fetch(url,{method:request===undefined?"GET":"POST",headers:{"Content-Type":"application/json",Accept:"application/json"},credentials:"same-origin",signal,...(request===undefined?{}:{body:JSON.stringify(request)})});}
  catch(error){if(error instanceof DOMException&&error.name==="AbortError")throw error;throw new EvaluationTransportError("NETWORK",null,"The column moment base service could not be reached.",error);}
  let value:unknown;
  try{value=await response.json();}catch(error){throw new EvaluationTransportError("RESPONSE",response.status,"Unreadable column moment base response.",error);}
  if(!response.ok)throw new EvaluationTransportError(response.status===422?"VALIDATION":"HTTP",response.status,"The server rejected the column moment base request.",value);
  return value;
}
export async function loadColumnMomentBasePreset(preset:string,layout:ColumnMomentBaseRequest["layout"],si:boolean,signal:AbortSignal):Promise<ColumnMomentBaseRequest>{
  const value=await exchange(`${endpoint}/defaults?preset=${encodeURIComponent(preset)}&layout=${layout}&unit_system=${si?"SI":"US_CUSTOMARY"}`,signal);
  if(!isColumnMomentBaseRequest(value))throw new EvaluationTransportError("RESPONSE",200,"Invalid backend column moment preset.",value);
  return value as ColumnMomentBaseRequest;
}
export async function convertColumnMomentBaseUnits(request:ColumnMomentBaseRequest,si:boolean,signal:AbortSignal):Promise<ColumnMomentBaseRequest>{
  const value=await exchange(`${endpoint}/convert-units?unit_system=${si?"SI":"US_CUSTOMARY"}`,signal,request);
  if(!isColumnMomentBaseRequest(value))throw new EvaluationTransportError("RESPONSE",200,"Invalid backend unit conversion.",value);
  return value as ColumnMomentBaseRequest;
}
export async function requestColumnMomentBase(kind:"preview"|"design-check",request:ColumnMomentBaseRequest,signal:AbortSignal):Promise<ColumnMomentBaseResponse>{
  const value=await exchange(`${endpoint}/${kind}`,signal,request);
  const valid=record(value)&&value.api_transport_schema_version==="4.5-API-RC1"&&value.contract==="4.5-RC1"&&value.request_id===request.request_id&&value.ordinary_pass_allowed===false&&value.whole_connection_status==="EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"&&shape({geometry_status:text,geometry_invalid_reasons:array(text),assembly_status:text,resistance_evaluated:bool,design_check_ready:bool,engineering_fingerprint:text,result_fingerprint:text})(value)&&record(value.result)&&preview(value.result.preview)&&(kind==="preview"?value.result.design===null&&value.resistance_evaluated===false:design(value.result.design));
  if(!valid)throw new EvaluationTransportError("RESPONSE",200,"Unsupported column moment base response contract.",value);
  const result=value as unknown as ColumnMomentBaseResponse;
  const ids=new Set(result.result.preview.geometry.member_hardware_envelopes.map(e=>e.bolt_id));
  if(result.result.preview.geometry.member_bolts.some(b=>!ids.has(b.hardware_id)))throw new EvaluationTransportError("RESPONSE",200,"Incomplete backend member-bolt hardware.",value);
  return result;
}
