import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MAT1MaterialsPanel } from "../src/features/MAT1MaterialsPanel";
import { adoptDirectConditions, DIRECT_LOAD_CLASSIFICATIONS, validChemicalStrengthFactor } from "../src/features/directMaterialConditions";
import { materialConditionIssues } from "../src/features/materialConditionValidation";
import * as service from "../src/api/mat1Service";
import { mat1Fetch } from "../src/api/mat1Transport";
import {
  ASCE_SHAPE_BASIS, DIRECT_PRODUCTION_MATERIAL_ID, acceptMAT1Design,
  createMAT1Session,
  mat1Conditions, mat1FamilyKey, mat1Snapshot, rememberMAT1Preview,
  setMAT1Active, setMAT1Catalog, setMAT1CatalogError, setMAT1Conditions,
  setMAT1DirectConditions, setMAT1DirectMaterial,
} from "../src/state/mat1Session";
import type { MAT1CatalogRecord, MAT1Conditions } from "../src/state/mat1Session";

const record: MAT1CatalogRecord = { id: DIRECT_PRODUCTION_MATERIAL_ID, revision: "RC1", content_digest: "A".repeat(64),
  display_name: "ICE polyester MC1", company: "ICE", resin: "ISOPHTHALIC_POLYESTER", source_kind: "ASCE", property_basis: ASCE_SHAPE_BASIS,
  qualification: "CODE_SPECIFICATION", missing: [], properties: [{ id: "tensile_strength_L", label: "Tensile L", symbol: "Ft", original: "30", unit: "ksi", basis: ASCE_SHAPE_BASIS }] };
let legacy: MAT1Conditions;
beforeEach(() => {
  const old = { ...mat1Snapshot().conditions };
  delete old.direct_policy;
  delete old.design_temperature;
  delete old.chemical_strength_factor;
  legacy = { ...old, sustained_temperature: { value: "70", unit: "degF" }, maximum_temperature: { value: "100", unit: "degF" },
    moisture: "REFERENCE", chemical: "NONE_DECLARED", load_case_name: "LC-1", time_effect_category: "WIND_TORNADO_SEISMIC",
    uv_weathering: "UNKNOWN", freeze_thaw: "UNKNOWN", full_amplitude_duration: "", live_load_subtype: "" };
  setMAT1Conditions(legacy); setMAT1DirectMaterial(record.id); setMAT1Catalog([record]); setMAT1Active(true);
  rememberMAT1Preview("multi-row", JSON.stringify({ direct_finalization_contract_version: "SHEAR01-DIRECT-F1" }));
  vi.spyOn(service, "loadMAT1Owners").mockResolvedValue(["BRACE", "COLUMN"]);
  vi.spyOn(service, "inspectMAT1Factors").mockResolvedValue({ contract: "MAT1-FACTOR-RC0", design_check_performed: false,
    result_status: "CODE_SPECIFICATION", record_id: record.id, ledgers: [{ lambda_factor: "1", issues: [] }],
    condition_basis: { status: "SPECIFICATION", required_tg: { value: "180", unit: "degF" }, required_tg_degC: "82.22222222", project_issues: [] } });
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); rememberMAT1Preview("multi-row", "{}"); setMAT1Conditions(legacy); });

it.each(["", "bad", "NaN", "Infinity", "-Infinity", "-.01", "0", "-0", "1.000000000000000001", "1e1", ".", "e0", "1e999999999999999999", "1e-999999999999999999", true as unknown as string])("rejects invalid chemical strength factor %s", value => {
  expect(validChemicalStrengthFactor(value)).toBe(false);
});
it.each([".8", "1", "1.00", "+0.80", "1e-88", ".0000000000001", "10e-1", "  .8  "])("accepts exact valid chemical strength factor %s", value => {
  expect(validChemicalStrengthFactor(value)).toBe(true);
});

