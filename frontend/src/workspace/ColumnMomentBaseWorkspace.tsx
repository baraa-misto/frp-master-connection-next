import { ConnectorBodyMaterialControl, ConnectorBodyMaterialResult } from "./connectorBodyMaterial";
import { useConnectorBodyMaterial } from "./useConnectorBodyMaterial";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MultiRowQuantity } from "../api/multirowContracts";
import { convertColumnMomentBaseUnits, loadColumnMomentBasePreset, requestColumnMomentBase } from "../api/columnMomentBaseClient";
import type { ColumnMomentBaseConnector, ColumnMomentBaseRequest, ColumnMomentBaseResponse } from "../api/columnMomentBaseContracts";
import type { WallMomentWrench } from "../api/wiWallMomentContracts";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import { buildColumnMomentBaseScene } from "../visualization/columnMomentBaseSceneModel";
import { ConnectionWorkspaceMain, ConnectionWorkspaceShell, ConnectionWorkspaceSidebar, PersistentConnectionViewer, SidebarGroup } from "./ConnectionWorkspaceShell";
import { formatDisplayQuantity, friendlyEnum } from "./presentation";
import { isIntentionalAbort } from "./previewWorkflow";
import { columnMomentBaseEngineeringKey, clearColumnMomentBaseQualifications, finiteColumnMomentBaseInputs, useColumnMomentBasePreview } from "./columnMomentBaseWorkflow";
import "./columnMomentBaseWorkspace.css";

type RequestUpdate=(change:(next:ColumnMomentBaseRequest)=>void,mode?:"engineering"|"source"|"view")=>void;

