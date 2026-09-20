import type { MultiRowQuantity } from "../api/multirowContracts";
import type {
  TeeConnectedMemberProfileRequest,
  TeeProfileFamily,
  TeeProfileSurface,
} from "../api/teeContracts";

interface ProfileDimensionControl {
  readonly key: string;
  readonly label: string;
}

interface TeeProfileDefinition {
  readonly label: string;
  readonly enabledForDirectTee: boolean;
  readonly dimensions: readonly ProfileDimensionControl[];
  readonly surfaces: readonly TeeProfileSurface[];
}

export const TEE_PROFILE_DEFINITIONS: Readonly<Record<TeeProfileFamily, TeeProfileDefinition>> = {
  ANGLE: {
    label: "Angle",
    enabledForDirectTee: true,
    dimensions: [
      { key: "leg_y", label: "Leg Y" },
      { key: "leg_z", label: "Leg Z" },
      { key: "thickness", label: "Thickness" },
      { key: "member_length", label: "Member / view length" },
    ],
    surfaces: ["LEG_Y_OUTER", "LEG_Z_OUTER"],
  },
  CHANNEL: {
    label: "Channel",
    enabledForDirectTee: true,
    dimensions: [
      { key: "depth", label: "Depth" },
      { key: "flange_width", label: "Flange width" },
      { key: "web_thickness", label: "Web thickness" },
      { key: "flange_thickness", label: "Flange thickness" },
      { key: "member_length", label: "Member / view length" },
    ],
    surfaces: ["WEB_OUTER", "FLANGE_POS_OUTER", "FLANGE_NEG_OUTER"],
  },
  WIDE_FLANGE_I: {
    label: "Wide-flange / I",
    enabledForDirectTee: true,
    dimensions: [
      { key: "depth", label: "Depth" },
      { key: "flange_width", label: "Flange width" },
      { key: "web_thickness", label: "Web thickness" },
      { key: "flange_thickness", label: "Flange thickness" },
      { key: "member_length", label: "Member / view length" },
    ],
    surfaces: ["WEB_POS_FACE", "WEB_NEG_FACE", "FLANGE_POS_OUTER", "FLANGE_NEG_OUTER"],
  },
  RECTANGULAR_HOLLOW_SECTION: {
    label: "Rectangular tube",
    enabledForDirectTee: true,
    dimensions: [
      { key: "depth", label: "Depth" },
      { key: "width", label: "Width" },
      { key: "wall_thickness", label: "Wall thickness" },
      { key: "member_length", label: "Member / view length" },
    ],
    surfaces: ["Y_POS_FACE", "Y_NEG_FACE", "Z_POS_FACE", "Z_NEG_FACE"],
  },
  SOLID_RECTANGULAR_SECTION: {
    label: "Solid Rectangular Section",
    enabledForDirectTee: true,
    dimensions: [
      { key: "depth", label: "Depth" },
      { key: "width", label: "Width" },
      { key: "member_length", label: "Member / view length" },
    ],
    surfaces: ["Z_POS_FACE", "Z_NEG_FACE", "Y_POS_FACE", "Y_NEG_FACE"],
  },
  FLAT_PLATE: {
    label: "Flat plate",
    enabledForDirectTee: true,
    dimensions: [
      { key: "width", label: "Width" },
      { key: "thickness", label: "Thickness" },
      { key: "member_length", label: "Member / view length" },
    ],
    surfaces: ["FACE_POS", "FACE_NEG"],
  },
  ROUND_HOLLOW_SECTION: {
    label: "Round tube — unavailable for direct Tee contact",
    enabledForDirectTee: false,
    dimensions: [
      { key: "outer_diameter", label: "Outer diameter" },
      { key: "wall_thickness", label: "Wall thickness" },
      { key: "member_length", label: "Member / view length" },
    ],
    surfaces: [],
  },
};

export const TEE_PROFILE_FAMILIES = Object.keys(TEE_PROFILE_DEFINITIONS) as TeeProfileFamily[];

