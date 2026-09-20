import type { MultiRowQuantity } from "../api/multirowContracts";
import type { WIFrpSupportMomentPreview } from "../api/wiFrpSupportMomentContracts";
import type { WallMomentVector } from "../api/wiWallMomentContracts";
import { buildRegionEmbeddedMaterialAxisPresentation } from "./materialAxisPresentation";
import { calculatePresentationBounds, type SceneArrow, type SceneBox, type SceneCylinder, type SceneMaterialAxes, type SingleBoltSceneModel, type Vec3 } from "./sceneModel";

// Drawing-unit conversion only. Every point, solid extent and direction comes
// from the backend; no connector placement or engineering wrench is computed.
// Proper rigid basis change: (L,V,T) -> (X,Z,-Y). Its determinant is +1,
// preserving handedness of the material bases and physical moment arrows.
const inches = (q: MultiRowQuantity) => Number(q.value) / (q.unit === "mm" ? 25.4 : 1);
const point = (p: WallMomentVector): Vec3 => ({ x: inches(p.x), y: -inches(p.z), z: inches(p.y) });
const direction = (p: readonly [string,string,string]): Vec3 => ({ x: Number(p[0]),y: -Number(p[2]),z: Number(p[1]) });
const label = (value: string) => value.replaceAll("_"," ");

