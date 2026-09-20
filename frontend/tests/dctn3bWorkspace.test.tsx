import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, assert, expect, it, vi } from "vitest";
import * as client from "../src/api/dctn3bClient";
import type { DCTN3BRequest, DCTN3BResponse, DCTNArrangement } from "../src/api/dctnContracts";
import type { SingleBoltSceneModel } from "../src/visualization/sceneModel";
import type { SceneSelection } from "../src/visualization/EngineeringScene";
import { DoubleChannelTrussNodeWorkspace } from "../src/workspace/DoubleChannelTrussNodeWorkspace";
import { DCTN3BResults } from "../src/workspace/DCTN3BResults";
import fixture from "./dctn3bNativeFixtures.json";
import golden from "../../backend/tests/golden/dctn_3b_golden_benchmarks_rc1.json";

const data = fixture as unknown as { request: DCTN3BRequest; preview: DCTN3BResponse; siPreview: DCTN3BResponse; shearPreview: DCTN3BResponse; shearDesign: DCTN3BResponse; axisPreviews: Record<string, DCTN3BResponse>; arrangements: Record<DCTNArrangement, { request: DCTN3BRequest; preview: DCTN3BResponse }> };
const probe = vi.hoisted(() => ({ model: null as SingleBoltSceneModel | null, select: null as ((selection: SceneSelection) => void) | null }));
vi.mock("../src/visualization/EngineeringScene", () => ({ default: ({ model, onSelect }: { model: SingleBoltSceneModel; onSelect: (selection: SceneSelection) => void }) => { probe.model = model; probe.select = onSelect; return <div data-testid="native-scene"/>; } }));
afterEach(() => { vi.restoreAllMocks(); probe.model = null; probe.select = null; });
const copy = <T,>(v: T): T => structuredClone(v);
function mocks() {
  vi.spyOn(client, "loadDCTN3BDefaults").mockImplementation(a => Promise.resolve(copy(data.arrangements[a].request)));
  return vi.spyOn(client, "requestDCTN3B").mockImplementation((_kind, request) => {
    const m = request.members[0]; assert(m !== undefined);
    const key = m.section.form + "_" + m.section.width.value + "_" + m.section.depth.value;
    // UI-only fixture dispatch: no frontend engineering computation.
    const selected = request.arrangement === "VERTICAL_ONLY"
      ? data.axisPreviews[key] ?? data.preview
      : data.arrangements[request.arrangement].preview;
    const response = copy(selected);
    return Promise.resolve({ ...response, result: { ...response.result, preview: { ...response.result.preview, input: copy(request) } } });
  });
}
const cases = golden.positive_cases.filter(c => {
  const n = Number(c.id.slice(1, 3)); return n >= 29 && n <= 34;
});

it("shows evaluated qualification for an explicitly blocker-free design result", () => {
  const result = data.shearDesign.result.design;
  assert(result !== null);
  render(<DCTN3BResults snapshot={data.shearPreview.result.preview} result={{ ...result, blockers: [] }} current={true}/>);
  expect(screen.getByText("EVALUATED", { selector: "dd" })).toBeInTheDocument();
});

