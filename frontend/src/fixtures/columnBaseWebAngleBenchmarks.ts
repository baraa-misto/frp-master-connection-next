import type {
  ColumnBaseProfileFamily,
  ColumnBaseProfileTransport,
  ColumnBaseWebAngleRequest,
  ColumnBaseWebAngleSignedRequest,
} from "../api/columnBaseWebAngleContracts";

function scaled(value: string, system: "US_CUSTOMARY" | "SI"): string {
  if (system === "US_CUSTOMARY") return value;
  return (Number(value) * 25.4).toFixed(10).replace(/\.?0+$/u, "");
}

export function loadHistoricalColumnBaseWebAngleBenchmark(
  system: "US_CUSTOMARY" | "SI",
): ColumnBaseWebAngleSignedRequest {
  const lengthUnit = system === "US_CUSTOMARY" ? "in" : "mm";
  const forceUnit = system === "US_CUSTOMARY" ? "kip" : "kN";
  const length = (value: string) => ({ value: scaled(value, system), unit: lengthUnit });
  const force = (value: string) => ({
    value: system === "US_CUSTOMARY" ? value : (Number(value) * 4.4482216152605).toFixed(13).replace(/\.?0+$/u, ""),
    unit: forceUnit,
  });
  return {
    orchestration_contract_version: "3.5C-R2-RC1",
    request_id: `STAGE-3.5C-R2-G3-${system}`,
    unit_system: system,
    source_length_unit: lengthUnit,
    concrete: { s_dimension: length("36"), t_dimension: length("36"), depth: length("12") },
    column: {
      profile_family: "WIDE_FLANGE_I", depth_s: length("10"), flange_width_t: length("8"),
      web_thickness: length("0.5"), flange_thickness: length("0.5"), display_height: length("24"),
    },
    assembly: "SYMMETRIC_DOUBLE_BASE_ANGLES",
    single_side: "+T_C",
    angle: { connected_leg_width: length("6"), support_leg_width: length("6"), thickness: length("0.5"), connector_length: length("6") },
    web_group: { row_count: 2, bolts_per_row: 2, pitch: length("3"), gauge: length("2"), centroid_height_l: length("3") },
    anchor_pattern: { row_count: 2, anchors_per_row: 1, pitch: length("3"), gauge: length("0"), centroid_offset_t: length("3.25") },
    web_bolt_diameter: length("0.5"), web_hole_diameter: length("0.563"),
    external_anchor: {
      nominal_diameter: length("0.5"), hole_diameter: length("0.563"), specified_embedment: length("4"),
      washer_outside_diameter: length("1.0625"), washer_thickness: length("0.109"),
      system_classification: "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR",
    },
    signed_axial_force: force("-20"), web_plane_shear: force("4"), web_normal_shear: force("0"),
    action_reference_s_t_l: { x: "0", y: "0", z: scaled("4", system), unit: lengthUnit },
  };
}

function profile(
  system: "US_CUSTOMARY" | "SI",
  family: ColumnBaseProfileFamily,
): ColumnBaseProfileTransport {
  const lengthUnit = system === "US_CUSTOMARY" ? "in" : "mm";
  const length = (value: string) => ({ value: scaled(value, system), unit: lengthUnit });
  const common = {
    profile_id: "column-base-profile",
    role: "COLUMN" as const,
    size_basis: "CUSTOM_DIMENSIONS" as const,
    profile_orientation: "ROTATION_0" as const,
    material_kind: "PULTRUDED_FRP" as const,
  };
  if (family === "WIDE_FLANGE_I") return {
    ...common,
    profile_family: family,
    selected_profile_surface: "WEB_POS_FACE",
    dimensions: {
      member_length: length("24"), depth: length("10"), flange_width: length("8"),
      web_thickness: length("0.5"), flange_thickness: length("0.5"),
    },
  };
  if (family === "RECTANGULAR_HOLLOW_SECTION") return {
    ...common,
    profile_family: family,
    selected_profile_surface: "Y_POS_FACE",
    dimensions: {
      member_length: length("24"), depth: length("10"), width: length("8"),
      wall_thickness: length("0.5"),
    },
  };
  if (family === "SOLID_RECTANGULAR_SECTION") return {
    ...common,
    profile_family: family,
    selected_profile_surface: "Y_POS_FACE",
    dimensions: { member_length: length("24"), depth: length("10"), width: length("8") },
  };
  return {
    ...common,
    profile_family: "ANGLE",
    selected_profile_surface: "LEG_Y_OUTER",
    dimensions: {
      member_length: length("24"), leg_y: length("6"), leg_z: length("6"), thickness: length("0.5"),
    },
  };
}

export function loadColumnBaseWebAngleBenchmark(
  system: "US_CUSTOMARY" | "SI",
  family: ColumnBaseProfileFamily = "WIDE_FLANGE_I",
): ColumnBaseWebAngleRequest {
  const historical = loadHistoricalColumnBaseWebAngleBenchmark(system);
  const {
    column: _column,
    web_plane_shear,
    web_normal_shear,
    action_reference_s_t_l: _actionReference,
    ...shared
  } = historical;
  void _column;
  void _actionReference;
  const anchorOffset = family === "WIDE_FLANGE_I" ? "3.25" : family === "ANGLE" ? "3" : "7";
  return {
    ...shared,
    orchestration_contract_version: "3.7A-RC1",
    request_id: `STAGE-3.7A-${family}-${system}`,
    column_profile: profile(system, family),
    assembly: "DOUBLE_BASE_ANGLES",
    angle: {
      ...historical.angle,
      connector_length: {
        ...historical.angle.connector_length,
        value: scaled(family === "ANGLE" ? "5" : "6", system),
      },
    },
    anchor_pattern: {
      ...historical.anchor_pattern,
      centroid_offset_t: {
        ...historical.anchor_pattern.centroid_offset_t,
        value: scaled(anchorOffset, system),
      },
    },
    connection_plane_shear: web_plane_shear,
    connection_normal_shear: web_normal_shear,
    angle_double_topology: "SAME_SELECTED_LEG_OPPOSITE_FACES",
  };
}
