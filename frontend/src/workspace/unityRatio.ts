/** Presentation of server-calculated utilization only. No demand or resistance is derived here. */
export type UnityFamily =
  | "single-bolt" | "multirow" | "tee" | "clip-angle" | "paired-clip-angle"
  | "multi-member-tee" | "dctn" | "web-splice" | "beam-concrete-paired-angle"
  | "direct-side-lap" | "column-base-web-angle" | "wi-moment-splice"
  | "channel-moment-splice" | "wi-wall-moment" | "wi-frp-support-moment"
  | "angle-column-moment-base" | "column-moment-base" | "ssmc";

export type UnityPhase = "not-checked" | "stale" | "checking" | "invalid" | "request-error" | "current";
export function unityPhase(input: { readonly design: unknown; readonly stale?: boolean; readonly checking?: boolean; readonly error?: unknown; readonly invalid?: boolean; readonly previewState?: string; readonly previewCurrent?: boolean }): UnityPhase {
  if (input.checking) return "checking";
  if (input.error) return "request-error";
  if (input.previewState?.includes("FAILED")) return "request-error";
  if (input.invalid || input.previewState?.includes("INVALID") || input.previewState === "NO_VALID_PREVIEW") return "invalid";
  if (input.stale || (input.design !== null && input.design !== undefined && (input.previewCurrent === false || (input.previewState !== undefined && input.previewState !== "CURRENT_VALID")))) return "stale";
  return input.design === null || input.design === undefined ? "not-checked" : "current";
}
export interface UnityInput { readonly family: UnityFamily; readonly phase: UnityPhase; readonly design?: unknown }
export function viewerUnity(family: UnityFamily, design: unknown, state: Omit<Parameters<typeof unityPhase>[0], "design"> = {}): UnityView {
  return resolveUnity({ family, design, phase: unityPhase({ ...state, design }) });
}
export interface UnityView {
  readonly tone: "green" | "red" | "yellow" | "gray";
  readonly ratio: number | null;
  readonly ratioText: string;
  readonly status: string;
  readonly governing: string | null;
  readonly explanation: string;
}

type RecordValue = Record<string, unknown>;
const record = (value: unknown): RecordValue | null => value !== null && typeof value === "object" && !Array.isArray(value) ? value as RecordValue : null;
const field = (value: unknown, name: string): unknown => record(value)?.[name];
const string = (value: unknown): string | null => typeof value === "string" && value.trim() !== "" ? value : null;
const array = (value: unknown): readonly unknown[] => Array.isArray(value) ? value : [];
const decimal = (value: unknown): number | null => {
  if (typeof value !== "string" && typeof value !== "number") return null;
  const raw = String(value).trim();
  if (!/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(raw)) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
};
interface CheckedRatio { readonly value: number; readonly label: string }
const checkedRatio = (value: unknown, label: string): CheckedRatio | null => {
  const parsed = decimal(value);
  return parsed === null ? null : { value: parsed, label };
};
const add = (out: CheckedRatio[], value: unknown, label: string) => { const ratio = checkedRatio(value, label); if (ratio !== null) out.push(ratio); };
const statusIsFail = (value: unknown): boolean => typeof value === "string" && (value === "FAIL" || value.startsWith("FAIL_") || value === "FAILED");
const firstText = (...values: unknown[]): string | null => values.map(string).find((item) => item !== null) ?? null;
const firstArrayText = (value: unknown): string | null => array(value).map(string).find((item) => item !== null) ?? null;

/** These fields are dimensionless server ratios; percentage fields are intentionally excluded. */
function nestedRatios(value: unknown, prefix: string, out: CheckedRatio[], depth = 0): void {
  if (depth > 8) return;
  if (Array.isArray(value)) { value.forEach((item, index) => { nestedRatios(item, `${prefix} ${String(index + 1)}`, out, depth + 1); }); return; }
  const object = record(value);
  if (object === null) return;
  const label = firstText(object.check_id, object.result_id, object.bolt_id, object.connector_id, object.path_id) ?? prefix;
  for (const [key, item] of Object.entries(object)) {
    if (key === "utilization" || key === "governing_utilization" || key === "normal_utilization" || key === "shear_utilization" || key === "rational_utilization" || key === "double_shear_governing_utilization") add(out, item, label);
    else if (typeof item === "object" && item !== null) nestedRatios(item, `${prefix} / ${key}`, out, depth + 1);
  }
}
function nestedFailure(value: unknown, depth = 0): boolean {
  if (depth > 8) return false;
  if (Array.isArray(value)) return value.some((item) => nestedFailure(item, depth + 1));
  const object = record(value);
  if (object === null) return false;
  return Object.entries(object).some(([key, item]) => key === "status" || key === "assembly_status" || key === "whole_connection_status" || key === "numerical_comparison"
    ? statusIsFail(item)
    : typeof item === "object" && item !== null && nestedFailure(item, depth + 1));
}

