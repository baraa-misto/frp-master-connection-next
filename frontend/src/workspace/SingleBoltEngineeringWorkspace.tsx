import { viewerUnity } from "./unityRatio";
import { useMemo, useRef, useState, type ReactNode } from "react";

import {
  EvaluationTransportError,
  evaluateMultiRow,
  evaluateSingleBolt,
} from "../api/client";
import type {
  ActionDirectionSnapshot,
  CalculationResultDTO,
  ConnectionViewExtentsDTO,
  JsonValue,
  MemberSectionDTO,
  SingleBoltEvaluationRequest,
  SingleBoltEvaluationResponse,
} from "../api/contracts";
import type {
  AutomaticGroupModeIntegrationResult,
  AutomaticHandoffResult,
  EccentricGroupModeLineResult,
  MultiRowConnectionRequest,
  MultiRowCalculationResult,
  MultiRowCheckResult,
  MultiRowDesignResponse,
  MultiRowQuantity,
} from "../api/multirowContracts";
import {
  loadJ1Benchmark,
  loadJ1ViewExtents,
  type BenchmarkUnitSystem,
} from "../fixtures/j1Benchmarks";
import {
  buildMultiRowSceneModel,
  buildSingleBoltSceneModel,
} from "../visualization/sceneModel";
import { MultiRowVisualizationPanel } from "../visualization/MultiRowVisualizationPanel";
import { VisualizationPanel } from "../visualization/VisualizationPanel";
import type { SceneSelection } from "../visualization/EngineeringScene";
import {
  ConnectionWorkspaceMain,
  ConnectionWorkspaceShell,
  ConnectionWorkspaceSidebar,
  PersistentConnectionViewer,
  SidebarGroup,
} from "./ConnectionWorkspaceShell";
import {
  exactQuantity,
  formatDecimal,
  formatDisplayQuantity,
  formatEditableDecimal,
  formatQuantity,
  formatUtilization,
  friendlyEnum,
  friendlyIdentifier,
} from "./presentation";
import {
  INPUT_CLASSIFICATION,
  buildSingleBoltPreviewRequest,
  requirePreviewScheduling,
  useCanonicalPreview,
  type CanonicalPreviewInput,
  type EngineeringInputClassification,
  type PreviewScheduling,
} from "./previewWorkflow";
import { useMultiRowPreview } from "./multirowWorkflow";

type DemandMode = MultiRowConnectionRequest["demand_source"];
type SectionQuantityName = "leg_y" | "leg_z" | "thickness" | "overall_depth" | "flange_width" | "web_thickness" | "flange_thickness";

type GroupDistribution =
  | "ASCE_PRESCRIBED"
  | "CONSERVATIVE_FULL_ROW_ENVELOPE"
  | "FRACTIONS"
  | "DIRECT_ROW_FORCES";

interface BoltGroupState {
  readonly rowCount: number;
  readonly boltsPerRow: number;
  readonly pitch: string;
  readonly gauge: string;
  readonly loadedBoundaryToRow1: string;
  readonly negativeSideDistance: string;
  readonly positiveSideDistance: string;
  readonly materialPair: "FRP_FRP" | "FRP_STEEL";
  readonly materialAxisAngleDegrees: string;
  readonly distribution: GroupDistribution;
  readonly engineerAllocations: MultiRowConnectionRequest["engineer_allocations"];
  readonly firstRowMethod: "ASCE_STANDARD_SIMPLIFIED" | "ASCE_COMMENTARY_FULL";
  readonly prescribedLbr: string;
  readonly forceLineOffset: string;
  readonly sourceCalculation: string;
  readonly showBlockPaths: boolean;
  readonly boltAxisTensionRequired: boolean;
  readonly boltAxisTensions: MultiRowConnectionRequest["bolt_axis_tensions"];
}

function initialBoltGroupState(unitSystem: BenchmarkUnitSystem): BoltGroupState {
  const si = unitSystem === "SI";
  return {
    rowCount: 1,
    boltsPerRow: 1,
    pitch: si ? "50.8" : "2",
    gauge: si ? "50.8" : "2",
    loadedBoundaryToRow1: si ? "50.8" : "2",
    negativeSideDistance: si ? "38.1" : "1.5",
    positiveSideDistance: si ? "38.1" : "1.5",
    materialPair: "FRP_FRP",
    materialAxisAngleDegrees: "0",
    distribution: "ASCE_PRESCRIBED",
    engineerAllocations: [],
    firstRowMethod: "ASCE_STANDARD_SIMPLIFIED",
    prescribedLbr: "0.5",
    forceLineOffset: "0",
    sourceCalculation: "Engineer-supplied connection demand",
    showBlockPaths: false,
    boltAxisTensionRequired: false,
    boltAxisTensions: [],
  };
}

function multirowQuantity(value: string, unit: string): MultiRowQuantity {
  return { value, unit };
}

function initialRequest(): SingleBoltEvaluationRequest {
  return loadJ1Benchmark("US_CUSTOMARY");
}

function requiredAt<Item>(values: readonly Item[], index: number, label: string): Item {
  const value = values[index];
  /* v8 ignore next -- governed J1 fixtures make absence an invariant violation */
  if (value === undefined) throw new Error(`${label} is required by the engineering workspace.`);
  return value;
}

function requiredValue<Value>(value: Value | null | undefined, label: string): Value {
  /* v8 ignore next -- governed J1 fixtures make absence an invariant violation */
  if (value === null || value === undefined) throw new Error(`${label} is required by the engineering workspace.`);
  return value;
}

function statusIcon(value: string | null): string {
  if (value === "PASS" || value === "CALCULATED") return "✓";
  if (value === "FAIL" || value === "KNOWN_NUMERICAL_FAILURE") return "×";
  if (value?.includes("REQUIRED") === true || value?.includes("REVIEW") === true) return "!";
  return "–";
}

function traceValue(value: JsonValue): string {
  if (value === null) return "—";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

function DecimalInput({ label, value, unit, onChange, readOnly = false }: {
  readonly label: string;
  readonly value: string;
  readonly unit?: string | undefined;
  readonly onChange: (value: string) => void;
  readonly readOnly?: boolean;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <label className="field-control">
      <span>{label}</span>
      <span className="input-with-unit">
        <input
          aria-label={label}
          type="text"
          inputMode="decimal"
          value={focused || value.trim() === "" ? value : formatEditableDecimal(value)}
          readOnly={readOnly}
          onFocus={() => { setFocused(true); }}
          onBlur={() => { setFocused(false); }}
          onChange={(event) => { onChange(event.currentTarget.value); }}
        />
        {unit === undefined ? null : <small>{unit}</small>}
      </span>
    </label>
  );
}

function ReadOnlyValue({ label, children }: { readonly label: string; readonly children: ReactNode }) {
  return (
    <div className="readonly-value">
      <span>{label}</span>
      <strong>{children}</strong>
    </div>
  );
}

function MaterialCard({ request }: { readonly request: SingleBoltEvaluationRequest }) {
  const material = requiredAt(request.material_snapshots, 0, "ICE material snapshot");
  const labels: Readonly<Record<string, string>> = {
    FT_L: "Ft,L",
    FT_T: "Ft,T",
    FBR_L: "Fbr,L",
    FBR_T: "Fbr,T",
    FSH_LT: "Fsh,LT",
  };
  return (
    <article className="source-card compact-source-card">
      <div className="card-title-row"><h4>{material.display_name}</h4><span className="locked-badge">Locked</span></div>
      <p><strong>Development only — Engineering Review Required.</strong></p>
      <dl className="property-list">
        {material.properties.filter((item) => labels[item.kind] !== undefined).map((item) => (
          <div key={item.kind}><dt>{labels[item.kind]}</dt><dd>{item.value.value} {item.value.unit}</dd></div>
        ))}
      </dl>
      <p className="qualification-note">The server selects direction from canonical material axes.</p>
    </article>
  );
}

function FastenerCard({ request }: { readonly request: SingleBoltEvaluationRequest }) {
  const fastener = request.fastener_snapshot;
  return (
    <article className="source-card compact-source-card">
      <div className="card-title-row"><h4>316/316L stainless fastener</h4><span className="locked-badge">Locked</span></div>
      <p>{fastener.bolt_specification} · {fastener.alloy_group}</p>
      <p>{fastener.nut_specification} nut · {fastener.washer_material_basis}</p>
      <p className="source-pending"><span aria-hidden="true">!</span> Fnt source pending; no generic value is substituted.</p>
    </article>
  );
}

function resultHeadline(response: SingleBoltEvaluationResponse): string {
  if (response.aggregate_status === "INVALID_GEOMETRY") {
    return "Invalid geometry";
  }
  if (response.results.some((value) => value.numerical_comparison === "FAIL")) {
    return "Known numerical failure";
  }
  if (response.aggregate_status === "SECTION_2_3_2_QUALIFICATION_REQUIRED") {
    return "Section 2.3.2 Qualification Required.";
  }
  if (response.qualification_flags.includes("ENGINEERING_REVIEW_REQUIRED")) {
    return "Engineering review required";
  }
  return friendlyEnum(response.aggregate_status);
}

function ResultSummary({ response }: { readonly response: SingleBoltEvaluationResponse }) {
  const qualification = response.aggregate_status === "SECTION_2_3_2_QUALIFICATION_REQUIRED";
  const governing = response.results.find((value) => response.governing_check_ids.includes(value.plan.check_id));
  return (
    <section className="result-summary" aria-labelledby="result-summary-title">
      <div className="summary-status">
        <span className="large-status-icon" aria-hidden="true">{statusIcon(response.aggregate_status)}</span>
        <div><p className="eyebrow">Aggregate engineering status</p><h3 id="result-summary-title">{resultHeadline(response)}</h3></div>
      </div>
      <div className="compact-result-facts">
        <span><strong>Governing:</strong> {governing === undefined ? "None returned" : `${friendlyIdentifier(governing.plan.component_id)} · ${friendlyEnum(governing.plan.limit_state)}`}</span>
        <span><strong>Utilization:</strong> {formatUtilization(governing?.utilization ?? null)}</span>
        <span><strong>Units:</strong> {response.unit_system}</span>
      </div>
      {qualification ? <p className="qualification-banner"><span aria-hidden="true">!</span> This is not an ordinary whole-joint PASS. Whole-connection qualification remains required.</p> : null}
    </section>
  );
}

function CheckDetails({ result }: { readonly result: CalculationResultDTO }) {
  const trace = result.equation_trace;
  const factorTrace = trace?.factor_trace as Record<string, JsonValue> | undefined;
  const fields: [string, JsonValue][] = [
    ["Exact demand", exactQuantity(result.demand)],
    ["Exact nominal resistance", exactQuantity(result.nominal_resistance)],
    ["Exact design resistance", exactQuantity(result.design_resistance)],
    ["Exact utilization", result.utilization],
    ["CM / CT / CCH and property", trace?.bearing_property ?? trace?.property_trace ?? null],
    ["C_delta", factorTrace?.c_delta ?? null],
    ["C_lap", factorTrace?.c_lap ?? null],
    ["phi", factorTrace?.phi ?? null],
    ["lambda", factorTrace?.lambda_factor ?? null],
    ["Intermediates", trace ?? null],
    ["Internal check ID", result.plan.check_id],
    ["Internal component ID", result.plan.component_id],
    ["Internal layer ID", result.plan.layer_id],
    ["Equation ID", result.plan.source_equation],
    ["Section / source", result.plan.source_section],
    ["Warnings", result.warnings],
  ];
  return (
    <details className="check-details">
      <summary>Details and exact values</summary>
      <dl>{fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd><pre>{traceValue(value)}</pre></dd></div>)}</dl>
    </details>
  );
}

