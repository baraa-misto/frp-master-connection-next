import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ASCEShapeBasisSummary } from "../src/features/ASCEShapeBasisSummary";
import { MAT1MaterialsPanel } from "../src/features/MAT1MaterialsPanel";
import { ConnectionWorkspaceShell, PersistentConnectionViewer } from "../src/workspace/ConnectionWorkspaceShell";
import type { UnityView } from "../src/workspace/unityRatio";
import * as service from "../src/api/mat1Service";
import { mat1Fetch } from "../src/api/mat1Transport";
import { ASCE_SHAPE_BASIS, DIRECT_PRODUCTION_MATERIAL_ID, acceptMAT1Design, clearMAT1Sessions,
  createMAT1Session, deleteMAT1Session, mat1DefaultId, mat1FamilyKey, mat1Snapshot, materialSelection,
  rememberMAT1Preview, setMAT1Active, setMAT1Catalog, setMAT1Conditions, setMAT1Default, setMAT1DirectMaterial } from "../src/state/mat1Session";
import type { MAT1CatalogRecord, MAT1Conditions } from "../src/state/mat1Session";

const poly: MAT1CatalogRecord = { id: DIRECT_PRODUCTION_MATERIAL_ID, revision: "RC1", content_digest: "A".repeat(64),
  display_name: "ICE — Isophthalic polyester", company: "ICE", resin: "ISOPHTHALIC_POLYESTER",
  source_kind: "ASCE_74_23_MINIMUM_CHARACTERISTIC_SHAPE_SPECIFICATION", property_basis: ASCE_SHAPE_BASIS,
  qualification: "CODE_MATERIAL_SPECIFICATION_REQUIREMENT", missing: ["ACTUAL_TG"], properties: [
    { id: "tensile_strength_L", label: "Tensile L", symbol: "Ft,L", original: "30", unit: "ksi", basis: ASCE_SHAPE_BASIS },
    { id: "pull_through_frp_thickness_0_500_in", label: "Pull-through at FRP thickness t=.5 in", symbol: "Fpt(t)", original: ".9", unit: "kip", basis: ASCE_SHAPE_BASIS },
  ] };
const vinyl: MAT1CatalogRecord = { ...poly, id: "ICE_VINYL_ESTER_ASCE74_23_MIN_SHAPE_RC1", display_name: "ICE — Vinyl ester", resin: "VINYL_ESTER" };
const legacy: MAT1CatalogRecord = { ...poly, id: "ICE_ISOPHTHALIC_POLYESTER_OWNER_SEED_RC0", revision: "RC0", property_basis: "DEVELOPMENT_NOMINAL", source_kind: "OWNER_SUPPLIED_NOMINAL_DATASET" };
const conditions: MAT1Conditions = { sustained_temperature: { value: "70", unit: "degF" }, maximum_temperature: { value: "100", unit: "degF" },
  glass_transition_temperature: null, moisture: "REFERENCE", chemical: "NONE_DECLARED", time_effect_category: "WIND_TORNADO_SEISMIC", load_case_name: "F5 QA ONLY", source_reference_condition: "UNKNOWN",
  chemical_substance: "", chemical_concentration: "", chemical_contact_form: "", chemical_duration: "", uv_weathering: "NONE_DECLARED", freeze_thaw: "NONE_DECLARED", protective_measures: "", exposure_notes: "", action_provenance: "", live_load_subtype: "", full_amplitude_duration: "", design_period: "", service_period: "", fatigue_cycles: "" };
const resolved = { contract: "MAT1-FACTOR-RC0" as const, result_status: "CODE_MATERIAL_SPECIFICATION_REQUIREMENT", record_id: poly.id,
  design_check_performed: false as const, ledgers: [{ issues: [] }], condition_basis: { status: "SPECIFICATION_REQUIREMENT_SATISFIED_BY_PROJECT_CONFORMANCE", required_tg: { value: "180", unit: "degF" as const }, required_tg_degC: "82.222222222222222222", project_issues: [] } };