interface Evidence { readonly ratios: CheckedRatio[]; readonly failed: boolean; readonly complete: boolean; readonly explanation: string }
function evidence(family: UnityFamily, design: unknown): Evidence {
  const ratios: CheckedRatio[] = [];
  const root = record(design) ?? {};
  const body = record(root.result) ?? root;
  let status: unknown = root.assembly_status ?? root.aggregate_status ?? body.whole_connection_status ?? body.status;
  let failed = statusIsFail(status);
  let complete = false;
  let explanation = firstText(root.required_check_status, root.status_reason, body.status_reason) ?? "Required check coverage or qualification is not established by this response.";

  if (family === "single-bolt") {
    status = root.aggregate_status;
    const rows = array(root.results);
    rows.forEach((row) => {
      const plan = field(row, "plan");
      add(ratios, field(row, "utilization"), firstText(field(plan, "check_id"), field(plan, "limit_state")) ?? "Bolt check");
      failed ||= statusIsFail(field(row, "numerical_comparison"));
    });
    failed ||= statusIsFail(status);
    complete = status === "PASS" && rows.length > 0 && array(root.qualification_flags).length === 0 && array(root.issues).length === 0;
    explanation = complete ? "Backend aggregate PASS; no qualification flags or issues." : firstArrayText(root.qualification_flags) ?? firstText(status) ?? explanation;
  } else if (family === "multirow") {
    const calculation = record(root.calculation_result);
    const integration = record(root.automatic_group_mode_integration);
    const scenarios = array(integration?.scenario_results);
    const handoffs = array(root.automatic_handoff_results);
    const scenario = scenarios.length === 1 ? record(scenarios[0]) : null;
    const handoff = handoffs.length === 1 ? record(handoffs[0]) : null;
    // A sole backend scenario/handoff is one design snapshot. Never envelope unrelated scenarios here.
    const selected = scenario ?? handoff ?? calculation;
    const rows = array(selected?.supported_results ?? selected?.results);
    rows.forEach((row) => { add(ratios, field(row, "utilization"), firstText(field(row, "result_id"), field(row, "limit_state")) ?? "Bolt-group check"); failed ||= statusIsFail(field(row, "numerical_comparison")); });
    status = selected?.overall_disposition;
    failed ||= statusIsFail(status) || array(selected?.failed_check_ids).length > 0 || statusIsFail(integration?.overall_disposition) || handoffs.some((item) => statusIsFail(field(item, "overall_disposition")));
    const coverage = scenario !== null ? array(scenario.required_check_ids).length > 0 : handoff !== null ? handoff.coverage === "FULL_LEGACY_COLLINEAR" : calculation !== null && array(calculation.required_check_ids).length === array(calculation.calculated_check_ids).length;
    complete = status === "PASS" && selected !== null && rows.length > 0 && selected.qualification === "QUALIFIED_ASCE_PRESCRIPTIVE" && array(selected.unsupported_check_ids ?? selected.unsupported_required_check_ids).length === 0 && array(selected.incomplete_required_check_ids).length === 0 && coverage && handoffs.every((item) => field(item, "overall_disposition") === "PASS") && (integration === null || integration.overall_disposition === "PASS");
    explanation = complete ? "Backend qualified PASS with required check coverage." : firstArrayText(selected?.unsupported_check_ids ?? selected?.unsupported_required_check_ids) ?? firstArrayText(selected?.incomplete_required_check_ids) ?? firstText(status) ?? explanation;
  } else if (family === "wi-moment-splice" || family === "channel-moment-splice") {
    add(ratios, body.governing_utilization, firstText(body.governing_check_id) ?? "Supported local governing check");
    failed ||= array(root.failed_check_ids).length > 0;
    explanation = firstArrayText(root.unavailable_check_ids) ?? firstText(root.required_check_status, body.disclaimer_text) ?? explanation;
  } else if (family === "web-splice") {
    nestedRatios(body.plate_body_interaction, "Plate body", ratios);
    nestedRatios(body.double_shear_results, "Double shear", ratios);
    add(ratios, body.double_shear_governing_utilization, "Double-shear governing bolt");
    failed ||= root.supported_local_failure_present === true || array(root.failed_local_check_ids).length > 0 || statusIsFail(field(body.plate_body_interaction, "status")) || statusIsFail(body.double_shear_status);
    explanation = firstArrayText(root.local_resistance_warnings) ?? firstText(root.required_check_status, body.connection_element_qualification) ?? explanation;
  } else if (family === "wi-wall-moment" || family === "wi-frp-support-moment") {
    nestedRatios(body, "Local check", ratios);
    failed ||= nestedFailure(body) || array(body.native_failed_checks).length > 0 || array(body.failed_checks).length > 0;
    explanation = firstText(body.status_reason, body.whole_connection_status, body.assembly_status) ?? explanation;
  } else if (family === "ssmc") {
    status = root.whole_connection_status ?? body.whole_connection_status;
    failed ||= statusIsFail(status) || array(body.checks).some((check) => statusIsFail(field(check, "status")));
    explanation = firstArrayText(body.blockers) ?? firstArrayText(body.applicability_reasons) ?? firstText(status) ?? explanation;
    // Current SSMC public checks contain demand but no design utilization.
  } else if (family === "dctn") {
    status = body.whole_connection_status;
    failed ||= statusIsFail(status) || array(body.checks).some((check) => statusIsFail(field(check, "status")));
    explanation = firstArrayText(body.blockers) ?? firstText(status) ?? explanation;
  } else {
    status = root.assembly_status ?? body.assembly_status ?? body.status ?? body.whole_connection_status;
    nestedRatios(body, "Supported local check", ratios);
    failed ||= statusIsFail(status) || nestedFailure(body) || root.supported_interface_failure_present === true || root.supported_failure_present === true || root.supported_beam_side_failure_present === true || root.supported_local_frp_failure_present === true || root.supported_local_failure_present === true;
    explanation = firstText(root.required_check_status, body.whole_connection_status, status) ?? explanation;
  }
  return { ratios, failed, complete, explanation };
}

