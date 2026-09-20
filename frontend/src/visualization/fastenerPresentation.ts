import type { SceneCylinder, Vec3 } from "./sceneModel";

/**
 * Schematic presentation ratios authorized for Stage 2.4C-R3.
 *
 * These values are display-only. They are not standard-specific hardware dimensions
 * and must never enter backend geometry, engineering contracts, fingerprints,
 * interference checks, resistance calculations, or reports.
 */
export const SCHEMATIC_HEAD_ACROSS_FLATS_RATIO = 1.5;
export const SCHEMATIC_HEAD_HEIGHT_RATIO = 0.625;
export const SCHEMATIC_NUT_ACROSS_FLATS_RATIO = 1.5;
export const SCHEMATIC_NUT_THICKNESS_RATIO = 0.875;

export interface SchematicHardwareDimensions {
  readonly headAcrossFlats: number;
  readonly headHeight: number;
  readonly nutAcrossFlats: number;
  readonly nutThickness: number;
}

export interface SchematicHexHardware {
  readonly id: string;
  readonly kind: "HEAD" | "NUT";
  readonly ownerBoltId: string;
  readonly start: Vec3;
  readonly end: Vec3;
  readonly acrossFlats: number;
}

export interface FastenerPresentation {
  readonly id: string;
  readonly ownerBoltId: string;
  readonly shank: SceneCylinder;
  readonly washers: readonly SceneCylinder[];
  readonly head: SchematicHexHardware;
  readonly nut: SchematicHexHardware;
  readonly renderedHardware: readonly SchematicHexHardware[];
}

export function schematicHardwareDimensions(
  canonicalBoltDiameter: number,
): SchematicHardwareDimensions {
  return {
    headAcrossFlats: canonicalBoltDiameter * SCHEMATIC_HEAD_ACROSS_FLATS_RATIO,
    headHeight: canonicalBoltDiameter * SCHEMATIC_HEAD_HEIGHT_RATIO,
    nutAcrossFlats: canonicalBoltDiameter * SCHEMATIC_NUT_ACROSS_FLATS_RATIO,
    nutThickness: canonicalBoltDiameter * SCHEMATIC_NUT_THICKNESS_RATIO,
  };
}

function offset(point: Vec3, direction: Vec3, distance: number): Vec3 {
  return {
    x: point.x + direction.x * distance,
    y: point.y + direction.y * distance,
    z: point.z + direction.z * distance,
  };
}

function canonicalAxis(shank: SceneCylinder): Vec3 | null {
  const x = shank.end.x - shank.start.x;
  const y = shank.end.y - shank.start.y;
  const z = shank.end.z - shank.start.z;
  const length = Math.hypot(x, y, z);
  if (length === 0) return null;
  return { x: x / length, y: y / length, z: z / length };
}

export function buildFastenerPresentation(
  shank: SceneCylinder,
  washers: readonly SceneCylinder[],
): FastenerPresentation | null {
  const axis = canonicalAxis(shank);
  if (axis === null) return null;
  const dimensions = schematicHardwareDimensions(shank.diameter);
  const ownedWashers = washers.filter(
    (washer) => washer.kind === "WASHER" && washer.ownerBoltId === shank.ownerBoltId,
  );
  const underHead = ownedWashers.find((washer) => washer.hardwareLocation === "UNDER_HEAD");
  const underNut = ownedWashers.find((washer) => washer.hardwareLocation === "UNDER_NUT");

  // Backend washer snapshots run from the outer head face to the stack on the
  // UNDER_HEAD side and from the stack to the outer nut face on UNDER_NUT.
  const headInner = underHead?.start ?? shank.start;
  const nutInner = underNut?.end ?? shank.end;
  const head: SchematicHexHardware = {
    id: `${shank.id}:schematic-head`,
    kind: "HEAD",
    ownerBoltId: shank.ownerBoltId,
    start: offset(headInner, axis, -dimensions.headHeight),
    end: headInner,
    acrossFlats: dimensions.headAcrossFlats,
  };
  const nut: SchematicHexHardware = {
    id: `${shank.id}:schematic-nut`,
    kind: "NUT",
    ownerBoltId: shank.ownerBoltId,
    start: nutInner,
    end: offset(nutInner, axis, dimensions.nutThickness),
    acrossFlats: dimensions.nutAcrossFlats,
  };
  const exteriorAnchorNut: SchematicHexHardware = {
    ...nut,
    id: `${shank.id}:exterior-anchor-nut`,
    start: offset(headInner, axis, -dimensions.nutThickness),
    end: headInner,
  };

  // New products may supply explicitly known backend hardware. Historical
  // cylinders omit this optional field and retain their exact existing path.
  const exact = shank.exactHardware;
  const actualHead = exact === undefined ? head : { ...head, id: `${shank.id}:exact-head`,
    start: exact.headStart, end: exact.headEnd, acrossFlats: exact.headAcrossFlats };
  const actualNut = exact === undefined ? nut : { ...nut, id: `${shank.id}:exact-nut`,
    start: exact.nutStart, end: exact.nutEnd, acrossFlats: exact.nutAcrossFlats };

  return {
    id: `${shank.id}:assembly`,
    ownerBoltId: shank.ownerBoltId,
    shank,
    washers: ownedWashers,
    head: actualHead,
    nut: actualNut,
    renderedHardware: shank.hardwareConfiguration === "EXTERIOR_NUT_WASHER_ANCHOR"
      ? [exteriorAnchorNut]
      : [actualHead, actualNut],
  };
}

export function buildFastenerPresentations(
  cylinders: readonly SceneCylinder[],
): FastenerPresentation[] {
  const washers = cylinders.filter((value) => value.kind === "WASHER");
  return cylinders
    .filter((value) => value.kind === "BOLT")
    .map((shank) => buildFastenerPresentation(shank, washers))
    .filter((value): value is FastenerPresentation => value !== null);
}