it.each(cases)("$id", async c => {
  mocks();
  render(<DoubleChannelTrussNodeWorkspace/>);
  await screen.findByText("CURRENT BACKEND PREVIEW");
  const ordinal = Number(c.id.slice(1, 3));
  if (ordinal === 29) {
    expect(screen.getByLabelText("V Member Horizontal Location")).toHaveValue("0");
    expect(screen.getByLabelText("V Member Vertical Location")).toHaveValue("0.625");
    expect(screen.queryByLabelText("V Chord station")).toBeNull();
    expect(screen.queryByLabelText("V Member-end center above lower clear web")).toBeNull();
    for (const axis of ["X", "Y", "Z"]) expect(screen.queryByLabelText("V START " + axis)).toBeNull();
    expect(screen.getByText(/Derived global member-end coordinates are read-only/)).toBeInTheDocument();
  } else if (ordinal === 30) {
    const expected = c.expected as { rows_label: string; first_label: string };
    expect(screen.getByLabelText("V " + expected.rows_label)).toHaveValue("2");
    expect(screen.getByLabelText("V " + expected.first_label)).toHaveValue("2");
  } else if (ordinal === 31) {
    const expected = c.expected as { statuses: string[] };
    for (const name of expected.statuses) expect(screen.getByText(name.slice(0, 1).toUpperCase() + name.slice(1), { selector: "dt" })).toBeInTheDocument();
  } else if (ordinal === 32) {
    expect(screen.getByRole("heading", { name: "V member-end demand" }).parentElement).toHaveTextContent("2 kip · -3 kip · 1 kip");
    const trace = screen.getByText("Complete current / last-valid native geometry and engineering trace").parentElement;
    expect(trace).toHaveTextContent("4448.2216152605");
  } else if (ordinal === 33) {
    expect(screen.getByLabelText("V Gap depth")).toBeInTheDocument();
    expect(screen.getByLabelText("V Wall thickness")).toBeInTheDocument();
    expect(screen.queryByLabelText("V Flange Thickness")).toBeNull();
    fireEvent.change(screen.getByLabelText("V section form"), { target: { value: "SOLID_RECTANGLE" } });
    expect(screen.queryByLabelText("V Wall thickness")).toBeNull();
    expect(screen.queryByLabelText("V Web thickness")).toBeNull();
    fireEvent.change(screen.getByLabelText("V section form"), { target: { value: "W_I" } });
    for (const label of ["Depth", "Flange width", "Web thickness", "Flange Thickness", "W/I transverse offset magnitude"]) expect(screen.getByLabelText("V " + label)).toBeInTheDocument();
  } else {
    assert(ordinal === 34);
    const expected = c.expected as { collapsible: string };
    const section = screen.getByText(expected.collapsible).parentElement;
    expect(section?.tagName).toBe("DETAILS");
    expect(section).not.toHaveAttribute("open");
    expect(screen.getByText("Response coverage / missing qualification")).toBeVisible();
    expect(screen.getByText(/Numerical failures:/)).toBeVisible();
  }
});

it.each(["RHS", "SOLID_RECTANGLE"])("N20/N21 and I06/I15/I16: %s labels cross equality without swapping actions", async form => {
  const send = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>);
  await screen.findByText("CURRENT BACKEND PREVIEW");
  if (form !== "RHS") {
    fireEvent.change(screen.getByLabelText("V section form"), { target: { value: form } });
    await screen.findByText("CURRENT BACKEND PREVIEW");
  }
  expect(screen.getByLabelText("V Minor shear")).toHaveValue("0");
  expect(screen.getByLabelText("V Major shear")).toHaveValue("0");
  fireEvent.change(screen.getByLabelText("V Minor shear"), { target: { value: "7.1234567890123" } });
  fireEvent.change(screen.getByLabelText("V Major shear"), { target: { value: "-3.98765432109" } });
  await screen.findByText("CURRENT BACKEND PREVIEW");
  fireEvent.change(screen.getByLabelText("V Gap depth"), { target: { value: "4" } });
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(screen.getByLabelText("V Shear p (equal axes)")).toHaveValue("7.1234567890123");
  expect(screen.getByLabelText("V Shear q (equal axes)")).toHaveValue("-3.98765432109");
  expect(screen.queryByLabelText("V Major shear")).toBeNull();
  fireEvent.change(screen.getByLabelText("V Width"), { target: { value: "6" } });
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(screen.getByLabelText("V Major shear")).toHaveValue("7.1234567890123");
  expect(screen.getByLabelText("V Minor shear")).toHaveValue("-3.98765432109");
  expect(send.mock.lastCall?.[1].members[0]?.Qp.value).toBe("7.1234567890123");
  expect(send.mock.lastCall?.[1].members[0]?.Qq.value).toBe("-3.98765432109");
});