function ConnectorControls({name,title,request,selection,setSelection,update}:{readonly name:"x_positive"|"x_negative"|"y_positive"|"y_negative";readonly title:string;readonly request:ColumnMomentBaseRequest;readonly selection:SceneSelection;readonly setSelection:(s:SceneSelection)=>void;readonly update:RequestUpdate}){
  const field=(title:string,q:MultiRowQuantity,change:(next:ColumnMomentBaseRequest,v:string)=>void,mode:"engineering"|"view"="engineering",disabled=false)=><label className="field-control"><span>{title}</span><span className="input-with-unit"><input aria-label={title} inputMode="decimal" disabled={disabled} value={q.value} onChange={e=>{const raw=e.currentTarget.value;update(n=>{change(n,raw);},mode);}}/><small>{disabled?"N/A":q.unit}</small></span></label>;

    const c=request[name],id={x_positive:"X_POS",x_negative:"X_NEG",y_positive:"Y_POS",y_negative:"Y_NEG"}[name];
    const derived=name==="x_negative"||(name==="y_negative"&&request.column.family!=="WI");
    const length=(label:string,q:MultiRowQuantity,change:(c:ColumnMomentBaseConnector,v:string)=>void,disabled=false)=>field(`${title} ${label}`,q,(n,v)=>{change(n[name],v);},"engineering",disabled);
    const source=(label:string,value:string,change:(c:ColumnMomentBaseConnector,v:string)=>void)=><label className="field-control base45-full"><span>{label}</span><input aria-label={`${title} ${label}`} value={value} onChange={e=>{const v=e.currentTarget.value;update(n=>{change(n[name],v);},"source");}}/></label>;
    const pattern=(which:"member_pattern"|"support_pattern",legend:string)=><fieldset className="base45-input-group"><legend>{legend}</legend><div className="field-grid">{(["across","along"] as const).map(k=><label className="field-control" key={k}><span>{k==="across"?"Across extrusion":"Along leaf"}</span><input aria-label={`${title} ${legend} ${k}`} type="number" min={1} step={1} value={Number.isFinite(c.angle[which][k])?c.angle[which][k]:""} onChange={e=>{const v=e.currentTarget.valueAsNumber;update(n=>{n[name].angle[which][k]=v;});}}/></label>)}{(["gauge","pitch","center"] as const).map(k=><span key={k}>{length(`${legend} ${k==="center"?"centroid offset":friendlyEnum(k)}`,c.angle[which][k],(a,v)=>{a.angle[which][k].value=v;},k==="gauge"?c.angle[which].across===1:k==="pitch"&&c.angle[which].along===1)}</span>)}</div></fieldset>;
    return <SidebarGroup title={title} summary="Independent geometry / qualified response" selected={selection.id===id} onSelect={()=>{setSelection({kind:"MEMBER",id});}} defaultOpen>
      <div className="field-grid">{derived?<p className="sidebar-note">Tangential center follows the canonical positive-face grid.</p>:length("Tangential extrusion center",c.extrusion_center,(a,v)=>{a.extrusion_center.value=v;})}{(["length","member_leg","support_leg","thickness","inside_radius"] as const).map(k=><span key={k}>{length(friendlyEnum(k),c.angle.geometry[k],(a,v)=>{a.angle.geometry[k].value=v;})}</span>)}</div>
      {derived?<p className="sidebar-note">Member grid, bolt diameter and hardware are derived from the positive-face owner. One shared physical shank; no equal-force assumption.</p>:pattern("member_pattern","Member bolts")}{pattern("support_pattern","Foundation attachments")}
      <div className="field-grid">{derived?null:<>{length("Member bolt diameter",c.angle.fastener.bolt_diameter,(a,v)=>{a.angle.fastener.bolt_diameter.value=v;})}{length("Member hole diameter",c.angle.fastener.hole_diameter,(a,v)=>{a.angle.fastener.hole_diameter.value=v;})}</>}
      {(["nominal_diameter","hole_diameter","specified_embedment","washer_outside_diameter","washer_thickness"] as const).map(k=><span key={k}>{length(`Foundation ${friendlyEnum(k)}`,c.angle.anchors[k],(a,v)=>{a.angle.anchors[k].value=v;})}</span>)}</div>
      {derived?null:<fieldset className="base45-input-group"><legend>Canonical member fastener</legend><label className="field-control base45-full"><span>Member thread condition</span><select aria-label={`${title} member thread condition`} value={c.angle.fastener.thread_condition} onChange={e=>{const v=e.currentTarget.value as "INCLUDED"|"EXCLUDED";update(n=>{n[name].angle.fastener.thread_condition=v;});}}><option value="EXCLUDED">Threads excluded</option><option value="INCLUDED">Threads included</option></select></label>
      <details><summary>Explicit member washer / head / nut geometry</summary><div className="field-grid">{(["washer_diameter","washer_thickness","head_across_flats","head_height","nut_across_flats","nut_height","end_extension"] as const).map(k=><span key={k}>{length(`Member ${friendlyEnum(k)}`,c.member_hardware[k],(a,v)=>{a.member_hardware[k].value=v;})}</span>)}</div><p className="sidebar-note">Known hardware geometry only; F593 nominal strength still requires a controlled source. Foundation nuts are schematic; no hidden pedestal nut.</p></details></fieldset>}
      {source("Angle-body source",c.angle.connector_source_reference,(a,v)=>{a.angle.connector_source_reference=v;})}
      {source("Member-attachment capacity source",c.angle.attachment_source_reference,(a,v)=>{a.angle.attachment_source_reference=v;})}
      {derived?null:source("Member bolt strength source",c.fastener_source_reference,(a,v)=>{a.fastener_source_reference=v;})}
      <p className="sidebar-note">Column LW is vertical. Connector LW follows its horizontal extrusion. Geometry equality is not load-sharing authority.</p>
    </SidebarGroup>;
}
function display(q:MultiRowQuantity,si:boolean):string {
  // Labels only; all engineering values are sent as the unchanged native strings.
  const moment:Readonly<Record<string,number>>={"N-mm":1,"kN-mm":1000,"kip-in":112984.8290276167};
  const factor=moment[q.unit];
  return factor===undefined?formatDisplayQuantity(q,si?"SI":"US_CUSTOMARY"):`${Number((Number(q.value)*factor/(si?1000:112984.8290276167)).toPrecision(7)).toString()} ${si?"kN-mm":"kip-in"}`;
}
function Wrench({title,value,si}:{readonly title:string;readonly value:WallMomentWrench;readonly si:boolean}){
  return <dl className="diagnostic-list"><dt>{title}</dt>{(["reference","force","moment"] as const).map(k=><div key={k}><dt>{friendlyEnum(k)} — X/Y/Z or named local frame</dt><dd>{[value[k].x,value[k].y,value[k].z].map(q=>display(q,si)).join(" · ")}</dd></div>)}</dl>;
}
export function ColumnMomentBaseWorkspace(){
  const [initial,setInitial]=useState<ColumnMomentBaseRequest|null>(null);
  const [error,setError]=useState<string|null>(null);
  const [retry,setRetry]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();let disposed=false;
    void loadColumnMomentBasePreset("WI","FOUR_XY",false,controller.signal).then(v=>{if(!disposed){setInitial(v);setError(null);}}).catch((e:unknown)=>{if(!disposed&&!isIntentionalAbort(e))setError(e instanceof Error?e.message:"Preset request failed.");});
    return()=>{disposed=true;controller.abort();};
  },[retry]);
  if(initial===null)return <section className="source-card" aria-label="Column moment base loading"><h2>W/I, RHS and SRS Column Moment Base</h2>{error===null?<p role="status">Loading backend-authoritative column defaults…</p>:<div role="alert">{error}<button onClick={()=>{setRetry(n=>n+1);}}>Retry preset</button></div>}</section>;
  return <ColumnMomentBaseEditor initial={initial}/>;
}

