import type { MultiRowQuantity } from "../api/multirowContracts";
import type { AngleBasePreview } from "../api/angleColumnMomentBaseContracts";
import type { WallMomentVector } from "../api/wiWallMomentContracts";
import { buildRegionEmbeddedMaterialAxisPresentation } from "./materialAxisPresentation";
import { calculatePresentationBounds, type SceneArrow, type SceneBox, type SceneCylinder, type SceneMaterialAxes, type SingleBoltSceneModel, type Vec3 } from "./sceneModel";

// Drawing only: backend XYZ already is the right-handed global viewer frame.
// No beam L/V/T remapping, column-centroid formula, or load allocation here.
const inches=(q:MultiRowQuantity)=>Number(q.value)/(q.unit==="mm"?25.4:1);
const point=(p:WallMomentVector):Vec3=>({x:inches(p.x),y:inches(p.y),z:inches(p.z)});
const axis=(v:readonly [string,string,string]):Vec3=>({x:Number(v[0]),y:Number(v[1]),z:Number(v[2])});
const label=(v:string)=>v.replaceAll("_"," ");
const BASIS:readonly [Vec3,Vec3,Vec3]=[{x:1,y:0,z:0},{x:0,y:1,z:0},{x:0,y:0,z:1}];
export function buildAngleColumnMomentBaseScene(p:AngleBasePreview):SingleBoltSceneModel {
  const boxes:SceneBox[]=p.geometry.display_parts.map(v=>({id:v.part_id,label:label(v.part_id),ownerId:v.box.component_id,ownerLabel:label(v.box.component_id),ownerRole:v.box.component_id==="FOUNDATION"?"OTHER":v.box.component_id==="ANGLE_COLUMN"?"COLUMN":"BRACE",elementId:v.part_id,materialRegionId:v.material_region?.region_id??null,
    center:{x:inches(v.box.center_l_v_t.l),y:inches(v.box.center_l_v_t.v),z:inches(v.box.center_l_v_t.t)},size:{x:inches(v.box.size_l_v_t.l),y:inches(v.box.size_l_v_t.v),z:inches(v.box.size_l_v_t.t)},basis:BASIS,deferred:false,interference:false}));
  const cylinders:SceneCylinder[]=p.geometry.member_bolts.flatMap(b=>{
    const e=p.geometry.member_hardware_envelopes.find(v=>v.bolt_id===b.hardware_id);
    if(e===undefined)throw new Error("Backend member hardware is incomplete.");
    const common={ownerBoltId:b.hardware_id,penetratedLayerIds:b.layers,interfaceId:b.group_id,rowId:null,boltLineId:null,hardwareLocation:null};
    return [
      {...common,id:b.hardware_id,label:label(b.hardware_id),start:point(e.shank_start),end:point(e.shank_end),diameter:inches(b.diameter),kind:"BOLT",hardwareConfiguration:"THROUGH_BOLT",exactHardware:{source:e.source,headStart:point(e.head_start),headEnd:point(e.head_end),headAcrossFlats:inches(e.head_across_flats),nutStart:point(e.nut_start),nutEnd:point(e.nut_end),nutAcrossFlats:inches(e.nut_across_flats)}},
      {...common,id:`${b.hardware_id}:HOLE`,label:"Physical two-leaf hole",start:point(b.start),end:point(b.end),diameter:inches(b.hole_diameter),kind:"HOLE"},
      {...common,id:`${b.hardware_id}:HEAD_WASHER`,label:"Actual head washer",start:point(e.head_washer_start),end:point(e.head_washer_end),diameter:inches(e.washer_diameter),kind:"WASHER",hardwareLocation:"UNDER_HEAD"},
      {...common,id:`${b.hardware_id}:NUT_WASHER`,label:"Actual nut washer",start:point(e.nut_washer_start),end:point(e.nut_washer_end),diameter:inches(e.washer_diameter),kind:"WASHER",hardwareLocation:"UNDER_NUT"},
    ];
  });
  for(const b of p.geometry.foundation_attachments){
    const common={ownerBoltId:b.hardware_id,penetratedLayerIds:b.layers,interfaceId:b.group_id,rowId:null,boltLineId:null,hardwareLocation:null,start:point(b.start),end:point(b.end)};
    cylinders.push({...common,id:b.hardware_id,label:"External foundation anchor — schematic nut, no capacity",diameter:inches(b.diameter),kind:"BOLT",hardwareConfiguration:"EXTERIOR_NUT_WASHER_ANCHOR"},{...common,id:`${b.hardware_id}:HOLE`,label:"Foundation attachment hole path",diameter:inches(b.hole_diameter),kind:"HOLE"});
    const washer=p.geometry.foundation_washers.find(w=>w.hardware_id===`${b.hardware_id}:WASHER`);
    if(washer===undefined)throw new Error("Backend foundation washer is incomplete.");
    cylinders.push({...common,id:washer.hardware_id,label:"Specified exterior foundation washer",start:point(washer.start),end:point(washer.end),diameter:inches(washer.diameter),kind:"WASHER",hardwareLocation:"UNDER_HEAD"});
  }
  const materialAxes:SceneMaterialAxes[]=p.geometry.display_parts.flatMap(v=>{
    const r=v.material_region;
    if(r===null)return [];
    const source={componentId:r.component_id,elementId:r.region_id,materialRegionId:r.region_id,lengthwise:axis(r.lw_axis),crosswise:axis(r.cw_axis),throughThickness:axis(r.tt_axis)};
    const presentation=buildRegionEmbeddedMaterialAxisPresentation(source,boxes,[]);
    return [{id:`${v.part_id}:MATERIAL`,...source,componentLabel:label(r.component_id),sectionFamily:"ANGLE",elementLabel:label(r.region_id),origin:presentation?.origin??{x:inches(v.box.center_l_v_t.l),y:inches(v.box.center_l_v_t.v),z:inches(v.box.center_l_v_t.t)},presentation}];
  });
  const origin=point(p.column_on_base.reference);
  const axes:readonly (readonly ["FX"|"FY"|"FZ"|"MX"|"MY",MultiRowQuantity,Vec3])[]=[
    ["FX",p.input.actions.shear_x,BASIS[0]],["FY",p.input.actions.shear_y,BASIS[1]],["FZ",p.input.actions.axial,BASIS[2]],["MX",p.input.actions.moment_x,BASIS[0]],["MY",p.input.actions.moment_y,BASIS[1]],
  ];
  const appliedArrows:SceneArrow[]=axes.flatMap(([component,q,direction])=>{
    const n=Number(q.value);
    if(n===0)return [];
    const sign=Math.sign(n);
    return [{id:`BASE_${component}`,component,kind:component.startsWith("M")?"ROTATIONAL":"LINEAR",origin,axis:{x:direction.x*sign,y:direction.y*sign,z:direction.z*sign},signedValue:n,unit:q.unit,sense:n<0?"NEGATIVE":"POSITIVE",isZero:false,referencePointId:"COLUMN_END_CENTROID",frameId:"BASE_XYZ",axialLoadingSense:component==="FZ"?(n<0?"COMPRESSION":"TENSION"):null}];
  });
  const corners=(v:SceneBox)=>[-1,1].flatMap(x=>[-1,1].flatMap(y=>[-1,1].map(z=>({x:v.center.x+x*v.size.x/2,y:v.center.y+y*v.size.y/2,z:v.center.z+z*v.size.z/2}))));
  const bounds=calculatePresentationBounds(boxes.flatMap(corners));
  const fit=calculatePresentationBounds(boxes.filter(b=>b.ownerId!=="FOUNDATION").flatMap(corners));
  return {snapshotVersion:"4.4-RC1",unitSystem:"US_CUSTOMARY",lengthUnit:"in",boxes,meshes:[],cylinders,materialAxes,
    frames:[{id:"BASE_XYZ",label:"Base X/Y/Z — leg-parallel, not principal axes",kind:"JOINT_LOCAL",ownerId:null,origin:{x:0,y:0,z:0},xAxis:BASIS[0],yAxis:BASIS[1],zAxis:BASIS[2],valid:true},...p.geometry.angles.map(a=>({id:`${a.connector_id}:ABC`,label:`${label(a.connector_id)} A/B/C`,kind:"MEMBER_LOCAL" as const,ownerId:a.connector_id,origin:point(a.heel),xAxis:axis(a.frame.a),yAxis:axis(a.frame.b),zAxis:axis(a.frame.c),valid:true}))],
    markers:[{id:"COLUMN_END_CENTROID",label:"Actual column lower-end centroid — action reference",kind:"REFERENCE_POINT",position:origin,connected:true,memberEnd:"START"},{id:"FOUNDATION_ORIGIN",label:"Foundation report O — required total, not anchors",kind:"REFERENCE_POINT",position:{x:0,y:0,z:0},connected:null,memberEnd:null},...p.geometry.angles.flatMap(a=>[{id:`${a.connector_id}:HEEL`,label:"Connector heel",kind:"REFERENCE_POINT",position:point(a.heel),connected:null,memberEnd:null},{id:`${a.connector_id}:MEMBER`,label:"Physical member-group reference",kind:"REFERENCE_POINT",position:point(a.member_reference_global),connected:null,memberEnd:null},{id:`${a.connector_id}:FOOT`,label:"Net foundation-group reference — anchor breakdown unavailable",kind:"REFERENCE_POINT",position:point(a.support_reference_global),connected:null,memberEnd:null}])],
    positiveArrows:axes.map(([component,,direction])=>({id:`POSITIVE_${component}`,component,kind:component.startsWith("M")?"ROTATIONAL":"LINEAR",origin,axis:direction,signedValue:null,unit:null,sense:"POSITIVE",isZero:false,referencePointId:"COLUMN_END_CENTROID",frameId:"BASE_XYZ",axialLoadingSense:null})),appliedArrows,connectionDemandArrows:[],perBoltDemandArrows:[],zones:[],connectionOrientation:null,boundsCenter:bounds.center,boundsRadius:bounds.radius,fitCenter:fit.center,fitRadius:fit.radius*1.08};
}
