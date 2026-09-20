import type { ChannelMomentSpliceRequest } from "../api/channelMomentSpliceContracts";

export function loadChannelMomentSpliceBenchmark(system: "US_CUSTOMARY" | "SI"): ChannelMomentSpliceRequest {
  const si = system === "SI";
  const length = si ? "mm" : "in";
  const force = si ? "kN" : "kip";
  const moment = si ? "kN-mm" : "kip-in";
  const q = (us: string, metric: string) => ({ value: si ? metric : us, unit: length });
  const f = (us: string, metric: string) => ({ value: si ? metric : us, unit: force });
  const m = (us: string, metric: string) => ({ value: si ? metric : us, unit: moment });
  const pendingFastener = {
    bolt_diameter: q("0.5", "12.7"),
    hole_diameter: q("0.563", "14.3002"),
    source_authority_id: "ASTM_F593_17_GROUP_2_316_316L",
    thread_condition: "EXCLUDED" as const,
    nominal_shear_stress: null,
  };
  return {
    orchestration_contract_version: "4.1B-RC1",
    request_id: `stage-4.1b-${system.toLowerCase()}`,
    unit_system: system,
    source_length_unit: length,
    beams_locked_identical: true,
    beams_same_orientation: true,
    opening_direction: "+T_CH",
    beam: {
      profile_family: "CHANNEL",
      depth: q("8", "203.2"),
      flange_width: q("4", "101.6"),
      web_thickness: q("0.5", "12.7"),
      flange_thickness: q("0.5", "12.7"),
      display_length_each_side: q("18", "457.2"),
      equal_flange: true,
      lipped: false,
      back_to_back: false,
    },
    beam_end_gap: q("0.5", "12.7"),
    web_splice_plate: { length: q("16", "406.4"), height: q("5.5", "139.7"), thickness: q("0.5", "12.7"), count: 2, locked_identical: true },
    web_bolt_group: { rows: 2, bolts_per_row: 2, vertical_pitch: q("3", "76.2"), longitudinal_gauge: q("3", "76.2"), centroid_offset: q("4", "101.6"), locked_identical_mirror: true },
    web_fastener: structuredClone(pendingFastener),
    flange_geometry: {
      plate_length: q("16", "406.4"),
      plate_thickness: q("0.5", "12.7"),
      inner_plate_width: q("3", "76.2"),
      transverse_gauge: q("1.5", "38.1"),
      bolts_per_transverse_line: 2,
      longitudinal_pitch: q("3", "76.2"),
      group_centroid_distance: q("4", "101.6"),
      outer_plate_count_per_flange: 1,
      inner_plate_count_per_flange: 1,
      locked_top_bottom_identical: true,
    },
    flange_fastener: structuredClone(pendingFastener),
    actions: { axial_force_l: f("20", "88.96443230521"), major_shear_v: f("-10", "-44.482216152605"), major_moment_t: m("100", "11298.48290276167") },
    shear_center: {
      method: "RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1",
      explicit_coordinate_t: null,
      explicit_provenance: null,
      include_rational_comparison: false,
    },
  };
}
