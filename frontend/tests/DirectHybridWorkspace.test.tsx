import { StrictMode } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { TwoBoltRequest } from "../src/api/directTwoBolt";
import type { HybridInputs, HybridResponse } from "../src/api/hybridWorkflow";
import type { SceneSelection } from "../src/visualization/EngineeringScene";
import { DirectHybridWorkspace } from "../src/workspace/DirectHybridWorkspace";
import * as hybrid from "../src/api/hybridWorkflow";
import inputs from "./fixtures/hybridLiveNativeInputs.json";
import specimens from "./fixtures/hybridLivePresentations.json";
import { defaultFastenerSelection, mat1Conditions, setMAT1Active, setMAT1DirectConditions, setFastenerSelection } from "../src/state/mat1Session";

const mocks = vi.hoisted(() => ({ calculate: vi.fn(), post: vi.fn(), download: vi.fn(), envelope: vi.fn() }));
vi.mock("../src/api/hybridWorkflow", async (original) => ({ ...await original<typeof import("../src/api/hybridWorkflow")>(), calculateHybrid: mocks.calculate, hybridPost: mocks.post, downloadHybrid: mocks.download }));
vi.mock("../src/api/mat1Transport", () => ({ buildMAT1DesignEnvelope: mocks.envelope }));
vi.mock("../src/features/MAT1MaterialsPanel", () => ({ MAT1MaterialsPanel: () => <label>Existing native material condition<input onChange={() => undefined} /></label> }));
vi.mock("../src/features/FastenerSelector", () => ({ FastenerSelector: ({ onSelect }: { onSelect: (value: unknown) => void }) => <button onClick={() => { onSelect({ kind: "CATALOG", contract: "F593-CATALOG-F4-RC1", revision: "native-source-change" }); }}>Choose native fastener</button> }));
vi.mock("../src/visualization/VisualizationPanel", () => ({ VisualizationPanel: ({ onSelect }: { onSelect: (s: SceneSelection) => void }) => <button type="button" onClick={() => { onSelect({ kind: "MEMBER", id: "member-b" }); }}>Current backend viewer</button> }));

function response(draft: HybridInputs): HybridResponse {
  const data = structuredClone(draft.geometry === null ? specimens.native : specimens.source) as unknown as HybridResponse;
  return { ...data, revision: draft.revision, fingerprint: "current-" + String(draft.revision) };
}
const native = (): TwoBoltRequest => structuredClone(inputs) as unknown as TwoBoltRequest;
function mount(value = native()) { return render(<DirectHybridWorkspace initialNative={value} onNative={vi.fn()} />); }
function change(label: string, value: string) { fireEvent.change(screen.getByLabelText(label), { target: { value } }); }
async function run() { fireEvent.click(screen.getByRole("button", { name: "Run Hybrid Calculations" })); await waitFor(() => { expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeEnabled(); }); }
function loadSource() { fireEvent.click(screen.getByRole("button", { name: "Load RHM source example" })); fireEvent.click(screen.getByRole("button", { name: "Confirm replacement" })); }
function lastDraft(): HybridInputs { return mocks.calculate.mock.calls.at(-1)?.[1] as HybridInputs; }
beforeEach(() => {
  setMAT1Active(false);
  mocks.calculate.mockReset().mockImplementation((_path: string, draft: HybridInputs) => Promise.resolve(response(draft)));
  mocks.post.mockReset().mockResolvedValue({ invalidated: true });
  mocks.download.mockReset().mockImplementation((_handle: string, _technical: boolean, _format: string, current: () => boolean) => { expect(current()).toBe(true); return Promise.resolve(); });
  mocks.envelope.mockReset().mockImplementation((_family: string, legacy: string) => ({ request: { legacy_request: JSON.parse(legacy) as unknown } }));
});
afterEach(() => { vi.restoreAllMocks(); });