export function buildWIFrpSupportMomentScene(value: WIFrpSupportMomentPreview): SingleBoltSceneModel {
  const actions = value.input.actions;
  const boxes: SceneBox[] = value.geometry.display_parts.map(p => ({ id: p.part_id, label: label(p.part_id), ownerId: p.box.component_id, ownerLabel: label(p.box.component_id), ownerRole: p.box.role === "SUPPORT" ? "COLUMN" : "BRACE", elementId: p.part_id, materialRegionId: p.material_region?.region_id ?? null,
    center: { x: inches(p.box.center_l_v_t.l), y: -inches(p.box.center_l_v_t.t), z: inches(p.box.center_l_v_t.v) }, size: { x: inches(p.box.size_l_v_t.l), y: inches(p.box.size_l_v_t.t), z: inches(p.box.size_l_v_t.v) }, basis: [{x:1,y:0,z:0},{x:0,y:1,z:0},{x:0,y:0,z:1}], deferred: false, interference: false }));
  const cylinders: SceneCylinder[] = [...value.geometry.member_bolts,...value.geometry.support_bolts.map(b => b.hardware)].flatMap(b => {
    const e = value.geometry.hardware_envelopes.find(e => e.bolt_id === b.hardware_id);
    if (e === undefined) throw new Error("Backend physical hardware envelope is missing.");
    const common = { ownerBoltId:b.hardware_id,penetratedLayerIds:b.layers,interfaceId:b.group_id,rowId:null,boltLineId:null,hardwareLocation:null };
    return [
      {...common,id:b.hardware_id,label:label(b.hardware_id),start:point(e.shank_start),end:point(e.shank_end),diameter:inches(b.diameter),kind:"BOLT",hardwareConfiguration:"THROUGH_BOLT",
        exactHardware:{source:e.source,headStart:point(e.head_start),headEnd:point(e.head_end),headAcrossFlats:inches(e.head_across_flats),nutStart:point(e.nut_start),nutEnd:point(e.nut_end),nutAcrossFlats:inches(e.nut_across_flats)}},
      {...common,id:`${b.hardware_id}:HOLE`,label:`${label(b.hardware_id)} hole path`,start:point(b.start),end:point(b.end),diameter:inches(b.hole_diameter),kind:"HOLE"},
      {...common,id:`${b.hardware_id}:HEAD_WASHER`,label:"Exterior head washer",start:point(e.head_washer_start),end:point(e.head_washer_end),diameter:inches(e.washer_diameter),kind:"WASHER",hardwareLocation:"UNDER_HEAD"},
      {...common,id:`${b.hardware_id}:NUT_WASHER`,label:"Exterior nut washer",start:point(e.nut_washer_start),end:point(e.nut_washer_end),diameter:inches(e.washer_diameter),kind:"WASHER",hardwareLocation:"UNDER_NUT"},
    ];
  });
  const materialAxes: SceneMaterialAxes[] = value.geometry.display_parts.flatMap(p => {
    const r = p.material_region;
    if (r === null) return [];
    const source = { componentId: r.component_id, elementId: r.region_id, materialRegionId: r.region_id, lengthwise: direction(r.lw_axis), crosswise: direction(r.cw_axis), throughThickness: direction(r.tt_axis) };
    const presentation = buildRegionEmbeddedMaterialAxisPresentation(source,boxes,[]);
    const center = { x: inches(p.box.center_l_v_t.l), y: -inches(p.box.center_l_v_t.t), z: inches(p.box.center_l_v_t.v) };
    return [{ id: `${p.part_id}:MATERIAL`, ...source, componentLabel: label(r.component_id), sectionFamily: r.component_id === "WI_BEAM" ? "WIDE_FLANGE" : r.component_id === "FRP_SUPPORT" ? ({WI_FLANGE:"WIDE_FLANGE",WI_WEB:"WIDE_FLANGE",CHANNEL_WEB:"CHANNEL",HOLLOW_SQUARE:"RECTANGULAR_TUBE",SOLID_SQUARE:"PLATE"} as const)[value.input.support.mode] : "ANGLE", elementLabel: label(r.region_id), origin: presentation?.origin ?? center, presentation }];
  });
  const origin = point(value.joint_right_hand_action.reference);
  const arrow = (component: "FX" | "FZ" | "MY", q: MultiRowQuantity, physical: Vec3): SceneArrow | null => {
    const raw = Number(q.value);
    if (raw === 0) return null;
    return { id: `WI_FRP_SUPPORT_${component}`, component, kind: component === "MY" ? "ROTATIONAL" : "LINEAR", origin, axis: physical, signedValue: raw, unit: q.unit, sense: raw < 0 ? "NEGATIVE" : "POSITIVE", isZero: false, referencePointId: "BEAM_END_ACTION", frameId: "WI_FRP_SUPPORT_FRAME", axialLoadingSense: component === "FX" ? raw < 0 ? "COMPRESSION" : "TENSION" : null };
  };
  const signedAxis = (q: MultiRowQuantity, axis: Vec3): Vec3 => { const sign = Math.sign(Number(q.value)); return { x: axis.x*sign,y: axis.y*sign,z: axis.z*sign }; };
  const native = value.joint_right_hand_action;
  const appliedArrows = [arrow("FX",actions.axial,signedAxis(native.force.x,{x:1,y:0,z:0})),arrow("FZ",actions.major_shear,signedAxis(native.force.y,{x:0,y:0,z:1})),arrow("MY",actions.structural_major_moment,signedAxis(native.moment.z,{x:0,y:-1,z:0}))].filter((a): a is SceneArrow => a !== null);
  const corners = boxes.flatMap(b => [-1,1].flatMap(x => [-1,1].flatMap(y => [-1,1].map(z => ({x:b.center.x+x*b.size.x/2,y:b.center.y+y*b.size.y/2,z:b.center.z+z*b.size.z/2})))));
  const bounds = calculatePresentationBounds(corners);
  const connection = calculatePresentationBounds(boxes.filter(b => b.ownerId !== "FRP_SUPPORT").flatMap(b => [{x:b.center.x-b.size.x/2,y:b.center.y-b.size.y/2,z:b.center.z-b.size.z/2},{x:b.center.x+b.size.x/2,y:b.center.y+b.size.y/2,z:b.center.z+b.size.z/2}]));
  return { snapshotVersion: "4.3-RC1", unitSystem: "US_CUSTOMARY", lengthUnit: "in", boxes, meshes: [], cylinders, materialAxes,
    frames: [{ id: "WI_FRP_SUPPORT_FRAME", label: "L / V / T — structural positive moment is -T", kind: "JOINT_LOCAL", ownerId: null, origin, xAxis: {x:1,y:0,z:0},yAxis:{x:0,y:0,z:1},zAxis:{x:0,y:-1,z:0},valid:true }],
    markers: [{ id: "BEAM_END_ACTION", label: "Beam-end action reference", kind: "REFERENCE_POINT", position: origin, connected: true, memberEnd: "START" },{id:"SUPPORT_CENTROID_REFERENCE",label:"Actual receiving-member centroid/reference",kind:"REFERENCE_POINT",position:point(value.geometry.support.centroid),connected:null,memberEnd:null},...value.geometry.angles.flatMap(a => [{id:`${a.connector_id}:HEEL`,label:`${label(a.connector_id)} heel`,kind:"REFERENCE_POINT",position:point(a.heel),connected:null,memberEnd:null},{id:`${a.connector_id}:MEMBER`,label:`${label(a.connector_id)} member interface`,kind:"REFERENCE_POINT",position:point(a.member_reference_global),connected:null,memberEnd:null},{id:`${a.connector_id}:SUPPORT`,label:`${label(a.connector_id)} support bolt group`,kind:"REFERENCE_POINT",position:point(a.support_reference_global),connected:null,memberEnd:null}])],
    positiveArrows: ([ ["FX",{x:1,y:0,z:0}], ["FZ",{x:0,y:0,z:1}], ["MY",{x:0,y:1,z:0}] ] as const).map(([component,axis]) => ({id:`POSITIVE_${component}`,component,axis,origin,kind:component === "MY" ? "ROTATIONAL" : "LINEAR",signedValue:null,unit:null,sense:"POSITIVE",isZero:false,referencePointId:"BEAM_END_ACTION",frameId:"WI_FRP_SUPPORT_FRAME",axialLoadingSense:null})), appliedArrows, connectionDemandArrows: [], perBoltDemandArrows: [], zones: value.geometry.support_contact_patches.map(p => ({id:p.patch_id,label:p.face_id,side:"SUPPORT",participantId:"FRP_SUPPORT",interfaceId:p.group_id,patchId:p.patch_id,normal:{x:1,y:0,z:0},selectedContact:true,corners:p.corners.map(point)})), connectionOrientation: null,
    boundsCenter: bounds.center, boundsRadius: bounds.radius, fitCenter: connection.center, fitRadius: connection.radius*1.08 };
}
