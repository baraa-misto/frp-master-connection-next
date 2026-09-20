import type { Vec3 } from "./sceneModel";

export const MOMENT_ARROW_ARC_ANGLE_RADIANS = Math.PI * 1.65;
export const MOMENT_LABEL_ANGLE_RADIANS = Math.PI * 1.15;

export interface MomentArrowGeometry {
  readonly radius: number;
  readonly tubeRadius: number;
  readonly headRadius: number;
  readonly headHeight: number;
  readonly arcAngle: number;
  readonly arcEnd: Vec3;
  readonly tangent: Vec3;
  readonly headBaseCenter: Vec3;
  readonly headCenter: Vec3;
  readonly headRotationZ: number;
}

export function calculateMomentArrowGeometry(length: number): MomentArrowGeometry {
  const radius = length * 0.42;
  const tubeRadius = length * 0.025;
  const headRadius = length * 0.08;
  const headHeight = length * 0.22;
  const arcAngle = MOMENT_ARROW_ARC_ANGLE_RADIANS;
  const arcEnd = {
    x: radius * Math.cos(arcAngle),
    y: radius * Math.sin(arcAngle),
    z: 0,
  };
  const tangent = {
    x: -Math.sin(arcAngle),
    y: Math.cos(arcAngle),
    z: 0,
  };
  const headOverlap = tubeRadius * 0.75;
  const headBaseCenter = {
    x: arcEnd.x - tangent.x * headOverlap,
    y: arcEnd.y - tangent.y * headOverlap,
    z: 0,
  };
  const headCenterOffset = headHeight / 2 - headOverlap;
  const headCenter = {
    x: arcEnd.x + tangent.x * headCenterOffset,
    y: arcEnd.y + tangent.y * headCenterOffset,
    z: 0,
  };
  return {
    radius,
    tubeRadius,
    headRadius,
    headHeight,
    arcAngle,
    arcEnd,
    tangent,
    headBaseCenter,
    headCenter,
    headRotationZ: arcAngle,
  };
}