it("opens live native inputs, retains the viewer, executes current checks and offers the three current exports", async () => {
  const back = vi.fn(); render(<DirectHybridWorkspace initialNative={native()} onNative={back} />);
  await screen.findByRole("button", { name: "Current backend viewer" });
  expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeDisabled();
  await run();
  expect(screen.getByText(/0\/0 requested RHM comparisons and 8 native/)).toBeVisible();
  expect(screen.getByRole("region", { name: "Current hybrid check results" })).toHaveTextContent("Existing ASCE calculation");
  expect(screen.getByRole("region", { name: "Current hybrid check results" })).not.toHaveTextContent("Unchanged Native Asce");
  expect(screen.getByRole("region", { name: "Hybrid calculation summary" })).toHaveTextContent(/Partial.*Section 2.3.2 qualification are not established/);
  fireEvent.click(screen.getByRole("button", { name: "Current backend viewer" }));
  for (const name of ["Hybrid Calculation Report", "Technical Audit", "Calculation JSON"]) fireEvent.click(screen.getByRole("button", { name }));
  expect(mocks.download.mock.calls.map((call) => (call as unknown[]).slice(1, 3))).toEqual([[false, "pdf"], [true, "pdf"], [false, "json"]]);
  fireEvent.click(screen.getByRole("button", { name: "Other bolt arrangements" })); expect(back).toHaveBeenCalledOnce();
});

it("uses an explicit source example, editable geometry, both accessible alignments and current case fields", async () => {
  mount(); loadSource();
  expect(screen.getByText("Geometry and constructability details").closest("details")).not.toHaveAttribute("open");
  fireEvent.click(screen.getByRole("radio", { name: "Along brace (default)" }));
  await waitFor(() => { expect(lastDraft().alignment).toBe("BRACE"); });
  fireEvent.click(screen.getByRole("radio", { name: "Along supporting member" }));
  change("Brace angle to source horizontal", "31"); change("Brace free-edge to bolt centerline (Xb)", ".5");
  change("ASD case ID", "Actual-case"); change("ASD action frame", "DIRECT_P_POSITIVE_N_CENTROID");
  change("ASD P / Fx", ".18310"); change("ASD Transverse +n / Fy", "-.0134"); change("ASD Moment Mz", "1");
  fireEvent.click(screen.getByText("Action reference point")); change("ASD reference 1", "1");
  await waitFor(() => { expect(lastDraft().asd_cases[0]).toMatchObject({ case_id: "Actual-case", frame: "DIRECT_P_POSITIVE_N_CENTROID", components: [{ value: ".18310" }, { value: "-.0134" }, {}, {}, {}, { value: "1" }] }); });
  expect(lastDraft().geometry?.phi).toBe("31"); expect(lastDraft().geometry?.xb.value).toBe(".5");
  change("ASD action frame", "GLOBAL"); change("ASD Global Fx", ".2"); change("ASD action frame", "DIRECT_P_SKETCH_V_CENTROID");
  change("ASD Moment Mx", "");
  await waitFor(() => { expect(lastDraft().asd_cases[0]?.components[3]).toBeNull(); });
  fireEvent.click(screen.getByRole("button", { name: "Remove ASD case" }));
  fireEvent.click(screen.getByRole("button", { name: "Add ASD case" }));
  fireEvent.click(screen.getByRole("button", { name: "Add LRFD case" }));
  change("LRFD case ID", "independent-LRFD");
  fireEvent.click(screen.getByRole("button", { name: "Remove LRFD case" }));
  await run();
  expect(screen.getByText(/7\/7 requested RHM comparisons/)).toBeVisible();
  expect(screen.getByRole("region", { name: "Current hybrid check results" })).toHaveTextContent("RHM reference calculation");
  expect(screen.getByRole("region", { name: "Current hybrid check results" })).not.toHaveTextContent("Hyb2 Direct Reference");
  expect(lastDraft().native_request).toBeNull();
});

it("immediately invalidates every export on geometry, profile, action or detailing edits", async () => {
  mount(); loadSource();
  await run(); change("Bearing-face definition", "DECLARED_STRAIGHT_FREE_EDGE");
  expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeDisabled();
  change("Washer outside diameter", "1"); change("RHM property profile", "UNMATCHED");
  await waitFor(() => { expect(lastDraft()).toMatchObject({ washer_od: { value: "1", unit: "in" }, source_profile: "UNMATCHED" }); });
  change("Washer outside diameter", "");
  await waitFor(() => { expect(lastDraft().washer_od).toBeNull(); });
  change("ASD P / Fx", ".4"); await waitFor(() => { expect(lastDraft().asd_cases[0]?.components[0]?.value).toBe(".4"); });
});

