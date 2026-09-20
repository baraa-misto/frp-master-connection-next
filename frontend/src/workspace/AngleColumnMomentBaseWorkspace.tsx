import { ConnectorBodyMaterialControl, ConnectorBodyMaterialResult } from "./connectorBodyMaterial";
import { useConnectorBodyMaterial } from "./useConnectorBodyMaterial";
import { useEffect, useMemo, useRef, useState } from "react";
import type { MultiRowQuantity } from "../api/multirowContracts";
import { loadAngleBasePreset, requestAngleBase } from "../api/angleColumnMomentBaseClient";
import type { AngleBaseConnector, AngleBaseRequest, AngleBaseResponse } from "../api/angleColumnMomentBaseContracts";
import type { WallMomentWrench } from "../api/wiWallMomentContracts";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import { buildAngleColumnMomentBaseScene } from "../visualization/angleColumnMomentBaseSceneModel";
import { ConnectionWorkspaceMain, ConnectionWorkspaceShell, ConnectionWorkspaceSidebar, PersistentConnectionViewer, SidebarGroup } from "./ConnectionWorkspaceShell";
import { formatDisplayQuantity, friendlyEnum } from "./presentation";
import { isIntentionalAbort } from "./previewWorkflow";
import { angleBaseEngineeringKey, clearAngleBaseQualifications, finiteAngleBaseInputs, useAngleColumnMomentBasePreview } from "./angleColumnMomentBaseWorkflow";
import "./angleColumnMomentBaseWorkspace.css";

function display(q:MultiRowQuantity,si:boolean):string {
  // Labels only; all engineering values are sent as the unchanged native strings.
  const moment:Readonly<Record<string,number>>={"N-mm":1,"kN-mm":1000,"kip-in":112984.8290276167};
  const factor=moment[q.unit];
  return factor===undefined?formatDisplayQuantity(q,si?"SI":"US_CUSTOMARY"):`${Number((Number(q.value)*factor/(si?1000:112984.8290276167)).toPrecision(7)).toString()} ${si?"kN-mm":"kip-in"}`;
}
function Wrench({title,value,si}:{readonly title:string;readonly value:WallMomentWrench;readonly si:boolean}){
  return <dl className="diagnostic-list"><dt>{title}</dt>{(["reference","force","moment"] as const).map(k=><div key={k}><dt>{friendlyEnum(k)} — X/Y/Z or named local frame</dt><dd>{[value[k].x,value[k].y,value[k].z].map(q=>display(q,si)).join(" · ")}</dd></div>)}</dl>;
}
export function AngleColumnMomentBaseWorkspace(){
  const [initial,setInitial]=useState<AngleBaseRequest|null>(null);
  const [error,setError]=useState<string|null>(null);
  const [retry,setRetry]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();let disposed=false;
    void loadAngleBasePreset(false,false,controller.signal).then(v=>{if(!disposed){setInitial(v);setError(null);}}).catch((e:unknown)=>{if(!disposed&&!isIntentionalAbort(e))setError(e instanceof Error?e.message:"Preset request failed.");});
    return()=>{disposed=true;controller.abort();};
  },[retry]);
  if(initial===null)return <section className="source-card" aria-label="Angle column moment base loading"><h2>Angle Column Two-Leg Moment Base</h2>{error===null?<p role="status">Loading backend-authoritative constructive preset…</p>:<div role="alert">{error}<button onClick={()=>{setRetry(n=>n+1);}}>Retry preset</button></div>}</section>;
  return <AngleBaseEditor initial={initial}/>;
}

