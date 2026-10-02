import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MAT1MaterialsPanel } from "../src/features/MAT1MaterialsPanel";
import {
  acceptMAT1Design, clearMAT1Sessions, mat1FamilyKey, mat1Snapshot, rememberMAT1Preview,
  setMAT1Active, setMAT1Catalog, setMAT1CatalogError, setMAT1Conditions, setMAT1Default,
  setMAT1PreviewOwners, setMAT1Override,
} from "../src/state/mat1Session";
import type { MAT1CatalogRecord } from "../src/state/mat1Session";

const record: MAT1CatalogRecord = {
  id: "ICE:POLY", revision: "RC0", content_digest: "A".repeat(64),
  display_name: "ICE polyester", company: "ICE", resin: "ISOPHTHALIC_POLYESTER",
  source_kind: "OWNER_SUPPLIED_NOMINAL_DATASET", missing: ["TG"], qualification: "OWNER_DATA",
  properties: [{ id: "tensile_strength_L", label: "Tensile L", symbol: "Ft,L", original: "33", unit: "ksi", basis: "NOMINAL_AS_SUPPLIED" }],
};

afterEach(() => { vi.unstubAllGlobals(); });

it("exposes catalog, session copy, physical owners, conditions and stale trace without design on preview", async () => {
  // OR1-09: the product bootstrap owns catalog transport; this panel consumes its resolved record.
  setMAT1Catalog([record]); setMAT1Default(record.id); setMAT1Active(true);
  vi.stubGlobal("crypto", { randomUUID: () => "panel-id" });
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const path = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (path.endsWith("/owners")) return Promise.resolve(new Response(JSON.stringify({ contract: "MAT1-OWNER-PREVIEW-RC0", family_id: "beam-web-splice", owners: ["FRP-A", "FRP-B"], design_check_performed: false }), { status: 200 }));
    if (path.endsWith("/factor-candidates")) return Promise.resolve(new Response(JSON.stringify({ contract: "MAT1-FACTOR-RC0", record_id: record.id, ledgers: [{ component_id: "FRP-A", adjusted_candidate: "21" }], design_check_performed: false }), { status: 200 }));
    throw new Error(`Unexpected request ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  rememberMAT1Preview("beam-web-splice", '{"request_id":"PREVIEW-1"}');
  render(<MAT1MaterialsPanel family="beam-web-splice" />);
  await waitFor(() => { expect(screen.getByText(/ICE · ISOPHTHALIC POLYESTER · RC0/)).toBeTruthy(); });
  await waitFor(() => { expect(screen.getByText(/Compatible FRP targets: FRP-A, FRP-B/)).toBeTruthy(); });
  expect(fetchMock).toHaveBeenCalledTimes(1);
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: record.id } });
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: "" } });
  expect(mat1Snapshot().defaultId).toBeNull();
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: record.id } });
  fireEvent.click(screen.getByText("Copy as session material"));
  expect(screen.getByLabelText("Session material name")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Session material name"), { target: { value: "Project coupon" } });
  fireEvent.change(screen.getByLabelText("Company/source label"), { target: { value: "Project lab" } });
  fireEvent.change(screen.getByLabelText("Resin"), { target: { value: "VINYL_ESTER" } });
  fireEvent.click(screen.getByText("View properties"));
  expect(screen.queryByLabelText("Tensile L value")).toBeNull();
  fireEvent.click(screen.getByText("View properties"));
  fireEvent.change(screen.getByLabelText("Tensile L value"), { target: { value: "40" } });
  expect(record.properties[0]?.original).toBe("33");
  fireEvent.change(screen.getByLabelText("Tensile L source basis"), { target: { value: "CHARACTERISTIC" } });
  const conditionDetails = screen.getByText("Project conditions and load case").closest("details");
  if (conditionDetails === null) throw new Error("Project conditions details missing");
  conditionDetails.open = true;
  fireEvent(conditionDetails, new Event("toggle"));
  fireEvent.change(screen.getByLabelText("Sustained material temperature"), { target: { value: "90" } });
  fireEvent.change(screen.getByLabelText("Maximum material temperature"), { target: { value: "100" } });
  fireEvent.change(screen.getByLabelText("Sustained material temperature"), { target: { value: "95" } });
  fireEvent.change(screen.getByLabelText("Temperature unit"), { target: { value: "degC" } });
  fireEvent.change(screen.getByLabelText("Sustained material temperature"), { target: { value: "30" } });
  fireEvent.change(screen.getByLabelText("Maximum material temperature"), { target: { value: "40" } });
  expect(screen.queryByLabelText("Glass transition temperature (Tg; optional evidence)")).toBeNull();
  fireEvent.change(screen.getByLabelText("Moisture"), { target: { value: "SUSTAINED_MOISTURE" } });
  fireEvent.change(screen.getByLabelText("Chemical exposure"), { target: { value: "SPECIFIED" } });
  for (const [label, value] of [["Substance", "salt"], ["Concentration", "5%"], ["Contact form", "spray"], ["Duration", "one year"]] as const) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.change(screen.getByLabelText("Load case name (required)"), { target: { value: "" } });
  expect(screen.getByRole("alert")).toHaveTextContent("Enter a load-case name");
  fireEvent.change(screen.getByLabelText("Load case name (required)"), { target: { value: "LC-1" } });
  fireEvent.change(screen.getByLabelText("Load present in this submitted combination"), { target: { value: "WIND_TORNADO_SEISMIC" } });
  fireEvent.change(screen.getByLabelText("Source reference condition"), { target: { value: "REFERENCE" } });
  fireEvent.change(screen.getByLabelText("UV / weathering"), { target: { value: "SPECIFIED" } });
  fireEvent.change(screen.getByLabelText("Freeze–thaw"), { target: { value: "NONE_DECLARED" } });
  for (const [label, value] of [["Protective measures", "coated"], ["Exposure notes", "outside"], ["Action provenance", "factored"], ["Design period", "30 y"], ["Service period", "20 y"], ["Fatigue cycles", "1000"]] as const) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByText("View calculated factors"));
  await waitFor(() => { expect(fetchMock).toHaveBeenCalledTimes(2); });
  const ownerA = screen.getByText("FRP-A").closest(".mat1-owner-assignment");
  expect(ownerA).not.toBeNull();
  fireEvent.change(within(ownerA as HTMLElement).getByLabelText("FRP-A"), { target: { value: record.id } });
  fireEvent.click(within(ownerA as HTMLElement).getByLabelText("Override conditions for FRP-A"));
  fireEvent.change(within(ownerA as HTMLElement).getByLabelText(/Sustained material temperature/), { target: { value: "35" } });
  fireEvent.change(within(ownerA as HTMLElement).getByLabelText(/Maximum material temperature/), { target: { value: "45" } });
  fireEvent.change(within(ownerA as HTMLElement).getByLabelText("Moisture"), { target: { value: "OTHER" } });
  fireEvent.change(within(ownerA as HTMLElement).getByLabelText("Chemical exposure"), { target: { value: "NONE_DECLARED" } });
  fireEvent.change(within(ownerA as HTMLElement).getByLabelText("Source reference condition"), { target: { value: "UNKNOWN" } });
  fireEvent.click(within(ownerA as HTMLElement).getByLabelText("Override conditions for FRP-A"));
  expect(mat1Snapshot().conditionOverrides["beam-web-splice"]?.["FRP-A"]).toBeUndefined();
  fireEvent.change(within(ownerA as HTMLElement).getByLabelText("FRP-A"), { target: { value: "__UNASSIGNED" } });
  expect(mat1Snapshot().overrides["beam-web-splice"]?.["FRP-A"]).toBeNull();
  fireEvent.change(within(ownerA as HTMLElement).getByLabelText("FRP-A"), { target: { value: "" } });
  expect(mat1Snapshot().overrides["beam-web-splice"]?.["FRP-A"]).toBeUndefined();
  fireEvent.click(screen.getByText("Apply selected material to compatible FRP components"));
  expect(mat1Snapshot().overrides["beam-web-splice"]?.["FRP-A"]).toBe(mat1Snapshot().defaultId);
  const key = mat1FamilyKey("beam-web-splice");
  expect(acceptMAT1Design("beam-web-splice", key, { overall_status: "SOURCE_REQUIRED", material_ledgers: [{ component_id: "FRP-A" }] })).toBe(true);
  await waitFor(() => { expect(screen.getByText(/Design status: SOURCE_REQUIRED/)).toBeTruthy(); });
  fireEvent.click(screen.getByText("Material adjustment trace"));
  expect(screen.queryByText(/Design status: SOURCE_REQUIRED/)).toBeNull();
  fireEvent.click(screen.getByText("Material adjustment trace"));
  setMAT1Conditions({ ...mat1Snapshot().conditions, moisture: "REFERENCE" });
  await waitFor(() => { expect(screen.getByText(/Design result stale or not run/)).toBeTruthy(); });
  expect(acceptMAT1Design("beam-web-splice", mat1FamilyKey("beam-web-splice"), {})).toBe(true);
  await waitFor(() => { expect(screen.getByText(/Design status: SOURCE_REQUIRED/)).toBeTruthy(); });
  fireEvent.click(screen.getByText("Clear session materials"));
  expect(mat1Snapshot().defaultId).toBeNull();
  expect(screen.getByText(/Session materials cleared/)).toBeTruthy();
  setMAT1Default(record.id);
});

it("reports catalog and owner preview failures and keeps unreferenced session deletion safe", async () => {
  setMAT1Active(false); setMAT1Catalog([]); clearMAT1Sessions(); setMAT1Default(null); setMAT1Active(true);
  vi.stubGlobal("crypto", { randomUUID: () => "error-session" });
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response("{}", { status: 422 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ contract: "MAT1-OWNER-PREVIEW-RC0", family_id: "paired-clip-angle", owners: null, design_check_performed: true }), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  render(<MAT1MaterialsPanel family="paired-clip-angle" />);
  // OR1-09: catalog errors are supplied by the typed product bootstrap, not an independent panel fetch.
  setMAT1CatalogError("Material catalog unavailable.");
  await waitFor(() => { expect(screen.getByRole("alert").textContent).toContain("Material catalog unavailable"); });
  setMAT1Catalog([record]);
  rememberMAT1Preview("paired-clip-angle", '{"id":1}');
  await waitFor(() => { expect(screen.getByRole("status").textContent).toContain("Check the required material and project condition fields"); });
  rememberMAT1Preview("paired-clip-angle", '{"id":2}');
  await waitFor(() => { expect(screen.getByRole("status").textContent).toContain("MAT1 owner preview contract is invalid"); });
  setMAT1PreviewOwners("paired-clip-angle", '{"id":2}', ["POSITIVE_CLIP_ANGLE"]);
  fireEvent.click(screen.getByText("New session material"));
  expect(screen.getByText(/Linked-material method/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Add property"), { target: { value: "" } });
  fireEvent.click(screen.getByText("View calculated factors"));
  expect(screen.getByRole("status").textContent).toContain("complete the project conditions");
  fireEvent.change(screen.getByLabelText("Add property"), { target: { value: "tensile_strength_L" } });
  expect(screen.getByLabelText("Tensile L value")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: record.id } });
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: "SESSION:error-session" } });
  fireEvent.click(screen.getByText("Delete New session material"));
  expect(screen.getByRole("status").textContent).toContain("Reassign components");
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: record.id } });
  fireEvent.click(screen.getByText("Delete New session material"));
  expect(screen.getByRole("status").textContent).toContain("Session material deleted");
});

it("reports factor transport errors and keeps aborted owner requests silent", async () => {
  setMAT1Active(false); setMAT1Catalog([]); clearMAT1Sessions(); setMAT1Default(null); setMAT1Active(true);
  const pending: ((error: Error) => void)[] = [];
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((_resolve, reject) => { pending.push(reject); })));
  setMAT1Catalog([record]);
  rememberMAT1Preview("beam-web-splice", '{"request_id":"ABORT"}');
  const first = render(<MAT1MaterialsPanel family="beam-web-splice" />);
  await waitFor(() => { expect(pending).toHaveLength(1); });
  fireEvent.click(screen.getByText("New session material"));
  expect(screen.getByLabelText("Add property").querySelectorAll("option")).toHaveLength(2);
  clearMAT1Sessions();
  first.unmount();
  pending[0]?.(new Error("aborted owner preview"));
  expect(mat1Snapshot().catalogError).toBeNull();
  rememberMAT1Preview("beam-web-splice", '{"request_id":"ABORT-2"}');
  const second = render(<MAT1MaterialsPanel family="beam-web-splice" />);
  await waitFor(() => { expect(pending).toHaveLength(2); });
  second.unmount();
  pending[1]?.(new Error("aborted owner preview"));
  expect(mat1Snapshot().catalogError).toBeNull();
  setMAT1PreviewOwners("beam-web-splice", '{"request_id":"ABORT-2"}', ["FRP-A"]);

  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("{}", { status: 503 }))));
  render(<MAT1MaterialsPanel family="beam-web-splice" />);
  fireEvent.click(screen.getByText("View calculated factors"));
  expect(screen.getByRole("status").textContent).toContain("Select a material");
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: record.id } });
  act(() => { setMAT1Conditions({
    ...mat1Snapshot().conditions,
    sustained_temperature: { value: "90", unit: "degF" },
    maximum_temperature: { value: "90", unit: "degF" },
    load_case_name: "LC-1",
    time_effect_category: "WIND_TORNADO_SEISMIC",
  }); });
  fireEvent.click(screen.getByText("View calculated factors"));
  await waitFor(() => { expect(screen.getByRole("status").textContent).toContain("Unable to complete the material request"); });
});

it("preserves blank and invalid temperature evidence during unit changes", () => {
  setMAT1Catalog([record]); setMAT1Default(record.id); setMAT1Active(true);
  setMAT1Conditions({ ...mat1Snapshot().conditions,
    sustained_temperature: { value: "", unit: "degF" },
    maximum_temperature: { value: "not-a-number", unit: "degF" },
    glass_transition_temperature: { value: "212", unit: "degF" },
  });
  render(<MAT1MaterialsPanel family="beam-web-splice" />);
  fireEvent.change(screen.getByLabelText("Temperature unit"), { target: { value: "degC" } });
  expect(mat1Snapshot().conditions.sustained_temperature.value).toBe("");
  expect(mat1Snapshot().conditions.maximum_temperature.value).toBe("not-a-number");
  expect(mat1Snapshot().conditions.glass_transition_temperature?.value).toBe("100");
});

it("shows resolved, not-applicable, and source-required factors from the current signed trace", () => {
  setMAT1Catalog([record]); setMAT1Default(record.id); setMAT1Active(false);
  const view = render(<MAT1MaterialsPanel family="beam-web-splice" />);
  expect(screen.queryByLabelText("Connection default material")).not.toBeInTheDocument();
  act(() => { setMAT1Active(true); });
  expect(screen.getByLabelText("Connection default material")).toBeInTheDocument();
  act(() => { expect(acceptMAT1Design("beam-web-splice", mat1FamilyKey("beam-web-splice"), {
    overall_status: "SOURCE_REQUIRED",
    material_ledgers: [
      { component_id: "FRP-A", property_id: "tensile_modulus_L", cm: 0.75, ct: 1, cch: true, lambda_factor: null },
      { component_id: "FRP-A", property_id: "tensile_strength_L", cm: "0.75", ct: "1", cch: null, lambda_factor: "0.8" },
      { component_id: "FRP-A", property_id: 12, cm: null, ct: false, cch: "1", lambda_factor: "1" },
    ],
  })).toBe(true); });
  expect(screen.getByText("Not applicable to modulus")).toBeVisible();
  expect(screen.getAllByText("Source required").length).toBeGreaterThan(0);
  expect(screen.getByText("Strength")).toBeVisible();
  expect(screen.getByText("Property")).toBeVisible();
  fireEvent.change(screen.getByLabelText("Load present in this submitted combination"), { target: { value: "LONG_TERM_OPERATING" } });
  fireEvent.change(screen.getByLabelText("Full nominal operating amplitude"), { target: { value: "MORE_THAN_ONE_YEAR" } });
  expect(mat1Snapshot().conditions.full_amplitude_duration).toBe("MORE_THAN_ONE_YEAR");
  fireEvent.change(screen.getByLabelText("Load present in this submitted combination"), { target: { value: "" } });
  expect(mat1Snapshot().conditions.live_load_subtype).toBe("");
  fireEvent.change(screen.getByLabelText("Temperature unit"), { target: { value: "degC" } });
  fireEvent.change(screen.getByLabelText("Temperature unit"), { target: { value: "degF" } });
  view.unmount();
});

it("offers no invented property seeds when the controlled catalog is unavailable", () => {
  setMAT1Catalog([]); setMAT1Default(null); setMAT1Active(true);
  vi.stubGlobal("crypto", { randomUUID: () => "no-catalog-session" });
  render(<MAT1MaterialsPanel family="beam-web-splice" />);
  fireEvent.click(screen.getByRole("button", { name: "New session material" }));
  expect(screen.getByLabelText("Add property").querySelectorAll("option")).toHaveLength(1);
});

it("binds a new linked Direct material automatically and catches an empty load-case name before a factor request", () => {
  setMAT1Catalog([record]); setMAT1Default(record.id); setMAT1Active(true);
  setMAT1Override("multi-row", "member-a", record.id);
  setMAT1Override("multi-row", "member-b", record.id);
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  render(<MAT1MaterialsPanel family="multi-row" />);
  expect(screen.getByText(/Selected FRP material applies to the angle brace and supporting W member/)).toBeVisible();
  expect(screen.queryByRole("button", { name: "Apply selected material to compatible FRP components" })).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: "" } });
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: record.id } });
  expect(mat1Snapshot().overrides["multi-row"]).toEqual({});
  act(() => { setMAT1Conditions({ ...mat1Snapshot().conditions, load_case_name: "" }); });
  expect(screen.getByRole("alert")).toHaveTextContent("Enter a load-case name");
  fireEvent.click(screen.getByText("Advanced Engineering Diagnostics · FRP component assignments and factor trace"));
  fireEvent.click(screen.getByText("View calculated factors"));
  expect(screen.getByRole("status")).toHaveTextContent("Enter a load-case name");
  expect(fetchMock).not.toHaveBeenCalled();
});

it("clears obsolete material errors after current calculation and labels unknown adjustments", async () => {
  setMAT1Catalog([record]); setMAT1Default(record.id); setMAT1Active(true);
  setMAT1Conditions({ ...mat1Snapshot().conditions, sustained_temperature: { value: "70", unit: "degF" }, maximum_temperature: { value: "70", unit: "degF" }, time_effect_category: "WIND_TORNADO_SEISMIC", load_case_name: "OR2-QA" });
  rememberMAT1Preview("paired-clip-angle", '{"id":"current-error"}');
  setMAT1PreviewOwners("paired-clip-angle", '{"id":"current-error"}', []);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 422 })));
  render(<MAT1MaterialsPanel family="paired-clip-angle" />);
  fireEvent.click(screen.getByText("Advanced Engineering Diagnostics · FRP component assignments and factor trace"));
  fireEvent.click(screen.getByRole("button", { name: "View calculated factors" }));
  expect(await screen.findByText("Error: Check the required material and project condition fields, then try again.")).toBeVisible();
  act(() => { acceptMAT1Design("paired-clip-angle", mat1FamilyKey("paired-clip-angle"), { overall_status: "SOURCE_REQUIRED", material_ledgers: [{ property_id: "tensile_strength_L", adjusted_candidate: null }] }); });
  expect(screen.queryByText("Error: Check the required material and project condition fields, then try again.")).not.toBeInTheDocument();
  expect(screen.getByText("Diagnostic only — adjusted resistance unavailable.")).toBeVisible();
});

it("ignores a successful owner response after its preview is aborted", async () => {
  setMAT1Active(true);
  rememberMAT1Preview("paired-clip-angle", '{"id":"late-owner-success"}');
  let resolveResponse: ((value: Response) => void) | undefined;
  const fetchMock = vi.fn(() => new Promise<Response>((resolve) => { resolveResponse = resolve; }));
  vi.stubGlobal("fetch", fetchMock);
  const view = render(<MAT1MaterialsPanel family="paired-clip-angle" />);
  await waitFor(() => { expect(fetchMock).toHaveBeenCalledTimes(1); });
  view.unmount();
  await act(async () => { resolveResponse?.(new Response(JSON.stringify({ contract: "MAT1-OWNER-PREVIEW-RC0", family_id: "paired-clip-angle", owners: ["late"], design_check_performed: false }))); await Promise.resolve(); });
  expect(mat1Snapshot().previewOwnerKeys["paired-clip-angle"]).not.toBe('{"id":"late-owner-success"}');
});