const direct = JSON.stringify({ direct_finalization_contract_version: "SHEAR01-DIRECT-F1" });

beforeEach(() => { clearMAT1Sessions(); setMAT1Catalog([legacy, poly, vinyl]); setMAT1Default(legacy.id); setMAT1DirectMaterial(poly.id); setMAT1Conditions(conditions); setMAT1Active(true); rememberMAT1Preview("multi-row", direct);
  vi.spyOn(service, "loadMAT1Owners").mockResolvedValue(["BRACE", "COLUMN"]);
  vi.spyOn(service, "inspectMAT1Factors").mockResolvedValue(resolved);
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); rememberMAT1Preview("multi-row", "{}"); });

it("uses two production selections in Direct while preserving other-family legacy binding", async () => {
  render(<MAT1MaterialsPanel family="multi-row" />);
  const select = screen.getByLabelText("Connection default material");
  expect(within(select).getByRole("option", { name: poly.display_name })).toBeInTheDocument();
  expect(within(select).getByRole("option", { name: vinyl.display_name })).toBeInTheDocument();
  expect(within(select).queryByText(/RC0/)).not.toBeInTheDocument();
  expect(mat1DefaultId("multi-row")).toBe(poly.id);
  expect(mat1DefaultId("beam-web-splice")).toBe(legacy.id);
  expect(screen.queryByLabelText("Tg applicability")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Source reference condition")).not.toBeInTheDocument();
  await waitFor(() => { expect(screen.getByLabelText("Tg requirement")).toHaveTextContent(">= 180 °F (82.222 °C)"); });
  expect(screen.getByRole("region", { name: "ASCE shape material design basis" })).toHaveClass("information-status");
  fireEvent.change(select, { target: { value: vinyl.id } });
  expect(mat1DefaultId("multi-row")).toBe(vinyl.id);
  expect(mat1DefaultId("beam-web-splice")).toBe(legacy.id);
});

it("retains imported extraordinary exposure evidence without exposing removed Direct controls", () => {
  render(<MAT1MaterialsPanel family="multi-row" />);
  const original = mat1FamilyKey("multi-row");
  act(() => { acceptMAT1Design("multi-row", original, { overall_status: "ENGINEERING_REVIEW_REQUIRED", material_ledgers: [{ property_id: "tensile_strength_L", cm: "1", ct: "1", cch: "1", lambda_factor: "1", adjusted_candidate: "30" }] }); });
  expect(screen.getByText(/ASCE shape specification/)).toBeInTheDocument();
  expect(screen.queryByLabelText("Extraordinary UV / weathering")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Extraordinary freeze-thaw")).not.toBeInTheDocument();
  act(() => { setMAT1Conditions({ ...conditions, uv_weathering: "SPECIFIED", freeze_thaw: "UNKNOWN" }); });
  expect(mat1Snapshot().conditions.uv_weathering).toBe("SPECIFIED");
  expect(mat1Snapshot().conditions.freeze_thaw).toBe("UNKNOWN");
  expect(mat1FamilyKey("multi-row")).not.toBe(original);
  expect(screen.getByText(/Run Design Check to see/)).toBeInTheDocument();
  fireEvent.click(screen.getByText("View properties"));
  expect(screen.getByText("Pull-through at FRP thickness t=.5 in")).toBeInTheDocument();
});

it("keeps explicit legacy selection source-gated and allows return to production", () => {
  render(<MAT1MaterialsPanel family="multi-row" />);
  fireEvent.change(screen.getByLabelText("Development / legacy material"), { target: { value: legacy.id } });
  expect(mat1DefaultId("multi-row")).toBe(legacy.id);
  expect(screen.getByText(/Material basis needed/)).toBeInTheDocument();
  expect(screen.getByLabelText("Tg applicability")).toHaveTextContent("NOT CONFIRMED");
  expect(screen.getByText(/DEVELOPMENT DATA/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Actual Tg from controlled custom source"), { target: { value: "179.999" } });
  expect(mat1Snapshot().directConditions?.glass_transition_temperature?.value).toBe("179.999");
  fireEvent.change(screen.getByLabelText("Actual Tg from controlled custom source"), { target: { value: "" } });
  expect(mat1Snapshot().directConditions?.glass_transition_temperature).toBeNull();
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: poly.id } });
  expect(screen.queryByLabelText("Tg applicability")).not.toBeInTheDocument();
});

it("copies production values as unqualified custom data and does not import discrete thickness methods", () => {
  vi.stubGlobal("crypto", { randomUUID: () => "f5-copy" });
  const id = createMAT1Session(poly);
  setMAT1DirectMaterial(id);
  expect(mat1Snapshot().custom[id]?.properties.tensile_strength_L?.basis).toBe("UNKNOWN");
  expect(mat1Snapshot().custom[id]?.properties.pull_through_frp_thickness_0_500_in).toBeUndefined();
  expect(materialSelection(id)).toMatchObject({ kind: "SESSION", copied_from: poly.id });
  expect(deleteMAT1Session(id)).toBe(false);
  clearMAT1Sessions();
  expect(mat1DefaultId("multi-row")).toBeNull();
  expect(mat1DefaultId("clip-angle")).toBe(legacy.id);
});

it("binds the selected production identity to Direct transport and signed result authority", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ native_design: { preview: {} }, material_sources: { default: { id: poly.id, property_basis: ASCE_SHAPE_BASIS } }, material_ledgers: [] }), { status: 200, headers: { "X-Report-Handle": "f5-signed" } })));
  await mat1Fetch("/api/v1/calculations/multi-row/design-check", { method: "POST", body: JSON.stringify({ direct_finalization_contract_version: "SHEAR01-DIRECT-F1", layers: [] }) });
  const mock = vi.mocked(fetch);
  const body = mock.mock.calls[0]?.[1]?.body;
  expect(typeof body).toBe("string");
  const request = JSON.parse(body as string) as { assignments: { default_material: { id: string }; default_conditions: MAT1Conditions } };
  expect(request.assignments.default_material.id).toBe(poly.id);
  expect(request.assignments.default_conditions.source_reference_condition).toBe("UNKNOWN");
  expect(mat1Snapshot().designTraces["multi-row"]).toMatchObject({ material_sources: { default: { id: poly.id } } });
});

