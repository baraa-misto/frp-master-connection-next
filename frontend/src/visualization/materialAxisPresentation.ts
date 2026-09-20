export interface MaterialAxisPresentationVec3 {
  readonly x: number;
  readonly y: number;
  readonly z: number;
}

export interface MaterialAxisRegionIdentity {
  readonly componentId: string;
  readonly elementId: string;
  readonly materialRegionId: string;
  readonly lengthwise: MaterialAxisPresentationVec3;
  readonly crosswise: MaterialAxisPresentationVec3;
  readonly throughThickness: MaterialAxisPresentationVec3;
}

export interface MaterialAxisOwnedIdentity {
  readonly ownerId: string;
  readonly localId: string;
}

export interface MaterialAxisBoxPrimitive {
  readonly id: string;
  readonly ownerId: string;
  readonly elementId: string | null;
  readonly materialRegionId: string | null;
  readonly center: MaterialAxisPresentationVec3;
  readonly size: MaterialAxisPresentationVec3;
  readonly basis: readonly [
    MaterialAxisPresentationVec3,
    MaterialAxisPresentationVec3,
    MaterialAxisPresentationVec3,
  ];
}

export interface MaterialAxisMeshPrimitive {
  readonly id: string;
  readonly ownerId: string;
  readonly elementId: string | null;
  readonly materialRegionId: string | null;
  readonly points: readonly MaterialAxisPresentationVec3[];
}

export interface RegionEmbeddedMaterialAxisPresentation {
  readonly origin: MaterialAxisPresentationVec3;
  readonly lengthwiseLength: number;
  readonly crosswiseLength: number;
  readonly markerRadius: number;
  readonly primitiveIds: readonly string[];
  readonly surfaceOffset: number;
}

export type ThroughThicknessMarkerFacing = "CROSS" | "DOT" | "TANGENT";

export type ThroughThicknessMarkerBasis = readonly [
  MaterialAxisPresentationVec3,
  MaterialAxisPresentationVec3,
  MaterialAxisPresentationVec3,
];

const MATERIAL_AXIS_FACING_TOLERANCE = 0.08;

function add(
  first: MaterialAxisPresentationVec3,
  second: MaterialAxisPresentationVec3,
): MaterialAxisPresentationVec3 {
  return {
    x: first.x + second.x,
    y: first.y + second.y,
    z: first.z + second.z,
  };
}

function scale(
  value: MaterialAxisPresentationVec3,
  factor: number,
): MaterialAxisPresentationVec3 {
  return { x: value.x * factor, y: value.y * factor, z: value.z * factor };
}

function subtract(
  first: MaterialAxisPresentationVec3,
  second: MaterialAxisPresentationVec3,
): MaterialAxisPresentationVec3 {
  return {
    x: first.x - second.x,
    y: first.y - second.y,
    z: first.z - second.z,
  };
}

function dot(
  first: MaterialAxisPresentationVec3,
  second: MaterialAxisPresentationVec3,
): number {
  return first.x * second.x + first.y * second.y + first.z * second.z;
}

function cross(
  first: MaterialAxisPresentationVec3,
  second: MaterialAxisPresentationVec3,
): MaterialAxisPresentationVec3 {
  return {
    x: first.y * second.z - first.z * second.y,
    y: first.z * second.x - first.x * second.z,
    z: first.x * second.y - first.y * second.x,
  };
}

function normalize(value: MaterialAxisPresentationVec3): MaterialAxisPresentationVec3 {
  const magnitude = Math.hypot(value.x, value.y, value.z);
  if (magnitude === 0) throw new Error("Material-axis presentation requires nonzero vectors.");
  return scale(value, 1 / magnitude);
}

function matchesRegion(
  primitive: MaterialAxisBoxPrimitive | MaterialAxisMeshPrimitive,
  axes: MaterialAxisRegionIdentity,
): boolean {
  return (
    primitive.ownerId === axes.componentId &&
    primitive.elementId === axes.elementId &&
    (primitive.materialRegionId === null ||
      primitive.materialRegionId === axes.materialRegionId)
  );
}

/**
 * Resolve an optional backend owner-qualified material identity without changing its
 * engineering identifier. The returned local id is presentation-only; component
 * ownership remains part of the stable region binding key.
 */
export function resolveMaterialAxisOwnedIdentity(
  fallbackOwnerId: string,
  value: string,
  primitiveOwnerIds: readonly string[],
): MaterialAxisOwnedIdentity {
  const ownerId = primitiveOwnerIds.find((candidate) =>
    value.startsWith(`${candidate}:`),
  ) ?? fallbackOwnerId;
  const prefix = `${ownerId}:`;
  return {
    ownerId,
    localId: value.startsWith(prefix) ? value.slice(prefix.length) : value,
  };
}

/** Normalize a primitive's owner-qualified local id for region binding only. */
export function normalizeMaterialAxisPrimitiveId(
  ownerId: string,
  value: string,
): string {
  const prefix = `${ownerId}:`;
  return value.startsWith(prefix) ? value.slice(prefix.length) : value;
}

