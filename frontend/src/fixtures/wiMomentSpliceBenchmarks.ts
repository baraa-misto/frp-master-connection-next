import type { WIMomentSpliceRequest } from "../api/wiMomentSpliceContracts";

export function loadWIMomentSpliceBenchmark(system: "US_CUSTOMARY" | "SI"): WIMomentSpliceRequest {
  const si = system === "SI";
  const length = si ? "mm" : "in";
  const force = si ? "kN" : "kip";
  const moment = si ? "kN-mm" : "kip-in";
  const q = (us: string, metric: string) => ({ value: si ? metric : us, unit: length });
  const f = (us: string, metric: string) => ({ value: si ? metric : us, unit: force });
  const m = (us: string, metric: string) => ({ value: si ? metric : us, unit: moment });
  const pendingFastener = {
    bolt_diameter: q("0.5", "12.7"), hole_diameter: q("0.563", "14.3002"),
    source_authority_id: "ASTM_F593_17_GROUP_2_316_316L", thread_condition: "EXCLUDED" as const,
    nominal_shear_stress: null,
  };
  return {
    orchestration_contract_version: "4.1A-RC1", request_id: `stage-4.1a-${system.toLowerCase()}`,
    unit_system: system, source_length_unit: length, profile_family: "WIDE_FLANGE_I", beams_locked_identical: true,
    beam: { profile_family: "WIDE_FLANGE_I", depth: q("10", "254"), flange_width: q("8", "203.2"), web_thickness: q("0.5", "12.7"), flange_thickness: q("0.5", "12.7"), display_length_each_side: q("18", "457.2") },
    beam_end_gap: q("0.5", "12.7"),
    web_splice_plate: { length: q("16", "406.4"), height: q("8", "203.2"), thickness: q("0.5", "12.7"), count: 2, locked_identical: true },
    web_bolt_group: { rows: 2, bolts_per_row: 2, vertical_pitch: q("3", "76.2"), longitudinal_gauge: q("3", "76.2"), centroid_offset: q("4", "101.6"), locked_identical_mirror: true },
    web_fastener: structuredClone(pendingFastener),
    flange_geometry: { plate_length: q("16", "406.4"), plate_thickness: q("0.5", "12.7"), inner_strip_width: q("3", "76.2"), bolts_per_line: 2, longitudinal_pitch: q("3", "76.2"), group_centroid_distance: q("4", "101.6"), outer_plate_count_per_flange: 1, inner_strip_count_per_flange: 2, locked_top_bottom_identical: true, locked_inner_symmetric: true },
    flange_fastener: structuredClone(pendingFastener),
    actions: { axial_force_l: f("20", "88.96443230521"), major_shear_v: f("-10", "-44.482216152605"), major_moment_t: m("100", "11298.48290276167") },
  };
}