function AngleBaseEditor({initial}:{readonly initial:AngleBaseRequest}){
  const [request,setRequest]=useState(initial),[revision,setRevision]=useState(0);
  const [design,setDesign]=useState<{key:string;response:AngleBaseResponse}|null>(null);
  const [busy,setBusy]=useState(false),[presetBusy,setPresetBusy]=useState(false),[error,setError]=useState<string|null>(null);
  const [selection,setSelection]=useState<SceneSelection>({kind:"MEMBER",id:"ANGLE_COLUMN"});
  const designSequence=useRef(0),designAbort=useRef<AbortController|null>(null),presetSequence=useRef(0),presetAbort=useRef<AbortController|null>(null);
  useEffect(()=>()=>{designSequence.current+=1;presetSequence.current+=1;designAbort.current?.abort();presetAbort.current?.abort();},[]);
  const update=(change:(next:AngleBaseRequest)=>void,mode:"engineering"|"source"|"view"="engineering")=>{
    const next=structuredClone(request);change(next);
    if(mode==="engineering")clearAngleBaseQualifications(next);
    presetSequence.current+=1;presetAbort.current?.abort();setPresetBusy(false);
    if(mode!=="view"){designSequence.current+=1;designAbort.current?.abort();setBusy(false);}
    setRequest(next);setRevision(n=>n+1);setError(null);
  };
  const load=async(unequal:boolean,si:boolean)=>{
    const serial=++presetSequence.current;presetAbort.current?.abort();const controller=new AbortController();presetAbort.current=controller;
    designSequence.current+=1;designAbort.current?.abort();setBusy(false);setPresetBusy(true);setError(null);
    try{const next=await loadAngleBasePreset(unequal,si,controller.signal);if(serial===presetSequence.current){setRequest(next);setRevision(n=>n+1);setDesign(null);}}
    catch(e){if(serial===presetSequence.current&&!isIntentionalAbort(e))setError(e instanceof Error?e.message:"Preset request failed.");}
    finally{if(serial===presetSequence.current)setPresetBusy(false);}
  };
  const invalid=finiteAngleBaseInputs(request)?null:"Enter finite decimal values before previewing.";
  const preview=useAngleColumnMomentBasePreview(request,revision,invalid);
  const result=preview.response?.result.preview??null;
  const sceneCurrent=preview.current&&!presetBusy;
  const model=useMemo(()=>{
    if(result===null)return null;
    const accepted=buildAngleColumnMomentBaseScene(result);
    // Retain the complete accepted physical snapshot, never partial invalid geometry.
    // Old action arrows/labels must not impersonate the editor's unverified loads.
    return sceneCurrent?accepted:{...accepted,appliedArrows:[],positiveArrows:[]};
  },[result,sceneCurrent]);
  const viewerState=sceneCurrent?"CURRENT BACKEND PREVIEW":preview.invalidInputs?"CURRENT INPUTS INVALID":preview.error===null?"UPDATING CURRENT INPUTS":"CURRENT PREVIEW UNAVAILABLE";
  const key=angleBaseEngineeringKey(request);
  const stale=design!==null&&(design.key!==key||preview.error!==null||(preview.current&&design.response.engineering_fingerprint!==preview.response?.engineering_fingerprint));
  const current=stale?null:design?.response.result.design??null;
  const si=request.column.leg_x.unit==="mm";
  const bodyMaterial = useConnectorBodyMaterial("angle-column-two-leg-moment-base", request, revision, () => {
    designSequence.current += 1; designAbort.current?.abort(); setBusy(false); setDesign(null); setError(null);
  });
  const run=async()=>{
    if (bodyMaterial.material === "SS316") { await bodyMaterial.run(); return; }
    const serial=++designSequence.current;designAbort.current?.abort();const controller=new AbortController();designAbort.current=controller;setBusy(true);setError(null);
    try{const value=await requestAngleBase("design-check",request,controller.signal);if(serial===designSequence.current)setDesign({key,response:value});}
    catch(e){if(serial===designSequence.current&&!isIntentionalAbort(e))setError(e instanceof Error?e.message:"Design check failed.");}
    finally{if(serial===designSequence.current)setBusy(false);}
  };
  const field=(title:string,q:MultiRowQuantity,change:(next:AngleBaseRequest,v:string)=>void,mode:"engineering"|"view"="engineering")=><label className="field-control"><span>{title}</span><span className="input-with-unit"><input aria-label={title} inputMode="decimal" value={q.value} onChange={e=>{const raw=e.currentTarget.value;update(n=>{change(n,raw);},mode);}}/><small>{q.unit}</small></span></label>;
  const connector=(name:"leg_1"|"leg_2",title:string)=>{
    const c=request[name],id=name==="leg_1"?"LEG_1_BASE_ANGLE":"LEG_2_BASE_ANGLE";
    const length=(label:string,q:MultiRowQuantity,change:(c:AngleBaseConnector,v:string)=>void)=>field(`${title} ${label}`,q,(n,v)=>{change(n[name],v);});
    const source=(label:string,value:string,change:(c:AngleBaseConnector,v:string)=>void)=><label className="field-control base44-full"><span>{label}</span><input aria-label={`${title} ${label}`} value={value} onChange={e=>{const v=e.currentTarget.value;update(n=>{change(n[name],v);},"source");}}/></label>;
    const pattern=(which:"member_pattern"|"support_pattern",legend:string)=><fieldset className="base44-input-group"><legend>{legend}</legend><div className="field-grid">{(["across","along"] as const).map(k=><label className="field-control" key={k}><span>{k==="across"?"Across extrusion":"Along leaf"}</span><input aria-label={`${title} ${legend} ${k}`} type="number" min={1} step={1} value={Number.isFinite(c.angle[which][k])?c.angle[which][k]:""} onChange={e=>{const v=e.currentTarget.valueAsNumber;update(n=>{n[name].angle[which][k]=v;});}}/></label>)}{(["gauge","pitch","center"] as const).map(k=><span key={k}>{length(`${legend} ${k==="center"?"centroid offset":friendlyEnum(k)}`,c.angle[which][k],(a,v)=>{a.angle[which][k].value=v;})}</span>)}</div></fieldset>;
    return <SidebarGroup title={title} summary="Independent geometry / qualified response" selected={selection.id===id} onSelect={()=>{setSelection({kind:"MEMBER",id});}} defaultOpen>
      <div className="field-grid">{length("Extrusion center on column leg",c.extrusion_center,(a,v)=>{a.extrusion_center.value=v;})}{(["length","member_leg","support_leg","thickness","inside_radius"] as const).map(k=><span key={k}>{length(friendlyEnum(k),c.angle.geometry[k],(a,v)=>{a.angle.geometry[k].value=v;})}</span>)}</div>
      {pattern("member_pattern","Member bolts")}{pattern("support_pattern","Foundation attachments")}
      <div className="field-grid">{length("Member bolt diameter",c.angle.fastener.bolt_diameter,(a,v)=>{a.angle.fastener.bolt_diameter.value=v;})}{length("Member hole diameter",c.angle.fastener.hole_diameter,(a,v)=>{a.angle.fastener.hole_diameter.value=v;})}
      {(["nominal_diameter","hole_diameter","specified_embedment","washer_outside_diameter","washer_thickness"] as const).map(k=><span key={k}>{length(`Foundation ${friendlyEnum(k)}`,c.angle.anchors[k],(a,v)=>{a.angle.anchors[k].value=v;})}</span>)}</div>
      <label className="field-control base44-full"><span>Member thread condition</span><select aria-label={`${title} member thread condition`} value={c.angle.fastener.thread_condition} onChange={e=>{const v=e.currentTarget.value as "INCLUDED"|"EXCLUDED";update(n=>{n[name].angle.fastener.thread_condition=v;});}}><option value="EXCLUDED">Threads excluded</option><option value="INCLUDED">Threads included</option></select></label>
      <details><summary>Explicit member washer / head / nut geometry</summary><div className="field-grid">{(["washer_diameter","washer_thickness","head_across_flats","head_height","nut_across_flats","nut_height","end_extension"] as const).map(k=><span key={k}>{length(`Member ${friendlyEnum(k)}`,c.member_hardware[k],(a,v)=>{a.member_hardware[k].value=v;})}</span>)}</div><p className="sidebar-note">Known hardware geometry only; F593 nominal strength still requires a controlled source. Foundation nuts are schematic; no hidden pedestal nut.</p></details>
      {source("Angle-body source",c.angle.connector_source_reference,(a,v)=>{a.angle.connector_source_reference=v;})}
      {source("Member-attachment capacity source",c.angle.attachment_source_reference,(a,v)=>{a.angle.attachment_source_reference=v;})}
      {source("Member normal/contact response source",c.normal_response_source_reference,(a,v)=>{a.normal_response_source_reference=v;})}
      {source("Member bolt strength source",c.fastener_source_reference,(a,v)=>{a.fastener_source_reference=v;})}
      <p className="sidebar-note">Column LW is vertical. Connector LW follows its horizontal extrusion. Geometry equality is not load-sharing authority.</p>
    </SidebarGroup>;
  };
  return <ConnectionWorkspaceShell className="angle-base44-workspace" banner={<section className="stage-banner"><h2>Angle Column Two-Leg Moment Base</h2><p>4.4-RC1 · one exterior connector on each different column leg · qualified response required</p></section>}>
    <ConnectionWorkspaceSidebar ariaLabel="Angle column two-leg moment base inputs">
      <ConnectorBodyMaterialControl material={bodyMaterial.material} onChange={bodyMaterial.choose} />
      <SidebarGroup title="Constructive presets" summary="Replace inputs — not adequate designs" defaultOpen><div className="base44-preset-grid">{([{unequal:false,system:false},{unequal:false,system:true},{unequal:true,system:false},{unequal:true,system:true}]).map(({unequal,system})=><button key={String(unequal)+String(system)} disabled={presetBusy} onClick={()=>{void load(unequal,system);}}>{unequal?"Unequal":"Equal"} / {system?"SI":"U.S."}</button>)}</div><p className="sidebar-note">Loading a preset replaces inputs and clears sources/results. No stiffness, contact or 50/50 split is inferred.</p></SidebarGroup>
      <SidebarGroup title="Angle column" summary="Actual centroid at lower end" defaultOpen selected={selection.id==="ANGLE_COLUMN"} onSelect={()=>{setSelection({kind:"MEMBER",id:"ANGLE_COLUMN"});}}><div className="field-grid">{(["leg_x","leg_y","thickness","view_length"] as const).map(k=><span key={k}>{field(k==="view_length"?"Column view length":`Column ${friendlyEnum(k)}`,request.column[k],(n,v)=>{n.column[k].value=v;},k==="view_length"?"view":"engineering")}</span>)}</div><p className="sidebar-note">X/Y are leg-parallel axes, not principal axes. View length defines no failure end plane and does not stale design.</p></SidebarGroup>
      <SidebarGroup title="Finite concrete pedestal" summary="External foundation design" defaultOpen><div className="field-grid">{(["width_x","width_y","depth"] as const).map(k=><span key={k}>{field(`Pedestal ${friendlyEnum(k)}`,request.foundation[k],(n,v)=>{n.foundation[k].value=v;})}</span>)}</div><p className="sidebar-note">Nominal flush prepared contact. The real L footprint is not its bounding rectangle. Embedment is geometry, not anchor capacity.</p></SidebarGroup>
      <SidebarGroup title="Column-end actions" summary="Signed physical right-hand X/Y/Z" defaultOpen><div className="field-grid">{([["axial","Axial N — positive uplift"],["shear_x","Shear Vx"],["shear_y","Shear Vy"],["moment_x","Moment Mx"],["moment_y","Moment My"]] as const).map(([k,title])=><span key={k}>{field(title,request.actions[k],(n,v)=>{n.actions[k].value=v;})}</span>)}</div><p className="sidebar-note">Positive N = uplift; negative N = compression. Independent input torque Mz is outside RC1. Reference-generated Mz remains in the foundation handoff.</p></SidebarGroup>
      {connector("leg_1","Leg 1 base angle")}{connector("leg_2","Leg 2 base angle")}
      <SidebarGroup title="Assembly qualification" summary="Trusted server records only" defaultOpen>{([["response_source_reference","Complete two-leg base-response source"],["column_zone_source_reference","Common column-end-zone capacity source"]] as const).map(([k,title])=><label className="field-control base44-full" key={k}><span>{title}</span><input aria-label={title} value={request[k]} onChange={e=>{const v=e.currentTarget.value;update(n=>{n[k]=v;},"source");}}/></label>)}<p className="sidebar-note">Typed text is not qualification. Geometry and load edits clear incompatible references. No synthetic source is available in production.</p></SidebarGroup>
      <SidebarGroup title="Model / design status" summary={current?.status??(stale?"Stale":"Not checked")} defaultOpen><p role="status">{preview.state}</p><p>Branch allocation: {preview.current?result?.branch_allocation_status:"Not current"}</p><p>Internal checks: {current?.status??(stale?"Stale — rerun explicitly":"Not checked")}</p><button className="primary-button" disabled={bodyMaterial.busy || busy||presetBusy||!preview.current||preview.response?.design_check_ready!==true} onClick={()=>{void run();}}>{busy?"Running design check…":"Run Design Check"}</button></SidebarGroup>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain><ConnectorBodyMaterialResult state={bodyMaterial} /><PersistentConnectionViewer><section className={sceneCurrent?"base44-preview-state":"base44-preview-state base44-last-valid"} aria-label="Stage 4.4 preview state" data-preview-state={sceneCurrent?"current":model===null?"empty":"last-valid"} data-preview-fingerprint={result?.engineering_fingerprint??""}>
      <div className="base44-viewer-status" role="status" id="base44-viewer-status"><strong>{!sceneCurrent&&model!==null?"LAST VALID PREVIEW — ":""}{viewerState}</strong>
        {!sceneCurrent&&model!==null?<p>All displayed column, base-angle, member-bolt and foundation-attachment geometry belongs to the last valid preview, not the current inputs. Previous action arrows and labels are hidden. Design check is unavailable until the current preview is valid.</p>:null}
        {result===null?null:<details><summary>{sceneCurrent?"Current":"Last valid"} scene fingerprint</summary><code>{result.engineering_fingerprint}</code></details>}
      </div>
      {preview.error===null?null:<div role="alert" className="error-banner">{preview.error}<button onClick={preview.retry}>Retry preview</button></div>}
      <div aria-describedby="base44-viewer-status">{model===null?<p>No valid backend geometry yet.</p>:<VisualizationPanel title="Angle Column Two-Leg Moment Base" model={model} selection={selection} onSelect={setSelection} actionSourceLabel="Column" appliedActionInputValues={{FX:request.actions.shear_x.value,FY:request.actions.shear_y.value,FZ:request.actions.axial.value,MX:request.actions.moment_x.value,MY:request.actions.moment_y.value,MZ:"0"}} onAppliedActionValueChange={(component,value)=>{const fields={FX:"shear_x",FY:"shear_y",FZ:"axial",MX:"moment_x",MY:"moment_y"} as const;if(sceneCurrent&&component!=="MZ")update(n=>{n.actions[fields[component]].value=value;});}}/>}</div>
      </section></PersistentConnectionViewer>
      {error===null?null:<p role="alert">{error}</p>}{stale?<p role="status" className="stale-banner">Design is stale. No previous-case checks are shown for these inputs.</p>:null}
      {result===null?null:<section className="tee-results-grid" aria-label="Stage 4.4 engineering preview"><article className="source-card"><h3>Required total foundation action</h3><p>{preview.current?"Current input":"Last valid input"} · not individual anchor reactions</p><Wrench title="Base on foundation at O — X/Y/Z" value={result.required_total_foundation_action} si={si}/><details><summary>Applied centroid wrench and opposite reaction</summary><Wrench title="Column on base at actual C" value={result.column_on_base} si={si}/><Wrench title="Opposite foundation reaction — do not add again" value={result.opposite_foundation_reaction} si={si}/></details><p>Total input transport: {result.exact_total_transport?"Exact":"Not proven"}</p><p>Base-response conservation: {result.response.exact_equilibrium===null?"Unavailable":result.response.exact_equilibrium?"Exact":"Not proven"}</p><p>Response qualification: {result.response.status}</p>{result.response.reasons.map(r=><p key={r}>{r}</p>)}</article>
        {(["LEG_1_BASE_ANGLE","LEG_2_BASE_ANGLE"] as const).map((id,index)=>{const t=result.transfers.find(v=>v.connector_id===id);return <article className="source-card" key={id}><h3>{friendlyEnum(id)}</h3>{t===undefined?<p>Member / heel / foot wrenches and per-bolt demands unavailable — complete base-response source required. Unknown is not zero.</p>:<><Wrench title="Net connector on foundation — global XYZ" value={t.connector_on_foundation} si={si}/><p>Core equilibrium: {t.native_core_equilibrium?"Exact":"Not proven"}</p><p>Member complement F_C / M_A / M_B: {t.member_out_of_plane_f_c_m_a_m_b.map(q=>display(q,si)).join(" · ")}</p><details><summary>Complete local member / heel and unchanged Slice 8 trace</summary><Wrench title="Member A/B/C" value={t.core.request.member_action} si={si}/><Wrench title="Heel A/B/C" value={t.core.heel} si={si}/><pre>{JSON.stringify(t,null,2)}</pre></details></>}<p>Angle body: {current?.connector_results[index]?.status??"Not evaluated"}</p><p>Member attachment: {current?.member_attachment_results[index]?.check.status??"Not evaluated"}</p><p>Normal/contact response: {current?.member_responses[index]?.status??"Unavailable / not checked"}</p>{result.foundation_breakdowns.filter(b=>b.domain.connector_id===id).map(b=><div key={b.domain.connector_id}><p>Anchor/contact breakdown: {b.status} · external design</p>{b.reasons.map(reason=><p key={reason}>{reason}</p>)}{b.record===null?null:<details><summary>Qualified foundation actions — {b.record.reference}</summary><p>{b.record.issuer} · {b.record.applicability}</p><p>Exact parent recovery: {b.proof?.passed===true?"Proven":"Not proven"}</p><pre>{JSON.stringify(b.record.actions,null,2)}</pre></details>}</div>)}<p>Net foot handoff already includes any foot contact; never add its breakdown again.</p></article>;})}
        <article className="source-card"><h3>Direct column-end contact</h3>{result.direct_column_contact===null?<p>Unavailable — compression sign alone does not determine active contact.</p>:<Wrench title="Direct column on foundation — counted once" value={result.direct_column_contact} si={si}/>}<details><summary>Assembled handoff / native diagnostics / physical records</summary><pre>{JSON.stringify({assembled:result.assembled_foundation_action,forceResidual:result.assembled_force_residual,momentResidual:result.assembled_moment_residual,geometry:result.geometry},null,2)}</pre></details></article>
        <article className="qualification-banner"><div><h3>External design and engineering review required</h3><p>{result.disclaimer}</p><p>{result.foundation_strength_status}</p><p>{result.overall_column_status}</p><p>{result.classification_status}</p><p>Engineering fingerprint: {result.engineering_fingerprint}</p></div></article>
      </section>}
      {current===null?null:<section className="source-card" aria-label="Stage 4.4 design results"><h3>Explicit design-check trace</h3><p>{current.status} · {current.status_reason}</p><p>Native governing: {current.native_governing_check_ids.join(", ")||"No native governing check selected"}</p><table><thead><tr><th>Scope</th><th>Status</th></tr></thead><tbody>{current.scope_statuses.map(([scope,state])=><tr key={scope}><td>{friendlyEnum(scope)}</td><td>{state}</td></tr>)}</tbody></table><h3>Required evaluated failures</h3>{current.failed_check_ids.length===0?<p>No evaluated failure returned for this input; unresolved coverage is not a PASS.</p>:current.failed_check_ids.map(id=><p key={id}>FAIL · {id}</p>)}<h3>Member bolt and local FRP checks</h3><div className="base44-table"><table><thead><tr><th>Actual region / check</th><th>Status / applicability</th><th>Demand / resistance</th></tr></thead><tbody>{current.local_checks.map(c=><tr key={c.check_id}><td>{c.check_id}<br/>{c.material_direction}</td><td>{c.status}<br/>{c.applicability}</td><td>{c.demand===null?"Unavailable":display(c.demand,si)} / {c.resistance===null?"Unavailable":display(c.resistance,si)}</td></tr>)}</tbody></table></div><h3>Missing qualification and source-limited checks</h3>{current.missing_sources.map(s=><p key={s}>{s}</p>)}<details><summary>Complete current native design/source trace</summary><pre>{JSON.stringify(current,null,2)}</pre></details><p>Design input: {design?.response.engineering_fingerprint}<br/>Result: {current.result_fingerprint}</p></section>}
    </ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
