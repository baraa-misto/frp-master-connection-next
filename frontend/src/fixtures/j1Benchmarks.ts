import j1Si from "./j1-si.json";
import j1Us from "./j1-us.json";

import type {
  ConnectionViewExtentsDTO,
  SingleBoltEvaluationRequest,
} from "../api/contracts";

export type BenchmarkUnitSystem = "US_CUSTOMARY" | "SI";

const BENCHMARKS: Readonly<Record<BenchmarkUnitSystem, unknown>> = {
  US_CUSTOMARY: j1Us,
  SI: j1Si,
};

const VIEW_EXTENTS: Readonly<Record<BenchmarkUnitSystem, ConnectionViewExtentsDTO>> = {
  US_CUSTOMARY: {
    brace_view_length: { value: "4", unit: "in" },
    column_view_extent_below: { value: "8.7426406871192848", unit: "in" },
    column_view_extent_above: { value: "1.5", unit: "in" },
  },
  SI: {
    brace_view_length: { value: "101.6", unit: "mm" },
    column_view_extent_below: { value: "222.06307345282983392", unit: "mm" },
    column_view_extent_above: { value: "38.1", unit: "mm" },
  },
};

export function loadJ1Benchmark(unitSystem: BenchmarkUnitSystem): SingleBoltEvaluationRequest {
  const request = structuredClone(BENCHMARKS[unitSystem]) as SingleBoltEvaluationRequest;
  /* v8 ignore next 3 -- governed JSON fixtures make absence an invariant violation */
  if (request.geometry_template === undefined) {
    throw new Error("The governed J1 benchmark must define backend-owned template geometry.");
  }
  return request;
}

export function loadJ1ViewExtents(
  unitSystem: BenchmarkUnitSystem,
): ConnectionViewExtentsDTO {
  return structuredClone(VIEW_EXTENTS[unitSystem]);
}
