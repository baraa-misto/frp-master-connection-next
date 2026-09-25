import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { buildSingleBoltSceneModel } from "../src/visualization/sceneModel";
import { VisualizationPanel } from "../src/visualization/VisualizationPanel";
import { ConnectionWorkspaceMain, PersistentConnectionViewer } from "../src/workspace/ConnectionWorkspaceShell";
import { UnityRatioIndicator } from "../src/workspace/UnityRatioIndicator";
import { formatUnityPercent, resolveUnity, unityPhase, viewerUnity, type UnityFamily } from "../src/workspace/unityRatio";
import { visualizationFixture } from "./fixtures";

vi.mock("../src/visualization/EngineeringScene", () => ({ default: () => <div data-testid="mock-scene" /> }));

const single = (ratio: string, status = "PASS") => ({
  aggregate_status: status,
  qualification_flags: [], issues: [],
  results: [{ utilization: ratio, numerical_comparison: ratio === "1.142" ? "FAIL" : "PASS", plan: { check_id: "bolt shear", required: true } }],
});

describe("unity result authority", () => {
  it("uses the backend aggregate to show a complete qualified result", () => {
    expect(resolveUnity({ family: "single-bolt", phase: "current", design: single("0.824") })).toMatchObject({ tone: "green", ratioText: "UR: 82.4%", status: "Complete", governing: "bolt shear" });
    expect(resolveUnity({ family: "single-bolt", phase: "current", design: single("1") })).toMatchObject({ tone: "green", ratioText: "UR: 100%", status: "At limit · Complete" });
    expect(resolveUnity({ family: "single-bolt", phase: "current", design: { ...single("0.824"), qualification_flags: ["REVIEW_REQUIRED"] } })).toMatchObject({ tone: "yellow", status: "Incomplete design" });
    expect(resolveUnity({ family: "single-bolt", phase: "current", design: { ...single("0.824"), issues: [{ code: "missing" }] } })).toMatchObject({ tone: "yellow" });
    expect(resolveUnity({ family: "single-bolt", phase: "current", design: { results: [], qualification_flags: [], issues: [] } }).explanation).toContain("not established");
  });

  it("keeps numerical and backend failures red even when other work is unsupported", () => {
    expect(resolveUnity({ family: "single-bolt", phase: "current", design: single("1.142", "FAIL_WITH_UNSUPPORTED_REQUIRED_CHECK") })).toMatchObject({ tone: "red", ratioText: "UR: 114.2%", status: "Failed" });
    expect(resolveUnity({ family: "single-bolt", phase: "current", design: { aggregate_status: "FAIL", results: [], qualification_flags: [], issues: [] } })).toMatchObject({ tone: "red", ratioText: "UR: —", status: "Design failed" });
    expect(resolveUnity({ family: "web-splice", phase: "current", design: { assembly_status: "NOT_EVALUATED", result: { plate_body_interaction: { rational_utilization: "1.12", status: "FAIL_RATIONAL_METHOD", governing_section_id: "section A" }, double_shear_results: [] } } })).toMatchObject({ tone: "red", ratioText: "UR: 112.0%" });
    expect(resolveUnity({ family: "ssmc", phase: "current", design: { result: { checks: [{ status: "FAIL" }], blockers: [], applicability_reasons: [] } } })).toMatchObject({ tone: "red", status: "Design failed" });
    expect(resolveUnity({ family: "dctn", phase: "current", design: { checks: [{ status: "FAIL" }], blockers: [] } })).toMatchObject({ tone: "red", status: "Design failed" });
  });

  it("selects only current server-calculated dimensionless ratios, never a percent field", () => {
    const result = resolveUnity({ family: "web-splice", phase: "current", design: { assembly_status: "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED", required_check_status: "ENGINEERING_REVIEW_REQUIRED", result: { plate_body_interaction: { normal_utilization: "0.54", shear_utilization: "0.72", rational_utilization: "0.824", utilization_percent: "82.4", governing_section_id: "A" }, double_shear_results: [{ bolt_id: "B1", utilization: "0.71", status: "PASS" }], double_shear_governing_utilization: "0.71" } } });
    expect(result).toMatchObject({ tone: "yellow", ratioText: "UR (checked): 82.4%", status: "Incomplete design" });
    expect(resolveUnity({ family: "web-splice", phase: "current", design: { assembly_status: "NOT_EVALUATED", result: {} } })).toMatchObject({ tone: "yellow", ratioText: "UR: —" });
    expect(resolveUnity({ family: "web-splice", phase: "current", design: { assembly_status: "NOT_EVALUATED", result: { governing_utilization: "-0.2", utilization: "NaN" } } })).toMatchObject({ ratio: null, ratioText: "UR: —" });
    for (const invalid of ["-0.2", "NaN", "1e999", Number.POSITIVE_INFINITY]) {
      expect(resolveUnity({ family: "single-bolt", phase: "current", design: single(String(invalid)) }).ratio).toBeNull();
    }
    expect(resolveUnity({ family: "single-bolt", phase: "current", design: { aggregate_status: "ENGINEERING_REVIEW_REQUIRED", results: [{ utilization: "0.2", numerical_comparison: "PASS" }], qualification_flags: [], issues: [] } })).toMatchObject({ tone: "yellow", governing: "Bolt check" });
    expect(resolveUnity({ family: "multirow", phase: "current", design: { calculation_result: { overall_disposition: "INCOMPLETE_OR_UNSUPPORTED", results: [{ utilization: "0.2", numerical_comparison: "PASS" }] } } })).toMatchObject({ tone: "yellow", governing: "Bolt-group check" });
  });

  it("preserves the side of the limit before rounding", () => {
    expect(formatUnityPercent(1)).toBe("100%");
    expect(formatUnityPercent(0.99999999999)).toMatch(/^<100%|99\.99/u);
    expect(formatUnityPercent(1.00000000001)).toMatch(/^>100%|100\.00/u);
    expect(resolveUnity({ family: "single-bolt", phase: "current", design: single("1.00000000001") }).tone).toBe("red");
    expect(resolveUnity({ family: "single-bolt", phase: "current", design: single("0.99999999999") }).tone).toBe("green");
  });

  it("uses gray for no run, stale, checking, invalid input and transport failure", () => {
    for (const [phase, status] of [["not-checked", "Not checked"], ["stale", "Results stale"], ["checking", "Checking…"], ["invalid", "Invalid inputs"], ["request-error", "Request error"]] as const) {
      expect(resolveUnity({ family: "single-bolt", phase, design: single("1.142") })).toMatchObject({ tone: "gray", ratioText: "UR: —", status });
    }
    expect(unityPhase({ design: single("0.5"), stale: true })).toBe("stale");
    expect(unityPhase({ design: single("0.5"), previewCurrent: false })).toBe("stale");
    expect(unityPhase({ design: single("0.5"), previewState: "PREVIEW_PENDING" })).toBe("stale");
    expect(unityPhase({ design: null, previewState: "CURRENT_VALID" })).toBe("not-checked");
    expect(unityPhase({ design: undefined })).toBe("not-checked");
    expect(unityPhase({ design: single("0.5"), previewState: "CURRENT_VALID" })).toBe("current");
    expect(resolveUnity({ family: "single-bolt", phase: "current", design: undefined })).toMatchObject({ tone: "gray", status: "Not checked" });
    expect(unityPhase({ design: single("0.5"), checking: true, stale: true })).toBe("checking");
    expect(unityPhase({ design: single("0.5"), error: "network" })).toBe("request-error");
    expect(unityPhase({ design: single("0.5"), invalid: true })).toBe("invalid");
    expect(unityPhase({ design: single("0.5"), previewState: "CURRENT_INVALID_SHOWING_LAST_VALID" })).toBe("invalid");
    expect(unityPhase({ design: null, previewState: "NO_VALID_PREVIEW" })).toBe("invalid");
    expect(unityPhase({ design: single("0.5"), previewState: "PREVIEW_FAILED_SHOWING_LAST_VALID" })).toBe("request-error");
    expect(viewerUnity("single-bolt", single("0.824"), { stale: true }).tone).toBe("gray");
  });

  it("requires the multirow aggregate, qualified method and exact required coverage", () => {
    const calculation = { overall_disposition: "PASS", qualification: "QUALIFIED_ASCE_PRESCRIPTIVE", required_check_ids: ["B1"], calculated_check_ids: ["B1"], unsupported_check_ids: [], failed_check_ids: [], results: [{ result_id: "B1", utilization: "0.75", numerical_comparison: "PASS" }] };
    expect(resolveUnity({ family: "multirow", phase: "current", design: { calculation_result: calculation } })).toMatchObject({ tone: "green", ratioText: "UR: 75.0%" });
    expect(resolveUnity({ family: "multirow", phase: "current", design: { calculation_result: { ...calculation, unsupported_check_ids: ["B2"] } } }).tone).toBe("yellow");
    expect(resolveUnity({ family: "multirow", phase: "current", design: { calculation_result: { ...calculation, failed_check_ids: ["B1"], overall_disposition: "FAIL" } } }).tone).toBe("red");
    expect(resolveUnity({ family: "multirow", phase: "current", design: { calculation_result: calculation, automatic_handoff_results: [{ overall_disposition: "INCOMPLETE_OR_UNSUPPORTED" }] } }).tone).toBe("yellow");
    expect(resolveUnity({ family: "multirow", phase: "current", design: { calculation_result: calculation, automatic_group_mode_integration: { overall_disposition: "FAIL" } } }).tone).toBe("red");
    expect(resolveUnity({ family: "multirow", phase: "current", design: { calculation_result: null } })).toMatchObject({ tone: "yellow", ratioText: "UR: —" });
    const handoff = { overall_disposition: "PASS", qualification: "QUALIFIED_ASCE_PRESCRIPTIVE", coverage: "FULL_LEGACY_COLLINEAR", supported_results: [{ result_id: "H1", utilization: "0.6", numerical_comparison: "PASS" }], unsupported_required_check_ids: [], incomplete_required_check_ids: [] };
    expect(resolveUnity({ family: "multirow", phase: "current", design: { calculation_result: null, automatic_handoff_results: [handoff] } })).toMatchObject({ tone: "green", ratioText: "UR: 60.0%" });
    const scenario = { overall_disposition: "PASS", qualification: "QUALIFIED_ASCE_PRESCRIPTIVE", required_check_ids: ["S1"], supported_results: [{ result_id: "S1", utilization: "0.7", numerical_comparison: "PASS" }], unsupported_required_check_ids: [], incomplete_required_check_ids: [] };
    expect(resolveUnity({ family: "multirow", phase: "current", design: { calculation_result: null, automatic_handoff_results: [handoff], automatic_group_mode_integration: { overall_disposition: "PASS", scenario_results: [scenario] } } })).toMatchObject({ tone: "green", ratioText: "UR: 70.0%" });
    expect(resolveUnity({ family: "multirow", phase: "current", design: { calculation_result: null, automatic_handoff_results: [], automatic_group_mode_integration: { overall_disposition: "PASS", scenario_results: [scenario, { ...scenario, supported_results: [{ utilization: "1.5" }] }] } } })).toMatchObject({ tone: "yellow", ratio: null });
  });

  it("preserves server coverage and blocker reasons for incomplete family responses", () => {
    expect(resolveUnity({ family: "ssmc", phase: "current", design: { result: { whole_connection_status: "SOURCE_REQUIRED", checks: [], applicability_reasons: ["Single-lap scope unresolved"], blockers: [] } } }).explanation).toBe("Single-lap scope unresolved");
    expect(resolveUnity({ family: "ssmc", phase: "current", design: { whole_connection_status: "SOURCE_REQUIRED", result: { checks: [], applicability_reasons: [], blockers: [] } } }).explanation).toBe("SOURCE_REQUIRED");
    expect(resolveUnity({ family: "ssmc", phase: "current", design: { result: { checks: [], applicability_reasons: [], blockers: [] } } }).explanation).toContain("not established");
    expect(resolveUnity({ family: "dctn", phase: "current", design: { whole_connection_status: "SOURCE_REQUIRED", blockers: [] } }).explanation).toBe("SOURCE_REQUIRED");
    expect(resolveUnity({ family: "dctn", phase: "current", design: { blockers: [] } }).explanation).toContain("not established");
    expect(resolveUnity({ family: "wi-wall-moment", phase: "current", design: {} }).explanation).toContain("not established");
    expect(resolveUnity({ family: "angle-column-moment-base", phase: "current", design: { result: { whole_connection_status: "EXTERNAL_DESIGN_REQUIRED" } } }).explanation).toBe("EXTERNAL_DESIGN_REQUIRED");
    expect(resolveUnity({ family: "angle-column-moment-base", phase: "current", design: {} }).explanation).toContain("not established");
    expect(resolveUnity({ family: "tee", phase: "current", design: "unexpected" })).toMatchObject({ tone: "yellow", ratioText: "UR: —" });
  });

  it("ignores excessively deep or unrelated payload branches", () => {
    let deep: unknown = { utilization: "1.2", status: "FAIL" };
    for (let index = 0; index < 12; index += 1) deep = { nested: deep };
    const design = { assembly_status: "NOT_EVALUATED", result: { preview: { nested: deep }, unrelated: [null, "text"] } };
    expect(resolveUnity({ family: "tee", phase: "current", design })).toMatchObject({ tone: "yellow", ratio: null });
  });

  it.each<[UnityFamily, unknown]>([
    ["tee", { assembly_status: "NOT_EVALUATED", result: { interface_a: { supported_results: [{ utilization: "0.4" }] } } }],
    ["clip-angle", { assembly_status: "NOT_EVALUATED", result: { interface_a: { supported_results: [{ utilization: "0.4" }] } } }],
    ["paired-clip-angle", { assembly_status: "NOT_EVALUATED", result: {} }],
    ["multi-member-tee", { assembly_status: "NOT_EVALUATED", result: {} }],
    ["dctn", { whole_connection_status: "SOURCE_REQUIRED", checks: [], blockers: ["member source missing"] }],
    ["beam-concrete-paired-angle", { assembly_status: "NOT_EVALUATED", required_check_status: "NOT_EVALUATED", result: {} }],
    ["direct-side-lap", { assembly_status: "NOT_EVALUATED", result: {} }],
    ["column-base-web-angle", { assembly_status: "NOT_EVALUATED", result: {} }],
    ["wi-moment-splice", { assembly_status: "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED", required_check_status: "ENGINEERING_REVIEW_REQUIRED", result: { governing_utilization: "0.8", governing_check_id: "flange" } }],
    ["channel-moment-splice", { assembly_status: "PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED", result: { governing_utilization: "0.8" } }],
    ["web-splice", { assembly_status: "NOT_EVALUATED", result: {} }],
    ["wi-wall-moment", { whole_connection_status: "EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED", connector_results: [{ detail: { body: { utilization: "0.7" } } }] }],
    ["wi-frp-support-moment", { whole_connection_status: "LOCAL_SUPPORT_COMPLETENESS_AND_OVERALL_MEMBER_ANALYSIS_REQUIRED", connector_results: [{ detail: { utilization: "0.7" } }] }],
    ["angle-column-moment-base", { status: "ENGINEERING_REVIEW_REQUIRED" }],
    ["column-moment-base", { status: "ENGINEERING_REVIEW_REQUIRED" }],
    ["ssmc", { whole_connection_status: "SOURCE_REQUIRED", result: { checks: [], blockers: ["material source missing"] } }],
  ])("keeps %s incomplete without whole-connection qualification", (family, design) => {
    expect(resolveUnity({ family, phase: "current", design }).tone).toBe("yellow");
  });
});