it("edits actual native members, bolts, physical end, actions and MAT1 envelope together", async () => {
  mount();
  for (const [label, value] of [["Angle leg width", "5"], ["Angle thickness", ".6"], ["Receiving I flange thickness", ".6"], ["action-1 force x", "1.4"], ["Bolt diameter", ".625"], ["Bolt spacing", "2.5"], ["Brace angle to receiving member", "45"], ["Hole diameter", ".625"], ["Brace end distance", "4"], ["Negative physical side distance", "1.1"], ["Declared straight-edge distance", ".6"]]) change(label ?? "", value ?? "");
  fireEvent.click(screen.getByRole("radio", { name: "Along supporting member" }));
  fireEvent.click(screen.getByRole("checkbox", { name: "Evaluate applicable ASCE LRFD checks" }));
  change("Existing native material condition", "new");
  await waitFor(() => { expect(lastDraft().native_request?.legacy.bolt_diameter.value).toBe(".625"); });
  const draft = lastDraft();
  expect(draft.include_native_lrfd).toBe(false); expect(draft.native_request?.spacing.value).toBe("2.5");
  expect(draft.native_request?.legacy.unloaded_end_e1.value).toBe("4");
  expect(draft.native_request?.legacy.physical_connection?.bolt_diameter.value).toBe(".625");
  expect(draft.native_request?.hole_diameter?.value).toBe(".625");
  expect(draft.native_request?.legacy.physical_connection?.geometry_template?.hole_diameter.value).toBe(".625");
  if (draft.native_request === null) throw new Error("Native request required");
  expect(draft.native_request.material_request).toMatchObject({ legacy_request: draft.native_request.legacy });
  expect(mocks.envelope).toHaveBeenCalled();
});

it("keeps incomplete native conditions actionable without disabling independent runs", async () => {
  const value = native(); delete value.material_request; mount(value);
  mocks.envelope.mockImplementation(() => { throw new Error("Select actual project conditions"); });
  change("Angle return-leg width", "5"); change("Existing native material condition", "incomplete");
  expect(await screen.findByRole("alert")).toHaveTextContent("Select actual project conditions");
  expect(screen.getByRole("button", { name: "Run Hybrid Calculations" })).toBeEnabled();
  await waitFor(() => { expect(lastDraft().native_request).not.toHaveProperty("material_request"); });
});

it("does not invalidate revision zero during StrictMode's effect probe and invalidates on actual unmount", async () => {
  const view = render(<StrictMode><DirectHybridWorkspace initialNative={native()} onNative={vi.fn()} /></StrictMode>);
  await screen.findByRole("button", { name: "Current backend viewer" });
  expect(mocks.post).not.toHaveBeenCalledWith("invalidate", expect.anything());
  view.unmount(); await act(async () => { await Promise.resolve(); });
  expect(mocks.post).toHaveBeenCalledWith("invalidate", expect.objectContaining({ revision: 1 }));
});

