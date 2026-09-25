import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MAT1MaterialsPanel } from "../src/features/MAT1MaterialsPanel";
import {
  acceptMAT1Design, clearMAT1Sessions, mat1FamilyKey, mat1Snapshot, rememberMAT1Preview,
  setMAT1Active, setMAT1Catalog, setMAT1Conditions, setMAT1Default,
  setMAT1PreviewOwners,
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
  vi.stubGlobal("crypto", { randomUUID: () => "panel-id" });
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const path = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (path.endsWith("/catalog")) return Promise.resolve(new Response(JSON.stringify({ records: [record] }), { status: 200 }));
    if (path.endsWith("/owners")) return Promise.resolve(new Response(JSON.stringify({ owners: ["FRP-A", "FRP-B"], design_check_performed: false }), { status: 200 }));
    if (path.endsWith("/factor-candidates")) return Promise.resolve(new Response(JSON.stringify({ material_ledgers: [{ component_id: "FRP-A", adjusted_candidate: "21" }] }), { status: 200 }));
    throw new Error(`Unexpected request ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  rememberMAT1Preview("beam-web-splice", '{"request_id":"PREVIEW-1"}');
  render(<MAT1MaterialsPanel family="beam-web-splice" />);
  fireEvent.change(screen.getByLabelText("Material mode"), { target: { value: "MAT1" } });
  await waitFor(() => { expect(screen.getByText(/ICE · ISOPHTHALIC POLYESTER · RC0/)).toBeTruthy(); });
  await waitFor(() => { expect(screen.getByText(/Compatible FRP targets: FRP-A, FRP-B/)).toBeTruthy(); });
  expect(fetchMock).toHaveBeenCalledTimes(2);
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
  const conditionDetails = screen.getByText("Design Conditions").closest("details");
  if (conditionDetails === null) throw new Error("Design Conditions details missing");
  conditionDetails.open = true;
  fireEvent(conditionDetails, new Event("toggle"));
  fireEvent.change(screen.getByLabelText("Sustained material temperature"), { target: { value: "90" } });
  fireEvent.change(screen.getByLabelText("Maximum material temperature"), { target: { value: "100" } });
  fireEvent.change(screen.getByLabelText("Sustained material temperature"), { target: { value: "95" } });
  fireEvent.change(screen.getByLabelText("Temperature unit"), { target: { value: "degC" } });
  fireEvent.change(screen.getByLabelText("Sustained material temperature"), { target: { value: "30" } });
  fireEvent.change(screen.getByLabelText("Maximum material temperature"), { target: { value: "40" } });
  fireEvent.change(screen.getByLabelText("Glass transition temperature (Tg; optional evidence)"), { target: { value: "100" } });
  fireEvent.change(screen.getByLabelText("Glass transition temperature (Tg; optional evidence)"), { target: { value: "" } });
  fireEvent.change(screen.getByLabelText("Moisture"), { target: { value: "SUSTAINED_MOISTURE" } });
  fireEvent.change(screen.getByLabelText("Chemical exposure"), { target: { value: "SPECIFIED" } });
  for (const [label, value] of [["Substance", "salt"], ["Concentration", "5%"], ["Contact form", "spray"], ["Duration", "one year"]] as const) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.change(screen.getByLabelText("Load case name"), { target: { value: "LC-1" } });
  fireEvent.change(screen.getByLabelText("Time effect category"), { target: { value: "WIND_TORNADO_SEISMIC" } });
  fireEvent.change(screen.getByLabelText("Source reference condition"), { target: { value: "REFERENCE" } });
  fireEvent.change(screen.getByLabelText("UV / weathering"), { target: { value: "SPECIFIED" } });
  fireEvent.change(screen.getByLabelText("Freeze–thaw"), { target: { value: "NONE_DECLARED" } });
  for (const [label, value] of [["Protective measures", "coated"], ["Exposure notes", "outside"], ["Action provenance", "factored"], ["Live-load subtype", "occupancy"], ["Full-amplitude operating duration", "8 h"], ["Design period", "30 y"], ["Service period", "20 y"], ["Fatigue cycles", "1000"]] as const) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByText("Inspect factor candidates"));
  await waitFor(() => { expect(fetchMock).toHaveBeenCalledTimes(3); });
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
  setMAT1Active(false); setMAT1Catalog([]); clearMAT1Sessions(); setMAT1Default(null); setMAT1Active(false);
  vi.stubGlobal("crypto", { randomUUID: () => "error-session" });
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response("{}", { status: 503 }))
    .mockResolvedValueOnce(new Response("{}", { status: 200 }))
    .mockResolvedValueOnce(new Response("{}", { status: 422 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ owners: null, design_check_performed: true }), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  render(<MAT1MaterialsPanel family="paired-clip-angle" />);
  fireEvent.change(screen.getByLabelText("Material mode"), { target: { value: "MAT1" } });
  await waitFor(() => { expect(screen.getByRole("alert").textContent).toContain("Material catalog HTTP 503"); });
  setMAT1Catalog([]);
  await waitFor(() => { expect(screen.getByRole("alert").textContent).toContain("Material catalog response is invalid"); });
  setMAT1Catalog([record]);
  rememberMAT1Preview("paired-clip-angle", '{"id":1}');
  await waitFor(() => { expect(screen.getByRole("status").textContent).toContain("Material owner preview HTTP 422"); });
  rememberMAT1Preview("paired-clip-angle", '{"id":2}');
  await waitFor(() => { expect(screen.getByRole("status").textContent).toContain("Invalid material owner preview"); });
  setMAT1PreviewOwners("paired-clip-angle", '{"id":2}', ["POSITIVE_CLIP_ANGLE"]);
  fireEvent.click(screen.getByText("New session material"));
  expect(screen.getByText(/Linked-material method/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Add property"), { target: { value: "" } });
  fireEvent.click(screen.getByText("Inspect factor candidates"));
  expect(screen.getByRole("status").textContent).toContain("complete the conditions");
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

it("reports factor transport errors and keeps catalog and owner request aborts silent", async () => {
  setMAT1Active(false); setMAT1Catalog([]); clearMAT1Sessions(); setMAT1Default(null);
  const pending: ((error: Error) => void)[] = [];
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((_resolve, reject) => { pending.push(reject); })));
  const first = render(<MAT1MaterialsPanel family="beam-web-splice" />);
  fireEvent.change(screen.getByLabelText("Material mode"), { target: { value: "MAT1" } });
  await waitFor(() => { expect(pending).toHaveLength(1); });
  fireEvent.click(screen.getByText("New session material"));
  expect(screen.getByLabelText("Add property").querySelectorAll("option")).toHaveLength(1);
  clearMAT1Sessions();
  first.unmount();
  pending[0]?.(new Error("aborted catalog"));
  setMAT1Catalog([record]);
  rememberMAT1Preview("beam-web-splice", '{"request_id":"ABORT"}');
  const second = render(<MAT1MaterialsPanel family="beam-web-splice" />);
  await waitFor(() => { expect(pending).toHaveLength(2); });
  second.unmount();
  pending[1]?.(new Error("aborted owner preview"));
  expect(mat1Snapshot().catalogError).toBeNull();
  setMAT1PreviewOwners("beam-web-splice", '{"request_id":"ABORT"}', ["FRP-A"]);

  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("{}", { status: 503 }))));
  render(<MAT1MaterialsPanel family="beam-web-splice" />);
  fireEvent.click(screen.getByText("Inspect factor candidates"));
  expect(screen.getByRole("status").textContent).toContain("Select a material");
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: record.id } });
  setMAT1Conditions({
    ...mat1Snapshot().conditions,
    sustained_temperature: { value: "90", unit: "degF" },
    maximum_temperature: { value: "90", unit: "degF" },
    load_case_name: "LC-1",
    time_effect_category: "WIND_TORNADO_SEISMIC",
  });
  fireEvent.click(screen.getByText("Inspect factor candidates"));
  await waitFor(() => { expect(screen.getByRole("status").textContent).toContain("Factor inspection HTTP 503"); });
});