describe("shared viewer badge", () => {
  it("keeps a viewer without a design adapter free of a misleading badge", () => {
    const mounted = render(<PersistentConnectionViewer><span>Viewer only</span></PersistentConnectionViewer>);
    expect(screen.getByText("Viewer only")).toBeInTheDocument();
    expect(mounted.container.querySelector(".unity-indicator")).toBeNull();
  });

  it("provides text, detail disclosure and a fallback when canonical geometry is unavailable", () => {
    const value = resolveUnity({ family: "single-bolt", phase: "current", design: single("0.824") });
    render(<ConnectionWorkspaceMain><PersistentConnectionViewer unity={value}><div>No canonical model</div></PersistentConnectionViewer></ConnectionWorkspaceMain>);
    expect(screen.getByRole("group", { name: /Unity ratio: UR: 82.4%/u })).toHaveAttribute("data-unity-tone", "green");
    fireEvent.click(screen.getByText("Details"));
    expect(screen.getByText(/Governing check: bolt shear/u)).toBeVisible();
  });

  it("stays in the canvas overlay while the camera mode changes", () => {
    const value = resolveUnity({ family: "single-bolt", phase: "current", design: single("0.824") });
    const model = buildSingleBoltSceneModel(visualizationFixture());
    render(<PersistentConnectionViewer unity={value}><VisualizationPanel model={model} selection={{ kind: "MEMBER", id: "brace" }} onSelect={() => undefined} /></PersistentConnectionViewer>);
    expect(document.querySelector(".canvas-shell > .unity-canvas-overlay .unity-indicator")).toHaveAttribute("data-unity-tone", "green");
    expect(document.querySelector(".persistent-connection-viewer > .unity-viewer-fallback")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Front" }));
    expect(document.querySelector(".canvas-shell > .unity-canvas-overlay .unity-indicator")).toHaveTextContent("UR: 82.4%");
  });

  it("renders an incomplete source-required SSMC check without manufacturing zero", () => {
    const value = resolveUnity({ family: "ssmc", phase: "current", design: { whole_connection_status: "SOURCE_REQUIRED", result: { blockers: ["LRFD source required"], checks: [] } } });
    render(<UnityRatioIndicator value={value} />);
    expect(screen.getByText("UR: —")).toBeInTheDocument();
    expect(screen.getByText("Incomplete design")).toBeInTheDocument();
  });
});