it("ignores a genuinely delivered older result after a newer result, without aborting it", async () => {
  let deliver: ((r: HybridResponse) => void) | undefined;
  mount(); loadSource();
  await screen.findByRole("button", { name: "Current backend viewer" });
  const old = lastDraft();
  mocks.calculate.mockImplementation((path: string, draft: HybridInputs) => path === "assess" && draft.revision === old.revision ? new Promise<HybridResponse>((resolve) => { deliver = resolve; }) : Promise.resolve(response(draft)));
  fireEvent.click(screen.getByRole("button", { name: "Run Hybrid Calculations" }));
  change("ASD P / Fx", ".18310"); await run();
  const newFingerprint = "current-" + String(lastDraft().revision);
  await act(async () => { deliver?.({ ...response(old), fingerprint: "SUPERSEDED-DELIVERED" }); await Promise.resolve(); });
  expect(screen.queryByText(/SUPERSEDED-DELIVERED/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByText("Method notes and technical provenance"));
  // Stored record is presented only for the current request; delivery of an old
  // response neither clears its export authority nor triggers another run.
  expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeEnabled();
  expect(newFingerprint).not.toBe("current-" + String(old.revision));
});

it("presents scoped failure and actual fit/detailing failures without converting notes into yellow", async () => {
  const failed = response({ geometry: {} } as HybridInputs);
  if (failed.record === undefined) throw new Error("Actual record specimen required");
  failed.record.assessment.evaluated_outcome = "FAIL"; failed.record.assessment.tone = "red";
  failed.record.assessment.fit.state = "NOT_FIT";
  failed.record.detailing_failures = [{ check_kind: "CHAPTER_8_END_DISTANCE", actual_distance: ".9", required_distance: "1", unit: "in", boundary_label: "loaded physical end", source_rule: "ASCE Table 8-1" }];
  mocks.calculate.mockResolvedValue(failed); mount(); await run();
  expect(screen.getByRole("heading", { name: "Evaluated checks: FAIL (scoped)" })).toBeVisible();
  expect(screen.getByText(/Chapter 8 End Distance: .9 in; required 1 in/)).toBeVisible();
  expect(screen.getByText(/Physical fit: Not Fit/)).toHaveClass("hybrid-detail-failure");
  expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeEnabled();
});

it.each(["preview", "assess", "export", "units"])("shows an actionable current %s error and keeps old results unavailable", async (path) => {
  mount(); loadSource();
  await screen.findByRole("button", { name: "Current backend viewer" });
  if (path === "export") { await run(); mocks.download.mockRejectedValue(new Error("Export stale; recalculate")); fireEvent.click(screen.getByRole("button", { name: "Hybrid Calculation Report" })); }
  else if (path === "units") { mocks.post.mockRejectedValue(new Error("Unit conversion rejected; review units")); change("Hybrid unit system", "mm"); }
  else {
    mocks.calculate.mockRejectedValue(new Error("Invalid current " + path + "; review inputs"));
    if (path === "preview") change("Brace free-edge to bolt centerline (Xb)", "-1");
    else fireEvent.click(screen.getByRole("button", { name: "Run Hybrid Calculations" }));
  }
  expect(await screen.findByRole("alert")).toHaveTextContent(/review|recalculate/i);
  expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeDisabled();
});

it.each(["preview", "assess", "units"])("does not publish a stale or unmounted %s rejection", async (path) => {
  let reject: ((error: Error) => void) | undefined;
  const view = mount(); loadSource();
  await screen.findByRole("button", { name: "Current backend viewer" });
  const delayed = new Promise<HybridResponse>((_resolve, no) => { reject = no; });
  if (path === "units") { mocks.post.mockImplementation((p: string) => p === "units" ? delayed : Promise.resolve({ invalidated: true })); change("Hybrid unit system", "mm"); }
  else { mocks.calculate.mockImplementation((p: string, draft: HybridInputs) => p === path ? delayed : Promise.resolve(response(draft))); if (path === "preview") change("Brace free-edge to bolt centerline (Xb)", ".5"); else fireEvent.click(screen.getByRole("button", { name: "Run Hybrid Calculations" })); }
  mocks.calculate.mockImplementation((_p: string, draft: HybridInputs) => Promise.resolve(response(draft)));
  change("ASD P / Fx", ".2");
  await act(async () => { reject?.(new Error("STALE REJECTION")); await Promise.resolve(); });
  expect(screen.queryByText(/STALE REJECTION/)).not.toBeInTheDocument();
  view.unmount();
});

it("ignores a rejected old export after an input edit, and tolerates invalidation transport failure", async () => {
  let reject: ((error: Error) => void) | undefined;
  const view = mount(); await run();
  mocks.download.mockImplementation(() => new Promise<void>((_yes, no) => { reject = no; }));
  fireEvent.click(screen.getByRole("button", { name: "Hybrid Calculation Report" }));
  mocks.post.mockRejectedValue(new Error("Backend temporarily unreachable"));
  change("Bolt spacing", "2.2");
  const stillCurrent = mocks.download.mock.calls[0]?.[3] as () => boolean;
  expect(stillCurrent()).toBe(false);
  await act(async () => { reject?.(new Error("OLD EXPORT")); await Promise.resolve(); });
  expect(screen.queryByText(/OLD EXPORT/)).not.toBeInTheDocument();
  view.unmount(); expect(stillCurrent()).toBe(false); await act(async () => { await Promise.resolve(); });
  const unmounted = mount(); await run();
  fireEvent.click(screen.getByRole("button", { name: "Hybrid Calculation Report" }));
  unmounted.unmount();
  await act(async () => { reject?.(new Error("UNMOUNTED EXPORT")); await Promise.resolve(); });
});

it("converts current units only, ignores a late conversion and retains explicitly unknown actions", async () => {
  let deliver: ((value: HybridInputs) => void) | undefined;
  const view = mount(); loadSource();
  await screen.findByRole("button", { name: "Current backend viewer" });
  const original = lastDraft();
  mocks.post.mockImplementation((path: string) => path === "units" ? Promise.resolve(original) : Promise.resolve({ invalidated: true }));
  change("Hybrid unit system", "mm"); await waitFor(() => { expect(lastDraft().revision).toBeGreaterThan(original.revision); });
  mocks.post.mockImplementation((path: string) => path === "units" ? new Promise<HybridInputs>((yes) => { deliver = yes; }) : Promise.resolve({ invalidated: true }));
  change("Hybrid unit system", "mm"); change("Brace free-edge to bolt centerline (Xb)", ".7");
  await act(async () => { deliver?.(original); await Promise.resolve(); });
  expect(screen.getByLabelText("Brace free-edge to bolt centerline (Xb)")).toHaveValue(".7");
  change("ASD P / Fx", ""); change("ASD Moment Mz", "");
  fireEvent.click(screen.getByRole("button", { name: "Add ASD case" }));
  const secondCase = screen.getAllByLabelText("ASD case ID")[1], removeFirst = screen.getAllByRole("button", { name: "Remove ASD case" })[0];
  if (secondCase === undefined || removeFirst === undefined) throw new Error("Two current cases required");
  fireEvent.change(secondCase, { target: { value: "second" } });
  fireEvent.click(removeFirst);
  expect(screen.getByLabelText("ASD case ID")).toHaveValue("second");
  view.unmount();
});

it("does not publish an unmounted preview or assessment success", async () => {
  let deliverPreview: ((value: HybridResponse) => void) | undefined;
  let deliverAssess: ((value: HybridResponse) => void) | undefined;
  mocks.calculate.mockImplementation((path: string) => new Promise<HybridResponse>((yes) => { if (path === "preview") deliverPreview = yes; else deliverAssess = yes; }));
  const view = mount(); const draft = lastDraft();
  fireEvent.click(screen.getByRole("button", { name: "Run Hybrid Calculations" }));
  view.unmount();
  await act(async () => { deliverPreview?.(response(draft)); deliverAssess?.(response(draft)); await Promise.resolve(); });
  expect(screen.queryByRole("button", { name: "Hybrid Calculation Report" })).not.toBeInTheDocument();
});

it("gives explicit recovery for missing physical or template geometry without substituting the source example", () => {
  const missing = native(); delete missing.legacy.physical_connection;
  const view = mount(missing); expect(screen.getByText(/current physical connection is missing/)).toBeVisible(); view.unmount();
  const noTemplate = native(); if (noTemplate.legacy.physical_connection !== undefined) delete noTemplate.legacy.physical_connection.geometry_template;
  const second = mount(noTemplate); expect(screen.queryByLabelText("Brace end distance")).not.toBeInTheDocument(); second.unmount();
  vi.spyOn(hybrid, "sourceExample").mockImplementation((current) => ({ ...current, native_request: null, geometry: null }));
  mount(); loadSource();
  expect(screen.getByRole("alert")).toHaveTextContent("Define one current physical connection");
  expect(mocks.envelope).not.toHaveBeenCalled();
});

it("preserves another independently entered native member action and clears the declared edge when unknown", async () => {
  const value = native(), physical = value.legacy.physical_connection;
  if (physical?.joint_assembly.member_end_actions[0] === undefined) throw new Error("Native specimen required");
  const action = structuredClone(physical.joint_assembly.member_end_actions[0]); action.id = "action-2"; physical.joint_assembly.member_end_actions.push(action);
  mount(value); change("action-2 moment z", "2"); change("Declared straight-edge distance", ".5"); change("Declared straight-edge distance", "");
  await waitFor(() => { expect(lastDraft().native_edge_distance).toBeNull(); });
  expect(lastDraft().native_request?.legacy.physical_connection?.joint_assembly.member_end_actions[0]?.moment.z).toBe("0");
  expect(lastDraft().native_request?.legacy.physical_connection?.joint_assembly.member_end_actions[1]?.moment.z).toBe("2");
});

it("confirms presets, cancels without overwriting edits, and restores all previous inputs without results", async () => {
  mount(); change("Bolt spacing", "2.75"); change("action-1 force x", "1.4"); await run();
  const previous = structuredClone(lastDraft());
  fireEvent.click(screen.getByRole("button", { name: "Load RHM source example" }));
  expect(screen.getByRole("alertdialog")).toBeVisible();
  expect(screen.getByLabelText("Bolt spacing")).toHaveValue("2.75");
  fireEvent.click(screen.getByRole("button", { name: "Keep current inputs" }));
  expect(lastDraft()).toEqual(previous);
  expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeEnabled();
  loadSource(); expect(screen.getByLabelText("Bolt spacing")).toHaveValue("2");
  expect(screen.getByText(/RHM source sample preset/)).toBeVisible();
  expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeDisabled();
  change("Bolt spacing", "2.5");
  fireEvent.click(screen.getByRole("button", { name: "Restore previous inputs" }));
  fireEvent.click(screen.getByRole("button", { name: "Confirm replacement" }));
  expect(screen.getByLabelText("Bolt spacing")).toHaveValue("2.75");
  const restored = lastDraft();
  expect({ ...restored, revision: previous.revision }).toEqual(previous);
  expect(restored.revision).toBeGreaterThan(previous.revision);
  expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Load native ASCE example" }));
  fireEvent.click(screen.getByRole("button", { name: "Confirm replacement" }));
  expect(screen.getByLabelText("Bolt spacing")).toHaveValue("2");
});

it("keeps the physical connection when changing basis or opening supplemental inputs, and hides premature results", async () => {
  mount(); await screen.findByRole("button", { name: "Current backend viewer" });
  expect(screen.queryByRole("region", { name: "Hybrid calculation summary" })).not.toBeInTheDocument();
  expect(screen.queryByText(/NOT EVALUATED/)).not.toBeInTheDocument();
  change("Angle thickness", ".6");
  const connection = structuredClone(lastDraft().native_request);
  fireEvent.click(screen.getByText("RHM supplemental properties"));
  expect(lastDraft().native_request).toEqual(connection);
  fireEvent.click(screen.getByRole("checkbox", { name: "Evaluate applicable ASCE LRFD checks" }));
  expect(lastDraft().native_request).toEqual(connection);
  loadSource();
  const geometry = structuredClone(lastDraft().geometry);
  fireEvent.click(screen.getByRole("checkbox", { name: "Evaluate applicable ASCE LRFD checks" }));
  fireEvent.click(screen.getByRole("button", { name: "Add LRFD case" }));
  expect(lastDraft().geometry).toEqual(geometry);
  expect(screen.getAllByLabelText("Bolt spacing")).toHaveLength(1);
  await screen.findByRole("button", { name: "Current backend viewer" });
  expect(screen.getAllByRole("button", { name: "Current backend viewer" })).toHaveLength(1);
  await run();
  expect(screen.getByRole("region", { name: "Current hybrid check results" })).toHaveTextContent("0.101 (10.1%)");
  expect(screen.getByRole("region", { name: "Current hybrid check results" })).not.toHaveTextContent("DIRECT_BRACE_LOCAL");
});

it("binds material, condition and hardware changes from the external MAT1 store without reusing native results", async () => {
  mount(); await run();
  act(() => { setMAT1Active(true); });
  await waitFor(() => { expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeDisabled(); });
  expect(lastDraft().native_request?.material_request).toBeDefined();
  await run();
  fireEvent.click(screen.getByRole("button", { name: "Choose native fastener" }));
  expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeDisabled();
  mocks.envelope.mockImplementation(() => { throw new Error("Actual conditions incomplete"); });
  act(() => { setMAT1DirectConditions({ ...mat1Conditions("multi-row"), load_case_name: "Changed current combination" }); });
  await waitFor(() => { expect(lastDraft().native_request?.material_request).toBeUndefined(); });
  fireEvent.click(screen.getByRole("button", { name: "Run Hybrid Calculations" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Complete the selected FRP material");
  fireEvent.click(screen.getByRole("button", { name: "Load native ASCE example" }));
  fireEvent.click(screen.getByRole("button", { name: "Confirm replacement" }));
  expect(lastDraft().native_request?.material_request).toBeUndefined();
  mocks.envelope.mockImplementation((_family: string, legacy: string) => ({ request: { legacy_request: JSON.parse(legacy) as unknown } }));
  fireEvent.click(screen.getByRole("button", { name: "Load native ASCE example" }));
  fireEvent.click(screen.getByRole("button", { name: "Confirm replacement" }));
  expect(lastDraft().native_request?.material_request).toBeDefined();
  loadSource(); await run();
  const source = structuredClone(lastDraft());
  act(() => { setFastenerSelection("multi-row", defaultFastenerSelection); });
  expect(lastDraft()).toEqual(source);
  expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeEnabled();
  act(() => { setMAT1Active(false); });
});

it("uses accessible preset keyboard cancellation and keeps the same input controls through native/source restoration", async () => {
  mount(); await screen.findByRole("button", { name: "Current backend viewer" }); change("Bolt spacing", "2.75");
  fireEvent.click(screen.getByRole("button", { name: "Load RHM source example" }));
  const cancel = screen.getByRole("button", { name: "Keep current inputs" });
  expect(cancel).toHaveFocus();
  fireEvent.keyDown(cancel, { key: "Tab" });
  expect(screen.getByRole("button", { name: "Confirm replacement" })).toHaveFocus();
  fireEvent.keyDown(document.activeElement ?? cancel, { key: "Tab", shiftKey: true });
  expect(cancel).toHaveFocus();
  fireEvent.keyDown(cancel, { key: "a" });
  fireEvent.keyDown(cancel, { key: "Escape" });
  expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Bolt spacing")).toHaveValue("2.75");
  fireEvent.change(screen.getByLabelText("Supporting W — longitudinal extent"), { target: { value: "FINITE_BOTH_ENDS" } });
  change("Distance from connection reference to W end above", "12");
  change("Distance from connection reference to W end below", "8");
  expect(lastDraft().native_request?.legacy.supporting_w_longitudinal_ends).toMatchObject({ condition: "FINITE_BOTH_ENDS", positive_end_distance: { value: "12" }, negative_end_distance: { value: "8" } });
});

it("retains incomplete imported native inputs without inventing a material envelope or evaluated result", async () => {
  const value = native(); delete value.material_request; delete value.legacy.supporting_w_longitudinal_ends;
  const physical = value.legacy.physical_connection;
  if (physical?.joint_assembly.members[0] === undefined) throw new Error("Physical import specimen required");
  Object.assign(physical.joint_assembly.members[0].section, { unknown_radius: { value: ".1", unit: "in" } });
  mount(value);
  expect(screen.getByLabelText("Pultruded FRP angle brace unknown radius")).toHaveValue(".1");
  expect(screen.getByLabelText("Supporting W — longitudinal extent")).toHaveValue("UNSPECIFIED");
  change("action-1 force x", "1.4");
  fireEvent.change(screen.getByLabelText("Supporting W — longitudinal extent"), { target: { value: "CONTINUOUS_THROUGH_CONNECTION" } });
  await waitFor(() => { expect(lastDraft().native_request?.legacy.supporting_w_longitudinal_ends?.condition).toBe("CONTINUOUS_THROUGH_CONNECTION"); });
  expect(lastDraft().native_request?.material_request).toBeUndefined();
  expect(screen.getByRole("button", { name: "Hybrid Calculation Report" })).toBeDisabled();
  expect(mocks.calculate.mock.calls.some(([path]) => path === "assess")).toBe(false);
});