function boxCorners(value: MaterialAxisBoxPrimitive): readonly MaterialAxisPresentationVec3[] {
  const halfAxes = [
    scale(value.basis[0], value.size.x / 2),
    scale(value.basis[1], value.size.y / 2),
    scale(value.basis[2], value.size.z / 2),
  ] as const;
  const result: MaterialAxisPresentationVec3[] = [];
  for (const xSign of [-1, 1]) {
    for (const ySign of [-1, 1]) {
      for (const zSign of [-1, 1]) {
        result.push(
          add(
            add(add(value.center, scale(halfAxes[0], xSign)), scale(halfAxes[1], ySign)),
            scale(halfAxes[2], zSign),
          ),
        );
      }
    }
  }
  return result;
}

function projectionRange(
  points: readonly MaterialAxisPresentationVec3[],
  axis: MaterialAxisPresentationVec3,
): readonly [number, number] {
  const projections = points.map((point) => dot(point, axis));
  return [Math.min(...projections), Math.max(...projections)];
}

function midpoint(range: readonly [number, number]): number {
  return (range[0] + range[1]) / 2;
}

export function buildRegionEmbeddedMaterialAxisPresentation(
  axes: MaterialAxisRegionIdentity,
  boxes: readonly MaterialAxisBoxPrimitive[],
  meshes: readonly MaterialAxisMeshPrimitive[],
): RegionEmbeddedMaterialAxisPresentation | null {
  const matchingBoxes = boxes.filter((value) => matchesRegion(value, axes));
  const matchingMeshes = meshes.filter((value) => matchesRegion(value, axes));
  const points = [
    ...matchingBoxes.flatMap(boxCorners),
    ...matchingMeshes.flatMap((value) => value.points),
  ];
  if (points.length === 0) return null;

  const lengthwise = normalize(axes.lengthwise);
  const crosswise = normalize(axes.crosswise);
  const throughThickness = normalize(axes.throughThickness);
  const lengthwiseRange = projectionRange(points, lengthwise);
  const crosswiseRange = projectionRange(points, crosswise);
  const thicknessRange = projectionRange(points, throughThickness);
  const lengthwiseSpan = lengthwiseRange[1] - lengthwiseRange[0];
  const crosswiseSpan = crosswiseRange[1] - crosswiseRange[0];
  const thicknessSpan = thicknessRange[1] - thicknessRange[0];
  const limitingInPlaneSpan = Math.min(lengthwiseSpan, crosswiseSpan);
  if (limitingInPlaneSpan <= 0 || thicknessSpan <= 0) return null;

  const axisLengthLimit = limitingInPlaneSpan * 0.72;
  const lengthwiseLength = Math.min(lengthwiseSpan * 0.58, axisLengthLimit);
  const crosswiseLength = Math.min(crosswiseSpan * 0.58, axisLengthLimit);
  const surfaceOffset = Math.max(
    thicknessSpan * 0.04,
    limitingInPlaneSpan * 0.006,
  );
  const origin = add(
    add(
      scale(lengthwise, midpoint(lengthwiseRange)),
      scale(crosswise, midpoint(crosswiseRange)),
    ),
    scale(throughThickness, thicknessRange[1] + surfaceOffset),
  );

  return {
    origin,
    lengthwiseLength,
    crosswiseLength,
    markerRadius: limitingInPlaneSpan * 0.075,
    primitiveIds: [
      ...matchingBoxes.map((value) => value.id),
      ...matchingMeshes.map((value) => value.id),
    ].sort(),
    surfaceOffset,
  };
}

export function classifyThroughThicknessMarkerFacing(
  origin: MaterialAxisPresentationVec3,
  throughThickness: MaterialAxisPresentationVec3,
  cameraPosition: MaterialAxisPresentationVec3,
): ThroughThicknessMarkerFacing {
  const towardCamera = normalize(subtract(cameraPosition, origin));
  const facing = dot(normalize(throughThickness), towardCamera);
  if (facing > MATERIAL_AXIS_FACING_TOLERANCE) return "DOT";
  if (facing < -MATERIAL_AXIS_FACING_TOLERANCE) return "CROSS";
  return "TANGENT";
}

/**
 * Build a proper-rotation presentation frame whose local Z axis is exactly the
 * backend-authored TT direction. Reflected LW/CW/TT bases may have determinant -1,
 * which no quaternion can represent; using TT directly keeps reflection handling out
 * of the engineering-vector transport.
 */
export function buildThroughThicknessMarkerBasis(
  throughThickness: MaterialAxisPresentationVec3,
): ThroughThicknessMarkerBasis {
  const normal = normalize(throughThickness);
  const reference = Math.abs(normal.z) < 0.9
    ? { x: 0, y: 0, z: 1 }
    : { x: 0, y: 1, z: 0 };
  const localX = normalize(cross(reference, normal));
  const localY = cross(normal, localX);
  return [localX, localY, normal];
}

export function materialAxisDepthTest(displayMode: "SOLID" | "XRAY"): boolean {
  return displayMode === "SOLID";
}