it("shows backend Tg and project-source requirements without deriving engineering values in the UI", async () => {
  vi.mocked(service.inspectMAT1Factors).mockResolvedValue({ ...resolved, ledgers: [{ issues: ["TEST_BASED_TEMPERATURE_FACTOR_REQUIRED", "EXTRAORDINARY_UV_WEATHERING_REVIEW_REQUIRED"] }], condition_basis: { ...resolved.condition_basis, required_tg: { value: "190", unit: "degF" }, required_tg_degC: "87.7777777777777777" } });
  render(<ASCEShapeBasisSummary record={poly} conditions={{ ...conditions, maximum_temperature: { value: "150", unit: "degF" } }} />);
  await waitFor(() => { expect(screen.getByLabelText("Tg requirement")).toHaveTextContent(">= 190 °F"); });
  expect(screen.getByText("test based temperature factor required")).toBeInTheDocument();
  expect(screen.getByText("extraordinary uv weathering review required")).toBeInTheDocument();
});

it("keeps incomplete and stale requirements pending and prevents late response overwrite", async () => {
  let resolve: ((r: Awaited<ReturnType<typeof service.inspectMAT1Factors>>) => void) | undefined;
  vi.mocked(service.inspectMAT1Factors).mockImplementation(() => new Promise(r => { resolve = r; }));
  const view = render(<ASCEShapeBasisSummary record={poly} conditions={conditions} />);
  view.rerender(<ASCEShapeBasisSummary record={vinyl} conditions={{ ...conditions, maximum_temperature: { value: "", unit: "degF" } }} />);
  await act(async () => { resolve?.(resolved); await Promise.resolve(); });
  expect(screen.getByLabelText("Tg requirement")).toHaveTextContent("Complete project temperatures");
  expect(screen.getByLabelText("Tg requirement")).not.toHaveTextContent(">= 180");
});

