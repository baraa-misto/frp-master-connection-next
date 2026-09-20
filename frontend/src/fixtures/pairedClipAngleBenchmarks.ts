import type { PairedClipAngleRequest } from "../api/pairedClipAngleContracts";
import { loadClipAngleC2Benchmark, type ClipAngleBenchmarkUnitSystem } from "./clipAngleBenchmarks";

/** Load the controlled G1 symmetric paired-angle fixture without duplicating base geometry data. */
export function loadPairedClipAngleBenchmark(
  system: ClipAngleBenchmarkUnitSystem,
): PairedClipAngleRequest {
  const single = loadClipAngleC2Benchmark(system);
  const paired = structuredClone(single) as unknown as PairedClipAngleRequest;
  paired.orchestration_contract_version = "3.3C3-RC1";
  paired.request_id = `PAIRED-CLIP-ANGLE-WORKSPACE-${system}`;
  paired.pair_symmetry = "LOCKED_IDENTICAL_MIRROR";
  paired.common_member_layout = structuredClone(single.interface_a_layout);
  paired.mirrored_support_layout = structuredClone(single.interface_b_layout);
  paired.global_force.z = system === "US_CUSTOMARY" ? "4" : "17.792886461042";
  paired.global_reference_point.x = "0";
  paired.connected_member_profile.dimensions.thickness = structuredClone(single.bolt_diameter);
  paired.support_profile.flange_width = {
    value: system === "US_CUSTOMARY" ? "10" : "254",
    unit: single.source_length_unit,
  };
  delete (paired as unknown as Record<string, unknown>).hand;
  delete (paired as unknown as Record<string, unknown>).interface_a_layout;
  delete (paired as unknown as Record<string, unknown>).interface_b_layout;
  return paired;
}
