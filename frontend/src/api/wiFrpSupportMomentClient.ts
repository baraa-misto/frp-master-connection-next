import { mat1Fetch } from "./mat1Transport";
import { EvaluationTransportError } from "./client";
import type { WIFrpSupportMomentDesign, WIFrpSupportMomentPreview, WIFrpSupportMomentRequest, WIFrpSupportMomentResponse } from "./wiFrpSupportMomentContracts";

type Guard = (v: unknown) => boolean;
const record = (v: unknown): v is Record<string,unknown> => v !== null && typeof v === "object" && !Array.isArray(v);
const text: Guard = v => typeof v === "string";
const bool: Guard = v => typeof v === "boolean";
const finite: Guard = v => typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v));
const array = (g: Guard): Guard => v => Array.isArray(v) && v.every(g);
const nullable = (g: Guard): Guard => v => v === null || g(v);
const shape = (fields: Record<string,Guard>): Guard => v => record(v) && Object.entries(fields).every(([k,g])=>g(v[k]));
const q=shape({value:finite,unit:text});
const vec=shape({x:q,y:q,z:q});
const lvt=shape({l:q,v:q,t:q});
const wrench=shape({reference:vec,force:vec,moment:vec});
const axis: Guard = v => Array.isArray(v) && v.length===3 && v.every(finite);
const part=shape({part_id:text,box:shape({component_id:text,role:text,center_l_v_t:lvt,size_l_v_t:lvt}),material_region:nullable(shape({component_id:text,region_id:text,lw_axis:axis,cw_axis:axis,tt_axis:axis}))});
const bolt=shape({hardware_id:text,group_id:text,start:vec,end:vec,diameter:q,hole_diameter:q,layers:array(text),blind:bool});
const envelope=shape({bolt_id:text,source:text,head_start:vec,head_end:vec,head_washer_start:vec,head_washer_end:vec,nut_start:vec,nut_end:vec,nut_washer_start:vec,nut_washer_end:vec,shank_start:vec,shank_end:vec,washer_diameter:q,head_across_flats:q,nut_across_flats:q});
const preview=shape({
  product:v=>v==="WI_BEAM_FRP_SUPPORT_MAJOR_AXIS_MOMENT_CONNECTION",contract:v=>v==="4.3-RC1",
  input:shape({actions:shape({axial:q,major_shear:q,structural_major_moment:q}),support:shape({mode:v=>["WI_FLANGE","WI_WEB","HOLLOW_SQUARE","SOLID_SQUARE","CHANNEL_WEB"].includes(String(v)),face:text})}),
  geometry:shape({status:text,reasons:array(text),parts:array(part),display_parts:array(part),member_bolts:array(bolt),support_bolts:array(shape({hardware:bolt,crossing:shape({layer_ids:array(text),depth:finite,material_thicknesses:array(finite),physical_face:text}),support_point:vec,loaded_planes_status:text})),hardware_envelopes:array(envelope),
    support_contact_patches:array(shape({patch_id:text,group_id:text,face_id:text,corners:array(vec)})),support:shape({centroid:vec,centroid_authority:text}),angles:array(shape({connector_id:text,heel:vec,member_reference_global:vec,support_reference_global:vec}))}),
  connectors:array(shape({connector_id:text,core:shape({request:shape({member_action:wrench}),heel:wrench,connector_on_support:wrench,fingerprint:text}),support_lvt:wrench,support_uvn:wrench,support_at_centroid:wrench,support_in_plane_scope:text,member_out_of_plane_f_c_m_a_m_b:array(q),support_out_of_plane_f_n_m_u_m_v:array(q)})),
  joint_right_hand_action:wrench,support_contribution:nullable(wrench),support_reaction:nullable(wrench),equilibrium:nullable(shape({proof_passed:bool,serialized_force_residual:vec,serialized_moment_residual:vec})),engineering_fingerprint:text,disclaimer:text,beam_allocation_applicability:text,source_availability:array(v=>Array.isArray(v)&&v.length===3&&v.every(text)),
});
const comparison=shape({numerical_comparison:text,utilization:nullable(finite)});
const qualified=shape({status:text,utilization:nullable(finite),method:text,interaction_method:text});
const design=shape({preview,status:text,status_reason:text,native_governing_check_ids:array(text),missing_sources:array(text),
  native_failed_checks:array(shape({result_id:text,limit_state:text,numerical_comparison:text,utilization:nullable(finite),demand:nullable(q),design_resistance:nullable(q)})),
  connector_results:array(shape({core_fingerprint:text,status:text,reason:text,detail:nullable(shape({body:qualified,instep:nullable(shape({method:text,passed:bool,utilization:finite,demand:q,factors:shape({design_resistance:q})}))}))})),
  attachment_results:array(shape({connector_id:text,method:text,check:qualified})),
  common_web_bolts:array(shape({bolt_id:text,status:text,method:text,governing_utilization:nullable(finite),source_required_reason:nullable(text),per_plane_design_capacity:nullable(q)})),
  beam_local_checks:array(shape({connector_id:text,layer_id:text,scope_status:text})),
  beam_bearings:array(shape({check_id:text,layer_id:text,demand:q,material_direction:text,comparison,trace:shape({factor_trace:shape({design_resistance:q})})})),
  support_response:nullable(shape({status:text,reasons:array(text)})),support_bolts:array(shape({check_id:text,connector_id:text,bolt_id:text,section_id:text,layer_ids:array(text),status:text,reason:text,shear_magnitude:nullable(q),total_tension_including_prying:nullable(q)})),
  support_local_checks:array(shape({check_id:text,connector_id:text,layer_id:text,bolt_id:nullable(text),status:text,method:text,demand:nullable(q),resistance:nullable(q),applicability:text,source:text,material_direction:text})),
  local_zone:nullable(shape({status:text,required_coverage:array(text),reasons:array(text)})),scope_statuses:array(v=>Array.isArray(v)&&v.length===2&&v.every(text)),
});