it("shows an actionable current service error and hides errors belonging to an earlier selection", async () => {
  vi.mocked(service.inspectMAT1Factors).mockRejectedValueOnce(new Error("Material service unavailable; restart backend."));
  const view = render(<ASCEShapeBasisSummary record={poly} conditions={conditions} />);
  await waitFor(() => { expect(screen.getByRole("alert")).toHaveTextContent("restart backend"); });
  vi.mocked(service.inspectMAT1Factors).mockResolvedValue(resolved);
  view.rerender(<ASCEShapeBasisSummary record={vinyl} conditions={conditions} />);
  await waitFor(() => { expect(screen.getByLabelText("Tg requirement")).toHaveTextContent(">= 180"); });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("suppresses late errors after unmount and handles non-Error service failures", async () => {
  vi.mocked(service.inspectMAT1Factors).mockRejectedValueOnce("offline");
  const first = render(<ASCEShapeBasisSummary record={poly} conditions={conditions} />);
  await waitFor(() => { expect(screen.getByRole("alert")).toHaveTextContent("Check project conditions"); });
  first.unmount();
  let reject: ((e: Error) => void) | undefined;
  vi.mocked(service.inspectMAT1Factors).mockImplementation(() => new Promise((_r, j) => { reject = j; }));
  const second = render(<ASCEShapeBasisSummary record={poly} conditions={conditions} />);
  second.unmount();
  await act(async () => { reject?.(new Error("late")); await Promise.resolve(); });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("keeps unassigned Direct materials explicit in both ordinary and development selectors", () => {
  render(<MAT1MaterialsPanel family="multi-row" />);
  fireEvent.change(screen.getByLabelText("Development / legacy material"), { target: { value: "" } });
  expect(mat1DefaultId("multi-row")).toBeNull();
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: poly.id } });
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: "" } });
  expect(mat1DefaultId("multi-row")).toBeNull();
  expect(screen.getByText(/Material unavailable/)).toBeInTheDocument();
});

it("inspects applicable production factors without importing thickness-indexed pull-through into a connection", async () => {
  render(<MAT1MaterialsPanel family="multi-row" />);
  fireEvent.click(screen.getByRole("button", { name: "View calculated factors" }));
  await waitFor(() => { expect(screen.getByText(/ASCE shape specification factors calculated/)).toBeInTheDocument(); });
  expect(service.inspectMAT1Factors).toHaveBeenLastCalledWith(expect.objectContaining({ property_ids: ["tensile_strength_L"] }), expect.any(AbortSignal));
});

it("keeps resolved catalog basis yellow for missing methods and gives actual material failure RED precedence", () => {
  const unity: UnityView = { tone: "yellow", ratio: null, ratioText: "—", status: "Incomplete", governing: null, explanation: "Methods pending" };
  const view = render(<ConnectionWorkspaceShell family="multi-row" banner={<span>F5 material result</span>}><PersistentConnectionViewer unity={unity}><span>Model</span></PersistentConnectionViewer></ConnectionWorkspaceShell>);
  act(() => { acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { overall_status: "ENGINEERING_REVIEW_REQUIRED", material_sources: { default: { property_basis: ASCE_SHAPE_BASIS } } }); });
  expect(view.container.querySelector(".unity-indicator")).toHaveAttribute("data-unity-tone", "yellow");
  expect(screen.getByText(/ASCE shape material basis resolved/)).toBeInTheDocument();
  act(() => { acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { overall_status: "FAIL", material_issues: ["ACTUAL_TG_BELOW_PROJECT_REQUIREMENT"] }); });
  expect(view.container.querySelector(".unity-indicator")).toHaveAttribute("data-unity-tone", "red");
  expect(view.container.querySelector(".unity-indicator")).toHaveTextContent("ACTUAL_TG_BELOW_PROJECT_REQUIREMENT");
});