it("adopts the higher physical legacy temperature without editing legacy state or auto-classifying", async () => {
  render(<MAT1MaterialsPanel family="multi-row" />);
  expect(screen.getByLabelText("Design Temperature")).toHaveValue("100");
  expect(screen.getByText(/adopts the higher prior value/)).toBeVisible();
  expect(mat1Snapshot().conditions).toEqual(legacy);
  expect(mat1Conditions("multi-row").load_case_name).toBe("DIRECT-FACTORED-ACTION");
  expect(mat1Conditions("clip-angle")).toBe(legacy);
  expect(screen.queryByLabelText(/Load case name/)).not.toBeInTheDocument();
  for (const label of ["Extraordinary UV / weathering", "UV / weathering", "Freeze–thaw", "Protective measures", "Exposure notes", "Substance", "Concentration", "Duration"]) expect(screen.queryByLabelText(label)).not.toBeInTheDocument();
  expect(within(screen.getByLabelText("Moisture condition")).getAllByRole("option").filter(o => !(o as HTMLOptionElement).disabled)).toHaveLength(2);
  expect(within(screen.getByLabelText("Chemical environment")).getAllByRole("option").filter(o => !(o as HTMLOptionElement).disabled)).toHaveLength(2);
  expect(within(screen.getByLabelText("Load Combination Classification")).getAllByRole("option")).toHaveLength(8);
  const advanced = screen.getByText("Advanced Material Details").closest("details");
  expect(advanced).not.toHaveAttribute("open");
  fireEvent.click(screen.getByLabelText("Help: Load Combination Classification"));
  expect(screen.getByLabelText("Help: Load Combination Classification").closest("details")).toHaveAttribute("open");
  await waitFor(() => { expect(screen.getByText("Resistance time-effect factor λ:")).toHaveTextContent("1"); });
});

it("supports compact selections, custom factor validation, strength-only disclosure and staleness", async () => {
  render(<MAT1MaterialsPanel family="multi-row" />);
  const key = mat1FamilyKey("multi-row");
  act(() => { acceptMAT1Design("multi-row", key, {}); });
  fireEvent.change(screen.getByLabelText("Moisture condition"), { target: { value: "SUSTAINED_MOISTURE" } });
  expect(mat1FamilyKey("multi-row")).not.toBe(key);
  fireEvent.change(screen.getByLabelText("Chemical environment"), { target: { value: "SPECIFIED" } });
  expect(screen.getByLabelText("Chemical strength factor C_CH")).toHaveAttribute("aria-invalid", "true");
  expect(screen.getByText(/Strength only · chemical-modulus/)).toBeVisible();
  fireEvent.change(screen.getByLabelText("Chemical strength factor C_CH"), { target: { value: ".8" } });
  expect(screen.getByLabelText("Chemical strength factor C_CH")).toHaveAttribute("aria-invalid", "false");
  fireEvent.change(screen.getByLabelText("Load Combination Classification"), { target: { value: "LONG_TERM_OPERATING" } });
  expect(mat1Conditions("multi-row").full_amplitude_duration).toBe("MORE_THAN_ONE_YEAR");
  expect(mat1Conditions("multi-row").live_load_subtype).toBe("LONG_TERM_OPERATING");
  fireEvent.change(screen.getByLabelText("Load Combination Classification"), { target: { value: "" } });
  expect(screen.getByText("Select the Load Combination Classification.")).toBeVisible();
  fireEvent.change(screen.getByLabelText("Load Combination Classification"), { target: { value: "OTHER_LIVE" } });
  expect(mat1Conditions("multi-row").live_load_subtype).toBe("OTHER_LIVE");
  fireEvent.change(screen.getByLabelText("Chemical environment"), { target: { value: "NONE_DECLARED" } });
  expect(mat1Conditions("multi-row").chemical_strength_factor).toBeUndefined();
  fireEvent.change(screen.getByLabelText("Chemical environment"), { target: { value: "SPECIFIED" } });
  expect(screen.getByLabelText("Chemical strength factor C_CH")).toHaveValue("");
  await waitFor(() => { expect(service.inspectMAT1Factors).toHaveBeenCalled(); });
});

it("switches display units without rounding the stored physical temperature or changing fingerprints", () => {
  render(<MAT1MaterialsPanel family="multi-row" />);
  const key = mat1FamilyKey("multi-row");
  fireEvent.change(screen.getByLabelText("Temperature unit"), { target: { value: "degC" } });
  expect(screen.getByLabelText("Design Temperature")).toHaveValue("37.777778");
  expect(mat1FamilyKey("multi-row")).toBe(key);
  fireEvent.change(screen.getByLabelText("Design Temperature"), { target: { value: "40" } });
  expect(mat1Conditions("multi-row").sustained_temperature).toEqual({ value: "40", unit: "degC" });
  expect(mat1Conditions("multi-row").maximum_temperature).toEqual({ value: "40", unit: "degC" });
  fireEvent.change(screen.getByLabelText("Temperature unit"), { target: { value: "degF" } });
  expect(screen.getByLabelText("Design Temperature")).toHaveValue("104");
  fireEvent.change(screen.getByLabelText("Design Temperature"), { target: { value: "" } });
  expect(screen.getByLabelText("Design Temperature")).toHaveAttribute("aria-invalid", "true");
});