function ResultTable({ response }: { readonly response: SingleBoltEvaluationResponse }) {
  return (
    <section className="results-panel" aria-labelledby="result-table-title">
      <div className="panel-heading"><div><p className="eyebrow">Server-authoritative check set</p><h3 id="result-table-title">Calculation checks</h3></div></div>
      <div className="table-scroll compact-results-table">
        <table>
          <thead><tr><th>Component</th><th>Limit state</th><th>Status</th><th>Demand</th><th>Design resistance</th><th>Utilization</th><th>Source / details</th></tr></thead>
          <tbody>
            {response.results.map((result) => (
              <tr key={result.plan.check_id}>
                <td>{friendlyIdentifier(result.plan.component_id)}<br /><small>{friendlyIdentifier(result.plan.layer_id)}</small></td>
                <td>{friendlyEnum(result.plan.limit_state)}</td>
                <td><span aria-hidden="true">{statusIcon(result.numerical_comparison === "NOT_EVALUATED" ? result.availability : result.numerical_comparison)}</span> {friendlyEnum(result.numerical_comparison === "NOT_EVALUATED" ? result.availability : result.numerical_comparison)}</td>
                <td>{formatQuantity(result.demand)}</td>
                <td>{formatQuantity(result.design_resistance)}</td>
                <td>{formatUtilization(result.utilization)}</td>
                <td>{result.plan.source_section}{result.plan.source_equation === null ? "" : ` · ${result.plan.source_equation}`}<CheckDetails result={result} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {response.issues.length === 0 ? null : (
        <div className="issue-list" role="status"><h4>Engineering issues and limits</h4><ul>{response.issues.map((issue) => <li key={`${issue.code}:${issue.identities.join(":")}`}><strong>{friendlyEnum(issue.code)}:</strong> {issue.message}</li>)}</ul></div>
      )}
    </section>
  );
}

function MultirowCheckDetails({ result }: { readonly result: MultiRowCheckResult }) {
  return (
    <details className="check-details">
      <summary>Details and exact values</summary>
      <pre>{JSON.stringify({
        row_id: result.row_id,
        bolt_line_id: result.bolt_line_id,
        bolt_id: result.bolt_id,
        layer_id: result.layer_id,
        path_id: result.path_id,
        demand: result.demand,
        design_resistance: result.design_resistance,
        method: result.equation_method,
        factor_trace: result.factor_trace,
        equation_trace: result.equation_trace,
        source: result.source_locator,
      }, null, 2)}</pre>
    </details>
  );
}

function MultirowResults({
  result,
  displayUnitSystem,
}: {
  readonly result: MultiRowCalculationResult;
  readonly displayUnitSystem: "US_CUSTOMARY" | "SI";
}) {
  const qualificationRequired =
    result.qualification.includes("QUALIFICATION_REQUIRED") ||
    result.method_applicability.includes("OUTSIDE_PRESCRIPTIVE_SCOPE");
  return (
    <>
      <section className="result-summary" aria-labelledby="multirow-result-summary-title">
        <div className="summary-status"><span className="large-status-icon" aria-hidden="true">{statusIcon(result.numerical_comparison)}</span><div><p className="eyebrow">Aggregate multi-row engineering status</p><h3 id="multirow-result-summary-title">{friendlyEnum(result.overall_disposition)}</h3></div></div>
        <div className="compact-result-facts"><span><strong>Comparison:</strong> {friendlyEnum(result.numerical_comparison)}</span><span><strong>Applicability:</strong> {friendlyEnum(result.method_applicability)}</span><span><strong>Governing:</strong> {result.governing_result_ids.map(friendlyIdentifier).join(", ") || "None"}</span></div>
        {qualificationRequired ? <p className="qualification-banner"><span aria-hidden="true">!</span> This arrangement is not an ordinary prescriptive PASS. Section 2.3.2 qualification remains required.</p> : null}
      </section>
      <section className="results-panel" aria-labelledby="multirow-checks-title">
        <div className="panel-heading"><div><p className="eyebrow">Server-authoritative multi-row check set</p><h3 id="multirow-checks-title">Calculation checks</h3></div></div>
        <div className="table-scroll compact-results-table"><table><thead><tr><th>Check</th><th>Critical identity</th><th>Status</th><th>Demand</th><th>Design resistance</th><th>Utilization</th><th>Trace</th></tr></thead><tbody>{result.results.map((check) => <tr key={check.result_id}><td>{friendlyEnum(check.limit_state)}</td><td>{[check.layer_id, check.bolt_id, check.row_id, check.bolt_line_id, check.path_id].filter((value): value is string => value !== null).map(friendlyIdentifier).join(" · ") || "Connection"}</td><td>{friendlyEnum(check.numerical_comparison === "NOT_EVALUATED" ? check.availability : check.numerical_comparison)}</td><td>{formatQuantity(check.demand)}</td><td>{formatQuantity(check.design_resistance)}</td><td>{formatUtilization(check.utilization)}</td><td><MultirowCheckDetails result={check} /></td></tr>)}</tbody></table></div>
        <dl className="diagnostic-list"><div><dt>Input fingerprint</dt><dd>{result.input_fingerprint}</dd></div><div><dt>Result fingerprint</dt><dd>{result.result_fingerprint}</dd></div><div><dt>Display units</dt><dd>{displayUnitSystem}</dd></div></dl>
      </section>
    </>
  );
}

function eccentricLineStatus(line: EccentricGroupModeLineResult): string {
  if (line.handoff_status === "NOT_REQUIRED_ZERO_LINE_DEMAND") {
    return "Not required — zero line demand";
  }
  if (line.handoff_status === "NOT_REQUIRED_PARENT_EXEMPTION") {
    return "Not required — parent exemption";
  }
  if (line.handoff_status === "INHERITED_LEGACY_STAGE_2_4B") {
    return line.shear_out_result === null
      ? "Inherited legacy Stage 2.4B"
      : friendlyEnum(
          line.shear_out_result.numerical_comparison === "NOT_EVALUATED"
            ? line.shear_out_result.availability
            : line.shear_out_result.numerical_comparison,
        );
  }
  if (line.handoff_status === "CALCULATION_NOT_SUPPORTED") {
    return line.warnings[0] === undefined
      ? "Calculation not supported"
      : friendlyEnum(line.warnings[0].code);
  }
  return line.shear_out_result === null
    ? "Calculation not supported"
    : friendlyEnum(
        line.shear_out_result.numerical_comparison === "NOT_EVALUATED"
          ? line.shear_out_result.availability
          : line.shear_out_result.numerical_comparison,
      );
}

function EccentricGroupModeResults({
  integration,
  displayUnitSystem,
}: {
  readonly integration: AutomaticGroupModeIntegrationResult;
  readonly displayUnitSystem: "US_CUSTOMARY" | "SI";
}) {
  return (
    <section className="results-panel" aria-labelledby="eccentric-group-mode-title">
      <div className="panel-heading"><div><p className="eyebrow">Stage 2.6A backend-authoritative compatibility and resistance</p><h3 id="eccentric-group-mode-title">Eccentric group-mode checks</h3></div></div>
      {integration.scenario_results.map((scenario) => (
        <article className="group-mode-scenario" key={scenario.scenario_id}>
          <h4>{friendlyEnum(scenario.scenario_id)}</h4>
          <div className="table-scroll compact-results-table">
            <table>
              <thead><tr><th>Bolt line</th><th>Actual line resultant</th><th>Parallel / transverse</th><th>Status</th><th>Method / equation</th><th>Design resistance</th><th>Utilization</th></tr></thead>
              <tbody>{scenario.line_results.map((line) => {
                const resistance = line.shear_out_result;
                return <tr key={line.bolt_line_id}><td>{friendlyIdentifier(line.bolt_line_id)}<br /><small>{line.contributing_bolt_ids.map(friendlyIdentifier).join(" · ")}</small></td><td>u {formatDisplayQuantity(line.line_resultant.u, displayUnitSystem)}<br />v {formatDisplayQuantity(line.line_resultant.v, displayUnitSystem)}{line.required_line_demand === null ? null : <><br /><small>Authorized scalar {formatDisplayQuantity(line.required_line_demand, displayUnitSystem)}</small></>}</td><td>{formatDisplayQuantity(line.parallel_scalar, displayUnitSystem)}<br />{formatDisplayQuantity(line.transverse_scalar, displayUnitSystem)}</td><td><strong>{eccentricLineStatus(line)}</strong>{line.warnings.map((warning) => <small className="group-mode-warning" key={`${line.bolt_line_id}:${warning.code}`}>{friendlyEnum(warning.code)}{warning.trace.length === 0 ? "" : ` — ${warning.trace.join(", ")}`}</small>)}</td><td>{friendlyEnum(line.method_id)}{resistance === null ? null : <><br /><small>{friendlyEnum(resistance.equation_method)} · {resistance.source_locator}</small></>}</td><td>{formatDisplayQuantity(resistance?.design_resistance ?? null, displayUnitSystem)}</td><td>{formatUtilization(resistance?.utilization ?? null)}</td></tr>;
              })}</tbody>
            </table>
          </div>
          <div className="first-row-compatibility">
            <h4>First-row net-tension compatibility</h4>
            <p><strong>{friendlyEnum(scenario.first_row_compatibility.status)}</strong></p>
            {scenario.first_row_compatibility.status === "CALCULATION_NOT_SUPPORTED" ? <p className="unsupported-note"><span aria-hidden="true">!</span> Eccentric first-row net tension is not supported by the current RC1 mechanics. No PASS or utilization is assigned.</p> : null}
            {scenario.first_row_compatibility.required_check_ids.length === 0 ? null : <p>Required checks: {scenario.first_row_compatibility.required_check_ids.map(friendlyIdentifier).join(", ")}</p>}
            {scenario.first_row_compatibility.warnings.map((warning) => <p className="unsupported-note" key={`${scenario.scenario_id}:${warning.code}`}><span aria-hidden="true">!</span> {friendlyEnum(warning.code)}{warning.trace.length === 0 ? "" : ` — ${warning.trace.join(", ")}`}</p>)}
          </div>
          <dl className="diagnostic-list"><div><dt>Stage 2.6A input fingerprint</dt><dd>{scenario.input_fingerprint}</dd></div><div><dt>Stage 2.6A result fingerprint</dt><dd>{scenario.result_fingerprint}</dd></div><div><dt>Trace layers</dt><dd>{scenario.trace_stages.join(" → ")} → APPLICATION_INTEGRATION</dd></div></dl>
        </article>
      ))}
    </section>
  );
}

function AutomaticMultirowResults({
  handoff,
  integration,
  demandFingerprint,
  displayUnitSystem,
}: {
  readonly handoff: AutomaticHandoffResult;
  readonly integration: AutomaticGroupModeIntegrationResult;
  readonly demandFingerprint: string;
  readonly displayUnitSystem: "US_CUSTOMARY" | "SI";
}) {
  const legacyOnly = integration.scenario_results.every((scenario) =>
    scenario.first_row_compatibility.status !== "CALCULATION_NOT_SUPPORTED" &&
    scenario.line_results.every((line) =>
      line.handoff_status === "INHERITED_LEGACY_STAGE_2_4B" ||
      line.handoff_status === "NOT_REQUIRED_PARENT_EXEMPTION"
    )
  );
  const overallDisposition = legacyOnly
    ? handoff.overall_disposition
    : integration.overall_disposition;
  const numericalComparison = legacyOnly
    ? handoff.numerical_comparison
    : integration.numerical_comparison;
  const qualification = legacyOnly ? handoff.qualification : integration.qualification;
  const governing = legacyOnly
    ? handoff.governing_supported_check_ids
    : integration.governing_supported_check_ids;
  const limitations = [
    ...(legacyOnly
      ? handoff.unsupported_required_check_ids
      : integration.unsupported_required_check_ids
    ).map((value) => `Unsupported: ${friendlyIdentifier(value)}`),
    ...(legacyOnly
      ? handoff.incomplete_required_check_ids
      : integration.incomplete_required_check_ids
    ).map((value) => `Incomplete: ${friendlyIdentifier(value)}`),
  ];
  return (
    <>
      <section className="result-summary" aria-labelledby="automatic-result-summary-title">
        <div className="summary-status"><span className="large-status-icon" aria-hidden="true">{statusIcon(numericalComparison)}</span><div><p className="eyebrow">Automatic member-end-force demand</p><h3 id="automatic-result-summary-title">{friendlyEnum(overallDisposition)}</h3></div></div>
        <div className="compact-result-facts"><span><strong>Method:</strong> Rational elastic bolt-group eccentricity</span><span><strong>Handoff coverage:</strong> {friendlyEnum(handoff.coverage)}</span><span><strong>Comparison:</strong> {friendlyEnum(numericalComparison)}</span><span><strong>Qualification:</strong> {friendlyEnum(qualification)}</span><span><strong>Governing supported:</strong> {governing.map(friendlyIdentifier).join(", ") || "None"}</span></div>
        {limitations.length === 0 ? null : <div className="qualification-banner"><span aria-hidden="true">!</span> Ordinary whole-connection PASS is prohibited while required checks remain unsupported or incomplete.<ul>{limitations.map((value) => <li key={value}>{value}</li>)}</ul></div>}
        {handoff.parent_action_transfer_warnings.map((warning) => <p className="unsupported-note" key={warning.code}><span aria-hidden="true">!</span> {friendlyEnum(warning.code)}{warning.trace.length === 0 ? "" : ` — ${warning.trace.join(", ")}`}</p>)}
      </section>
      <section className="results-panel" aria-labelledby="automatic-checks-title">
        <div className="panel-heading"><div><p className="eyebrow">Stage 2.5B supported resistance handoff</p><h3 id="automatic-checks-title">Calculated supported checks</h3></div></div>
        <div className="table-scroll compact-results-table"><table><thead><tr><th>Check</th><th>Critical identity</th><th>Status</th><th>Demand</th><th>Design resistance</th><th>Utilization</th><th>Trace</th></tr></thead><tbody>{handoff.supported_results.map((check) => <tr key={check.result_id}><td>{friendlyEnum(check.limit_state)}</td><td>{[check.layer_id, check.bolt_id, check.row_id, check.bolt_line_id, check.path_id].filter((value): value is string => value !== null).map(friendlyIdentifier).join(" · ") || "Connection"}</td><td>{friendlyEnum(check.numerical_comparison === "NOT_EVALUATED" ? check.availability : check.numerical_comparison)}</td><td>{formatQuantity(check.demand)}</td><td>{formatQuantity(check.design_resistance)}</td><td>{formatUtilization(check.utilization)}</td><td><MultirowCheckDetails result={check} /></td></tr>)}</tbody></table></div>
        <dl className="diagnostic-list"><div><dt>Demand fingerprint</dt><dd>{demandFingerprint}</dd></div><div><dt>Handoff fingerprint</dt><dd>{handoff.result_fingerprint}</dd></div><div><dt>Group-mode integration fingerprint</dt><dd>{integration.result_fingerprint}</dd></div><div><dt>Display units</dt><dd>{displayUnitSystem}</dd></div></dl>
      </section>
      {legacyOnly ? null : <EccentricGroupModeResults integration={integration} displayUnitSystem={displayUnitSystem} />}
    </>
  );
}

function sectionValue(section: MemberSectionDTO, name: SectionQuantityName): string {
  return requiredValue(section[name], `Section property ${name}`).value;
}

function previewValidationMessage(
  request: SingleBoltEvaluationRequest,
  viewExtents: ConnectionViewExtentsDTO,
): string | null {
  const template = requiredValue(request.geometry_template, "Template geometry");
  const angle = Number(template.brace_to_column_directed_angle_deg);
  if (template.brace_to_column_directed_angle_deg.trim() === "" || !Number.isFinite(angle) || angle <= 0 || angle >= 180) {
    return "Directed brace-to-column angle must be between 0 and 180 degrees.";
  }
  const positiveQuantities = [
    ["Bolt-to-brace-end distance e1", template.bolt_to_brace_end_distance],
    ["Column view extent below connection", viewExtents.column_view_extent_below],
    ["Column view extent above connection", viewExtents.column_view_extent_above],
    ["Brace view length", viewExtents.brace_view_length],
    ["Standard hole display", template.hole_diameter],
    ["Bolt diameter", request.bolt_diameter],
    ["Washer outside diameter", requiredValue(request.fastener_snapshot.washer_geometry, "Washer geometry").outside_diameter],
    ["Washer thickness", requiredValue(request.fastener_snapshot.washer_geometry, "Washer geometry").thickness],
    ...request.joint_assembly.members.flatMap((member) =>
      Object.entries(member.section)
        .filter((entry): entry is [string, { value: string; unit: string }] =>
          typeof entry[1] === "object" && entry[1] !== null && "value" in entry[1],
        )
        .map(([name, quantity]) => [`${member.label} ${name}`, quantity] as const),
    ),
  ] as const;
  for (const [label, quantity] of positiveQuantities) {
    const value = Number(quantity.value);
    if (quantity.value.trim() === "" || !Number.isFinite(value) || value <= 0) return `${label} must be greater than zero.`;
  }
  const action = requiredAt(request.joint_assembly.member_end_actions, 0, "Member-end action");
  const signedValues = [
    action.force.x,
    action.force.y,
    action.force.z,
    action.moment.x,
    action.moment.y,
    action.moment.z,
    ...(request.explicit_resolved_demand === null
      ? []
      : [
          request.explicit_resolved_demand.in_plane_force_vector.x,
          request.explicit_resolved_demand.in_plane_force_vector.y,
          request.explicit_resolved_demand.in_plane_force_vector.z,
          request.explicit_resolved_demand.bolt_axis_tensile_demand.value,
          request.explicit_resolved_demand.externally_supplied_prying_demand.value,
        ]),
  ];
  if (signedValues.some((value) => value.trim() === "" || !Number.isFinite(Number(value)))) {
    return "Action and resolved-demand values must be complete finite decimals.";
  }
  return null;
}

function designValidationMessage(request: SingleBoltEvaluationRequest): string | null {
  if (request.time_effect_category === "") return "Select a time-effect category.";
  if ([request.end_use_factors.cm, request.end_use_factors.ct, request.end_use_factors.cch]
    .some((value) => value.trim() === "" || !Number.isFinite(Number(value)))) {
    return "Select finite CM, CT, and CCH factors.";
  }
  return null;
}

function sourceLengthUnit(request: SingleBoltEvaluationRequest): "in" | "mm" {
  const unit = request.bolt_diameter.unit;
  /* v8 ignore next 3 -- strict workspace DTOs make any other geometry unit an invariant violation */
  if (unit !== "in" && unit !== "mm") {
    throw new Error("The unified connection workspace requires in or mm geometry.");
  }
  return unit;
}

function buildMultirowRequest(
  request: SingleBoltEvaluationRequest,
  viewExtents: ConnectionViewExtentsDTO,
  group: BoltGroupState,
  demandMode: DemandMode,
): MultiRowConnectionRequest {
  const lengthUnit = sourceLengthUnit(request);
  const brace = requiredAt(request.joint_assembly.members, 0, "Brace member");
  const assignment = requiredAt(request.material_assignments, 0, "FRP material assignment");
  const geometryTemplate = requiredValue(request.geometry_template, "Template geometry");
  const action = requiredAt(request.joint_assembly.member_end_actions, 0, "Member-end action");
  const explicit = request.explicit_resolved_demand;
  const physicalSource = structuredClone(request);
  if (demandMode === "AUTOMATIC_MEMBER_END_FORCE") {
    physicalSource.explicit_resolved_demand = null;
  }
  const engineerDefined =
    group.distribution === "FRACTIONS" || group.distribution === "DIRECT_ROW_FORCES";
  return {
    orchestration_contract_version: "2.5C-RC1",
    request_id: `${request.calculation_id}-MULTIROW`,
    connection_id: request.joint_assembly.id,
    interface_id: request.interface_id,
    load_combination_id: request.load_combination_id,
    source_reference: "Unified connection workspace input",
    display_unit_system: request.joint_assembly.unit_system,
    source_length_unit: lengthUnit,
    row_count: group.rowCount,
    bolts_per_row: group.boltsPerRow,
    bolt_diameter: request.bolt_diameter,
    hole_basis: request.published_code_unit_basis as MultiRowConnectionRequest["hole_basis"],
    pitch: multirowQuantity(group.pitch, lengthUnit),
    gauge: multirowQuantity(group.gauge, lengthUnit),
    unloaded_end_e1: geometryTemplate.bolt_to_brace_end_distance,
    loaded_boundary_to_row_1_distance: multirowQuantity(
      group.loadedBoundaryToRow1,
      lengthUnit,
    ),
    negative_side_distance: multirowQuantity(group.negativeSideDistance, lengthUnit),
    positive_side_distance: multirowQuantity(group.positiveSideDistance, lengthUnit),
    geometry_tolerance: multirowQuantity(lengthUnit === "in" ? "0.000001" : "0.0000254", lengthUnit),
    material_pair: group.materialPair,
    layers: [{
      layer_id: "layer-A",
      component_id: brace.id,
      material_id: "ICE_LOCKED_PULTRUDED_FRP",
      thickness: requiredValue(brace.section.thickness, "Brace thickness"),
      element_classification: "SHAPE",
      material_axis_angle_degrees: group.materialAxisAngleDegrees,
      end_use_factors: request.end_use_factors,
      bearing_thread_status: assignment.bearing_thread_status as
        MultiRowConnectionRequest["layers"][number]["bearing_thread_status"],
    }],
    demand_source: demandMode,
    ...(demandMode === "AUTOMATIC_MEMBER_END_FORCE"
      ? { automatic_action_source_id: action.id }
      : explicit === null
      ? {}
      : {
          signed_force_x: multirowQuantity(
            explicit.in_plane_force_vector.x,
            explicit.in_plane_force_vector.unit,
          ),
          signed_force_y: multirowQuantity(
            explicit.in_plane_force_vector.y,
            explicit.in_plane_force_vector.unit,
          ),
          force_reference: explicit.source_reference_point_id,
        }),
    row_distribution_basis: engineerDefined
      ? "ENGINEER_DEFINED_ROW_DISTRIBUTION"
      : group.distribution,
    engineer_distribution_kind: engineerDefined ? group.distribution : null,
    engineer_allocations: engineerDefined ? group.engineerAllocations : [],
    provenance: {
      source_method: demandMode === "AUTOMATIC_MEMBER_END_FORCE"
        ? "STAGE_2_4A_APPROVED_DIRECT_ROW_DISTRIBUTION"
        : "EXTERNALLY_RESOLVED_CONNECTION_DEMAND",
      source_document_or_calculation: group.sourceCalculation,
      revision: "1",
      load_combination: request.load_combination_id,
      reference_point: demandMode === "AUTOMATIC_MEMBER_END_FORCE"
        ? `${action.reference_point.kind}:${action.reference_point.owner_id ?? action.id}`
        : explicit?.source_reference_point_id ?? null,
      clearance_or_contact_modeled: true,
      engineer_confirmed: engineerDefined,
    },
    bolt_axis_tension_required: group.boltAxisTensionRequired,
    bolt_axis_tensions: group.boltAxisTensionRequired ? group.boltAxisTensions : [],
    time_effect_category: request.time_effect_category === "OTHER"
      ? "OTHER_LIVE"
      : request.time_effect_category,
    lap_configuration: request.lap_configuration as "DOUBLE_LAP" | "SINGLE_LAP",
    first_row_method: group.firstRowMethod,
    prescribed_lbr: group.prescribedLbr,
    force_line_offset: multirowQuantity(group.forceLineOffset, lengthUnit),
    eccentricity_tolerance: multirowQuantity(
      lengthUnit === "in" ? "0.000001" : "0.0000254",
      lengthUnit,
    ),
    physical_connection: buildSingleBoltPreviewRequest(physicalSource, viewExtents),
  };
}

function multirowValidationMessage(
  request: SingleBoltEvaluationRequest,
  group: BoltGroupState,
  demandMode: DemandMode,
): string | null {
  if (group.rowCount === 1) {
    return group.boltsPerRow === 1
      ? "The accepted single-bolt route is active."
      : "One row with multiple bolts is not supported by the accepted calculation methods.";
  }
  if (!Number.isInteger(group.rowCount) || group.rowCount < 2) {
    return "Row count must be a positive integer.";
  }
  if (!Number.isInteger(group.boltsPerRow) || group.boltsPerRow < 1) {
    return "Bolts per row must be a positive integer.";
  }
  const positive = [
    group.pitch,
    group.gauge,
    group.loadedBoundaryToRow1,
    group.negativeSideDistance,
    group.positiveSideDistance,
    requiredValue(request.geometry_template, "Template geometry").bolt_to_brace_end_distance.value,
  ];
  if (positive.some((value) => !Number.isFinite(Number(value)) || Number(value) <= 0)) {
    return "Bolt-group dimensions must be finite and greater than zero.";
  }
  if (demandMode === "AUTOMATIC_MEMBER_END_FORCE") {
    const action = requiredAt(request.joint_assembly.member_end_actions, 0, "Member-end action");
    const values = [
      action.force.x, action.force.y, action.force.z,
      action.moment.x, action.moment.y, action.moment.z,
    ];
    return values.some((value) => value.trim() === "" || !Number.isFinite(Number(value)))
      ? "Automatic member-end actions must be complete finite decimals."
      : null;
  }
  if (request.explicit_resolved_demand === null) {
    return "Explicit externally resolved connection demand is required for multi-row design.";
  }
  const demand = request.explicit_resolved_demand.in_plane_force_vector;
  const forces = [Number(demand.x), Number(demand.y)];
  if (forces.some((value) => !Number.isFinite(value)) || forces.every((value) => value === 0)) {
    return "The signed externally resolved connection demand must be finite and nonzero.";
  }
  if ([request.end_use_factors.cm, request.end_use_factors.ct, request.end_use_factors.cch]
    .some((value) => value.trim() === "" || !Number.isFinite(Number(value)))) {
    return "Select finite CM, CT, and CCH factors before multi-row preview.";
  }
  return null;
}

export function SingleBoltEngineeringWorkspace() {
  const [request, setRequest] = useState<SingleBoltEvaluationRequest>(initialRequest);
  const requestRef = useRef(request);
  const [viewExtents, setViewExtents] = useState<ConnectionViewExtentsDTO>(() =>
    loadJ1ViewExtents("US_CUSTOMARY"),
  );
  const viewExtentsRef = useRef(viewExtents);
  const engineeringRevisionRef = useRef(0);
  const previewRevisionRef = useRef(0);
  const [previewInput, setPreviewInput] = useState<CanonicalPreviewInput>(() => {
    const initial = initialRequest();
    const initialViewExtents = loadJ1ViewExtents("US_CUSTOMARY");
    return {
      request: initial,
      viewExtents: initialViewExtents,
      revision: 0,
      scheduling: "IMMEDIATE",
      validationMessage: previewValidationMessage(initial, initialViewExtents),
    };
  });
  const [caseLabel, setCaseLabel] = useState("");
  const [demandMode, setDemandMode] = useState<DemandMode>(
    "EXPLICIT_RESOLVED_CONNECTION_DEMAND",
  );
  const [groupState, setGroupState] = useState<BoltGroupState>(() =>
    initialBoltGroupState("US_CUSTOMARY"),
  );
  const groupStateRef = useRef(groupState);
  const [multirowRevision, setMultirowRevision] = useState(0);
  const [response, setResponse] = useState<SingleBoltEvaluationResponse | null>(null);
  const [multirowDesign, setMultirowDesign] = useState<MultiRowDesignResponse | null>(null);
  const [error, setError] = useState<EvaluationTransportError | null>(null);
  const [multirowDesignError, setMultirowDesignError] =
    useState<EvaluationTransportError | null>(null);
  const [loading, setLoading] = useState(false);
  const [edited, setEdited] = useState(false);
  const [stale, setStale] = useState(false);
  const [resultsOpen, setResultsOpen] = useState(false);
  const [selection, setSelection] = useState<SceneSelection>({ kind: "MEMBER", id: "member-a" });
  const designAbortController = useRef<AbortController | null>(null);
  const preview = useCanonicalPreview(previewInput);
  const multirowRequest = useMemo(
    () => buildMultirowRequest(request, viewExtents, groupState, demandMode),
    [demandMode, groupState, request, viewExtents],
  );
  const multirowPreviewInput = useMemo(() => ({
    request: multirowRequest,
    revision: multirowRevision,
    immediate: false,
    validationMessage: multirowValidationMessage(request, groupState, demandMode),
  }), [demandMode, groupState, multirowRequest, multirowRevision, request]);
  const multirowPreview = useMultiRowPreview(multirowPreviewInput);
  const singleArrangement = groupState.rowCount === 1 && groupState.boltsPerRow === 1;
  const supportedMultirowArrangement = groupState.rowCount >= 2;
  const canonicalModel = useMemo(() => {
    if (supportedMultirowArrangement) {
      const multirowVisualization = multirowPreview.response?.visualization;
      return multirowVisualization === null || multirowVisualization === undefined
        ? null
        : buildMultiRowSceneModel(multirowVisualization);
    }
    const previewResponse = preview.response;
    const visualization = previewResponse?.visualization;
    return visualization === null || visualization === undefined
      ? null
      : buildSingleBoltSceneModel(visualization);
  }, [multirowPreview.response, preview.response, supportedMultirowArrangement]);
  const brace = requiredAt(request.joint_assembly.members, 0, "Brace member");
  const support = requiredAt(request.joint_assembly.members, 1, "Support member");
  const action = requiredAt(request.joint_assembly.member_end_actions, 0, "Member-end action");
  const geometryTemplate = requiredValue(request.geometry_template, "Template geometry");
  const shearPlaneStatus = requiredAt(request.fastener_snapshot.shear_plane_thread_statuses, 0, "Shear-plane thread status");
  const washerGeometry = requiredValue(request.fastener_snapshot.washer_geometry, "Washer geometry");
  const lengthUnit = request.bolt_diameter.unit;
  const resolvedMultirowHole = multirowPreview.response?.visualization?.bolts[0]?.hole_diameter ?? null;
  const materialRelationship = (() => {
    if (preview.response === null) return "Awaiting server preview";
    const mapping = preview.response.material_relationships.find((value) => value.layer_id === "layer-B");
    const angle = mapping?.theta_degrees ?? null;
    const direction = mapping?.direction_family ?? null;
    if (angle === null) return "Server returned no resolved angle";
    return `${formatDecimal(angle, 1)}°${direction === null ? "" : ` · ${friendlyEnum(direction)}`}`;
  })();

  const updateRequest = (
    change: (next: SingleBoltEvaluationRequest) => void,
    classification: EngineeringInputClassification = INPUT_CLASSIFICATION.geometry,
    scheduling: PreviewScheduling = "DEBOUNCED",
  ) => {
    const next = structuredClone(requestRef.current);
    change(next);
    requestRef.current = next;
    setRequest(next);
    setEdited(true);
    setError(null);
    setMultirowDesignError(null);
    /* v8 ignore next -- every request mutation in this workspace is deliberately engineering-classified */
    if (
      classification === "PREVIEW_AFFECTING_ENGINEERING_INPUT" ||
      classification === "DESIGN_ONLY_ENGINEERING_INPUT"
    ) {
      engineeringRevisionRef.current += 1;
      designAbortController.current?.abort();
      setMultirowRevision((value) => value + 1);
      if (response !== null || multirowDesign !== null) setStale(true);
    }
    if (classification === "PREVIEW_AFFECTING_ENGINEERING_INPUT") {
      previewRevisionRef.current += 1;
      setPreviewInput({
        request: next,
        viewExtents: viewExtentsRef.current,
        revision: previewRevisionRef.current,
        scheduling: requirePreviewScheduling(scheduling),
        validationMessage: previewValidationMessage(next, viewExtentsRef.current),
      });
    }
  };

  const updateViewExtent = (
    name: keyof ConnectionViewExtentsDTO,
    value: string,
  ) => {
    const next = structuredClone(viewExtentsRef.current);
    next[name].value = value;
    viewExtentsRef.current = next;
    setViewExtents(next);
    setEdited(true);
    setError(null);
    setMultirowRevision((current) => current + 1);
    previewRevisionRef.current += 1;
    setPreviewInput({
      request: requestRef.current,
      viewExtents: next,
      revision: previewRevisionRef.current,
      scheduling: "DEBOUNCED",
      validationMessage: previewValidationMessage(requestRef.current, next),
    });
  };

  const loadBenchmark = (unitSystem: BenchmarkUnitSystem) => {
    const next = loadJ1Benchmark(unitSystem);
    const nextViewExtents = loadJ1ViewExtents(unitSystem);
    requestRef.current = next;
    viewExtentsRef.current = nextViewExtents;
    engineeringRevisionRef.current += 1;
    previewRevisionRef.current += 1;
    setRequest(next);
    setViewExtents(nextViewExtents);
    setPreviewInput({
      request: next,
      viewExtents: nextViewExtents,
      revision: previewRevisionRef.current,
      scheduling: "IMMEDIATE",
      validationMessage: previewValidationMessage(next, nextViewExtents),
    });
    setCaseLabel(unitSystem === "US_CUSTOMARY" ? "Verified J1 — U.S." : "Verified J1 — SI");
    setDemandMode("EXPLICIT_RESOLVED_CONNECTION_DEMAND");
    const nextGroup = initialBoltGroupState(unitSystem);
    groupStateRef.current = nextGroup;
    setGroupState(nextGroup);
    setMultirowRevision((value) => value + 1);
    setResponse(null); setMultirowDesign(null); setError(null); setMultirowDesignError(null);
    setLoading(false); setEdited(false); setStale(false); setResultsOpen(false);
    setSelection({ kind: "MEMBER", id: "member-a" });
  };

  const changeUnitSystem = (unitSystem: BenchmarkUnitSystem) => {
    if (unitSystem === request.joint_assembly.unit_system) return;
    const confirmed = !edited || window.confirm(`Changing unit systems resets every input to the verified J1 ${unitSystem === "SI" ? "SI" : "U.S."} profile. Continue?`);
    if (confirmed) loadBenchmark(unitSystem);
  };

  const setSectionQuantity = (memberIndex: number, name: SectionQuantityName, value: string) => {
    updateRequest((next) => { requiredValue(requiredAt(next.joint_assembly.members, memberIndex, "Edited member").section[name], `Section property ${name}`).value = value; });
  };
  const setActionValue = (kind: "force" | "moment", axis: "x" | "y" | "z", value: string) => {
    updateRequest(
      (next) => { requiredAt(next.joint_assembly.member_end_actions, 0, "Member-end action")[kind][axis] = value; },
      INPUT_CLASSIFICATION.memberAction,
    );
  };
  const setActionComponentValue = (
    component: ActionDirectionSnapshot["component"],
    value: string,
  ) => {
    const mapping = {
      FX: ["force", "x"],
      FY: ["force", "y"],
      FZ: ["force", "z"],
      MX: ["moment", "x"],
      MY: ["moment", "y"],
      MZ: ["moment", "z"],
    } as const;
    const [kind, axis] = mapping[component];
    setActionValue(kind, axis, value);
  };
  const appliedActionInputValues = {
    FX: action.force.x,
    FY: action.force.y,
    FZ: action.force.z,
    MX: action.moment.x,
    MY: action.moment.y,
    MZ: action.moment.z,
  } as const;
  const setDemandModeValue = (mode: DemandMode) => {
    setDemandMode(mode);
    updateRequest(
      () => { /* source selection is top-level integration state; engineering values are retained */ },
      INPUT_CLASSIFICATION.demandMode,
      "IMMEDIATE",
    );
  };

  const updateGroup = (
    change: Partial<BoltGroupState>,
    engineering = true,
  ) => {
    const next = { ...groupStateRef.current, ...change };
    groupStateRef.current = next;
    setGroupState(next);
    setEdited(true);
    setMultirowDesignError(null);
    if (engineering) {
      engineeringRevisionRef.current += 1;
      setMultirowRevision((value) => value + 1);
      designAbortController.current?.abort();
      if (response !== null || multirowDesign !== null) setStale(true);
    }
  };

  const setGroupCount = (field: "rowCount" | "boltsPerRow", raw: string) => {
    const value = Number(raw);
    let change: Partial<BoltGroupState> = { [field]: value };
    if (field === "rowCount" && (
      groupState.distribution === "FRACTIONS" ||
      groupState.distribution === "DIRECT_ROW_FORCES"
    )) {
      const count = Math.max(0, value);
      change = {
        ...change,
        engineerAllocations: Array.from({ length: count }, (_, index) => (
          groupState.distribution === "DIRECT_ROW_FORCES"
            ? {
                row_ordinal: index + 1,
                direct_force: multirowQuantity(
                  "0",
                  request.explicit_resolved_demand?.in_plane_force_vector.unit ?? action.force.unit,
                ),
              }
            : { row_ordinal: index + 1, fraction: String(1 / count) }
        )),
      };
    }
    updateGroup(change);
  };

  const setGroupDistribution = (distribution: GroupDistribution) => {
    const engineerDefined = distribution === "FRACTIONS" || distribution === "DIRECT_ROW_FORCES";
    const forceUnit = request.explicit_resolved_demand?.in_plane_force_vector.unit ?? action.force.unit;
    updateGroup({
      distribution,
      engineerAllocations: engineerDefined
        ? Array.from({ length: Math.max(groupState.rowCount, 0) }, (_, index) => (
            distribution === "DIRECT_ROW_FORCES"
              ? { row_ordinal: index + 1, direct_force: multirowQuantity("0", forceUnit) }
              : { row_ordinal: index + 1, fraction: String(1 / groupState.rowCount) }
          ))
        : [],
    });
  };

  const evaluate = async () => {
    const submittedRevision = engineeringRevisionRef.current;
    designAbortController.current?.abort();
    const controller = new AbortController();
    designAbortController.current = controller;
    setLoading(true); setError(null); setMultirowDesignError(null); setStale(false);
    try {
      if (supportedMultirowArrangement) {
        const result = await evaluateMultiRow(multirowRequest, controller.signal);
        if (submittedRevision !== engineeringRevisionRef.current) return;
        setMultirowDesign(result); setResultsOpen(true);
        return;
      }
      const result = await evaluateSingleBolt(requestRef.current, controller.signal);
      if (submittedRevision !== engineeringRevisionRef.current) return;
      setResponse(result); setResultsOpen(true);
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === "AbortError") return;
      if (submittedRevision !== engineeringRevisionRef.current) return;
      const resolved = caught instanceof EvaluationTransportError
        ? caught
        : new EvaluationTransportError(
            "RESPONSE",
            null,
            "Unexpected client response handling failure.",
            caught,
          );
      if (supportedMultirowArrangement) setMultirowDesignError(resolved);
      else setError(resolved);
    } finally { setLoading(false); }
  };

  const previewPending = supportedMultirowArrangement
    ? multirowPreview.state === "WAITING" || multirowPreview.state === "PREVIEWING"
    : preview.state === "WAITING" || preview.state === "PREVIEWING";
  const previewCurrent = preview.state === "CURRENT_VALID" &&
    preview.currentRevision === previewInput.revision;
  const localDesignBlocker = designValidationMessage(request);
  const multirowBlocker = multirowValidationMessage(request, groupState, demandMode);
  const designButtonBlocker = singleArrangement && demandMode === "AUTOMATIC_MEMBER_END_FORCE"
    ? "Automatic member-end-force demand is available for the accepted multi-row workflow."
    : !singleArrangement && !supportedMultirowArrangement
    ? "One row with multiple bolts is not supported by the accepted calculation methods."
    : supportedMultirowArrangement
      ? multirowBlocker ?? (previewPending
        ? "Updating the canonical multi-row model."
        : multirowPreview.state === "CURRENT_INVALID"
          ? "Invalid geometry must be corrected before design check."
          : multirowPreview.state !== "CURRENT_VALID"
            ? "A current canonical multi-row preview is required."
            : multirowPreview.response?.design_check_ready !== true
              ? "The backend has not marked this multi-row arrangement design-ready."
              : null)
      : previewPending
    ? "Updating the canonical model."
    : preview.state === "CURRENT_INVALID"
      ? "Invalid geometry must be corrected before design check."
      : preview.state === "CURRENT_INCOMPLETE"
        ? "Waiting for complete valid preview inputs."
        : preview.state === "PREVIEW_ERROR"
          ? "Preview unavailable — current inputs not validated."
          : !previewCurrent
            ? "A current canonical preview is required."
            : preview.response?.design_check_ready !== true
              ? requiredValue(preview.response, "Canonical preview response").design_check_blocking_reasons.join(", ")
              : localDesignBlocker;
  const orientation = supportedMultirowArrangement
    ? multirowPreview.response?.visualization?.physical_connection?.connection_orientation ?? null
    : preview.response?.visualization?.connection_orientation ?? null;
  const singleModelStatusLabel = previewPending
    ? "Updating model…"
    : preview.state === "CURRENT_VALID"
      ? "Valid geometry"
      : preview.state === "CURRENT_INVALID"
        ? "Invalid geometry"
        : preview.state === "CURRENT_INCOMPLETE"
          ? "Waiting for valid input"
          : preview.state === "PREVIEW_ERROR"
            ? "Preview unavailable"
            : "Awaiting preview";

  const modelStatusLabel = supportedMultirowArrangement
    ? previewPending
      ? "Updating multi-row model…"
      : multirowPreview.state === "CURRENT_VALID"
        ? "Valid multi-row geometry"
        : multirowPreview.state === "CURRENT_INVALID"
          ? "Invalid multi-row geometry"
          : multirowBlocker ?? "Awaiting multi-row preview"
    : singleModelStatusLabel;
  const multirowResult = multirowDesign?.calculation_result ?? null;
  const automaticHandoff = multirowDesign?.automatic_handoff_results[0] ?? null;
  const automaticGroupModeIntegration =
    multirowDesign?.automatic_group_mode_integration ?? null;
  const activeDesignSummary = supportedMultirowArrangement
    ? automaticGroupModeIntegration !== null
      ? friendlyEnum(automaticGroupModeIntegration.overall_disposition)
      : automaticHandoff !== null
      ? friendlyEnum(automaticHandoff.overall_disposition)
      : multirowResult === null
        ? "No design run"
        : friendlyEnum(multirowResult.overall_disposition)
    : response === null
      ? "No design run"
      : resultHeadline(response);
  const activePreviewError = supportedMultirowArrangement
    ? multirowPreview.error
    : preview.error;
  const activePreviewRetry = supportedMultirowArrangement
    ? multirowPreview.retry
    : preview.retry;
  const activeResults = singleArrangement && !stale && response !== null
    ? response.results
    : [];
  const activeResolvedLayers = singleArrangement
    ? preview.response?.resolved_layers ?? []
    : [];
  const selectedPhysicalBolt = selection.kind === "BOLT"
    ? multirowPreview.response?.visualization?.physical_bolts?.find(
        (bolt) => bolt.bolt_id === selection.id,
      ) ?? null
    : null;
  const multirowChecks = automaticHandoff?.supported_results ?? multirowResult?.results ?? [];
  const selectedBoltChecks = selectedPhysicalBolt === null || stale
    ? []
    : multirowChecks
        .filter((check) =>
          check.bolt_id === selectedPhysicalBolt.bolt_id ||
          check.row_id === selectedPhysicalBolt.row_id ||
          check.bolt_line_id === selectedPhysicalBolt.bolt_line_id,
        )
        .map((check) => ({
          id: check.result_id,
          label: friendlyEnum(check.limit_state),
          status: friendlyEnum(
            check.numerical_comparison === "NOT_EVALUATED"
              ? check.availability
              : check.numerical_comparison,
          ),
          demand: formatQuantity(check.demand),
          utilization: formatUtilization(check.utilization),
        }));

  return (
    <ConnectionWorkspaceShell family={singleArrangement ? "single-bolt" : "multi-row"} banner={<section className="workspace-banner" aria-labelledby="workspace-scope-title">
        <div><p className="eyebrow">Shear · Brace to column flange</p><h2 id="workspace-scope-title">Connection engineering workspace</h2></div>
        <div className="workspace-scope-chips"><span>One brace</span><span>{groupState.rowCount === 1 ? "One row" : `${String(groupState.rowCount)} rows`}</span><span>{singleArrangement ? "One selected bolt" : `${String(groupState.boltsPerRow)} bolt${groupState.boltsPerRow === 1 ? "" : "s"} per row`}</span><span>Session only</span></div>
      </section>}>
        <ConnectionWorkspaceSidebar ariaLabel="Connection properties">
          <SidebarGroup title="General / Case" summary={request.joint_assembly.unit_system} defaultOpen>
            <div className="benchmark-buttons"><button type="button" onClick={() => { loadBenchmark("US_CUSTOMARY"); }}>Load verified J1 — U.S.</button><button type="button" onClick={() => { loadBenchmark("SI"); }}>Load verified J1 — SI</button></div>
            <label className="field-control"><span>Case label</span><input type="text" value={caseLabel} placeholder="Project-facing label" onChange={(event) => { setCaseLabel(event.currentTarget.value); setEdited(true); }} /></label>
            <label className="field-control"><span>Unit system</span><select value={request.joint_assembly.unit_system} onChange={(event) => { changeUnitSystem(event.currentTarget.value as BenchmarkUnitSystem); }}><option value="US_CUSTOMARY">U.S. customary</option><option value="SI">SI</option></select></label>
            <ReadOnlyValue label="Storage">Session only · not saved</ReadOnlyValue>
          </SidebarGroup>

          <SidebarGroup title="Connection" summary={`${String(groupState.rowCount)} × ${String(groupState.boltsPerRow)} rectangular group`} defaultOpen>
            <ul className="classification-strip"><li>Brace to column flange</li><li>In-place rectangular bolt group</li><li>{request.lap_configuration === "SINGLE_LAP" ? "Single lap" : "Double lap"}</li></ul>
            <ReadOnlyValue label="Selected interface">Brace-to-column interface</ReadOnlyValue>
            <div className="field-grid arrangement-fields">
              <label className="field-control"><span>Row count</span><input aria-label="Row count" type="number" min="1" value={groupState.rowCount} onChange={(event) => { setGroupCount("rowCount", event.currentTarget.value); }} /></label>
              <label className="field-control"><span>Bolts per row</span><input aria-label="Bolts per row" type="number" min="1" value={groupState.boltsPerRow} onChange={(event) => { setGroupCount("boltsPerRow", event.currentTarget.value); }} /></label>
            </div>
            {groupState.rowCount === 1 && groupState.boltsPerRow > 1 ? <p className="unsupported-note"><span aria-hidden="true">!</span> One row with multiple bolts is visible as an unsupported arrangement. No accepted design method is assigned.</p> : null}
          </SidebarGroup>

          <SidebarGroup
            title="Members"
            summary="Angle + W column"
            defaultOpen
            selected={selection.kind === "MEMBER"}
            onSelect={() => { setSelection((current) => current.kind === "MEMBER" ? current : { kind: "MEMBER", id: "member-a" }); }}
          >
            <h4 className="sidebar-subheading">Angle brace</h4>
            <div className="field-grid"><DecimalInput label="Leg y" value={sectionValue(brace.section, "leg_y")} unit={lengthUnit} onChange={(value) => { setSectionQuantity(0, "leg_y", value); }} /><DecimalInput label="Leg z" value={sectionValue(brace.section, "leg_z")} unit={lengthUnit} onChange={(value) => { setSectionQuantity(0, "leg_z", value); }} /><DecimalInput label="Thickness" value={sectionValue(brace.section, "thickness")} unit={lengthUnit} onChange={(value) => { setSectionQuantity(0, "thickness", value); }} /></div>
            <h4 className="sidebar-subheading">W column</h4>
            <div className="field-grid"><DecimalInput label="d" value={sectionValue(support.section, "overall_depth")} unit={lengthUnit} onChange={(value) => { setSectionQuantity(1, "overall_depth", value); }} /><DecimalInput label="bf" value={sectionValue(support.section, "flange_width")} unit={lengthUnit} onChange={(value) => { setSectionQuantity(1, "flange_width", value); }} /><DecimalInput label="tw" value={sectionValue(support.section, "web_thickness")} unit={lengthUnit} onChange={(value) => { setSectionQuantity(1, "web_thickness", value); }} /><DecimalInput label="tf" value={sectionValue(support.section, "flange_thickness")} unit={lengthUnit} onChange={(value) => { setSectionQuantity(1, "flange_thickness", value); }} /></div>
          </SidebarGroup>

          <SidebarGroup
            title="Connection Orientation / Geometry"
            summary={geometryTemplate.column_flange_connection_side === "EXTERIOR" ? "Exterior face" : "Interior / web-side"}
            selected={selection.kind === "CONTACT"}
            onSelect={() => { setSelection({ kind: "CONTACT", id: preview.response?.visualization?.connection_orientation?.selected_flange_surface_id ?? "TOP_FLANGE" }); }}
          >
            <label className="field-control"><span>W column flange connection face</span><select value={geometryTemplate.column_flange_connection_side} onChange={(event) => { const value = event.currentTarget.value as "EXTERIOR" | "WEB_SIDE"; updateRequest((next) => { requiredValue(next.geometry_template, "Template geometry").column_flange_connection_side = value; }, INPUT_CLASSIFICATION.geometry, "IMMEDIATE"); }}><option value="EXTERIOR">Exterior face</option><option value="WEB_SIDE">Interior / web-side face</option></select></label>
            <label className="field-control"><span>Connected angle leg</span><select value={geometryTemplate.angle_connected_leg} onChange={(event) => { const value = event.currentTarget.value as "LEG_1" | "LEG_2"; updateRequest((next) => { requiredValue(next.geometry_template, "Template geometry").angle_connected_leg = value; const assignment = requiredValue(next.material_assignments.find((item) => item.participant_id === "member-a"), "Angle material assignment"); assignment.physical_element_id = value; assignment.material_region_id = value; }, INPUT_CLASSIFICATION.geometry, "IMMEDIATE"); }}><option value="LEG_1">Leg 1</option><option value="LEG_2">Leg 2</option></select></label>
            <label className="field-control"><span>Outstanding angle leg</span><select value={geometryTemplate.outstanding_leg_side} onChange={(event) => { const value = event.currentTarget.value as "POSITIVE_INTERFACE_Z" | "NEGATIVE_INTERFACE_Z"; updateRequest((next) => { requiredValue(next.geometry_template, "Template geometry").outstanding_leg_side = value; }, INPUT_CLASSIFICATION.geometry, "IMMEDIATE"); }}><option value="POSITIVE_INTERFACE_Z">+ interface side</option><option value="NEGATIVE_INTERFACE_Z">− interface side</option></select></label>
            <ReadOnlyValue label="Column orientation">Local +x = Global +Z; role Supporting column</ReadOnlyValue>
            <p className="sidebar-note">View extents change only the backend-authored local display context. They do not change member end planes, code distances, capacities, or the design fingerprint.</p>
            <div className="field-grid">
              <DecimalInput label="Column view extent below connection" value={viewExtents.column_view_extent_below.value} unit={viewExtents.column_view_extent_below.unit} onChange={(value) => { updateViewExtent("column_view_extent_below", value); }} />
              <DecimalInput label="Column view extent above connection" value={viewExtents.column_view_extent_above.value} unit={viewExtents.column_view_extent_above.unit} onChange={(value) => { updateViewExtent("column_view_extent_above", value); }} />
              <DecimalInput label="Brace-to-column angle" value={geometryTemplate.brace_to_column_directed_angle_deg} unit="degrees" onChange={(value) => { updateRequest((next) => { requiredValue(next.geometry_template, "Template geometry").brace_to_column_directed_angle_deg = value; }); }} />
              <DecimalInput label="Brace view length" value={viewExtents.brace_view_length.value} unit={viewExtents.brace_view_length.unit} onChange={(value) => { updateViewExtent("brace_view_length", value); }} />
            </div>
            <p className="sidebar-note">Directed geometry angle in the current vertical plane. Values above 90° reverse the brace slope relative to the column axis while preserving the selected connection side.</p>
            <ReadOnlyValue label="Brace orientation">diagonal in current vertical plane</ReadOnlyValue>
            <p className="sidebar-note">Out-of-plane / plan angle: 0° — fixed in current verified slice.</p>
            <ReadOnlyValue label="Connected elements">Angle {friendlyIdentifier(geometryTemplate.angle_connected_leg)} + W Column Flange</ReadOnlyValue>
            <ReadOnlyValue label="Selected contact surface">Backend-resolved by current preview; stable internal patch ID retained in inspector</ReadOnlyValue>
            <ReadOnlyValue label="Geometry angle">{formatDecimal(geometryTemplate.brace_to_column_directed_angle_deg, 1)}° directed</ReadOnlyValue>
            <ReadOnlyValue label="Material relationship">{materialRelationship}</ReadOnlyValue>
          </SidebarGroup>

          <SidebarGroup title="Bolt / Interface" summary="Selected bolt and group layout" selected={selection.kind === "BOLT"} onSelect={() => { setSelection({ kind: "BOLT", id: multirowPreview.response?.visualization?.physical_bolts?.[0]?.bolt_id ?? request.bolt_location_id }); }}>
            <div className="field-grid"><DecimalInput label="Bolt-to-brace-end distance e1" value={geometryTemplate.bolt_to_brace_end_distance.value} unit={geometryTemplate.bolt_to_brace_end_distance.unit} onChange={(value) => { updateRequest((next) => { requiredValue(next.geometry_template, "Template geometry").bolt_to_brace_end_distance.value = value; }); }} /><DecimalInput label="Bolt diameter" value={request.bolt_diameter.value} unit={request.bolt_diameter.unit} onChange={(value) => { updateRequest((next) => { next.bolt_diameter.value = value; }); }} />{supportedMultirowArrangement ? <ReadOnlyValue label="Standard physical hole">{formatDisplayQuantity(resolvedMultirowHole, request.joint_assembly.unit_system)} · backend-resolved from {friendlyEnum(request.published_code_unit_basis)}</ReadOnlyValue> : <DecimalInput label="Standard hole display" value={geometryTemplate.hole_diameter.value} unit={geometryTemplate.hole_diameter.unit} onChange={(value) => { updateRequest((next) => { requiredValue(next.geometry_template, "Template geometry").hole_diameter.value = value; }); }} />}<DecimalInput label="Washer outside diameter" value={washerGeometry.outside_diameter.value} unit={washerGeometry.outside_diameter.unit} onChange={(value) => { updateRequest((next) => { requiredValue(next.fastener_snapshot.washer_geometry, "Washer geometry").outside_diameter.value = value; }); }} /><DecimalInput label="Washer thickness" value={washerGeometry.thickness.value} unit={washerGeometry.thickness.unit} onChange={(value) => { updateRequest((next) => { requiredValue(next.fastener_snapshot.washer_geometry, "Washer geometry").thickness.value = value; }); }} /></div>
            <p className="sidebar-note">Engineering end distance from the connected brace end to Bolt 1. This affects connection design.</p>
            <ReadOnlyValue label="Bolt center">Backend-resolved selected station</ReadOnlyValue>
            <details className="advanced-demand bolt-group-layout" open={supportedMultirowArrangement || undefined}>
              <summary>Bolt-group layout</summary>
              <p className="sidebar-note">The backend places every bolt and hole on the canonical physical connection. The browser does not derive bolt coordinates.</p>
              <div className="field-grid">
                <DecimalInput label="Pitch" value={groupState.pitch} unit={lengthUnit} onChange={(value) => { updateGroup({ pitch: value }); }} />
                <DecimalInput label="Gauge" value={groupState.gauge} unit={lengthUnit} onChange={(value) => { updateGroup({ gauge: value }); }} />
                <DecimalInput label="Loaded boundary to Row 1" value={groupState.loadedBoundaryToRow1} unit={lengthUnit} onChange={(value) => { updateGroup({ loadedBoundaryToRow1: value }); }} />
                <DecimalInput label="Negative side distance" value={groupState.negativeSideDistance} unit={lengthUnit} onChange={(value) => { updateGroup({ negativeSideDistance: value }); }} />
                <DecimalInput label="Positive side distance" value={groupState.positiveSideDistance} unit={lengthUnit} onChange={(value) => { updateGroup({ positiveSideDistance: value }); }} />
              </div>
            </details>
            <label className="field-control"><span>Lap configuration</span><select value={request.lap_configuration} onChange={(event) => { const value = event.currentTarget.value; updateRequest((next) => { next.lap_configuration = value; }, INPUT_CLASSIFICATION.designFactor, "NONE"); }}><option value="SINGLE_LAP">Single lap</option><option value="DOUBLE_LAP">Double lap</option></select></label>
            {request.material_assignments.map((assignment, index) => <label className="field-control" key={`${assignment.participant_id}:${assignment.physical_element_id}`}><span>Bearing threads · {friendlyIdentifier(assignment.participant_id === "member-a" ? "layer-A" : "layer-B")}</span><select value={assignment.bearing_thread_status} onChange={(event) => { const value = event.currentTarget.value; updateRequest((next) => { requiredAt(next.material_assignments, index, "Material assignment").bearing_thread_status = value; requiredAt(next.fastener_snapshot.bearing_layer_thread_statuses, index, "Bearing-layer thread status").status = value; }, INPUT_CLASSIFICATION.designFactor, "NONE"); }}><option value="EXCLUDED">Excluded</option><option value="INCLUDED">Included</option><option value="UNKNOWN">Unknown</option></select></label>)}
            <label className="field-control"><span>Shear-plane threads</span><select value={shearPlaneStatus.status} onChange={(event) => { const value = event.currentTarget.value; updateRequest((next) => { requiredAt(next.fastener_snapshot.shear_plane_thread_statuses, 0, "Shear-plane thread status").status = value; }, INPUT_CLASSIFICATION.designFactor, "NONE"); }}><option value="EXCLUDED">Excluded</option><option value="INCLUDED">Included</option><option value="UNKNOWN">Unknown</option></select></label>
          </SidebarGroup>

          <SidebarGroup title="Materials" summary="Locked ICE and layer axes">
            <MaterialCard request={request} />
            <div className="field-grid">
              <label className="field-control"><span>Connected material pair</span><select aria-label="Connected material pair" value={groupState.materialPair} onChange={(event) => { updateGroup({ materialPair: event.currentTarget.value as BoltGroupState["materialPair"] }); }}><option value="FRP_FRP">FRP to FRP</option><option value="FRP_STEEL">FRP to steel</option></select></label>
              <DecimalInput label="FRP LW-axis angle" value={groupState.materialAxisAngleDegrees} unit="degrees" onChange={(value) => { updateGroup({ materialAxisAngleDegrees: value }); }} />
            </div>
          </SidebarGroup>
          <SidebarGroup title="Fastener" summary="F593 source pending"><FastenerCard request={request} /></SidebarGroup>

          <SidebarGroup title="Loads" summary="Factored member-end action">
            <p className="sidebar-note">Manual forces are factored design actions in the brace-local frame at connected START. No extra load factor is applied.</p>
            <p className="sidebar-note">{demandMode === "AUTOMATIC_MEMBER_END_FORCE" ? "The backend resolves these forces from the canonical member frame and physical reference point. Moments remain trace-only in the current automatic method." : "Member-end actions are provenance / visualization data for explicit-demand evaluation."}</p>
            <div className="field-grid"><DecimalInput label="P / Fx" value={action.force.x} unit={action.force.unit} onChange={(value) => { setActionValue("force", "x", value); }} /><DecimalInput label="Vy / Fy" value={action.force.y} unit={action.force.unit} onChange={(value) => { setActionValue("force", "y", value); }} /><DecimalInput label="Vz / Fz" value={action.force.z} unit={action.force.unit} onChange={(value) => { setActionValue("force", "z", value); }} /><DecimalInput label="T / Mx" value={action.moment.x} unit={action.moment.unit} onChange={(value) => { setActionValue("moment", "x", value); }} /><DecimalInput label="My" value={action.moment.y} unit={action.moment.unit} onChange={(value) => { setActionValue("moment", "y", value); }} /><DecimalInput label="Mz" value={action.moment.z} unit={action.moment.unit} onChange={(value) => { setActionValue("moment", "z", value); }} /></div>
          </SidebarGroup>

          <SidebarGroup title="Demand" summary={demandMode === "AUTOMATIC_MEMBER_END_FORCE" ? "Automatic member-end force" : supportedMultirowArrangement ? "Explicit connection resultant" : "Explicit one-bolt"} defaultOpen>
            <div className="mode-selector" role="group" aria-label="Demand source"><button type="button" aria-pressed={demandMode === "AUTOMATIC_MEMBER_END_FORCE"} onClick={() => { setDemandModeValue("AUTOMATIC_MEMBER_END_FORCE"); }}>Automatic from member-end force</button><button type="button" aria-pressed={demandMode === "EXPLICIT_RESOLVED_CONNECTION_DEMAND"} onClick={() => { setDemandModeValue("EXPLICIT_RESOLVED_CONNECTION_DEMAND"); }}>Explicit resolved connection demand</button></div>
            {demandMode === "AUTOMATIC_MEMBER_END_FORCE" ? <><p className="demand-boundary-note"><strong>Bolt-group demand is resolved by the backend from the member-end force and its canonical reference point.</strong> Member-end moments and unsupported out-of-plane effects remain separately identified; all six actions are not automatically distributed.</p>{singleArrangement ? <p className="unsupported-note"><span aria-hidden="true">!</span> Select at least two rows for the accepted automatic multi-row workflow.</p> : null}</> : request.explicit_resolved_demand === null ? <p className="unsupported-note"><span aria-hidden="true">!</span> Explicit externally resolved connection demand is required.</p> : <><p className="demand-boundary-note"><strong>The connection demand is independently resolved.</strong> Member-end actions remain separate provenance and visualization context.</p>{singleArrangement ? <p className="sidebar-note">The 1 × 1 route treats this as the explicit resolved Bolt 1 demand.</p> : null}<details className="advanced-demand"><summary>Advanced independently resolved demand</summary><p className="qualification-banner"><span aria-hidden="true">!</span> {singleArrangement ? "Use only when one-bolt demand was independently resolved." : "Use only when connection demand was independently resolved."}</p><div className="field-grid"><DecimalInput label="In-plane Fx" value={request.explicit_resolved_demand.in_plane_force_vector.x} unit={request.explicit_resolved_demand.in_plane_force_vector.unit} onChange={(value) => { updateRequest((next) => { requiredValue(next.explicit_resolved_demand, "Explicit demand").in_plane_force_vector.x = value; }, INPUT_CLASSIFICATION.resolvedDemand); }} /><DecimalInput label="In-plane Fy" value={request.explicit_resolved_demand.in_plane_force_vector.y} unit={request.explicit_resolved_demand.in_plane_force_vector.unit} onChange={(value) => { updateRequest((next) => { requiredValue(next.explicit_resolved_demand, "Explicit demand").in_plane_force_vector.y = value; }, INPUT_CLASSIFICATION.resolvedDemand); }} /><DecimalInput label="Bolt-axis tension" value={request.explicit_resolved_demand.bolt_axis_tensile_demand.value} unit={request.explicit_resolved_demand.bolt_axis_tensile_demand.unit} onChange={(value) => { updateRequest((next) => { requiredValue(next.explicit_resolved_demand, "Explicit demand").bolt_axis_tensile_demand.value = value; }, INPUT_CLASSIFICATION.resolvedDemand); }} /><DecimalInput label="Externally supplied prying" value={request.explicit_resolved_demand.externally_supplied_prying_demand.value} unit={request.explicit_resolved_demand.externally_supplied_prying_demand.unit} onChange={(value) => { updateRequest((next) => { requiredValue(next.explicit_resolved_demand, "Explicit demand").externally_supplied_prying_demand.value = value; }, INPUT_CLASSIFICATION.resolvedDemand); }} /><label className="field-control"><span>Layer loading sense</span><select value={request.explicit_resolved_demand.loading_sense} onChange={(event) => { const value = event.currentTarget.value as "TENSION" | "COMPRESSION"; updateRequest((next) => { requiredValue(next.explicit_resolved_demand, "Explicit demand").loading_sense = value; }, INPUT_CLASSIFICATION.resolvedDemand, "IMMEDIATE"); }}><option value="TENSION">Tension</option><option value="COMPRESSION">Compression</option></select></label></div></details></>}
            {supportedMultirowArrangement ? <details className="advanced-demand" open><summary>Row-demand method and provenance</summary><div className="field-grid"><label className="field-control"><span>Row-demand method</span><select aria-label="Row-demand method" value={groupState.distribution} onChange={(event) => { setGroupDistribution(event.currentTarget.value as GroupDistribution); }}><option value="ASCE_PRESCRIBED">ASCE prescribed</option><option value="CONSERVATIVE_FULL_ROW_ENVELOPE">Conservative full-row envelope</option><option value="FRACTIONS">Engineer-defined fractions</option><option value="DIRECT_ROW_FORCES">Engineer-defined direct row forces</option></select></label><label className="field-control"><span>Source calculation</span><input aria-label="Source calculation" value={groupState.sourceCalculation} onChange={(event) => { updateGroup({ sourceCalculation: event.currentTarget.value }); }} /></label><DecimalInput label="Force-line offset" value={groupState.forceLineOffset} unit={lengthUnit} onChange={(value) => { updateGroup({ forceLineOffset: value }); }} />{groupState.engineerAllocations.map((allocation, index) => allocation.fraction === undefined ? <DecimalInput key={allocation.row_ordinal} label={`Row ${String(allocation.row_ordinal)} direct force`} value={requiredValue(allocation.direct_force, "Direct row force").value} unit={requiredValue(allocation.direct_force, "Direct row force").unit} onChange={(value) => { const allocations = structuredClone(groupState.engineerAllocations); requiredValue(requiredAt(allocations, index, "Engineer allocation").direct_force, "Direct row force").value = value; updateGroup({ engineerAllocations: allocations }); }} /> : <DecimalInput key={allocation.row_ordinal} label={`Row ${String(allocation.row_ordinal)} fraction`} value={allocation.fraction} onChange={(value) => { const allocations = structuredClone(groupState.engineerAllocations); requiredAt(allocations, index, "Engineer allocation").fraction = value; updateGroup({ engineerAllocations: allocations }); }} />)}</div></details> : null}
          </SidebarGroup>

          <SidebarGroup title="Factors" summary="Explicit selections">
            <label className="field-control"><span>λ / time-effect category</span><select value={request.time_effect_category} onChange={(event) => { const value = event.currentTarget.value; updateRequest((next) => { next.time_effect_category = value; }, INPUT_CLASSIFICATION.designFactor, "NONE"); }}><option value="">Select explicitly</option><option value="WIND_TORNADO_SEISMIC">Wind / tornado / seismic</option><option value="OTHER">Other</option></select></label>
            <div className="field-grid"><DecimalInput label="CM" value={request.end_use_factors.cm} onChange={(value) => { updateRequest((next) => { next.end_use_factors.cm = value; }, INPUT_CLASSIFICATION.designFactor, "NONE"); }} /><DecimalInput label="CT" value={request.end_use_factors.ct} onChange={(value) => { updateRequest((next) => { next.end_use_factors.ct = value; }, INPUT_CLASSIFICATION.designFactor, "NONE"); }} /><DecimalInput label="CCH" value={request.end_use_factors.cch} onChange={(value) => { updateRequest((next) => { next.end_use_factors.cch = value; }, INPUT_CLASSIFICATION.designFactor, "NONE"); }} /></div>
            {(request.end_use_factors.cm === "" || request.end_use_factors.ct === "" || request.end_use_factors.cch === "") ? <p className="unsupported-note"><span aria-hidden="true">!</span> Blank factors require explicit selection; unity is not silently assumed.</p> : null}
            {supportedMultirowArrangement ? <details className="advanced-demand"><summary>Multi-row methods and bolt-axis tension</summary><label className="field-control"><span>First-row method</span><select aria-label="First-row method" value={groupState.firstRowMethod} onChange={(event) => { updateGroup({ firstRowMethod: event.currentTarget.value as BoltGroupState["firstRowMethod"] }); }}><option value="ASCE_STANDARD_SIMPLIFIED">ASCE simplified</option><option value="ASCE_COMMENTARY_FULL">ASCE commentary full</option></select></label><DecimalInput label="Prescribed Lbr" value={groupState.prescribedLbr} onChange={(value) => { updateGroup({ prescribedLbr: value }); }} /><label className="checkbox-control"><input aria-label="Bolt-axis tension required" type="checkbox" checked={groupState.boltAxisTensionRequired} onChange={(event) => { const required = event.currentTarget.checked; const unit = request.explicit_resolved_demand?.bolt_axis_tensile_demand.unit ?? action.force.unit; updateGroup({ boltAxisTensionRequired: required, boltAxisTensions: required ? (multirowPreview.response?.visualization?.physical_bolts ?? []).map((bolt) => ({ bolt_id: bolt.bolt_id, demand: multirowQuantity("0", unit) })) : [] }); }} /> Bolt-axis tension required</label>{groupState.boltAxisTensions.map((tension, index) => <DecimalInput key={tension.bolt_id} label={`${friendlyIdentifier(tension.bolt_id)} axis tension`} value={tension.demand.value} unit={tension.demand.unit} onChange={(value) => { const tensions = structuredClone(groupState.boltAxisTensions); requiredAt(tensions, index, "Bolt-axis tension").demand.value = value; updateGroup({ boltAxisTensions: tensions }); }} />)}</details> : null}
          </SidebarGroup>

          <SidebarGroup title="Model / Geometry Status" summary={modelStatusLabel} defaultOpen>
            <strong>{modelStatusLabel}</strong>
            {orientation === null ? null : <dl className="diagnostic-list"><div><dt>Contact</dt><dd>W Column Flange — {orientation.connection_side === "EXTERIOR" ? "Exterior" : "Interior / web-side"}</dd></div><div><dt>Connected leg</dt><dd>{friendlyIdentifier(orientation.connected_leg)}</dd></div><div><dt>Outstanding leg</dt><dd>{orientation.outstanding_leg_side === "POSITIVE_INTERFACE_Z" ? "+ interface side" : "− interface side"}</dd></div><div><dt>Geometry angle</dt><dd>{formatDecimal(orientation.brace_to_column_directed_angle_degrees, 1)}° directed</dd></div><div><dt>Bolt path</dt><dd>Angle Connected Leg → W Column Flange</dd></div><div><dt>Material relationship</dt><dd>{materialRelationship}</dd></div></dl>}
            {preview.response?.geometry_issues.length === 0 || preview.response === null ? null : <ul className="issue-list">{preview.response.geometry_issues.map((issue) => <li key={`${issue.code}:${issue.identities.join(":")}`}>{issue.message}</li>)}</ul>}
            {supportedMultirowArrangement ? multirowPreview.response?.warnings.map((warning) => <p className="unsupported-note" key={warning}>{friendlyEnum(warning)}</p>) : null}
            {(supportedMultirowArrangement ? multirowPreview.outdated : preview.outdated) ? <p className="stale-notice" role="status">Last canonical preview is outdated.</p> : null}
          </SidebarGroup>

          <SidebarGroup title="Design Results" summary={stale ? "Stale" : activeDesignSummary} defaultOpen>
            {supportedMultirowArrangement
              ? automaticHandoff !== null && automaticGroupModeIntegration !== null
                ? <><strong>{stale ? "STALE — previous design run" : friendlyEnum(automaticGroupModeIntegration.overall_disposition)}</strong><p className="sidebar-note">{friendlyEnum(automaticHandoff.coverage)} · {automaticGroupModeIntegration.governing_supported_check_ids.length} governing supported check(s)</p></>
                : multirowResult === null
                ? <p className="sidebar-note">No multi-row design run.</p>
                : <><strong>{stale ? "STALE — previous explicit run" : friendlyEnum(multirowResult.overall_disposition)}</strong><p className="sidebar-note">{multirowResult.governing_result_ids.length} governing / co-governing check(s)</p></>
              : response === null
                ? <p className="sidebar-note">No design run.</p>
                : <><strong>{stale ? "STALE — previous explicit run" : resultHeadline(response)}</strong><p className="sidebar-note">{response.governing_check_ids.length} governing / co-governing check(s)</p></>}
          </SidebarGroup>

          <SidebarGroup title="Advanced / Diagnostics" summary="Stable IDs and versions">
            <dl className="diagnostic-list"><div><dt>Assembly</dt><dd>{request.joint_assembly.id}</dd></div><div><dt>Interface</dt><dd>{request.interface_id}</dd></div><div><dt>Bolt group</dt><dd>{request.bolt_group_id}</dd></div><div><dt>Bolt</dt><dd>{request.bolt_location_id}</dd></div>{response === null ? null : <><div><dt>Fingerprint</dt><dd>{response.calculation_fingerprint ?? "Not available"}</dd></div><div><dt>Engine</dt><dd>{response.calculation_engine_version}</dd></div><div><dt>Rule set</dt><dd>{response.engineering_rule_set_version}</dd></div><div><dt>Contract</dt><dd>{response.calculation_contract_version}</dd></div></>}</dl>
          </SidebarGroup>

          <section className="evaluate-panel sidebar-evaluate" aria-label="Design-check controls"><p>Runs the verified engineering resistance checks for the current canonical model. HTTP success does not imply engineering PASS.</p><button type="button" className="primary-button" disabled={loading || designButtonBlocker !== null} title={designButtonBlocker ?? undefined} onClick={() => { void evaluate(); }}>{loading ? "Running design check…" : "Run Design Check"}</button>{designButtonBlocker === null ? null : <p className="sidebar-note" role="status">{designButtonBlocker}</p>}</section>
        </ConnectionWorkspaceSidebar>

        <ConnectionWorkspaceMain>
          <PersistentConnectionViewer unity={viewerUnity(singleArrangement ? "single-bolt" : "multirow", singleArrangement ? response : multirowDesign, { stale: stale || (supportedMultirowArrangement ? multirowPreview.outdated : preview.outdated), checking: loading, error: singleArrangement ? error : multirowDesignError })}>
            {canonicalModel === null ? <section className="viewer-prompt"><h3>Connection viewer</h3><p>The backend-authoritative model appears automatically when current engineering inputs are valid. The browser does not reconstruct calculation geometry.</p><div className="viewer-prompt-graphic" aria-hidden="true"><span /><span /><span /></div></section> : <VisualizationPanel model={canonicalModel} results={activeResults} resolvedLayers={activeResolvedLayers} selection={selection} onSelect={setSelection} appliedActionInputValues={appliedActionInputValues} onAppliedActionValueChange={setActionComponentValue} actionSourceLabel="Member" selectedBoltChecks={selectedBoltChecks} />}
          </PersistentConnectionViewer>
          {previewPending ? <p className="preview-notice" role="status">Updating model…</p> : null}
          {preview.state === "PREVIEW_ERROR" ? <div className="transport-error" role="alert"><strong>Preview unavailable — current inputs not validated.</strong><p>{requiredValue(preview.error, "Preview error").message}</p><button type="button" onClick={preview.retry}>Retry preview</button></div> : null}
          {stale ? <p className="stale-notice" role="status">Design results are stale — run Design Check to update.</p> : null}
          {supportedMultirowArrangement && activePreviewError !== null ? <div className="transport-error" role="alert"><strong>Preview unavailable — current inputs not validated.</strong><p>{activePreviewError.message}</p><button type="button" onClick={activePreviewRetry}>Retry preview</button></div> : null}
          {error === null ? null : <div className="transport-error" role="alert"><strong>{error.kind} {error.status === null ? "" : `HTTP ${String(error.status)}`}</strong><p>{error.message}</p></div>}
          {multirowDesignError === null ? null : <div className="transport-error" role="alert"><strong>{multirowDesignError.kind} {multirowDesignError.status === null ? "" : `HTTP ${String(multirowDesignError.status)}`}</strong><p>{multirowDesignError.message}</p></div>}
          {supportedMultirowArrangement && multirowPreview.response?.visualization !== null && multirowPreview.response?.visualization !== undefined ? <details className="layout-diagnostic"><summary>Bolt layout — optional 2D diagnostic</summary><p>The canonical 3D connection above remains primary. This backend-authored interface-plane diagram is a secondary layout and block-path diagnostic.</p><label className="checkbox-control"><input type="checkbox" checked={groupState.showBlockPaths} onChange={(event) => { updateGroup({ showBlockPaths: event.currentTarget.checked }, false); }} /> Show accepted block paths</label><MultiRowVisualizationPanel snapshot={multirowPreview.response.visualization} showBlockPaths={groupState.showBlockPaths} displayUnitSystem={request.joint_assembly.unit_system} /></details> : null}
          <details className={`results-drawer${stale ? " stale-design-results" : ""}`} open={resultsOpen} onToggle={(event) => { setResultsOpen(event.currentTarget.open); }}>
            <summary><span>Design results &amp; calculation details</span><small>{activeDesignSummary === "No design run" ? "Run Design Check to populate" : stale ? "STALE" : activeDesignSummary}</small></summary>
            <div className="results-drawer-body">{supportedMultirowArrangement ? automaticHandoff !== null && automaticGroupModeIntegration !== null && multirowDesign?.automatic_demand_result !== null && multirowDesign?.automatic_demand_result !== undefined ? <AutomaticMultirowResults handoff={automaticHandoff} integration={automaticGroupModeIntegration} demandFingerprint={multirowDesign.automatic_demand_result.result_fingerprint} displayUnitSystem={request.joint_assembly.unit_system} /> : multirowResult === null ? <p>No multi-row design run.</p> : <MultirowResults result={multirowResult} displayUnitSystem={request.joint_assembly.unit_system} /> : response === null ? <p>No design run.</p> : <><ResultSummary response={response} /><ResultTable response={response} /></>}</div>
          </details>
        </ConnectionWorkspaceMain>
    </ConnectionWorkspaceShell>
  );
}
