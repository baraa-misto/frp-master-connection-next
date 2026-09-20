import type { MultiRowQuantity } from "./multirowContracts";
import type {
  TeeProfileFamily,
  TeeProfileOrientation,
  TeeProfileSurface,
} from "./teeContracts";

export type SharedSupportTargetId =
  | "W_COLUMN_FLANGE"
  | "W_BEAM_FLANGE"
  | "W_COLUMN_WEB"
  | "CHANNEL_COLUMN_WEB"
  | "ANGLE_COLUMN_LEG"
  | "RECTANGULAR_HOLLOW_COLUMN_WALL"
  | "SOLID_RECTANGULAR_COLUMN_FACE";

export interface SharedSupportProfileRequest {
  profile_id: string;
  role: "COLUMN" | "BEAM";
  profile_family: Exclude<TeeProfileFamily, "FLAT_PLATE" | "ROUND_HOLLOW_SECTION">;
  profile_orientation: TeeProfileOrientation;
  selected_profile_surface: TeeProfileSurface;
  member_length: MultiRowQuantity;
  depth?: MultiRowQuantity;
  flange_width?: MultiRowQuantity;
  web_thickness?: MultiRowQuantity;
  flange_thickness?: MultiRowQuantity;
  leg_y?: MultiRowQuantity;
  leg_z?: MultiRowQuantity;
  thickness?: MultiRowQuantity;
  width?: MultiRowQuantity;
  wall_thickness?: MultiRowQuantity;
}

export const SHARED_SUPPORT_OPTIONS: readonly {
  readonly id: SharedSupportTargetId;
  readonly label: string;
}[] = [
  { id: "W_COLUMN_FLANGE", label: "W Column Flange" },
  { id: "W_BEAM_FLANGE", label: "W Beam Flange" },
  { id: "W_COLUMN_WEB", label: "W Column Web" },
  { id: "CHANNEL_COLUMN_WEB", label: "Channel Column Web" },
  { id: "ANGLE_COLUMN_LEG", label: "Angle Column Leg" },
  { id: "RECTANGULAR_HOLLOW_COLUMN_WALL", label: "Rectangular Hollow Column Wall" },
  { id: "SOLID_RECTANGULAR_COLUMN_FACE", label: "Solid Rectangular Column Face" },
];

function quantity(value: string, unit: "in" | "mm"): MultiRowQuantity {
  return { value, unit };
}

function value(unit: "in" | "mm", customary: string, metric: string): MultiRowQuantity {
  return quantity(unit === "in" ? customary : metric, unit);
}

export function initialSharedSupport(
  target: SharedSupportTargetId,
  unit: "in" | "mm",
  memberId: string,
): SharedSupportProfileRequest {
  const common = {
    profile_id: `${memberId}-profile`,
    role: target === "W_BEAM_FLANGE" ? ("BEAM" as const) : ("COLUMN" as const),
    profile_orientation: "ROTATION_0" as const,
    member_length: value(unit, "12", "304.8"),
  };
  if (target === "W_COLUMN_FLANGE" || target === "W_BEAM_FLANGE" || target === "W_COLUMN_WEB") {
    return {
      ...common,
      profile_family: "WIDE_FLANGE_I",
      depth: value(unit, "8", "203.2"),
      flange_width: value(unit, "8", "203.2"),
      web_thickness: value(unit, "0.5", "12.7"),
      flange_thickness: value(unit, "0.5", "12.7"),
      selected_profile_surface: target === "W_COLUMN_WEB" ? "WEB_POS_FACE" : "FLANGE_POS_OUTER",
    };
  }
  if (target === "CHANNEL_COLUMN_WEB") {
    return {
      ...common,
      profile_family: "CHANNEL",
      depth: value(unit, "8", "203.2"),
      flange_width: value(unit, "4", "101.6"),
      web_thickness: value(unit, "0.5", "12.7"),
      flange_thickness: value(unit, "0.5", "12.7"),
      selected_profile_surface: "WEB_OUTER",
    };
  }
  if (target === "ANGLE_COLUMN_LEG") {
    return {
      ...common,
      profile_family: "ANGLE",
      leg_y: value(unit, "8", "203.2"),
      leg_z: value(unit, "8", "203.2"),
      thickness: value(unit, "0.5", "12.7"),
      selected_profile_surface: "LEG_Y_OUTER",
    };
  }
  if (target === "RECTANGULAR_HOLLOW_COLUMN_WALL") {
    return {
      ...common,
      profile_family: "RECTANGULAR_HOLLOW_SECTION",
      width: value(unit, "8", "203.2"),
      depth: value(unit, "6", "152.4"),
      wall_thickness: value(unit, "0.5", "12.7"),
      selected_profile_surface: "Z_POS_FACE",
    };
  }
  return {
    ...common,
    profile_family: "SOLID_RECTANGULAR_SECTION",
    width: value(unit, "8", "203.2"),
    depth: value(unit, "6", "152.4"),
    selected_profile_surface: "Z_POS_FACE",
  };
}

export function sharedSupportLabel(target: SharedSupportTargetId): string {
  return SHARED_SUPPORT_OPTIONS.find((item) => item.id === target)?.label ?? target;
}
