import { viewerUnity } from "./unityRatio";
import { ConnectorBodyMaterialControl, ConnectorBodyMaterialResult } from "./connectorBodyMaterial";
import { useConnectorBodyMaterial } from "./useConnectorBodyMaterial";
import { useEffect, useMemo, useRef, useState } from "react";
import type { MultiRowQuantity } from "../api/multirowContracts";
import { designWIFrpSupportMoment } from "../api/wiFrpSupportMomentClient";
import { supportFaces, type FRPMomentAngle, type SupportMode, type WIFrpSupportMomentDesign, type WIFrpSupportMomentRequest, type WIFrpSupportMomentResponse } from "../api/wiFrpSupportMomentContracts";
import type { WallMomentVector, WallMomentWrench } from "../api/wiWallMomentContracts";
import { loadWIFrpSupportMomentPreset } from "../fixtures/wiFrpSupportMomentBenchmarks";
import type { SceneSelection } from "../visualization/EngineeringScene";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import { buildWIFrpSupportMomentScene } from "../visualization/wiFrpSupportMomentSceneModel";
import { ConnectionWorkspaceMain, ConnectionWorkspaceShell, ConnectionWorkspaceSidebar, PersistentConnectionViewer, SidebarGroup } from "./ConnectionWorkspaceShell";
import { formatDisplayQuantity, friendlyEnum } from "./presentation";
import { isIntentionalAbort } from "./previewWorkflow";
import { frpSupportMomentVisibleFailures } from "./wiFrpSupportMomentFailures";
import { useWIFrpSupportMomentPreview } from "./wiFrpSupportMomentWorkflow";
import "./wiFrpSupportMomentWorkspace.css";

const modeLabels: Readonly<Record<SupportMode,string>>={WI_FLANGE:"W/I flange",WI_WEB:"W/I web",HOLLOW_SQUARE:"Hollow square",SOLID_SQUARE:"Solid square",CHANNEL_WEB:"Channel web"};
function finiteInputs(value: unknown): boolean {
  if(value!==null&&typeof value==="object") {
    if("value" in value) return typeof value.value==="string"&&value.value.trim()!==""&&Number.isFinite(Number(value.value));
    return Object.values(value).every(finiteInputs);
  }
  return true;
}
function clearQualifications(next: WIFrpSupportMomentRequest) {
  next.response_source_reference="";next.local_zone_source_reference="";
  for(const key of ["top","bottom","positive_web","negative_web"] as const) {next[key].connector_source_reference="";next[key].attachment_source_reference="";}
}
function display(q:MultiRowQuantity,si:boolean):string {
  const factors:Readonly<Record<string,number>>={"N-mm":1,"kN-mm":1000,"kip-in":112984.8290276167};
  const factor=factors[q.unit];
  if(factor===undefined) return formatDisplayQuantity(q,si?"SI":"US_CUSTOMARY");
  return `${Number((Number(q.value)*factor/(si?1000:112984.8290276167)).toPrecision(7)).toString()} ${si?"kN-mm":"kip-in"}`;
}
function Wrench({title,value,si}:{readonly title:string;readonly value:WallMomentWrench;readonly si:boolean}) {
  const text=(v:WallMomentVector)=>[v.x,v.y,v.z].map(q=>display(q,si)).join(" · ");
  return <dl className="diagnostic-list"><div><dt>{title} — reference</dt><dd>{text(value.reference)}</dd></div><div><dt>Signed force components</dt><dd>{text(value.force)}</dd></div><div><dt>Signed moment components</dt><dd>{text(value.moment)}</dd></div></dl>;
}

