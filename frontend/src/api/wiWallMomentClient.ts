import { mat1Fetch } from "./mat1Transport";
import { EvaluationTransportError } from "./client";
import type { WIWallMomentDesign, WIWallMomentPreview, WIWallMomentRequest, WIWallMomentResponse } from "./wiWallMomentContracts";

function record(value: unknown): value is Record<string, unknown> { return value !== null && typeof value === "object" && !Array.isArray(value); }
type Guard = (value: unknown) => boolean;
const text: Guard = value => typeof value === "string";
const bool: Guard = value => typeof value === "boolean";
const array = (check: Guard): Guard => value => Array.isArray(value) && value.every(check);
const shape = (checks: Record<string, Guard>): Guard => value => record(value) && Object.entries(checks).every(([key,check]) => check(value[key]));
const nullable = (check: Guard): Guard => value => value === null || check(value);
const finite: Guard = value => typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value));
const quantity = shape({value:finite,unit:text});
const vector = shape({x:quantity,y:quantity,z:quantity});
const lvt = shape({l:quantity,v:quantity,t:quantity});
const wrench = shape({reference:vector,force:vector,moment:vector});
const axis: Guard = value => Array.isArray(value) && value.length === 3 && value.every(finite);
const actions = shape({axial:quantity,major_shear:quantity,structural_major_moment:quantity});
const hardware = shape({hardware_id:text,group_id:text,start:vector,end:vector,diameter:quantity,hole_diameter:quantity,layers:array(text),blind:bool});
const part = shape({part_id:text,box:shape({component_id:text,role:text,center_l_v_t:lvt,size_l_v_t:lvt}),material_region:nullable(shape({component_id:text,region_id:text,lw_axis:axis,cw_axis:axis,tt_axis:axis}))});
const previewContract = shape({
  geometry:shape({status:text,reasons:array(text),parts:array(part),member_bolts:array(hardware),wall_anchors:array(hardware),angles:array(shape({connector_id:text,heel:vector,member_reference_global:vector,support_reference_global:vector}))}),
  connectors:array(shape({connector_id:text,instep_plan_status:text,core:shape({request:shape({member_action:wrench}),heel:wrench,connector_on_support:wrench,fingerprint:text}),support_global:wrench,support_at_wall:wrench})),
  applied_actions:actions,joint_right_hand_action:wrench,wall_handoff:nullable(wrench),wall_reaction:nullable(wrench),
  equilibrium:nullable(shape({proof_passed:bool,serialized_force_diagnostic:vector,serialized_moment_diagnostic:vector,structural_major_moment:quantity})),
  engineering_fingerprint:text,disclaimer:text,disclaimer_id:text,sign_method:text,whole_connection_status:text,
});
const qualifiedCheck = shape({status:text,utilization:nullable(finite),method:text,interaction_method:text,terms:array(shape({component:text,signed_demand:quantity,selected_design_strength:nullable(quantity),utilization:finite}))});
const bearing = shape({check_id:text,layer_id:text,demand:quantity,material_direction:text,comparison:shape({numerical_comparison:text,utilization:nullable(finite)}),trace:shape({factor_trace:shape({design_resistance:quantity})})});
const designContract = shape({
  preview:previewContract,status:text,status_reason:text,native_governing_check_ids:array(text),missing_sources:array(text),
  native_failed_checks:array(shape({result_id:text,limit_state:text,utilization:nullable(finite),design_resistance:nullable(quantity),demand:nullable(quantity),numerical_comparison:text})),
  connector_results:array(shape({core_fingerprint:text,status:text,reason:text,detail:nullable(shape({body:qualifiedCheck,instep:nullable(shape({method:text,utilization:finite,passed:bool,demand:quantity,factors:shape({design_resistance:quantity})}))}))})),
  attachment_results:array(shape({connector_id:text,method:text,check:qualifiedCheck})),
  local_checks:array(shape({connector_id:text,layer_id:text,scope_status:text})),web_bearing:array(bearing),flange_bearing:array(bearing),
  common_web_bolts:array(shape({bolt_id:text,status:text,method:text,governing_utilization:nullable(finite),source_required_reason:nullable(text),per_plane_design_capacity:nullable(quantity)})),
});
async function post<T>(kind: "preview" | "design-check", request: WIWallMomentRequest, signal: AbortSignal): Promise<WIWallMomentResponse<T>> {
  let response: Response;
  try { response = await mat1Fetch(`/api/v1/calculations/wi-beam-concrete-wall-moment/${kind}`, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, credentials: "same-origin", body: JSON.stringify(request), signal }); }
  catch (error) { if (error instanceof DOMException && error.name === "AbortError") throw error; throw new EvaluationTransportError("NETWORK", null, "The W/I wall-moment service could not be reached.", error); }
  let value: unknown;
  try { value = await response.json(); } catch (error) { throw new EvaluationTransportError("RESPONSE", response.status, "The wall-moment service returned unreadable JSON.", error); }
  if (!response.ok) throw new EvaluationTransportError(response.status === 422 ? "VALIDATION" : "HTTP", response.status, "The server rejected the wall-moment request.", value);
  const base = record(value) && value.api_transport_schema_version === "4.2-API-RC1" && value.contract === "4.2-RC1" && value.ordinary_pass_allowed === false && value.request_id === request.request_id && value.whole_connection_status === "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED"
    && shape({geometry_status:text,geometry_invalid_reasons:array(text),assembly_status:text,resistance_evaluated:bool,design_check_ready:bool,engineering_fingerprint:text,result_fingerprint:text})(value)
    && (kind !== "preview" || value.resistance_evaluated === false);
  if (!base || !record(value) || !(kind === "preview" ? previewContract : designContract)(value.result)) throw new EvaluationTransportError("RESPONSE", response.status, "Unsupported wall-moment response contract.", value);
  return value as unknown as WIWallMomentResponse<T>;
}
export const previewWIWallMoment = (request: WIWallMomentRequest, signal: AbortSignal) => post<WIWallMomentPreview>("preview",request,signal);
export const designWIWallMoment = (request: WIWallMomentRequest, signal: AbortSignal) => post<WIWallMomentDesign>("design-check",request,signal);
