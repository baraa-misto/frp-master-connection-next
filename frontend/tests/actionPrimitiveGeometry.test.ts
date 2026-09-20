import { Quaternion, Vector3 } from "three";
import { describe, expect, it } from "vitest";

import {
  MOMENT_ARROW_ARC_ANGLE_RADIANS,
  calculateMomentArrowGeometry,
} from "../src/visualization/actionPrimitiveGeometry";

describe("Stage 2.3R8 moment-arrow presentation geometry", () => {
  it("overlaps the cone base with the exact torus endpoint and aligns its axis tangentially", () => {
    const geometry = calculateMomentArrowGeometry(10);
    const arcEnd = new Vector3(geometry.arcEnd.x, geometry.arcEnd.y, geometry.arcEnd.z);
    const headBase = new Vector3(
      geometry.headBaseCenter.x,
      geometry.headBaseCenter.y,
      geometry.headBaseCenter.z,
    );
    const tangent = new Vector3(geometry.tangent.x, geometry.tangent.y, geometry.tangent.z);
    const rotatedConeAxis = new Vector3(0, 1, 0).applyAxisAngle(
      new Vector3(0, 0, 1),
      geometry.headRotationZ,
    );

    expect(geometry.arcAngle).toBe(MOMENT_ARROW_ARC_ANGLE_RADIANS);
    expect(arcEnd.distanceTo(headBase)).toBeCloseTo(geometry.tubeRadius * 0.75);
    expect(arcEnd.distanceTo(headBase)).toBeLessThan(geometry.tubeRadius);
    expect(rotatedConeAxis.x).toBeCloseTo(tangent.x);
    expect(rotatedConeAxis.y).toBeCloseTo(tangent.y);
    expect(rotatedConeAxis.z).toBeCloseTo(tangent.z);
  });

  it("uses the same attached local geometry for Mx, My, and Mz axes", () => {
    const geometry = calculateMomentArrowGeometry(8);
    const localArcEnd = new Vector3(geometry.arcEnd.x, geometry.arcEnd.y, geometry.arcEnd.z);
    const localHeadBase = new Vector3(
      geometry.headBaseCenter.x,
      geometry.headBaseCenter.y,
      geometry.headBaseCenter.z,
    );
    const localTangent = new Vector3(
      geometry.tangent.x,
      geometry.tangent.y,
      geometry.tangent.z,
    );
    for (const axis of [
      new Vector3(1, 0, 0),
      new Vector3(0, 1, 0),
      new Vector3(0, 0, 1),
    ]) {
      const orientation = new Quaternion().setFromUnitVectors(new Vector3(0, 0, 1), axis);
      const worldArcEnd = localArcEnd.clone().applyQuaternion(orientation);
      const worldHeadBase = localHeadBase.clone().applyQuaternion(orientation);
      const worldTangent = localTangent.clone().applyQuaternion(orientation);
      expect(worldArcEnd.distanceTo(worldHeadBase)).toBeLessThan(geometry.tubeRadius);
      expect(worldTangent.dot(axis)).toBeCloseTo(0);
      expect(worldTangent.length()).toBeCloseTo(1);
    }
  });

  it("scales every visual dimension without changing attachment proportions", () => {
    const small = calculateMomentArrowGeometry(4);
    const large = calculateMomentArrowGeometry(12);
    expect(large.radius / small.radius).toBeCloseTo(3);
    expect(large.tubeRadius / small.tubeRadius).toBeCloseTo(3);
    expect(large.headRadius / small.headRadius).toBeCloseTo(3);
    expect(large.headHeight / small.headHeight).toBeCloseTo(3);
    expect(large.headRotationZ).toBe(small.headRotationZ);
  });
});