it("requires explicit unknown selections and retains imported provenance", () => {
  act(() => { setMAT1Conditions({ ...legacy, moisture: "UNKNOWN", chemical: "UNKNOWN", time_effect_category: "", load_case_name: "IMPORTED COMBO", exposure_notes: "Known extraordinary exposure" }); });
  render(<MAT1MaterialsPanel family="multi-row" />);
  expect(screen.getByLabelText("Moisture condition")).toHaveValue("");
  expect(screen.getByLabelText("Chemical environment")).toHaveValue("");
  expect(screen.getByLabelText("Load Combination Classification")).toHaveValue("");
  expect(mat1Conditions("multi-row").load_case_name).toBe("IMPORTED COMBO");
  expect(mat1Conditions("multi-row").exposure_notes).toBe("Known extraordinary exposure");
  expect(screen.getByText(/Known extraordinary exposure/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("FRP material"), { target: { value: "" } });
  expect(screen.getByLabelText("Resin system")).toHaveTextContent("Choose FRP material");
  fireEvent.change(screen.getByLabelText("FRP material"), { target: { value: record.id } });
  act(() => { setMAT1CatalogError("Material service unavailable"); });
  expect(screen.getAllByRole("alert").some(e => e.textContent === "Material service unavailable")).toBe(true);
});

it.each([
  [{ value: "32", unit: "degF" }, { value: "0", unit: "degC" }, "32", null],
  [{ value: "40", unit: "degC" }, { value: "104", unit: "degF" }, "40", null],
  [{ value: "-10", unit: "degC" }, { value: "-10", unit: "degF" }, "-10", "higher"],
  [{ value: "1e2", unit: "degF" }, { value: "99", unit: "degF" }, "1e2", "higher"],
  [{ value: "bad", unit: "degF" }, { value: "100", unit: "degF" }, "100", null],
  [{ value: "", unit: "degF" }, { value: "", unit: "degF" }, "", null],
  [{ value: "0", unit: "degF" }, { value: "0", unit: "degF" }, "0", null],
  [{ value: ".01e-1", unit: "degF" }, { value: ".002", unit: "degF" }, ".002", "higher"],
  [{ value: "1e-1000", unit: "degF" }, { value: "0", unit: "degF" }, "1e-1000", "higher"],
  [{ value: "1e-999999999999999999", unit: "degF" }, { value: "1e-999999999999999998", unit: "degF" }, "1e-999999999999999998", "higher"],
  [{ value: "-1e-1000", unit: "degC" }, { value: "32", unit: "degF" }, "32", "higher"],
  [{ value: "1e-1000", unit: "degC" }, { value: "32", unit: "degF" }, "1e-1000", "higher"],
  [{ value: "1000", unit: "degF" }, { value: "-1", unit: "degF" }, "1000", "higher"],
  [{ value: "-1000", unit: "degF" }, { value: "1", unit: "degF" }, "1", "higher"],
  [{ value: ".", unit: "degF" }, { value: "NaN", unit: "degF" }, ".", null],
  [{ value: "0x10", unit: "degF" }, { value: "100", unit: "degF" }, "100", null],
] as const)("adopts physical legacy temperatures %j and %j", (sustained, maximum, chosen, message) => {
  const adopted = adoptDirectConditions({ ...legacy, sustained_temperature: sustained, maximum_temperature: maximum, load_case_name: "" });
  expect(adopted.conditions.design_temperature?.value).toBe(chosen);
  expect(adopted.adoption === null ? null : "higher").toBe(message);
});

it("blocks incomplete new material transport before any network call", async () => {
  vi.stubGlobal("fetch", vi.fn());
  const newState = adoptDirectConditions(legacy).conditions;
  act(() => { setMAT1DirectConditions({ ...newState, chemical: "SPECIFIED" }); });
  await expect(mat1Fetch("/api/v1/calculations/multi-row/design-check", { method: "POST", body: JSON.stringify({ layers: [] }) })).rejects.toThrow(/dimensionless/);
  expect(fetch).not.toHaveBeenCalled();
  const missingTemperature = { ...newState };
  delete missingTemperature.design_temperature;
  expect(materialConditionIssues(missingTemperature)).toHaveProperty("design_temperature");
  expect(materialConditionIssues({ ...newState, time_effect_category: "LONG_TERM_OPERATING" })).toHaveProperty("full_amplitude_duration");
  expect(materialConditionIssues({ ...newState, chemical: "SPECIFIED", chemical_strength_factor: ".8", time_effect_category: "LONG_TERM_OPERATING", full_amplitude_duration: "MORE_THAN_ONE_YEAR" })).toEqual({});
  expect(DIRECT_LOAD_CLASSIFICATIONS.map(c => c[0])).toHaveLength(7);
});

it("keeps optional session material editing and source evidence in the advanced section", async () => {
  vi.stubGlobal("crypto", { randomUUID: () => "mc1-session" });
  const id = createMAT1Session(record);
  setMAT1DirectMaterial(id);
  render(<MAT1MaterialsPanel family="multi-row" />);
  expect(within(screen.getByLabelText("FRP material")).getByRole("option", { name: /Session/ })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Source reference condition"), { target: { value: "REFERENCE" } });
  expect(mat1Conditions("multi-row").source_reference_condition).toBe("REFERENCE");
  fireEvent.change(screen.getByLabelText("Actual Tg from controlled custom source"), { target: { value: "190" } });
  expect(mat1Conditions("multi-row").glass_transition_temperature?.value).toBe("190");
  fireEvent.change(screen.getByLabelText("FRP material"), { target: { value: record.id } });
  fireEvent.change(screen.getByLabelText("Chemical environment"), { target: { value: "SPECIFIED" } });
  act(() => {
    const missingFactor = { ...mat1Conditions("multi-row") };
    delete missingFactor.chemical_strength_factor;
    setMAT1DirectConditions(missingFactor);
  });
  expect(screen.getByLabelText("Chemical strength factor C_CH")).toHaveValue("");
  await waitFor(() => { expect(service.inspectMAT1Factors).toHaveBeenCalled(); });
});

it("transports valid Direct policy with an explicit family witness to backend factor inspection", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ contract: "MAT1-FACTOR-RC0",
    design_check_performed: false, record_id: record.id, ledgers: [] }), { status: 200 })));
  // Restore only this method so the actual typed transport is exercised.
  vi.mocked(service.inspectMAT1Factors).mockRestore();
  await service.inspectMAT1Factors({ material: { kind: "CATALOG", id: record.id, revision: record.revision, content_digest: record.content_digest },
    conditions: adoptDirectConditions(legacy).conditions, component_id: "BRACE", property_ids: ["tensile_strength_L"] }, new AbortController().signal);
  expect(JSON.parse(vi.mocked(fetch).mock.calls[0]?.[1]?.body as string)).toMatchObject({ family_id: "multi-row" });
});

it("accepts complete new Direct transport without changing unrelated family conditions", async () => {
  setMAT1DirectConditions(adoptDirectConditions(legacy).conditions);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ native_design: { preview: {} } }), { status: 200 })));
  await mat1Fetch("/api/v1/calculations/multi-row/design-check", { method: "POST", body: JSON.stringify({ direct_finalization_contract_version: "SHEAR01-DIRECT-F1", layers: [] }) });
  const sent = JSON.parse(vi.mocked(fetch).mock.calls[0]?.[1]?.body as string) as { assignments: { default_conditions: MAT1Conditions } };
  expect(sent.assignments.default_conditions.direct_policy).toBe("SHEAR01-DIRECT-MC1");
  expect(mat1Conditions("clip-angle")).toEqual(legacy);
  expect(materialConditionIssues({ ...sent.assignments.default_conditions, design_temperature: { value: "0x10", unit: "degF" } })).toHaveProperty("design_temperature");
  expect(materialConditionIssues({ ...sent.assignments.default_conditions, design_temperature: { value: "1e9999", unit: "degF" } })).toHaveProperty("design_temperature");
});
