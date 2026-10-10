import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { Mock, MockInstance } from "vitest";
import { useState } from "react";
import fixture from "./fixtures/directTwoBoltGeometry.json";
import { DirectTwoBoltGeometry, FaceView } from "../src/features/DirectTwoBoltGeometry";
import type { CurrentTwoBolt } from "../src/features/DirectTwoBoltGeometry";
import { INITIAL_TWO_BOLT } from "../src/api/directTwoBolt";
import type { GeometryResponse, TwoBoltOptions } from "../src/api/directTwoBolt";
import type { MultiRowConnectionRequest } from "../src/api/multirowContracts";
import * as api from "../src/api/directTwoBolt";
import { setMAT1Active } from "../src/state/mat1Session";
import { ConnectionWorkspaceShell, PersistentConnectionViewer } from "../src/workspace/ConnectionWorkspaceShell";

const legacy = fixture.request.legacy as unknown as MultiRowConnectionRequest;
const data = fixture.response as unknown as GeometryResponse;
let onCurrent: Mock<(current: CurrentTwoBolt | null) => void>;
let preview: MockInstance<typeof api.previewTwoBolt>;
function Harness({ initial = INITIAL_TWO_BOLT }: { initial?: TwoBoltOptions }) {
  const [options, update] = useState(initial);
  return <DirectTwoBoltGeometry legacy={legacy} options={options} onChange={update} onCurrent={onCurrent} />;
}
beforeEach(() => {
  setMAT1Active(false); onCurrent = vi.fn<(current: CurrentTwoBolt | null) => void>();
  preview = vi.spyOn(api, "previewTwoBolt").mockImplementation((request) => Promise.resolve({ ...data, revision: request.revision }));
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("shows independent fit outcomes, same face coordinates, fixed comparison and explicit limits", async () => {
  render(<Harness initial={{ ...INITIAL_TWO_BOLT, alignment: "SUPPORT" }} />);
  await screen.findByRole("button", { name: "Export Geometry and Constructability Review" });
  expect(screen.getByText(api.GEOMETRY_BANNER)).toBeInTheDocument();
  expect(screen.getByLabelText("Help: Bolt alignment")).toBeInTheDocument();
  expect(screen.getByText(/Bolt shafts remain normal to the selected interface/)).toBeInTheDocument();
  const figures = screen.getAllByRole("img");
  expect(figures).toHaveLength(4);
  for (const station of data.geometry.centers) {
    expect(document.querySelectorAll('[data-global-center="' + station.join(",") + '"]')).toHaveLength(2);
  }
  expect(screen.getByText("Hole containment")).toBeInTheDocument();
  expect(screen.getByText("Known obstructions")).toBeInTheDocument();
  expect(screen.getByText("Installation access")).toBeInTheDocument();
  const count = preview.mock.calls.length;
  fireEvent.change(screen.getByLabelText("Geometry review display units"), { target: { value: "mm" } });
  expect(screen.getByText(/Pair spacing: 50.800/)).toBeInTheDocument();
  expect(preview.mock.calls.length).toBe(count);
  expect(screen.queryByText(/eight PASS|GREEN — complete/)).not.toBeInTheDocument();
});
it("proposals preserve the submitted geometry until the explicit Apply action", async () => {
  render(<Harness />);
  await screen.findByRole("button", { name: "Export Geometry and Constructability Review" });
  fireEvent.change(screen.getByLabelText("Search half-width in both directions (in)"), { target: { value: "1" } });
  await waitFor(() => { expect(screen.getByRole("button", { name: "Find bounded midpoint proposals" })).toBeEnabled(); });
  fireEvent.click(screen.getByRole("button", { name: "Find bounded midpoint proposals" }));
  await screen.findByRole("button", { name: "Apply proposal 1" });
  expect(screen.getByLabelText("Midpoint offset +u (in)")).toHaveValue("0");
  fireEvent.click(screen.getByRole("button", { name: "Apply proposal 1" }));
  await waitFor(() => { expect(preview.mock.calls.at(-1)?.[0].offset.support_longitudinal.value).not.toBe("0"); });
  fireEvent.change(screen.getByLabelText("Midpoint offset +v (in)"), { target: { value: ".1" } });
  fireEvent.change(screen.getByLabelText("Bolt spacing along selected alignment (in)"), { target: { value: "2.25" } });
  fireEvent.change(screen.getByLabelText("Bolt alignment"), { target: { value: "SUPPORT" } });
  fireEvent.change(screen.getByLabelText("Angle root encroachment (in)"), { target: { value: ".1" } });
  fireEvent.change(screen.getByLabelText("Supporting member root encroachment (in)"), { target: { value: ".2" } });
  fireEvent.change(screen.getByLabelText("Manufactured geometry source"), { target: { value: "Measured section" } });
  await waitFor(() => { expect(preview.mock.calls.at(-1)?.[0].manufactured_geometry_source).toBe("Measured section"); });
});
it("ignores obsolete responses and presents an actionable retry", async () => {
  let finish: ((response: GeometryResponse) => void) | undefined;
  preview.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
  render(<Harness />);
  expect(screen.getByText("Updating two-bolt geometry…")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Bolt alignment"), { target: { value: "SUPPORT" } });
  await screen.findByText(api.GEOMETRY_BANNER);
  await act(async () => { finish?.({ ...data, revision: "STALE" }); await Promise.resolve(); });
  expect(onCurrent.mock.calls.at(-1)?.[0]?.request.alignment).toBe("SUPPORT");
  preview.mockRejectedValueOnce(new Error("Backend unavailable. Retry."));
  fireEvent.change(screen.getByLabelText("Bolt spacing along selected alignment (in)"), { target: { value: "2.25" } });
  await screen.findByText("Backend unavailable. Retry.");
  expect(screen.getByText("Current geometry unavailable")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry geometry" }));
  await screen.findByRole("button", { name: "Export Geometry and Constructability Review" });
});
it("exports a current geometry review and reports a bounded export failure", async () => {
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:sab2");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  const exported = vi.spyOn(api, "exportGeometry").mockResolvedValue(new Blob(["%PDF"]));
  render(<Harness />);
  fireEvent.click(await screen.findByRole("button", { name: "Export Geometry and Constructability Review" }));
  await waitFor(() => { expect(exported).toHaveBeenCalled(); });
  await waitFor(() => { expect(screen.getByRole("button", { name: "Export Geometry and Constructability Review" })).toBeEnabled(); });
  exported.mockRejectedValue(new Error("Snapshot changed. Refresh geometry."));
  fireEvent.click(screen.getByRole("button", { name: "Export Geometry and Constructability Review" }));
  await screen.findByText("Snapshot changed. Refresh geometry.");
});
it("compatible geometry retains a fresh-design explanation and missing face renders nothing", async () => {
  preview.mockImplementation((request) => Promise.resolve({ ...data, revision: request.revision, structural_eligible: true }));
  render(<Harness />);
  await screen.findByText(/Identical legacy layout/);
  expect(screen.queryByText(api.GEOMETRY_BANNER)).not.toBeInTheDocument();
  const rendered = render(<FaceView response={data} faceIndex={99} units="in" />);
  expect(rendered.container).toBeEmptyDOMElement();
});
it("geometry-only shell suppresses engineering export and previous MAT1 unity authority", () => {
  setMAT1Active(true);
  render(<ConnectionWorkspaceShell family="multi-row" banner={<h2>Direct</h2>} reportBlockedReason="Unmapped current geometry">
    <PersistentConnectionViewer geometryOnlyReason="Unmapped current geometry" unity={{
      tone: "yellow", ratio: .4, ratioText: "40%", status: "YELLOW", governing: "Old check", explanation: "Old snapshot",
    }}><p>Current stations</p></PersistentConnectionViewer>
  </ConnectionWorkspaceShell>);
  expect(screen.queryByRole("button", { name: /Export Engineer|Export Input/ })).not.toBeInTheDocument();
  const status = screen.getByText(/Design completeness status:/).closest('[role="status"]');
  expect(status).not.toHaveTextContent("YELLOW");
  expect(within(document.body).queryByText("40%")).not.toBeInTheDocument();
});

it("transmits only explicitly entered cut, neighbor and hardware geometry and exposes an empty bounded search", async () => {
  preview.mockImplementation((request) => Promise.resolve({ ...data, revision: request.revision,
    midpoint_regions: [], comparison: { ...data.comparison, alignment: "SUPPORT" },
    geometry: { ...data.geometry, hardware_state: "FUTURE_UNRESOLVED_STATE", installation_state: undefined } } as unknown as GeometryResponse));
  render(<Harness />);
  await screen.findByRole("button", { name: "Export Geometry and Constructability Review" });
  const fields: [string, string][] = [
    ["Angle cut dimension origin", "Specified cut"],
    ["Angle cut polygon (u,v; u,v; … in)", "0,0;8,0;8,4;0,4"],
    ["Neighbor dimension origin", "Measured neighboring body"],
    ["Neighbor box bounds (six values in)", "10,10,10,11,11,11"],
    ["Envelope dimension origin", "Specified finite envelopes"],
    ["Head envelope (radius,start,end in)", ".3,1,2"],
    ["Nut envelope (radius,start,end in)", ".4,-2,-1"],
    ["Tool envelope (radius,start,end in)", ".5,2,3"],
    ["Geometry-only hole diameter (in)", ".5625"],
    ["Search half-width in both directions (in)", "1"],
  ];
  for (const [label, value] of fields) fireEvent.change(screen.getByLabelText(label), { target: { value } });
  await waitFor(() => { expect(preview.mock.calls.at(-1)?.[0].hardware).toHaveLength(3); });
  fireEvent.click(screen.getByRole("button", { name: "Find bounded midpoint proposals" }));
  await screen.findByText(/No feasible seating proposal in the specified search domain/);
  expect(preview.mock.calls.at(-1)?.[0].end_cuts).toHaveLength(1);
  expect(preview.mock.calls.at(-1)?.[0].neighbors).toHaveLength(1);
  expect(screen.getByText("FUTURE_UNRESOLVED_STATE")).toBeVisible();
});

it("ignores an obsolete rejection and discards an export when inputs change", async () => {
  let rejectOld: ((reason: unknown) => void) | undefined;
  preview.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectOld = reject; }));
  let completeExport: ((value: Blob) => void) | undefined;
  const exported = vi.spyOn(api, "exportGeometry").mockImplementationOnce(() => new Promise((resolve) => { completeExport = resolve; }));
  const objectURL = vi.spyOn(URL, "createObjectURL");
  render(<Harness />);
  fireEvent.change(screen.getByLabelText("Bolt alignment"), { target: { value: "SUPPORT" } });
  await screen.findByRole("button", { name: "Export Geometry and Constructability Review" });
  await act(async () => { rejectOld?.("obsolete failure"); await Promise.resolve(); });
  expect(screen.queryByText("Geometry preview unavailable. Retry.")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Export Geometry and Constructability Review" }));
  await waitFor(() => { expect(exported).toHaveBeenCalled(); });
  fireEvent.change(screen.getByLabelText("Bolt spacing along selected alignment (in)"), { target: { value: "2.25" } });
  await act(async () => { completeExport?.(new Blob(["obsolete"])); await Promise.resolve(); });
  expect(objectURL).not.toHaveBeenCalled();
  exported.mockRejectedValue("untyped failure");
  fireEvent.click(await screen.findByRole("button", { name: "Export Geometry and Constructability Review" }));
  await screen.findByText("Geometry export unavailable. Retry.");
  preview.mockRejectedValueOnce("untyped preview failure");
  fireEvent.change(screen.getByLabelText("Bolt spacing along selected alignment (in)"), { target: { value: "2.5" } });
  await screen.findByText("Geometry preview unavailable. Retry.");
});
