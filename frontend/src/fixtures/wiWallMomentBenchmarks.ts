import type { WIWallMomentRequest, WallMomentAngle } from "../api/wiWallMomentContracts";

export function loadWIWallMomentBenchmark(system: "US_CUSTOMARY" | "SI"): WIWallMomentRequest {
  const si = system === "SI";
  const unit = si ? "mm" : "in";
  const q = (us: string, metric: string) => ({ value: si ? metric : us, unit });
  const angle = (gauge: string, metricGauge: string): WallMomentAngle => ({
    geometry: { length: q("8","203.2"), member_leg: q("4","101.6"), support_leg: q("4","101.6"), thickness: q("0.5","12.7"), inside_radius: q("0.25","6.35"), heel_end_reliefs: [q("0","0"),q("0","0")] },
    member_pattern: { across: 2, along: 2, gauge: q(gauge,metricGauge), pitch: q("1.5","38.1"), center: q("2","50.8") },
    support_pattern: { across: 2, along: 2, gauge: q(gauge,metricGauge), pitch: q("1.5","38.1"), center: q("2","50.8") },
    fastener: { bolt_diameter: q("0.5","12.7"), hole_diameter: q("0.563","14.3002"), source_authority_id: "ASTM_F593_17_GROUP_2_316_316L", thread_condition: "EXCLUDED", nominal_shear_stress: null },
    anchors: { nominal_diameter: q("0.5","12.7"), hole_diameter: q("0.563","14.3002"), specified_embedment: q("4","101.6"), washer_outside_diameter: q("1.25","31.75"), washer_thickness: q("0.125","3.175") },
    connector_source_reference: "", attachment_source_reference: "", material_id: "ICE_LOCKED_PULTRUDED_FRP", provider_id: "FRP",
  });
  return {
    contract: "4.2-RC1", request_id: `stage-4.2-${system.toLowerCase()}`, unit_system: system, source_length_unit: unit,
    beam: { profile_family: "WIDE_FLANGE_I", depth: q("10","254"), flange_width: q("8","203.2"), web_thickness: q("0.5","12.7"), flange_thickness: q("0.5","12.7"), display_length_each_side: q("16","406.4") }, gap: q("0.5","12.7"),
    wall: { width: q("48","1219.2"), height: q("48","1219.2"), thickness: q("8","203.2"), connection_origin_h: q("0","0"), connection_origin_v: q("0","0") },
    top: angle("5","127"), bottom: angle("5","127"), positive_web: angle("3","76.2"), negative_web: angle("3","76.2"),
    actions: { axial: { value: si ? "88.96443230521" : "20", unit: si ? "kN" : "kip" }, major_shear: { value: si ? "-44.482216152605" : "-10", unit: si ? "kN" : "kip" }, structural_major_moment: { value: si ? "11298.48290276167" : "100", unit: si ? "kN-mm" : "kip-in" } },
  };
}