export const PROFILE_SURFACE_LABELS: Readonly<Record<TeeProfileSurface, string>> = {
  LEG_Y_OUTER: "Leg Y outer face",
  LEG_Z_OUTER: "Leg Z outer face",
  WEB_OUTER: "Web outer face",
  WEB_POS_FACE: "Web positive face",
  WEB_NEG_FACE: "Web negative face",
  FLANGE_POS_OUTER: "Positive flange outer face",
  FLANGE_NEG_OUTER: "Negative flange outer face",
  Y_POS_FACE: "Positive Y face",
  Y_NEG_FACE: "Negative Y face",
  Z_POS_FACE: "Positive Z face",
  Z_NEG_FACE: "Negative Z face",
  FACE_POS: "Positive plate face",
  FACE_NEG: "Negative plate face",
};

function quantity(value: string, unit: "in" | "mm"): MultiRowQuantity {
  return { value, unit };
}

function values(
  unit: "in" | "mm",
  customary: Readonly<Record<string, string>>,
  metric: Readonly<Record<string, string>>,
): Record<string, MultiRowQuantity> & { member_length: MultiRowQuantity } {
  const selected = unit === "in" ? customary : metric;
  return Object.fromEntries(
    Object.entries(selected).map(([key, value]) => [key, quantity(value, unit)]),
  ) as Record<string, MultiRowQuantity> & { member_length: MultiRowQuantity };
}

export function initialConnectedMemberProfile(
  unit: "in" | "mm",
  family: TeeProfileFamily = "ANGLE",
): TeeConnectedMemberProfileRequest {
  const dimensions = (() => {
    if (family === "ANGLE") {
      return values(
        unit,
        { member_length: "8", leg_y: "4", leg_z: "3", thickness: "0.5" },
        { member_length: "203.2", leg_y: "101.6", leg_z: "76.2", thickness: "12.7" },
      );
    }
    if (family === "CHANNEL") {
      return values(
        unit,
        { member_length: "8", depth: "6", flange_width: "3", web_thickness: "0.5", flange_thickness: "0.5" },
        { member_length: "203.2", depth: "152.4", flange_width: "76.2", web_thickness: "12.7", flange_thickness: "12.7" },
      );
    }
    if (family === "WIDE_FLANGE_I") {
      return values(
        unit,
        { member_length: "8", depth: "8", flange_width: "8", web_thickness: "0.5", flange_thickness: "0.5" },
        { member_length: "203.2", depth: "203.2", flange_width: "203.2", web_thickness: "12.7", flange_thickness: "12.7" },
      );
    }
    if (family === "RECTANGULAR_HOLLOW_SECTION") {
      return values(
        unit,
        { member_length: "8", depth: "6", width: "4", wall_thickness: "0.5" },
        { member_length: "203.2", depth: "152.4", width: "101.6", wall_thickness: "12.7" },
      );
    }
    if (family === "SOLID_RECTANGULAR_SECTION") {
      return values(
        unit,
        { member_length: "8", depth: "6", width: "8" },
        { member_length: "203.2", depth: "152.4", width: "203.2" },
      );
    }
    if (family === "FLAT_PLATE") {
      return values(
        unit,
        { member_length: "8", width: "4", thickness: "0.5" },
        { member_length: "203.2", width: "101.6", thickness: "12.7" },
      );
    }
    return values(
      unit,
      { member_length: "8", outer_diameter: "4", wall_thickness: "0.25" },
      { member_length: "203.2", outer_diameter: "101.6", wall_thickness: "6.35" },
    );
  })();
  const definition = TEE_PROFILE_DEFINITIONS[family];
  const selectedSurface = definition.surfaces[0];
  if (selectedSurface === undefined) {
    throw new Error("Round hollow sections have no authorized direct Tee-stem surface.");
  }
  return {
    profile_id: "tee-connected-brace-profile",
    role: "BRACE",
    profile_family: family,
    size_basis: "CUSTOM_DIMENSIONS",
    dimensions,
    profile_orientation: "ROTATION_0",
    selected_profile_surface: selectedSurface,
    material_kind: "PULTRUDED_FRP",
  };
}
