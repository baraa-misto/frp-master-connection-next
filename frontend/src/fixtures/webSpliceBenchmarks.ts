import type { WebSpliceRequest } from "../api/webSpliceContracts";

export function loadWebSpliceBenchmark(system: "US_CUSTOMARY" | "SI", contract: "3.6A-RC1" | "3.6B-RC2" = "3.6A-RC1"): WebSpliceRequest {
  const si = system === "SI";
  const length = si ? "mm" : "in";
  const force = si ? "kN" : "kip";
  const q = (us: string, metric: string) => ({ value: si ? metric : us, unit: length });
  const f = (us: string, metric: string) => ({ value: si ? metric : us, unit: force });
  return {
    orchestration_contract_version: contract,
    request_id: `${contract === "3.6B-RC2" ? "stage-3.6b" : "stage-3.6a"}-${system.toLowerCase()}`,
    unit_system: system,
    source_length_unit: length,
    beam: { profile_family: "WIDE_FLANGE_I", depth: q("10", "254"), flange_width: q("8", "203.2"), web_thickness: q("0.5", "12.7"), flange_thickness: q("0.5", "12.7"), display_length_each_side: q("18", "457.2") },
    beam_end_gap: q("0.5", "12.7"),
    splice_plate: { length: q("16", "406.4"), height: q("8", "203.2"), thickness: q("0.5", "12.7"), count: 2, locked_identical: true },
    bolt_group: { rows: 2, bolts_per_row: 2, vertical_pitch: q("3", "76.2"), longitudinal_gauge: q("3", "76.2"), centroid_offset: q("4", "101.6"), locked_identical_mirror: true },
    bolt_diameter: q("0.5", "12.7"), hole_diameter: q("0.563", "14.3002"),
    transfer_force: { axial_force: f("0", "0"), major_shear: f("-10", "-44.482216152605"), minor_shear: f("0", "0") },
    user_moment_l_v_t: { x: "0", y: "0", z: "0", unit: si ? "kN-mm" : "kip-in" },
    flange_splice_enabled: false,
  };
}