export function WIFrpSupportMomentWorkspace() {
  const [request,setRequest]=useState(()=>loadWIFrpSupportMomentPreset("WI_FLANGE","US_CUSTOMARY"));
  const [revision,setRevision]=useState(0);
  const [immediate,setImmediate]=useState(true);
  const [design,setDesign]=useState<WIFrpSupportMomentResponse<WIFrpSupportMomentDesign>|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState<string|null>(null);
  const [selection,setSelection]=useState<SceneSelection>({kind:"MEMBER",id:"FRP_SUPPORT"});
  const sequence=useRef(0),abort=useRef<AbortController|null>(null);
  useEffect(()=>()=>{sequence.current+=1;abort.current?.abort();},[]);
  const update=(change:(next:WIFrpSupportMomentRequest)=>void,geometry=false)=>{
    sequence.current+=1;abort.current?.abort();setBusy(false);
    setRequest(old=>{const next=structuredClone(old);change(next);if(geometry)clearQualifications(next);return next;});
    setRevision(r=>r+1);setImmediate(false);
  };
  const si=request.beam.depth.unit==="mm";
  const load=(system:"US_CUSTOMARY"|"SI")=>{update(next=>Object.assign(next,loadWIFrpSupportMomentPreset(next.support.mode,system)));setImmediate(true);setDesign(null);setError(null);};
  const invalid=finiteInputs(request)?null:"Enter finite decimal values before previewing.";
  const preview=useWIFrpSupportMomentPreview(request,revision,immediate,invalid);
  const result=preview.response?.result??null;
  const model=useMemo(()=>result===null?null:buildWIFrpSupportMomentScene(result),[result]);
  const stale=design!==null&&(!preview.current||design.engineering_fingerprint!==preview.response?.engineering_fingerprint);
  const current=stale?null:design?.result??null;
  const failures=current===null?[]:frpSupportMomentVisibleFailures(current);
  const bodyMaterial = useConnectorBodyMaterial("wi-beam-frp-support-moment", request, revision, () => {
    sequence.current += 1; abort.current?.abort(); setBusy(false); setDesign(null); setError(null);
  });
  const run=async()=>{
    if (bodyMaterial.material === "SS316") { await bodyMaterial.run(); return; }
    const serial=++sequence.current;abort.current?.abort();const controller=new AbortController();abort.current=controller;
    setBusy(true);setError(null);
    try {const next=await designWIFrpSupportMoment(request,controller.signal);if(serial===sequence.current)setDesign(next);}
    catch(caught){if(serial===sequence.current&&!isIntentionalAbort(caught))setError(caught instanceof Error?caught.message:"Design request failed.");}
    finally{if(serial===sequence.current)setBusy(false);}
  };
  const field=(title:string,quantity:MultiRowQuantity,change:(next:WIFrpSupportMomentRequest,raw:string)=>void,geometry=true)=><label className="field-control"><span>{title}</span><span className="input-with-unit"><input aria-label={title} inputMode="decimal" value={quantity.value} onChange={e=>{const raw=e.currentTarget.value;update(next=>{change(next,raw);},geometry);}}/><small>{quantity.unit}</small></span></label>;
  const family=(key:"top"|"positive_web",title:string)=>{
    const partner=key==="top"?"bottom":"negative_web";
    const angle=request[key];
    const set=(change:(next:FRPMomentAngle)=>void,geometry=true)=>{update(next=>{change(next[key]);next[partner]=structuredClone(next[key]);},geometry);};
    const length=(label:string,quantity:MultiRowQuantity,change:(next:FRPMomentAngle,raw:string)=>void)=><label className="field-control"><span>{label}</span><span className="input-with-unit"><input aria-label={`${title} ${label}`} inputMode="decimal" value={quantity.value} onChange={e=>{const raw=e.currentTarget.value;set(next=>{change(next,raw);});}}/><small>{quantity.unit}</small></span></label>;
    const hardware=(key:"member_hardware"|"support_hardware",prefix:string)=><details className="frp43-full"><summary>{prefix} washer / head / nut geometry</summary><div className="field-grid">{(["washer_diameter","washer_thickness","head_across_flats","head_height","nut_across_flats","nut_height","end_extension"] as const).map(k=><span key={k}>{length(`${prefix} ${friendlyEnum(k)}`,angle[key][k],(next,v)=>{next[key][k].value=v;})}</span>)}</div><p className="sidebar-note">Explicit known geometry only. This is not bolt strength or response authority.</p></details>;
    const bolts=(support:boolean)=>{
      const pattern=support?"support_pattern":"member_pattern",fastener=support?"support_fastener":"fastener",name=support?"Support bolts":"Member bolts";
      return <fieldset className="frp43-input-group"><legend>{name}</legend><div className="field-grid">
        {(["across","along"] as const).map(k=><label className="field-control" key={k}><span>{friendlyEnum(k)} count</span><input aria-label={`${title} ${name} ${k} count`} type="number" min="1" step="1" value={angle[pattern][k]} onChange={e=>{const n=Number(e.currentTarget.value);set(next=>{next[pattern][k]=n;});}}/></label>)}
        {(["gauge","pitch","center"] as const).map(k=><span key={k}>{length(`${name} ${k==="center"?"centroid distance":k}`,angle[pattern][k],(next,v)=>{next[pattern][k].value=v;})}</span>)}
        {(["bolt_diameter","hole_diameter"] as const).map(k=><span key={k}>{length(`${name} ${friendlyEnum(k)}`,angle[fastener][k],(next,v)=>{next[fastener][k].value=v;})}</span>)}
        <label className="field-control frp43-full"><span>Thread condition</span><select aria-label={`${title} ${name} thread condition`} value={angle[fastener].thread_condition} onChange={e=>{const v=e.currentTarget.value as "INCLUDED"|"EXCLUDED";set(next=>{next[fastener].thread_condition=v;});}}><option value="EXCLUDED">Threads excluded</option><option value="INCLUDED">Threads included</option></select></label>
        <label className="field-control frp43-full"><span>{name} strength source / condition reference</span><input aria-label={`${title} ${name} strength source`} value={angle[fastener].source_authority_id} onChange={e=>{const v=e.currentTarget.value;set(next=>{next[fastener].source_authority_id=v;});}}/></label>
        {hardware(support?"support_hardware":"member_hardware",name)}
      </div></fieldset>;
    };
    return <SidebarGroup title={title} summary="Locked physical pair" defaultOpen><div className="field-grid">{(["length","member_leg","support_leg","thickness","inside_radius"] as const).map(k=><span key={k}>{length(friendlyEnum(k),angle.geometry[k],(next,v)=>{next.geometry[k].value=v;})}</span>)}</div>{bolts(false)}{bolts(true)}
      {(["connector_source_reference","attachment_source_reference"] as const).map(k=><label className="field-control frp43-source" key={k}><span>{k==="connector_source_reference"?"Qualified angle-body source":"Qualified member-attachment source"}</span><input aria-label={`${title} ${k==="connector_source_reference"?"angle-body source":"member-attachment source"}`} value={angle[k]} onChange={e=>{const v=e.currentTarget.value;set(next=>{next[k]=v;},false);}}/></label>)}
      <p className="sidebar-note">Connector material: locked ICE pultruded FRP. Pair geometry does not prove complete support response or receiving-wall sharing.</p></SidebarGroup>;
  };
  return <ConnectionWorkspaceShell className="wi-frp-support-moment-workspace" banner={<section className="workspace-banner"><div><p className="eyebrow">Stage 4.3 · RC1</p><h2>W/I Beam to FRP Support Moment Connection</h2><p>Four FRP angles · Actual support through-bolts · Qualified response remains explicit</p></div><div className="benchmark-actions"><button onClick={()=>{load("US_CUSTOMARY");}}>Load 4.3 U.S.</button><button onClick={()=>{load("SI");}}>Load 4.3 SI</button></div></section>}>
    <ConnectionWorkspaceSidebar ariaLabel="W/I FRP-support moment engineering properties">
      <ConnectorBodyMaterialControl material={bodyMaterial.material} onChange={bodyMaterial.choose} />
      <SidebarGroup title="Receiving support" summary={modeLabels[request.support.mode]} defaultOpen>
        <label className="field-control"><span>Support configuration</span><select aria-label="Support configuration" value={request.support.mode} onChange={e=>{const mode=e.currentTarget.value as SupportMode;update(next=>{next.support=loadWIFrpSupportMomentPreset(mode,si?"SI":"US_CUSTOMARY").support;},true);}}>{Object.entries(modeLabels).map(([key,label])=><option value={key} key={key}>{label}</option>)}</select></label>
        <label className="field-control"><span>Selected physical face</span><select aria-label="Selected physical face" value={request.support.face} onChange={e=>{const v=e.currentTarget.value;update(next=>{next.support.face=v;},true);}}>{supportFaces[request.support.mode].map(face=><option key={face} value={face}>{friendlyEnum(face)}</option>)}</select></label>
        <div className="field-grid">{(["depth","width","web_or_wall_thickness","flange_thickness","physical_length","connection_height","connection_transverse","view_length"] as const).map(k=><span key={k}>{field(`Support ${friendlyEnum(k)}`,request.support[k],(next,v)=>{next.support[k].value=v;},k!=="view_length")}</span>)}</div>
        <p className="sidebar-note">Physical member ends and connection location define engineering distances. View length only clips the drawing. Square depth and width must be equal; invalid values are not auto-corrected.</p>
        <p className="sidebar-note">Receiving material: locked ICE FRP; LW follows this vertical member. Whole-column/foundation analysis is not performed.</p>
      </SidebarGroup>
      <SidebarGroup title="Incoming W/I beam" summary="Physical member / display" defaultOpen><div className="field-grid">{(["depth","flange_width","web_thickness","flange_thickness","display_length_each_side"] as const).map(k=><span key={k}>{field(k==="display_length_each_side"?"Beam view length":`Beam ${friendlyEnum(k)}`,request.beam[k],(next,v)=>{next.beam[k].value=v;},k!=="display_length_each_side")}</span>)}{field("Beam physical length",request.beam_physical_length,(next,v)=>{next.beam_physical_length.value=v;})}{field("Beam-support gap",request.gap,(next,v)=>{next.gap.value=v;})}</div><p className="sidebar-note">Beam material: locked ICE FRP, independent of connector/support assignment. Gap must be positive and no greater than 0.5 in / 12.7 mm.</p></SidebarGroup>
      <SidebarGroup title="Joint actions" summary="Signed P / V / structural M" defaultOpen><div className="field-grid">{field("Axial force P_L",request.actions.axial,(next,v)=>{next.actions.axial.value=v;},false)}{field("Major shear V_V",request.actions.major_shear,(next,v)=>{next.actions.major_shear.value=v;},false)}{field("Structural major moment M_T",request.actions.structural_major_moment,(next,v)=>{next.actions.structural_major_moment.value=v;},false)}</div><p className="sidebar-note">At the negative beam end, physical right-hand moment = − structural moment. Complete local moments remain. No minor shear, minor moment or user torsion.</p></SidebarGroup>
      {family("top","Flange angles")}{family("positive_web","Web clip angles")}
      <SidebarGroup title="Support qualification" summary="Server-controlled sources" defaultOpen>{(["response_source_reference","local_zone_source_reference"] as const).map(k=><label className="field-control frp43-source" key={k}><span>{k==="response_source_reference"?"Complete support-response source":"Local support-zone capacity / interaction source"}</span><input aria-label={k==="response_source_reference"?"Complete support-response source":"Local support-zone capacity source"} value={request[k]} onChange={e=>{const v=e.currentTarget.value;update(next=>{next[k]=v;});}}/></label>)}<p className="sidebar-note">A typed reference is not qualification. No synthetic test source is available in production. Load/geometry changes require a matching source domain.</p></SidebarGroup>
      <SidebarGroup title="Model / design status" summary={current?.status??(stale?"Stale":"Not checked")} defaultOpen><p role="status">{preview.state}</p><p>Connection scope: {current?.status??(stale?"Stale — Run Design Check":"Not checked")}</p><p>Native governing: {current===null?"Not current":current.native_governing_check_ids.join(", ")||"No native group selected; inspect failures."}</p><p>Overall receiving-member analysis remains external.</p><button className="primary-button" disabled={bodyMaterial.busy || busy||!preview.current||preview.response?.design_check_ready!==true} onClick={()=>{void run();}}>{busy?"Running design check…":"Run Design Check"}</button></SidebarGroup>
    </ConnectionWorkspaceSidebar>
    <ConnectionWorkspaceMain><ConnectorBodyMaterialResult state={bodyMaterial} /><PersistentConnectionViewer unity={viewerUnity("wi-frp-support-moment", current, { stale, checking: busy, error, invalid: invalid !== null, previewCurrent: preview.current })}>{model===null?<p>No valid canonical model yet.</p>:<VisualizationPanel model={model} title="W/I beam to FRP support moment connection" selection={selection} onSelect={setSelection} contactSelectionLabel="Selected FRP support contact face" actionSourceLabel="Beam-end structural action" appliedActionInputValues={{FX:request.actions.axial.value,FY:"0",FZ:request.actions.major_shear.value,MX:"0",MY:request.actions.structural_major_moment.value,MZ:"0"}} onAppliedActionValueChange={(component,v)=>{if(component==="FX"||component==="FZ"||component==="MY")update(next=>{next.actions[component==="FX"?"axial":component==="FZ"?"major_shear":"structural_major_moment"].value=v;});}}/>}</PersistentConnectionViewer>
      {preview.error===null?null:<div className="error-banner" role="alert">{preview.error}<button onClick={preview.retry}>Retry preview</button></div>}{error===null?null:<div role="alert">{error}</div>}{stale?<div className="stale-banner" role="status">Design results are stale. Run Design Check explicitly for current inputs.</div>:null}
      {result===null?null:<details className="source-card"><summary>Source availability — preview only, no resistance</summary><table><thead><tr><th>Required source scope</th><th>Reference</th><th>Server availability</th></tr></thead><tbody>{result.source_availability.map(([scope,reference,status])=><tr key={scope}><td>{friendlyEnum(scope)}</td><td>{reference}</td><td>{status}</td></tr>)}</tbody></table><p>Registration alone is not qualification. Exact assembly, load, contact and coverage checks run only on Run Design Check.</p></details>}
      {result===null?null:<section className="tee-results-grid" aria-label="Stage 4.3 engineering trace"><article className="source-card"><h3>Connection contribution at support centroid</h3>{result.support_contribution===null?null:<Wrench title="Connection on support — L/V/T" value={result.support_contribution} si={si}/>}<details><summary>Equal-and-opposite reaction / exact proofs</summary>{result.support_reaction===null?null:<Wrench title="Support on connection — L/V/T" value={result.support_reaction} si={si}/>}<pre>{JSON.stringify(result.equilibrium,null,2)}</pre></details><p>Native equilibrium proofs: {result.equilibrium?.proof_passed?"Passed":"Unavailable"}</p><p>Actual centroid authority: {result.geometry.support.centroid_authority}</p><p>These are connection contributions, not solved column-end or foundation reactions.</p><details><summary>Slice 5 complete region resultants</summary><pre>{JSON.stringify(result.slice5,null,2)}</pre></details><details><summary>Physical support paths / hardware / material axes</summary><pre>{JSON.stringify(result.geometry,null,2)}</pre></details></article>
        {result.connectors.map((c,i)=><article className="source-card" key={c.connector_id}><h3>{friendlyEnum(c.connector_id)}</h3><Wrench title="Support group — u/v/n, not per-bolt force" value={c.support_uvn} si={si}/><p>In-plane scope: {c.support_in_plane_scope}</p><p>Normal/contact response: {current?.support_response?.status??"Source availability not checked"}</p><p>Angle-body source: {current?.connector_results[i]?.status??"Not checked"}</p><p>Member-attachment source: {current?.attachment_results[i]?.check.status??"Not checked"}</p><details><summary>Complete member → heel → support demand trace</summary><Wrench title="Member — A/B/C" value={c.core.request.member_action} si={si}/><Wrench title="Heel — A/B/C" value={c.core.heel} si={si}/><pre>{JSON.stringify(c,null,2)}</pre></details></article>)}
        <article className="qualification-banner"><div><h3>Engineering review and qualification required</h3><p>{result.disclaimer}</p><p>{result.beam_allocation_applicability}</p><p>Current engineering fingerprint: {result.engineering_fingerprint}</p></div></article></section>}
      {current===null?null:<section aria-label="Stage 4.3 design-check trace"><h3>Connection-scope completeness</h3><p>{current.status_reason}</p><table><thead><tr><th>Scope</th><th>Backend status</th></tr></thead><tbody>{current.scope_statuses.map(([scope,status])=><tr key={scope}><td>{friendlyEnum(scope)}</td><td>{status}</td></tr>)}</tbody></table>
        <h3>Required evaluated failures</h3><p>The backend selects governing checks. Subordinate failures remain visible.</p>{failures.length===0?<p>No evaluated failures returned for this design.</p>:<div className="frp43-table"><table><thead><tr><th>Check / region</th><th>Native reason</th><th>Demand / resistance</th><th>Utilization</th></tr></thead><tbody>{failures.map((c,i)=><tr key={`${c.checkId}:${String(i)}`}><td>{c.checkId}<br/>{friendlyEnum(c.component)}</td><td>FAIL · {c.reason}<details><summary>Exact native record</summary><pre>{JSON.stringify(c.nativeRecord,null,2)}</pre></details></td><td>{c.demand===null?"Unavailable":display(c.demand,si)} / {c.resistance===null?"See trace":display(c.resistance,si)}</td><td>{c.utilization===null?"See trace":Number(c.utilization).toPrecision(6)}</td></tr>)}</tbody></table></div>}
        <h3>Support bolt / local FRP checks</h3><p>Unavailable normal tension is not zero. Hollow-wall participation and solid effective thickness are never inferred.</p><details><summary>Actual per-bolt response, contact and loaded sections</summary><pre>{JSON.stringify({response:current.support_response,bolts:current.support_bolts},null,2)}</pre></details><details><summary>Receiving layers, angle support legs and joint-zone checks</summary><pre>{JSON.stringify({local:current.support_local_checks,zone:current.local_zone},null,2)}</pre></details>
        <h3>Missing sources and limitations</h3>{current.missing_sources.map(s=><p key={s}>{s}</p>)}<p>Design input: {design?.engineering_fingerprint}<br/>Design result: {design?.result_fingerprint}</p><details><summary>Complete native calculation / source / applicability trace</summary><pre>{JSON.stringify(current,null,2)}</pre></details>
      </section>}
    </ConnectionWorkspaceMain>
  </ConnectionWorkspaceShell>;
}