it("defaults action labels to the selected member and exposes the all-member overlay", async () => {
  const send = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>);
  await screen.findByText("CURRENT BACKEND PREVIEW");
  fireEvent.change(screen.getByLabelText("DCTN arrangement"), { target: { value: "VERTICAL_TWO_INCLINED" } });
  await screen.findByLabelText("D1 section form");
  await waitFor(() => { expect(send.mock.lastCall?.[1].arrangement).toBe("VERTICAL_TWO_INCLINED"); });
  await waitFor(() => { expect(probe.model?.appliedArrows.map(arrow => arrow.id)).toEqual(["V:P"]); });
  expect(probe.model?.appliedArrows.map(arrow => arrow.id)).toEqual(["V:P"]);
  expect(screen.getByRole("button", { name: "Edit V P applied load value" })).toHaveTextContent("V P =+1.00 kip");
  const overlay = screen.getByLabelText("All member actions");
  expect(overlay).not.toBeChecked();
  fireEvent.click(overlay);
  await waitFor(() => { expect(probe.model?.appliedArrows.map(arrow => arrow.id)).toEqual(["V:P", "D1:P", "D2:P"]); });
  fireEvent.click(screen.getByText("D1 incoming member"));
  fireEvent.click(overlay);
  await waitFor(() => { expect(probe.model?.appliedArrows.map(arrow => arrow.id)).toEqual(["D1:P"]); });
  act(() => { probe.select?.({ kind: "BOLT", id: "D1:ROW_1:THROUGH" }); });
  await waitFor(() => { expect(probe.model?.appliedArrows).toEqual([]); });
  fireEvent.change(screen.getByLabelText("DCTN arrangement"), { target: { value: "VERTICAL_ONLY" } });
  await waitFor(() => { expect(send.mock.lastCall?.[1].arrangement).toBe("VERTICAL_ONLY"); });
  await waitFor(() => { expect(probe.model?.appliedArrows.map(arrow => arrow.id)).toEqual(["V:P"]); });
});

it("fails closed while preserving a deterministic selection for malformed empty-member defaults", async () => {
  mocks();
  const malformed = copy(data.arrangements.ONE_INCLINED.request);
  malformed.members = [];
  render(<DoubleChannelTrussNodeWorkspace/>);
  await screen.findByText("CURRENT BACKEND PREVIEW");
  vi.mocked(client.loadDCTN3BDefaults).mockResolvedValueOnce(malformed);
  fireEvent.change(screen.getByLabelText("DCTN arrangement"), { target: { value: "ONE_INCLINED" } });
  await screen.findByRole("alert");
  expect(screen.getByText("LAST VALID PREVIEW — CURRENT INPUTS UNVERIFIED")).toBeVisible();
  expect(probe.model?.appliedArrows).toEqual([]);
});

it("shows local actions before global wrench and preserves human and exact qualification wording", () => {
  const snapshot = data.shearPreview.result.preview;
  render(<DCTN3BResults snapshot={snapshot} result={null} current/>);
  const card = screen.getByRole("heading", { name: "V member-end demand" }).parentElement;
  assert(card !== null);
  expect(within(card).getByText("Local engineering actions")).toBeVisible();
  expect(card).toHaveTextContent("Axial P1 kip");
  expect(card).toHaveTextContent("Minor shear (Qp)2 kip");
  expect(card).toHaveTextContent("Major shear (Qq)-3 kip");
  const localIndex = card.textContent.indexOf("Local engineering actions");
  const globalIndex = card.textContent.indexOf("Derived global member-end wrench");
  expect(localIndex).toBeGreaterThanOrEqual(0);
  expect(globalIndex).toBeGreaterThan(localIndex);
  expect(screen.getByText("Transverse demand calculated — connection response not yet qualified.")).toBeVisible();
  expect(screen.getByText("Status and qualification codes").parentElement).toHaveTextContent("DCTN_TRANSVERSE_RESPONSE_NOT_QUALIFIED");
});

