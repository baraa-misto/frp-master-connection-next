import type { PairedProfileFamily } from "../api/pairedClipAngleContracts";
import type { TeeProfileSurface } from "../api/teeContracts";

export const PAIRED_PROFILE_FAMILIES: readonly PairedProfileFamily[] = [
  "FLAT_PLATE",
  "WIDE_FLANGE_I",
  "CHANNEL",
  "ANGLE",
  "RECTANGULAR_HOLLOW_SECTION",
  "SOLID_RECTANGULAR_SECTION",
];

export const PAIRED_SURFACES: Readonly<
  Record<PairedProfileFamily, readonly TeeProfileSurface[]>
> = {
  FLAT_PLATE: ["FACE_POS", "FACE_NEG"],
  WIDE_FLANGE_I: ["WEB_POS_FACE", "WEB_NEG_FACE"],
  CHANNEL: ["WEB_OUTER"],
  ANGLE: ["LEG_Y_OUTER", "LEG_Z_OUTER"],
  RECTANGULAR_HOLLOW_SECTION: ["Y_POS_FACE", "Y_NEG_FACE", "Z_POS_FACE", "Z_NEG_FACE"],
  SOLID_RECTANGULAR_SECTION: ["Y_POS_FACE", "Y_NEG_FACE", "Z_POS_FACE", "Z_NEG_FACE"],
};
