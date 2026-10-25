import { friendlyEnum } from "./presentation";

const labels: Readonly<Record<string, string>> = {
  DIRECT_SHARED_BOLTS: "Shared bolts — shear", DIRECT_BRACE_BEARING: "Angle connected leg — bearing",
  DIRECT_BRACE_LOCAL: "Angle connected leg — local shear paths", DIRECT_BRACE_GLOBAL: "Angle — global block shear reference",
  DIRECT_COLUMN_BEARING: "Receiving I flange — bearing", DIRECT_COLUMN_LOCAL: "Receiving I flange — local shear paths",
  DIRECT_COLUMN_GLOBAL: "Receiving I flange — global block shear reference",
  LRFD: "ASCE LRFD", ASD: "RHM ASD", NO_NATIVE_ASCE: "ASCE checks unavailable for this physical layout",
  HYB2_DIRECT_REFERENCE: "RHM reference calculation", UNCHANGED_NATIVE_ASCE: "Existing ASCE calculation",
  ASCE_SAME_CONNECTION_COMPONENT_CALCULATION: "ASCE component — current connection",
  BRACE_END_DISTANCE_MINIMUM_LOWER_BOUND: "Angle end distance (minimum 2d screen)",
  RECEIVING_INTERROW_SHEAR_OUT: "Receiving I flange — longitudinal inter-row shear-out",
  ASCE_CURRENT_PHYSICAL_RECEIVING_COMPONENT: "ASCE physical component — current receiving flange",
  SCOPED_NUMERICAL_PASS: "PASS — evaluated numerical checks",
  SCOPED_NUMERICAL_FAIL: "FAIL — evaluated numerical checks",
  SCOPED_NUMERICAL_NOT_EVALUATED: "No numerical checks evaluated",
  DETAILING_FAIL: "Detailing requirements fail",
  DETAILING_UNKNOWN: "Detailing not fully verified",
  REQUIRED_COVERAGE_PARTIAL: "Partial — required mechanisms remain unevaluated",
  SCOPED_COMPONENTS_WITH_UNRESOLVED_COUPLED_METHODS: "Supported component checks; coupled methods unresolved",
  NOT_ESTABLISHED_SECTION_2_3_2: "Not established — Section 2.3.2 remains open",
  FAIL_EVALUATED_CHECKS_AND_DETAILING: "FAIL — evaluated checks and detailing",
  FAIL_EVALUATED_CHECKS: "FAIL — evaluated checks",
  FAIL_DETAILING: "FAIL — detailing",
  NOT_VERIFIED: "NOT VERIFIED",
};
export function calculationLabel(value: string): string {
  return value.split(":").map((part) => {
    const bolt = /^B_R(\d+)_L(\d+)$/u.exec(part);
    return bolt === null ? labels[part] ?? ({ "layer-A": "Angle connected leg", "layer-B": "Receiving I flange" }[part] ?? friendlyEnum(part)) : `Bolt row ${String(bolt[1])}, line ${String(bolt[2])}`;
  }).join(" — ");
}
