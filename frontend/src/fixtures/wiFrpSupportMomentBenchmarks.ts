import type { FRPMomentAngle, SupportMode, WIFrpSupportMomentRequest } from "../api/wiFrpSupportMomentContracts";
import { supportFaces } from "../api/wiFrpSupportMomentContracts";

/** Declared dimensional presets only. No frontend centroid, wrench or strength calculation. */
export function loadWIFrpSupportMomentPreset(mode: SupportMode, system: "US_CUSTOMARY" | "SI"): WIFrpSupportMomentRequest {
  const si = system === "SI";
  const unit = si ? "mm" : "in";
  const q = (us: string, metric: string) => ({value:si ? metric : us,unit});
  const hardware = () => ({washer_diameter:q("1.25","31.75"),washer_thickness:q(".125","3.175"),head_across_flats:q(".75","19.05"),head_height:q(".3125","7.9375"),nut_across_flats:q(".75","19.05"),nut_height:q(".4375","11.1125"),end_extension:q(".125","3.175"),geometry_source:"STAGE_4_3_EXPLICIT_PRESET_GEOMETRY_NOT_STRENGTH_AUTHORITY"});
  const fastener = () => ({bolt_diameter:q(".5","12.7"),hole_diameter:q(".563","14.3002"),source_authority_id:"ASTM_F593_17_GROUP_2_316_316L",thread_condition:"EXCLUDED" as const});
  const angle = (g: string, metric: string): FRPMomentAngle => ({
    geometry:{length:q("8","203.2"),member_leg:q("4","101.6"),support_leg:q("4","101.6"),thickness:q(".5","12.7"),inside_radius:q(".25","6.35"),heel_end_reliefs:[q("0","0"),q("0","0")]},
    member_pattern:{across:2,along:2,gauge:q(g,metric),pitch:q("1.5","38.1"),center:q("2","50.8")},support_pattern:{across:2,along:2,gauge:q(g,metric),pitch:q("1.5","38.1"),center:q("2","50.8")},
    fastener:fastener(),support_fastener:fastener(),member_hardware:hardware(),support_hardware:hardware(),
    connector_source_reference:"",attachment_source_reference:"",material_id:"ICE_LOCKED_PULTRUDED_FRP",provider_id:"FRP",
  });
  const dimensions = {
    WI_FLANGE:["16","406.4","12","304.8"], WI_WEB:["16","406.4","8","203.2"],CHANNEL_WEB:["16","406.4","6","152.4"],
    HOLLOW_SQUARE:["12","304.8","12","304.8"],SOLID_SQUARE:["12","304.8","12","304.8"],
  } as const;
  const [d,dm,w,wm]=dimensions[mode];
  return {contract:"4.3-RC1",request_id:`stage-4.3-${mode}-${system}`,
    beam:{profile_family:"WIDE_FLANGE_I",depth:q("10","254"),flange_width:q("8","203.2"),web_thickness:q(".5","12.7"),flange_thickness:q(".5","12.7"),display_length_each_side:q("16","406.4")},
    beam_physical_length:q("16","406.4"),gap:q(".5","12.7"),
    support:{mode,face:supportFaces[mode][0],depth:q(d,dm),width:q(w,wm),web_or_wall_thickness:q(".5","12.7"),flange_thickness:q(".5","12.7"),physical_length:q("48","1219.2"),connection_height:q("0","0"),connection_transverse:q("0","0"),view_length:q("36","914.4"),material_id:"ICE_LOCKED_PULTRUDED_FRP"},
    top:angle("5","127"),bottom:angle("5","127"),positive_web:angle("3","76.2"),negative_web:angle("3","76.2"),
    actions:{axial:{value:si?"88.96443230521":"20",unit:si?"kN":"kip"},major_shear:{value:si?"-44.482216152605":"-10",unit:si?"kN":"kip"},structural_major_moment:{value:si?"11298.48290276167":"100",unit:si?"kN-mm":"kip-in"}},
    response_source_reference:"",local_zone_source_reference:"",beam_material_id:"ICE_LOCKED_PULTRUDED_FRP"};
}
