import type {
  DirectSideLapConcreteRequest,
  DirectSideLapProfileFamily,
} from "../api/directSideLapConcreteContracts";

function scaled(value: string, system: "US_CUSTOMARY" | "SI"): string {
  if (system === "US_CUSTOMARY") return value;
  return (Number(value) * 25.4).toFixed(10).replace(/\.?0+$/u, "");
}

function force(value: string, system: "US_CUSTOMARY" | "SI"): string {
  if (system === "US_CUSTOMARY") return value;
  return (Number(value) * 4.4482216152605).toFixed(13).replace(/\.?0+$/u, "");
}

export function directSideLapProfile(
  system: "US_CUSTOMARY" | "SI",
  family: DirectSideLapProfileFamily,
): DirectSideLapConcreteRequest["connected_profile"] {
  const unit = system === "US_CUSTOMARY" ? "in" : "mm";
  const length = (value: string) => ({ value: scaled(value, system), unit });
  return family === "CHANNEL"
    ? {
        profile_id: "direct-side-lap-connected-member-profile",
        role: "BRACE",
        profile_family: "CHANNEL",
        size_basis: "CUSTOM_DIMENSIONS",
        dimensions: {
          member_length: length("28"), depth: length("8"), flange_width: length("4"),
          web_thickness: length("0.5"), flange_thickness: length("0.5"),
        },
        profile_orientation: "ROTATION_0",
        selected_profile_surface: "WEB_OUTER",
      }
    : {
        profile_id: "direct-side-lap-connected-member-profile",
        role: "BRACE",
        profile_family: "ANGLE",
        size_basis: "CUSTOM_DIMENSIONS",
        dimensions: {
          member_length: length("28"), leg_y: length("6"), leg_z: length("6"),
          thickness: length("0.5"),
        },
        profile_orientation: "ROTATION_0",
        selected_profile_surface: "LEG_Y_OUTER",
      };
}

export function loadDirectSideLapConcreteBenchmark(
  system: "US_CUSTOMARY" | "SI",
): DirectSideLapConcreteRequest {
  const lengthUnit = system === "US_CUSTOMARY" ? "in" : "mm";
  const forceUnit = system === "US_CUSTOMARY" ? "kip" : "kN";
  const length = (value: string) => ({ value: scaled(value, system), unit: lengthUnit });
  const load = (value: string) => ({ value: force(value, system), unit: forceUnit });
  return {
    orchestration_contract_version: "3.5B-RC1",
    request_id: `STAGE-3.5B-G1-${system}`,
    unit_system: system,
    source_length_unit: lengthUnit,
    wall: { run_length: length("48"), transverse_width: length("48"), thickness: length("8") },
    side_lap_length: length("12"),
    member_projection_beyond_wall: length("16"),
    connected_profile: directSideLapProfile(system, "CHANNEL"),
    anchor_pattern: {
      row_count: 2, anchors_per_row: 1, pitch: length("4"), gauge: length("4"),
      centroid_distance_behind_free_end: length("6"), transverse_offset: length("0"),
    },
    external_anchor: {
      nominal_diameter: length("0.5"), hole_diameter: length("0.563"),
      specified_embedment: length("4"), washer_outside_diameter: length("1.0625"),
      washer_thickness: length("0.109"),
      system_classification: "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR",
    },
    axial_force: load("0"), major_shear: load("-4"), minor_shear: load("0"),
  };
}