async function post<T>(kind: "preview" | "design-check", request: WIFrpSupportMomentRequest, signal: AbortSignal): Promise<WIFrpSupportMomentResponse<T>> {
  let response: Response;
  try { response=await mat1Fetch(`/api/v1/calculations/wi-beam-frp-support-moment/${kind}`,{method:"POST",headers:{"Content-Type":"application/json",Accept:"application/json"},credentials:"same-origin",body:JSON.stringify(request),signal}); }
  catch(error) { if(error instanceof DOMException&&error.name==="AbortError") throw error; throw new EvaluationTransportError("NETWORK",null,"The FRP-support service could not be reached.",error); }
  let value: unknown;
  try { value=await response.json(); } catch(error) { throw new EvaluationTransportError("RESPONSE",response.status,"The FRP-support service returned unreadable JSON.",error); }
  if(!response.ok) throw new EvaluationTransportError(response.status===422?"VALIDATION":"HTTP",response.status,"The server rejected the FRP-support request.",value);
  const base=record(value)&&value.api_transport_schema_version==="4.3-API-RC1"&&value.contract==="4.3-RC1"&&value.request_id===request.request_id&&value.ordinary_pass_allowed===false&&value.whole_connection_status==="LOCAL_SUPPORT_COMPLETENESS_AND_OVERALL_MEMBER_ANALYSIS_REQUIRED"
    &&shape({geometry_status:text,geometry_invalid_reasons:array(text),assembly_status:text,resistance_evaluated:bool,design_check_ready:bool,engineering_fingerprint:text,result_fingerprint:text})(value)
    &&value.resistance_evaluated===(kind==="design-check" ? value.design_check_ready : false);
  if(!base||!record(value)||!(kind==="preview"?preview:design)(value.result)) throw new EvaluationTransportError("RESPONSE",response.status,"Unsupported FRP-support response contract.",value);
  // Every rendered shank must have its own backend-authored complete hardware.
  const p=(kind==="preview" ? value.result : (value.result as {preview:unknown}).preview) as WIFrpSupportMomentPreview;
  const ids=new Set(p.geometry.hardware_envelopes.map(e=>e.bolt_id));
  if([...p.geometry.member_bolts,...p.geometry.support_bolts.map(b=>b.hardware)].some(b=>!ids.has(b.hardware_id))) throw new EvaluationTransportError("RESPONSE",response.status,"Incomplete FRP-support physical hardware response.",value);
  return value as unknown as WIFrpSupportMomentResponse<T>;
}
export const previewWIFrpSupportMoment=(request:WIFrpSupportMomentRequest,signal:AbortSignal)=>post<WIFrpSupportMomentPreview>("preview",request,signal);
export const designWIFrpSupportMoment=(request:WIFrpSupportMomentRequest,signal:AbortSignal)=>post<WIFrpSupportMomentDesign>("design-check",request,signal);
