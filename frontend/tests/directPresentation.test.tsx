import { act, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { currentSignedDirectReport, directViewerUnity, type DirectViewerCurrency } from "../src/features/directPresentation";
import { ConnectionWorkspaceShell, PersistentConnectionViewer } from "../src/workspace/ConnectionWorkspaceShell";
import { setMAT1Active } from "../src/state/mat1Session";

const current: DirectViewerCurrency = { currentKey: true, signedCurrent: true, stale: false, checking: false, error: null, invalid: false, previewCurrent: true };
const design = { automatic_handoff_results: [], automatic_group_mode_integration: { scenario_results: [] } };
const trace = (ratio: string | null = "0.247442895913268393954475557126535418459410731960869284539573", status = "YELLOW") => ({
  native_design: design, overall_status: "ENGINEERING_REVIEW_REQUIRED",
  final_decision: { contract: "DIRECT-STATUS-F9", current_snapshot_digest: "A".repeat(64), final_status: status, final_status_reason: "QUALIFICATION REQUIRED", qualification_capacity_state: "UNEVALUATED",
    analytical_check_summary: { evaluated: 8, highest_utilization: ratio, highest_analytical_check: "PIN_BEARING:layer-A:B_R1_L1", counts: { REQUIRED_UNRESOLVED: 6 } },
    schedule: [{ check_id: "PIN_BEARING:layer-A:B_R1_L1", label: "FRP pin bearing — Angle — row 1, bolt 1", category: "ANALYTICALLY_EVALUATED", utilization: ratio, outcome: status === "RED" ? "FAIL" : "PASS" }],
  },
});

it.each([0, 1, 2])("reads the single Direct decision rather than enveloping %s scenario/handoff objects", count => {
  const visible = { automatic_handoff_results: Array.from({ length: count }, () => ({ utilization: "999" })), automatic_group_mode_integration: { scenario_results: Array.from({ length: count }, () => ({ utilization: "999" })) } };
  const result = directViewerUnity({ ...trace(), native_design: visible }, visible, current);
  expect(result).toMatchObject({ tone: "yellow", ratio: 0.2474428959132684, ratioText: "UR (evaluated): 0.247443", governing: "FRP pin bearing — Angle — row 1, bolt 1 · PASS" });
  expect(result.status).toBe("Whole connection: YELLOW — qualification required");
  expect(result.explanation).toContain("6 required items unresolved");
});

it.each(["0", "0.0e-999", "1", "0.22269860632194155", "3.093036198915855", "1e-88"])("presents the exact backend maximum %s at display precision only", value => {
  const result = directViewerUnity(trace(value, value.startsWith("3.") ? "RED" : "YELLOW"), design, current);
  expect(result.ratio).toBe(Number(value));
  expect(result.explanation).toContain(`Exact analytical utilization: ${value}`);
  expect(result.tone).toBe(value.startsWith("3.") ? "red" : "yellow");
});

it("requires a clean design report session with a current signed handle", () => {
  expect(currentSignedDirectReport({ kind: null, token: null, dirty: false })).toBe(false);
  expect(currentSignedDirectReport({ kind: "input_only", token: "draft", dirty: false })).toBe(false);
  expect(currentSignedDirectReport({ kind: "design", token: null, dirty: false })).toBe(false);
  expect(currentSignedDirectReport({ kind: "design", token: "signed-current", dirty: true })).toBe(false);
  expect(currentSignedDirectReport({ kind: "design", token: "signed-current", dirty: false })).toBe(true);
});

it.each([null, "", "-0.1", "NaN", "Infinity", "1e999", "1e-999", "bad", 0.25 as unknown as string])("never displays an invalid maximum %s", value => {
  expect(directViewerUnity(trace(value), design, current)).toMatchObject({ tone: "gray", ratio: null });
});

it.each([
  { checking: true }, { error: "request failed" }, { invalid: true }, { stale: true },
  { previewCurrent: false }, { currentKey: false }, { signedCurrent: false },
])("blocks old or unavailable authority %j", change => {
  expect(directViewerUnity(trace(), design, { ...current, ...change })).toMatchObject({ tone: "gray", ratio: null });
});

it("requires matching visible design and signed snapshot context and a unique evaluated check", () => {
  for (const candidate of [undefined, {}, { ...trace(), native_design: undefined }, { ...trace(), native_design: { changed_spacing: true } },
    { ...trace(), final_decision: { ...trace().final_decision, current_snapshot_digest: "wrong" } },
    { ...trace(), final_decision: { ...trace().final_decision, final_status: "UNKNOWN" } },
    { ...trace(), final_decision: { ...trace().final_decision, final_status: "GRAY" } }]) {
    expect(directViewerUnity(candidate, design, current).ratio).toBeNull();
  }
  for (const schedule of [undefined, [], [...trace().final_decision.schedule, ...trace().final_decision.schedule],
    [{ ...trace().final_decision.schedule[0], category: "REQUIRED_UNRESOLVED" }],
    [{ ...trace().final_decision.schedule[0], utilization: "0.3" }],
    [{ ...trace().final_decision.schedule[0], label: "" }],
    [{ ...trace().final_decision.schedule[0], outcome: "NOT_EVALUATED" }]]) {
    expect(directViewerUnity({ ...trace(), final_decision: { ...trace().final_decision, schedule } }, design, current).ratio).toBeNull();
  }
  for (const evaluated of [0, -1, 1.5, Number.NaN]) {
    expect(directViewerUnity({ ...trace(), final_decision: { ...trace().final_decision, analytical_check_summary: { ...trace().final_decision.analytical_check_summary, evaluated } } }, design, current).ratio).toBeNull();
  }
  expect(directViewerUnity(trace(), null, current).status).toBe("Not calculated");
  expect(directViewerUnity({ ...trace(), final_decision: { ...trace().final_decision, analytical_check_summary: undefined } }, design, current).ratio).toBeNull();
  expect(directViewerUnity({ ...trace(), client_design: design, native_design: undefined }, design, current).ratio).not.toBeNull();
});

it("labels source-stopped independent bolt ratios without claiming an FRP check", () => {
  const server = trace("0.04083100878621659");
  server.final_decision.analytical_check_summary.evaluated = 2;
  server.final_decision.analytical_check_summary.counts.REQUIRED_UNRESOLVED = 14;
  server.final_decision.analytical_check_summary.highest_analytical_check = "BOLT_SHEAR:B_R1_L1";
  const original = server.final_decision.schedule[0];
  if (original === undefined) throw new Error("Missing fixture check");
  server.final_decision.schedule[0] = { ...original, check_id: "BOLT_SHEAR:B_R1_L1", label: "Bolt shear — row 1, bolt 1" };
  const result = directViewerUnity(server, design, current);
  expect(result.ratioText).toBe("UR (bolt checks): 0.0408310");
  expect(result.explanation).toContain("FRP resistances remain unevaluated");
  expect(result.status).toContain("YELLOW");
});

it("keeps the narrow Direct view and neutral geometry route out of generic MAT1 selection", () => {
  act(() => { setMAT1Active(true); });
  const currentView = directViewerUnity(trace(), design, current);
  const view = render(<ConnectionWorkspaceShell banner={null} family="multi-row"><PersistentConnectionViewer directUnity={currentView}>Model</PersistentConnectionViewer></ConnectionWorkspaceShell>);
  expect(screen.getAllByText("UR (evaluated): 0.247443")).toHaveLength(1);
  expect(screen.getByText(/Design completeness status:/)).toHaveTextContent("YELLOW — qualification required");
  expect(screen.getByText("Raw backend status: Not calculated").closest("details")).not.toHaveAttribute("open");
  view.rerender(<ConnectionWorkspaceShell banner={null} family="multi-row"><PersistentConnectionViewer directUnity={currentView} geometryOnlyReason="Support geometry only">Model</PersistentConnectionViewer></ConnectionWorkspaceShell>);
  expect(screen.getByRole("group", { name: "Unity ratio: —. Structural design not evaluated" })).toHaveAttribute("data-unity-tone", "gray");
  expect(screen.queryByText(/0.247443/)).not.toBeInTheDocument();
  expect(screen.getByText(/Design completeness status:/).parentElement).toHaveClass("mat1-result-gate-gray");
});