export function formatUnityPercent(ratio: number): string {
  if (ratio === 1) return "100%";
  const percent = ratio * 100;
  let digits = 1;
  while (digits < 8 && ratio !== 1 && Number(percent.toFixed(digits)) === 100) digits += 1;
  const formatted = percent.toFixed(digits);
  if (ratio < 1 && Number(formatted) === 100) return "<100%";
  if (ratio > 1 && Number(formatted) === 100) return ">100%";
  return `${formatted}%`;
}

export function resolveUnity(input: UnityInput): UnityView {
  const gray: Record<Exclude<UnityPhase, "current">, string> = {
    "not-checked": "Not checked", stale: "Results stale", checking: "Checking…", invalid: "Invalid inputs", "request-error": "Request error",
  };
  if (input.phase !== "current" || input.design === null || input.design === undefined) {
    const status = input.phase === "current" ? "Not checked" : gray[input.phase];
    return { tone: "gray", ratio: null, ratioText: "UR: —", status, governing: null, explanation: status === "Results stale" ? "Run Design Check again for the current engineering inputs." : "No current design-check result is available." };
  }
  const found = evidence(input.family, input.design);
  const governing = found.ratios.reduce<CheckedRatio | null>((max, item) => max === null || item.value > max.value ? item : max, null);
  const ratio = governing?.value ?? null;
  const failed = found.failed || (ratio !== null && ratio > 1);
  const tone = failed ? "red" : found.complete && ratio !== null && ratio <= 1 ? "green" : "yellow";
  const ratioText = ratio === null ? "UR: —" : `${tone === "yellow" ? "UR (checked)" : "UR"}: ${formatUnityPercent(ratio)}`;
  const status = failed ? ratio === null ? "Design failed" : "Failed" : tone === "green" ? ratio === 1 ? "At limit · Complete" : "Complete" : "Incomplete design";
  return { tone, ratio, ratioText, status, governing: governing?.label ?? null, explanation: found.explanation };
}