function ColumnMomentBaseEditor({initial}:{readonly initial:ColumnMomentBaseRequest}){
  const [request,setRequest]=useState(initial),[revision,setRevision]=useState(0);
  const [design,setDesign]=useState<{key:string;response:ColumnMomentBaseResponse}|null>(null);
  const [busy,setBusy]=useState(false),[presetBusy,setPresetBusy]=useState(false),[error,setError]=useState<string|null>(null);
  const [selection,setSelection]=useState<SceneSelection>({kind:"MEMBER",id:"COLUMN"});
  const designSequence=useRef(0),designAbort=useRef<AbortController|null>(null),presetSequence=useRef(0),presetAbort=useRef<AbortController|null>(null);
  useEffect(()=>()=>{designSequence.current+=1;presetSequence.current+=1;designAbort.current?.abort();presetAbort.current?.abort();},[]);
  const update=useCallback((change:(next:ColumnMomentBaseRequest)=>void,mode:"engineering"|"source"|"view"="engineering")=>{
    const next=structuredClone(request);change(next);
    if(mode==="engineering")clearColumnMomentBaseQualifications(next);
    presetSequence.current+=1;presetAbort.current?.abort();setPresetBusy(false);
    if(mode!=="view"){designSequence.current+=1;designAbort.current?.abort();setBusy(false);}
    setRequest(next);setRevision(n=>n+1);setError(null);
  },[request]);
  const load=useCallback(async(preset:string,layout:ColumnMomentBaseRequest["layout"],si:boolean)=>{
    const serial=++presetSequence.current;presetAbort.current?.abort();const controller=new AbortController();presetAbort.current=controller;
    designSequence.current+=1;designAbort.current?.abort();setBusy(false);setPresetBusy(true);setError(null);
    try{const next=await loadColumnMomentBasePreset(preset,layout,si,controller.signal);if(serial===presetSequence.current){setRequest(next);setRevision(n=>n+1);setDesign(null);}}
    catch(e){if(serial===presetSequence.current&&!isIntentionalAbort(e))setError(e instanceof Error?e.message:"Preset request failed.");}
    finally{if(serial===presetSequence.current)setPresetBusy(false);}
  },[]);
  const convertUnits=async(si:boolean)=>{
    const serial=++presetSequence.current;presetAbort.current?.abort();const controller=new AbortController();presetAbort.current=controller;
    designSequence.current+=1;designAbort.current?.abort();setBusy(false);setPresetBusy(true);setError(null);
    try{const next=await convertColumnMomentBaseUnits(request,si,controller.signal);if(serial===presetSequence.current){setRequest(next);setRevision(n=>n+1);setDesign(previous=>previous?.key!==columnMomentBaseEngineeringKey(request)?previous:{...previous,key:columnMomentBaseEngineeringKey(next)});}}
    catch(e){if(serial===presetSequence.current&&!isIntentionalAbort(e))setError(e instanceof Error?e.message:"Unit conversion failed.");}
    finally{if(serial===presetSequence.current)setPresetBusy(false);}
  };
  const invalid=finiteColumnMomentBaseInputs(request)?null:"Enter finite decimal values before previewing.";
  const preview=useColumnMomentBasePreview(request,revision,invalid);
  const result=preview.response?.result.preview??null;
  const sceneCurrent=preview.current&&!presetBusy;
  const model=useMemo(()=>{
    if(result===null)return null;
    const accepted=buildColumnMomentBaseScene(result);
    // Retain the complete accepted physical snapshot, never partial invalid geometry.
    // Old action arrows/labels must not impersonate the editor's unverified loads.
    return sceneCurrent?accepted:{...accepted,appliedArrows:[],positiveArrows:[]};
  },[result,sceneCurrent]);
  const viewerState=sceneCurrent?"CURRENT BACKEND PREVIEW":preview.invalidInputs?"CURRENT INPUTS INVALID":preview.error===null?"UPDATING CURRENT INPUTS":"CURRENT PREVIEW UNAVAILABLE";
  const key=columnMomentBaseEngineeringKey(request);
  const stale=design!==null&&(design.key!==key||preview.error!==null||(preview.current&&design.response.engineering_fingerprint!==preview.response?.engineering_fingerprint));
  const current=stale?null:design?.response.result.design??null;
  const si=request.column.width.unit==="mm";
  const bodyMaterial = useConnectorBodyMaterial("wi-rhs-srs-column-moment-base", request, revision, () => {
    designSequence.current += 1; designAbort.current?.abort(); setBusy(false); setDesign(null); setError(null);
  });
  const run=async()=>{
    if (bodyMaterial.material === "SS316") { await bodyMaterial.run(); return; }
    const serial=++designSequence.current;designAbort.current?.abort();const controller=new AbortController();designAbort.current=controller;setBusy(true);setError(null);
    try{const value=await requestColumnMomentBase("design-check",request,controller.signal);if(serial===designSequence.current)setDesign({key,response:value});}
    catch(e){if(serial===designSequence.current&&!isIntentionalAbort(e))setError(e instanceof Error?e.message:"Design check failed.");}
    finally{if(serial===designSequence.current)setBusy(false);}
  };
  const field=(title:string,q:MultiRowQuantity,change:(next:ColumnMomentBaseRequest,v:string)=>void,mode:"engineering"|"view"="engineering")=><label className="field-control"><span>{title}</span><span className="input-with-unit"><input aria-label={title} inputMode="decimal" value={q.value} onChange={e=>{const raw=e.currentTarget.value;update(n=>{change(n,raw);},mode);}}/><small>{q.unit}</small></span></label>;
  return <ConnectionWorkspaceShell className="column-base45-workspace" banner={<section className="stage-banner"><h2>W/I, RHS and SRS Column Moment Base</h2><p>4.5-RC1 · opposite web/exterior face pairs or four angles · complete response qualification required</p></section>}>
    <ConnectionWorkspaceSidebar ariaLabel="Column moment base inputs">
      <ConnectorBodyMaterialControl material={bodyMaterial.material} onChange={bodyMaterial.choose} />
      <SidebarGroup title="Units / column shape / layout" summary="Independent controls — editable geometry" defaultOpen>
        <label className="field-control"><span>Display / input units — preserve physical inputs</span><select aria-label="Unit system" value={si?"SI":"US_CUSTOMARY"} disabled={presetBusy||invalid!==null} onChange={e=>{void convertUnits(e.currentTarget.value==="SI");}}><option value="US_CUSTOMARY">U.S. Units</option><option value="SI">S.I. Units</option></select></label>
        <label className="field-control"><span>Column shape</span><select aria-label="Column shape" value={request.column.family} disabled={presetBusy} onChange={e=>{void load(e.currentTarget.value,request.layout,si);}}><option value="WI">W/I Shape Column</option><option value="RHS">Hollow Rectangular Tube</option><option value="SRS">Solid Rectangular Tube</option></select></label>
        <label className="field-control"><span>Active connector layout</span><select aria-label="Active connector layout" value={request.layout} onChange={e=>{const layout=e.currentTarget.value as ColumnMomentBaseRequest["layout"];update(n=>{n.layout=layout;});}}><option value="TWO_X">TWO_X — opposite X faces</option><option value="TWO_Y">TWO_Y — opposite Y faces</option><option value="FOUR_XY">FOUR_XY — all four faces</option></select></label>
        <p className="sidebar-note">Shape changes initialize editable generic geometry and clear qualification. Units preserve physical inputs. New angles use 2 × 1 member bolts and 1 × 1 foundation attachments. Zero tangential offset centers each angle on its selected column face. X/Y elevations remain staggered. No load-sharing assumption.</p>
      </SidebarGroup>
      <SidebarGroup title="Column profile / placement" summary={request.column.family+" · native lower-end centroid"} defaultOpen selected={selection.id==="COLUMN"} onSelect={()=>{setSelection({kind:"MEMBER",id:"COLUMN"});}}>
        <div className="field-grid">{(["width","depth",...(request.column.family==="WI"?["web_thickness","flange_thickness"] as const:request.column.family==="RHS"?["wall_thickness"] as const:[]),"offset_x","offset_y","view_length"] as const).map(k=><span key={k}>{field(k==="view_length"?"Column view length":`Column ${friendlyEnum(k)}`,request.column[k],(n,v)=>{n.column[k].value=v;},k==="view_length"?"view":"engineering")}</span>)}</div>
        <p className="sidebar-note">X/Y are native width/depth axes; neither is automatically the stronger direction. View length defines no failure end or action lever arm. Placement offsets contribute exact generated Mz.</p>
      </SidebarGroup>
      <SidebarGroup title="Finite concrete pedestal" summary="External foundation design" defaultOpen><div className="field-grid">{(["width_x","width_y","depth"] as const).map(k=><span key={k}>{field(`Pedestal ${friendlyEnum(k)}`,request.foundation[k],(n,v)=>{n.foundation[k].value=v;})}</span>)}</div><p className="sidebar-note">Nominal flush prepared contact. Pressure acts only on the actual W/I, hollow-ring or solid footprint. Embedment is geometry, not anchor capacity.</p></SidebarGroup>
      <SidebarGroup title="Column-end actions" summary="Signed physical right-hand X/Y/Z" defaultOpen><div className="field-grid">{([["axial","Axial N — positive uplift"],["shear_x","Shear Vx"],["shear_y","Shear Vy"],["moment_x","Moment Mx"],["moment_y","Moment My"]] as const).map(([k,title])=><span key={k}>{field(title,request.actions[k],(n,v)=>{n.actions[k].value=v;})}</span>)}</div><p className="sidebar-note">Positive N = uplift; negative N = compression. Independent input torque Mz is outside RC1. Reference-generated Mz remains in the foundation handoff.</p></SidebarGroup>
      {request.layout!=="TWO_Y"?<><ConnectorControls name="x_positive" title="X positive base angle" request={request} selection={selection} setSelection={setSelection} update={update}/><ConnectorControls name="x_negative" title="X negative base angle" request={request} selection={selection} setSelection={setSelection} update={update}/></>:null}{request.layout!=="TWO_X"?<><ConnectorControls name="y_positive" title="Y positive base angle" request={request} selection={selection} setSelection={setSelection} update={update}/><ConnectorControls name="y_negative" title="Y negative base angle" request={request} selection={selection} setSelection={setSelection} update={update}/></>:null}
      <SidebarGroup title="Assembly qualification" summary="Trusted server records only" defaultOpen>{([["response_source_reference","Complete multi-angle base-response source"],["column_zone_source_reference","Common column-end-zone capacity source"]] as const).map(([k,title])=><label className="field-control base45-full" key={k}><span>{title}</span><input aria-label={title} value={request[k]} onChange={e=>{const v=e.currentTarget.value;update(n=>{n[k]=v;},"source");}}/></label>)}<p className="sidebar-note">Typed text is not qualification. Geometry and load edits clear incompatible references. No synthetic source is available in production.</p></SidebarGroup>
      <SidebarGroup title="Model / design status" summary={current?.status??(stale?"Stale":"Not checked")} defaultOpen><p role="status">{preview.state}</p><p>Branch allocation: {preview.current?result?.branch_allocation_status:"Not current"}</p><p>Internal checks: {current?.status??(stale?"Stale — rerun explicitly":"Not checked")}</p><button className="primary-button" disabled={bodyMaterial.busy || busy||presetBusy||!preview.current||preview.response?.design_check_ready!==true} onClick={()=>{void run();}}>{busy?"Running design check…":"Run Design Check"}</button></SidebarGroup>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain><ConnectorBodyMaterialResult state={bodyMaterial} /><PersistentConnectionViewer><section className={sceneCurrent?"base45-preview-state":"base45-preview-state base45-last-valid"} aria-label="Stage 4.5 preview state" data-preview-state={sceneCurrent?"current":model===null?"empty":"last-valid"} data-preview-fingerprint={result?.engineering_fingerprint??""}>
      <div className="base45-viewer-status" role="status" id="base45-viewer-status"><strong>{!sceneCurrent&&model!==null?"LAST VALID PREVIEW — ":""}{viewerState}</strong>
        {!sceneCurrent&&model!==null?<p>All displayed column, base-angle, member-bolt and foundation-attachment geometry belongs to the last valid preview, not the current inputs. Previous action arrows and labels are hidden. Design check is unavailable until the current preview is valid.</p>:null}
        {result===null?null:<details><summary>{sceneCurrent?"Current":"Last valid"} scene fingerprint</summary><code>{result.engineering_fingerprint}</code></details>}
      </div>
      {preview.error===null?null:<div role="alert" className="error-banner">{preview.error}<button onClick={preview.retry}>Retry preview</button></div>}
      <div aria-describedby="base45-viewer-status">{model===null?<p>No valid backend geometry yet.</p>:<VisualizationPanel title="W/I, RHS and SRS Column Moment Base" model={model} selection={selection} onSelect={setSelection} actionSourceLabel="Column" appliedActionInputValues={{FX:request.actions.shear_x.value,FY:request.actions.shear_y.value,FZ:request.actions.axial.value,MX:request.actions.moment_x.value,MY:request.actions.moment_y.value,MZ:"0"}} onAppliedActionValueChange={(component,value)=>{const fields={FX:"shear_x",FY:"shear_y",FZ:"axial",MX:"moment_x",MY:"moment_y"} as const;if(sceneCurrent&&component!=="MZ")update(n=>{n.actions[fields[component]].value=value;});}}/>}</div>
      </section></PersistentConnectionViewer>
      {error===null?null:<p role="alert">{error}</p>}{stale?<p role="status" className="stale-banner">Design is stale. No previous-case checks are shown for these inputs.</p>:null}
      {result===null?null:<section className="tee-results-grid" aria-label="Stage 4.5 engineering preview"><article className="source-card"><h3>Required total foundation action</h3><p>{preview.current?"Current input":"Last valid input"} · not individual anchor reactions</p><Wrench title="Base on foundation at O — X/Y/Z" value={result.required_total_foundation_action} si={si}/><details><summary>Applied centroid wrench and opposite reaction</summary><Wrench title="Column on base at actual C" value={result.column_on_base} si={si}/><Wrench title="Opposite foundation reaction — do not add again" value={result.opposite_foundation_reaction} si={si}/></details><p>Total input transport: {result.exact_total_transport?"Exact":"Not proven"}</p><p>Base-response conservation: {result.response.exact_equilibrium===null?"Unavailable":result.response.exact_equilibrium?"Exact":"Not proven"}</p><p>Response qualification: {result.response.status}</p>{result.response.reasons.map(r=><p key={r}>{r}</p>)}</article>
        {result.geometry.angles.map(({connector_id:id},index)=>{const t=result.transfers.find(v=>v.connector_id===id);return <article className="source-card" key={id}><h3>{friendlyEnum(id)}</h3>{t===undefined?<p>Member / heel / foot wrenches and per-bolt demands unavailable — complete base-response source required. Unknown is not zero.</p>:<><Wrench title="Net connector on foundation — global XYZ" value={t.connector_on_foundation} si={si}/><p>Core equilibrium: {t.native_core_equilibrium?"Exact":"Not proven"}</p><p>Member complement F_C / M_A / M_B: {t.member_out_of_plane_f_c_m_a_m_b.map(q=>display(q,si)).join(" · ")}</p><details><summary>Complete local member / heel and native core and separate Slice 8 reference candidate</summary><Wrench title="Member A/B/C" value={t.core.request.member_action} si={si}/><Wrench title="Heel A/B/C" value={t.core.heel} si={si}/><pre>{JSON.stringify(t,null,2)}</pre></details></>}<p>Angle body: {current?.connector_results[index]?.status??"Not evaluated"}</p><p>Member attachment: {current?.member_attachment_results[index]?.check.status??"Not evaluated"}</p><p>Normal/contact response: {result.response.qualified?"Qualified coupled response":"Unavailable / not checked"}</p>{result.foundation_breakdowns.filter(b=>b.domain.connector_id===id).map(b=><div key={b.domain.connector_id}><p>Anchor/contact breakdown: {b.status} · external design</p>{b.reasons.map(reason=><p key={reason}>{reason}</p>)}{b.record===null?null:<details><summary>Qualified foundation actions — {b.record.reference}</summary><p>{b.record.issuer} · {b.record.applicability}</p><p>Exact parent recovery: {b.proof?.passed===true?"Proven":"Not proven"}</p><pre>{JSON.stringify(b.record.actions,null,2)}</pre></details>}</div>)}<p>Net foot handoff already includes any foot contact; never add its breakdown again.</p></article>;})}
        <article className="source-card"><h3>Direct column-end contact</h3>{result.direct_column_contact===null?<p>Unavailable — compression sign alone does not determine active contact.</p>:<Wrench title="Direct column on foundation — counted once" value={result.direct_column_contact} si={si}/>}<details><summary>Assembled handoff / native diagnostics / physical records</summary><pre>{JSON.stringify({assembled:result.assembled_foundation_action,forceResidual:result.assembled_force_residual,momentResidual:result.assembled_moment_residual,geometry:result.geometry},null,2)}</pre></details></article>
        <article className="qualification-banner"><div><h3>External design and engineering review required</h3><p>{result.disclaimer}</p><p>{result.foundation_strength_status}</p><p>{result.overall_column_status}</p><p>{result.classification_status}</p><p>Engineering fingerprint: {result.engineering_fingerprint}</p></div></article>
      </section>}
      {current===null?null:<section className="source-card" aria-label="Stage 4.5 design results"><h3>Explicit design-check trace</h3><p>{current.status} · {current.status_reason}</p><table><thead><tr><th>Scope</th><th>Status</th></tr></thead><tbody>{current.scope_statuses.map(([scope,state])=><tr key={scope}><td>{friendlyEnum(scope)}</td><td>{state}</td></tr>)}</tbody></table><h3>Required evaluated failures</h3>{current.failed_check_ids.length===0?<p>No evaluated failure returned for this input; unresolved coverage is not a PASS.</p>:current.failed_check_ids.map(id=><p key={id}>FAIL · {id}</p>)}<h3>Member bolt and local FRP checks</h3><div className="base45-table"><table><thead><tr><th>Actual region / check</th><th>Status / applicability</th><th>Demand / resistance</th></tr></thead><tbody>{current.local_checks.map(c=><tr key={c.check_id}><td>{c.check_id}<br/>{c.material_direction}</td><td>{c.status}<br/>{c.applicability}</td><td>{c.demand===null?"Unavailable":display(c.demand,si)} / {c.resistance===null?"Unavailable":display(c.resistance,si)}</td></tr>)}</tbody></table></div><h3>Missing qualification and source-limited checks</h3>{current.missing_sources.map(s=><p key={s}>{s}</p>)}<details><summary>Complete current native design/source trace</summary><pre>{JSON.stringify(current,null,2)}</pre></details><p>Design input: {design?.response.engineering_fingerprint}<br/>Result: {current.result_fingerprint}</p></section>}
    </ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