it("fails closed when a demand member lacks its trusted input authority", () => {
  const snapshot = copy(data.shearPreview.result.preview);
  snapshot.input.members = [];
  expect(() => { render(<DCTN3BResults snapshot={snapshot} result={null} current/>); }).toThrow("DCTN member demand is missing its input authority.");
});

it("presents W/I local major and minor actions without rewriting the exact trace", () => {
  const axisPreview = data.axisPreviews.W_I_4_6; assert(axisPreview !== undefined);
  const snapshot = copy(axisPreview.result.preview);
  const member = snapshot.input.members[0]; assert(member !== undefined);
  member.P.value = "1.25"; member.Qp.value = "-2.5"; member.Qq.value = "3.75";
  const before = JSON.stringify(snapshot);
  render(<DCTN3BResults snapshot={snapshot} result={null} current/>);
  const card = screen.getByRole("heading", { name: "V member-end demand" }).parentElement;
  expect(card).toHaveTextContent("Axial P1.25 kip");
  expect(card).toHaveTextContent("Minor shear (Qp)-2.5 kip");
  expect(card).toHaveTextContent("Major shear (Qq)3.75 kip");
  expect(JSON.stringify(snapshot)).toBe(before);
});

it("N30/N31 and I17: concise selected units never alter exact engineering trace", () => {
  const snapshot = data.shearPreview.result.preview;
  const exact = JSON.stringify(snapshot);
  const view = render(<DCTN3BResults snapshot={snapshot} result={null} current/>);
  const demand = screen.getByRole("heading", { name: "V member-end demand" }).parentElement;
  expect(demand).toHaveTextContent("2 kip · -3 kip · 1 kip");
  expect(screen.getAllByText(/kip-in/).length).toBeGreaterThan(0);
  expect(JSON.stringify(snapshot)).toBe(exact);
  const trace = screen.getByText("Complete current / last-valid native geometry and engineering trace").parentElement;
  expect(trace).toHaveTextContent(JSON.stringify(snapshot, null, 2).slice(0, 1));
  expect(trace?.querySelector("pre")?.textContent).toBe(JSON.stringify(snapshot, null, 2));
  view.rerender(<DCTN3BResults snapshot={data.siPreview.result.preview} result={null} current/>);
  expect(screen.getAllByText(/kN-mm/).length).toBeGreaterThan(0);
});

it("N32/N33 and I18: invalid current geometry hides actions and disables design", async () => {
  const send = mocks();
  render(<DoubleChannelTrussNodeWorkspace/>);
  await screen.findByText("CURRENT BACKEND PREVIEW");
  send.mockResolvedValueOnce({ ...data.preview, geometry_status: "INVALID_GEOMETRY", geometry_invalid_reasons: ["DCTN_INVALID_GEOMETRY:CONTAINMENT"] });
  fireEvent.change(screen.getByLabelText("Channel Depth"), { target: { value: "4" } });
  await screen.findByRole("alert");
  expect(screen.getByText("LAST VALID PREVIEW — CURRENT INPUTS UNVERIFIED")).toBeInTheDocument();
  expect(probe.model?.appliedArrows).toEqual([]);
  expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Channel Depth"), { target: { value: "8" } });
  await screen.findByText("CURRENT BACKEND PREVIEW");
  expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled();
});

it("N34: collapsed source details leave unresolved response and qualification visible", () => {
  render(<DCTN3BResults snapshot={data.shearPreview.result.preview} result={data.shearDesign.result.design} current/>);
  expect(screen.getByText("Response coverage / missing qualification")).toBeVisible();
  expect(screen.getByText(/No automatic transverse Channel\/row sharing/)).toBeVisible();
  expect(screen.getAllByText("DCTN_TRANSVERSE_RESPONSE_NOT_QUALIFIED").some(e => e.closest("details") === null)).toBe(true);
  const design = screen.getByRole("region", { name: "DCTN design results" });
  expect(within(design).getByRole("heading", { name: "ENGINEERING_REVIEW_REQUIRED" })).toBeVisible();
});
