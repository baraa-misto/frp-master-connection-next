import type {
  BeamConcretePairedAngleR2Request,
  BeamConcretePairedAngleRequest,
  HistoricalBeamConcretePairedAngleRequest,
} from "../api/beamConcretePairedAngleContracts";
import type { PairedProfileFamily } from "../api/pairedClipAngleContracts";
import type { TeeProfileOrientation, TeeProfileSurface } from "../api/teeContracts";
import { PAIRED_SURFACES } from "../workspace/pairedClipAngleOptions";

function scaled(value: string, system: "US_CUSTOMARY" | "SI"): string {
  if (system === "US_CUSTOMARY") return value;
  return (Number(value) * 25.4).toFixed(10).replace(/\.?0+$/u, "");
}

type BeamProfile = BeamConcretePairedAngleRequest["beam_profile"];

export const BEAM_CONCRETE_PROFILE_FAMILIES: readonly PairedProfileFamily[] = [
  "FLAT_PLATE",
  "ANGLE",
  "CHANNEL",
  "WIDE_FLANGE_I",
  "RECTANGULAR_HOLLOW_SECTION",
  "SOLID_RECTANGULAR_SECTION",
];

export function beamConcreteConnectedProfile(
  system: "US_CUSTOMARY" | "SI",
  family: PairedProfileFamily,
): BeamProfile {
  const unit = system === "US_CUSTOMARY" ? "in" : "mm";
  const length = (value: string) => ({ value: scaled(value, system), unit });
  const dimensions = (() => {
    if (family === "FLAT_PLATE") return { member_length: length("16"), width: length("6"), thickness: length("0.5") };
    if (family === "ANGLE") return { member_length: length("16"), leg_y: length("6"), leg_z: length("6"), thickness: length("0.5") };
    if (family === "CHANNEL") return { member_length: length("16"), depth: length("8"), flange_width: length("4"), web_thickness: length("0.5"), flange_thickness: length("0.5") };
    if (family === "WIDE_FLANGE_I") return { member_length: length("16"), depth: length("10"), flange_width: length("8"), web_thickness: length("0.5"), flange_thickness: length("0.5") };
    if (family === "RECTANGULAR_HOLLOW_SECTION") return { member_length: length("16"), depth: length("6"), width: length("4"), wall_thickness: length("0.5") };
    return { member_length: length("16"), depth: length("6"), width: length("4") };
  })();
  const selectedSurface = PAIRED_SURFACES[family][0];
  if (selectedSurface === undefined) throw new Error("A beam-to-concrete connected profile requires an authorized paired surface.");
  return {
    profile_id: "beam-concrete-connected-beam-profile",
    role: "BEAM",
    profile_family: family,
    size_basis: "CUSTOM_DIMENSIONS",
    dimensions,
    profile_orientation: "ROTATION_0" satisfies TeeProfileOrientation,
    selected_profile_surface: selectedSurface satisfies TeeProfileSurface,
  };
}

function request(
  system: "US_CUSTOMARY" | "SI",
  contract: "3.5A-RC1" | "3.5A-R1-RC1",
): HistoricalBeamConcretePairedAngleRequest {
  const lengthUnit = system === "US_CUSTOMARY" ? "in" : "mm";
  const forceUnit = system === "US_CUSTOMARY" ? "kip" : "kN";
  const momentUnit = system === "US_CUSTOMARY" ? "kip-in" : "kN-mm";
  const length = (value: string) => ({ value: scaled(value, system), unit: lengthUnit });
  const reaction = system === "US_CUSTOMARY" ? "-4" : "-17.792886461042";
  const historical = contract === "3.5A-RC1";
  return {
    orchestration_contract_version: contract,
    request_id: `${historical ? "STAGE-3.5A" : "STAGE-3.5A-R1"}-G1-${system}`,
    unit_system: system,
    source_length_unit: lengthUnit,
    wall: {
      width: length("48"), height: length("48"), thickness: length("8"),
      connection_origin_h: length("0"), connection_origin_v: length("0"),
    },
    beam_profile: beamConcreteConnectedProfile(system, "WIDE_FLANGE_I"),
    beam_end_gap: length("0.5"),
    connector_dimensions: {
      connected_leg_width: length("4"), support_leg_width: length("4"),
      thickness: length("0.5"), connector_length: length("8"),
    },
    connector_length_anchor_position: length("0"),
    common_beam_layout: {
      row_count: 2, bolts_per_row: 2, pitch: length("2"), gauge: length("2"),
      heel_edge_distance: length("1"), free_edge_distance: length("1"),
      negative_end_distance: length("3"), positive_end_distance: length("3"),
      placement_mode: "EDGE_DISTANCE_CONTROLLED", length_offset: null, width_offset: null,
    },
    wall_anchor_pattern: {
      row_count: historical ? 2 : 1,
      anchors_per_row: historical ? 2 : 1,
      pitch: length("2"), gauge: length("2"),
      centroid_offset_h: length("3"), centroid_v: length("0"),
    },
    common_bolt_diameter: length("0.5"),
    common_hole_diameter: length("0.563"),
    external_anchor: {
      nominal_diameter: length("0.5"), hole_diameter: length("0.563"),
      specified_embedment: length("4"), washer_outside_diameter: length("1.0625"),
      washer_thickness: length("0.109"),
      system_classification: "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR",
    },
    reaction_shear: { value: reaction, unit: forceUnit },
    user_force_hvn: { x: "0", y: reaction, z: "0", unit: forceUnit },
    user_moment_hvn: { x: "0", y: "0", z: "0", unit: momentUnit },
  };
}

/** Load the controlled Stage 3.5A-R2 successor default. */
export function loadBeamConcretePairedAngleBenchmark(
  system: "US_CUSTOMARY" | "SI",
): BeamConcretePairedAngleR2Request {
  const r1 = request(system, "3.5A-R1-RC1");
  const {
    reaction_shear: majorShear,
    user_force_hvn: historicalForce,
    user_moment_hvn: historicalMoment,
    ...base
  } = r1;
  void historicalForce;
  void historicalMoment;
  return {
    ...base,
    orchestration_contract_version: "3.5A-R2-RC1",
    request_id: `STAGE-3.5A-R2-G1-${system}`,
    major_shear: majorShear,
    minor_shear: { value: "0", unit: majorShear.unit },
    axial_force: { value: "0", unit: majorShear.unit },
  };
}

/** Preserve the exact historical Stage 3.5A W/I + 2x2 request. */
export function loadHistoricalBeamConcretePairedAngleBenchmark(
  system: "US_CUSTOMARY" | "SI",
): BeamConcretePairedAngleRequest {
  return request(system, "3.5A-RC1");
}
