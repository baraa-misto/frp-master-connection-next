import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ReportExportButton } from "../src/features/ReportExportButton";
import { setMAT1Active, setMAT1Catalog } from "../src/state/mat1Session";
import { acceptReportSnapshot, currentReportSnapshot, invalidateReportSnapshot, reportGeneration } from "../src/state/reportSession";
import { ConnectionWorkspaceShell } from "../src/workspace/ConnectionWorkspaceShell";

let sequence = 0;

function family(): string {
  sequence += 1;
  return `report-ui-${sequence.toString()}`;
}

function authorize(id: string, kind: "design" | "input_only" = "design"): void {
  acceptReportSnapshot(id, `handle-${id}`, kind, reportGeneration(id));
}

function button(name: string): HTMLButtonElement {
  const element = screen.getByRole("button", { name });
  if (!(element instanceof HTMLButtonElement)) throw new Error("Expected a button");
  return element;
}

function pdfResponse(disposition?: string): Response {
  return new Response(new Blob(["%PDF-1.4"], { type: "application/pdf" }), {
    status: 200,
    headers: {
      "Content-Type": "application/pdf",
      ...(disposition === undefined ? {} : { "Content-Disposition": disposition }),
    },
  });
}

afterEach(() => {
  cleanup();
  setMAT1Active(false);
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("requires a current backend snapshot and distinguishes input-only state", () => {
  const id = family();
  const view = render(<ReportExportButton family={id} />);
  expect(button("Export PDF Report").disabled).toBe(true);
  expect(screen.getByText(/Run a preview or design check/)).toBeTruthy();
  act(() => { authorize(id, "input_only"); });
  fireEvent.click(screen.getByRole("button", { name: "Export PDF Report" }));
  expect(screen.getByRole("heading", { name: "Inputs and model report" })).toBeTruthy();
  expect(screen.getByText(/Inputs and model only/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  act(() => { invalidateReportSnapshot(id); });
  expect(button("Export PDF Report").disabled).toBe(true);
  expect(screen.getByText(/Inputs changed/)).toBeTruthy();
  view.unmount();
});

it("seals an unrun workspace draft before downloading an input-only PDF", async () => {
  const id = family();
  const fetchMock = vi.fn<typeof fetch>()
    .mockResolvedValueOnce(new Response(JSON.stringify({ report_handle: "sealed-draft" }), { status: 201 }))
    .mockResolvedValueOnce(pdfResponse());
  vi.stubGlobal("fetch", fetchMock);
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:draft") });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(vi.fn());
  render(<ReportExportButton family={id} draft={{ length: { value: "-1", unit: "in" } }} />);
  expect(button("Export PDF Report").disabled).toBe(false);
  fireEvent.click(button("Export PDF Report"));
  expect(screen.getByText("Submitted inputs report")).toBeTruthy();
  fireEvent.click(button("Download PDF"));
  await waitFor(() => { expect(click).toHaveBeenCalledOnce(); });
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
    "/api/v1/reports/input-only-snapshot", "/api/v1/reports/export",
  ]);
  expect(JSON.parse(fetchMock.mock.calls[0]?.[1]?.body as string)).toMatchObject({
    family: id, draft: { length: { value: "-1", unit: "in" } },
  });
  expect(JSON.parse(fetchMock.mock.calls[1]?.[1]?.body as string)).toMatchObject({ report_handle: "sealed-draft" });
});

it("discards a draft export if its source changes during snapshot capture", async () => {
  const id = family();
  let resolveCapture: (value: Response) => void = () => { throw new Error("Not assigned"); };
  const fetchMock = vi.fn<typeof fetch>(() => new Promise<Response>(resolve => { resolveCapture = resolve; }));
  vi.stubGlobal("fetch", fetchMock);
  const view = render(<ReportExportButton family={id} draft={{ length: "1" }} />);
  fireEvent.click(button("Export PDF Report"));
  fireEvent.click(button("Download PDF"));
  view.rerender(<ReportExportButton family={id} draft={{ length: "2" }} />);
  act(() => { resolveCapture(new Response(JSON.stringify({ report_handle: "old-draft" }), { status: 201 })); });
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Inputs changed during export. Reopen the report dialog.");
  expect(fetchMock).toHaveBeenCalledOnce();
});

it("includes only the active family's MAT1 assignment in an unrun input draft", async () => {
  const id = family();
  setMAT1Active(true);
  const fetchMock = vi.fn<typeof fetch>()
    .mockResolvedValueOnce(new Response(JSON.stringify({ report_handle: "mat1-draft" }), { status: 201 }))
    .mockResolvedValueOnce(pdfResponse());
  vi.stubGlobal("fetch", fetchMock);
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:mat1") });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(vi.fn());
  render(<ReportExportButton family={id} draft={{ length: "1" }} />);
  fireEvent.click(button("Export PDF Report"));
  fireEvent.click(button("Download PDF"));
  await waitFor(() => { expect(fetchMock).toHaveBeenCalledTimes(2); });
  const captured = JSON.parse(fetchMock.mock.calls[0]?.[1]?.body as string) as {
    draft: { legacy_request: { length: string }; mat1_assignment: { family: string } };
  };
  expect(captured.draft.legacy_request.length).toBe("1");
  expect(captured.draft.mat1_assignment.family).toBe(id);
});

it("does not send a vanished draft after opening the input-only dialog", () => {
  const id = family();
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  const view = render(<ReportExportButton family={id} draft={{ length: "1" }} />);
  fireEvent.click(button("Export PDF Report"));
  view.rerender(<ReportExportButton family={id} />);
  fireEvent.click(button("Download PDF"));
  expect(fetchMock).not.toHaveBeenCalled();
});

it("shows draft-capture validation and malformed-response errors without downloading", async () => {
  const id = family();
  const fetchMock = vi.fn<typeof fetch>()
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Draft too large" }), { status: 413 }))
    .mockResolvedValueOnce(new Response("Service unavailable", { status: 503 }))
    .mockResolvedValueOnce(new Response("{}", { status: 201 }));
  vi.stubGlobal("fetch", fetchMock);
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(vi.fn());
  render(<ReportExportButton family={id} draft={{ length: "1" }} />);
  fireEvent.click(button("Export PDF Report"));
  fireEvent.click(button("Download PDF"));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Draft too large");
  fireEvent.click(button("Download PDF"));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Input snapshot failed.");
  fireEvent.click(button("Download PDF"));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Input snapshot has no report handle.");
  expect(fetchMock).toHaveBeenCalledTimes(3);
  expect(click).not.toHaveBeenCalled();
});

it("downloads the exact snapshot with safe metadata and presentation choices", async () => {
  const id = family();
  authorize(id);
  const fetchMock = vi.fn<typeof fetch>(() =>
    Promise.resolve(pdfResponse('attachment; filename="PROJECT_CONNECTION_R1.pdf"')));
  vi.stubGlobal("fetch", fetchMock);
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:test") });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(vi.fn());
  render(<ReportExportButton family={id} />);
  fireEvent.click(screen.getByRole("button", { name: "Export PDF Report" }));
  fireEvent.change(screen.getByLabelText("Project name"), { target: { value: "Project" } });
  fireEvent.change(screen.getByLabelText("Paper size"), { target: { value: "A4" } });
  fireEvent.change(screen.getByLabelText("Display units"), { target: { value: "SI" } });
  fireEvent.click(screen.getByRole("button", { name: "Download PDF" }));
  await waitFor(() => { expect(screen.queryByRole("dialog")).toBeNull(); });
  const request = fetchMock.mock.calls[0]?.[1];
  if (request === undefined) throw new Error("Missing report request");
  const body = JSON.parse(request.body as string) as Record<string, unknown>;
  expect(body).toMatchObject({ report_handle: `handle-${id}`, paper: "A4", display_units: "SI", project_name: "Project" });
  expect(request.credentials).toBe("same-origin");
  expect(click).toHaveBeenCalledOnce();
});

it("offers the Direct full audit from the same current snapshot", async () => {
  const id = "multi-row";
  authorize(id);
  const fetchMock = vi.fn<typeof fetch>(() => Promise.resolve(pdfResponse()));
  vi.stubGlobal("fetch", fetchMock);
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:direct-audit") });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(vi.fn());
  render(<ReportExportButton family={id} draft={{ direct_finalization_contract_version: "SHEAR01-DIRECT-F1" }} />);
  fireEvent.click(button("Export PDF Report"));
  fireEvent.change(screen.getByLabelText("Report detail"), { target: { value: "FULL_TECHNICAL_AUDIT" } });
  fireEvent.click(button("Download PDF"));
  await waitFor(() => { expect(fetchMock).toHaveBeenCalledOnce(); });
  expect(JSON.parse(fetchMock.mock.calls[0]?.[1]?.body as string)).toMatchObject({
    report_handle: `handle-${id}`,
    mode: "FULL_TECHNICAL_AUDIT",
  });
});

it("shows an expired-snapshot error without downloading a partial file", async () => {
  const id = family();
  authorize(id);
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ detail: "Snapshot expired" }), {
    status: 409, headers: { "Content-Type": "application/json" },
  }))));
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(vi.fn());
  render(<ReportExportButton family={id} />);
  fireEvent.click(screen.getByRole("button", { name: "Export PDF Report" }));
  fireEvent.click(screen.getByRole("button", { name: "Download PDF" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Snapshot expired");
  expect(click).not.toHaveBeenCalled();
});

it("rejects a non-PDF success response", async () => {
  const id = family();
  authorize(id);
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("not a pdf", { status: 200 }))));
  render(<ReportExportButton family={id} />);
  fireEvent.click(screen.getByRole("button", { name: "Export PDF Report" }));
  fireEvent.click(screen.getByRole("button", { name: "Download PDF" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Server returned a non-PDF response.");
});

it("shows a recoverable message for a plain-text renderer failure", async () => {
  const id = family();
  authorize(id);
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("Service unavailable", { status: 503 }))));
  render(<ReportExportButton family={id} />);
  fireEvent.click(screen.getByRole("button", { name: "Export PDF Report" }));
  fireEvent.click(screen.getByRole("button", { name: "Download PDF" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "PDF export failed.");
});

it("discards an old export when inputs change during rendering", async () => {
  const id = family();
  authorize(id);
  let resolveResponse: (value: Response) => void = () => { throw new Error("Not assigned"); };
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(resolve => { resolveResponse = resolve; })));
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(vi.fn());
  render(<ReportExportButton family={id} />);
  fireEvent.click(screen.getByRole("button", { name: "Export PDF Report" }));
  fireEvent.click(screen.getByRole("button", { name: "Download PDF" }));
  expect(button("Creating PDF…").disabled).toBe(true);
  act(() => { invalidateReportSnapshot(id); });
  act(() => { resolveResponse(pdfResponse()); });
  await waitFor(() => {
    expect(screen.getByRole("alert").textContent).toContain("Inputs changed during export");
  });
  expect(click).not.toHaveBeenCalled();
});

it("cancels an in-flight export without downloading its late response", async () => {
  const id = family();
  authorize(id);
  let resolveResponse: (value: Response) => void = () => { throw new Error("Not assigned"); };
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(resolve => { resolveResponse = resolve; })));
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(vi.fn());
  render(<ReportExportButton family={id} />);
  fireEvent.click(screen.getByRole("button", { name: "Export PDF Report" }));
  fireEvent.click(screen.getByRole("button", { name: "Download PDF" }));
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  act(() => { resolveResponse(pdfResponse()); });
  await waitFor(() => { expect(button("Export PDF Report").disabled).toBe(false); });
  expect(click).not.toHaveBeenCalled();
});

it("times out an export and rejects a late PDF response", async () => {
  const id = family();
  authorize(id);
  let resolveResponse: (value: Response) => void = () => { throw new Error("Not assigned"); };
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(resolve => { resolveResponse = resolve; })));
  const timer = vi.spyOn(window, "setTimeout");
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(vi.fn());
  render(<ReportExportButton family={id} />);
  fireEvent.click(screen.getByRole("button", { name: "Export PDF Report" }));
  fireEvent.click(screen.getByRole("button", { name: "Download PDF" }));
  const abortTimer = timer.mock.calls.find(([, delay]) => delay === 120_000)?.[0];
  if (typeof abortTimer !== "function") throw new Error("Missing report timeout");
  act(() => { abortTimer(); resolveResponse(pdfResponse()); });
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent", "PDF export was cancelled or timed out. Try again.",
  );
  expect(click).not.toHaveBeenCalled();
});

it("rejects a stale action even before React has repainted the disabled button", () => {
  const id = family();
  authorize(id);
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  render(<ReportExportButton family={id} />);
  fireEvent.click(screen.getByRole("button", { name: "Export PDF Report" }));
  invalidateReportSnapshot(id);
  fireEvent.click(screen.getByRole("button", { name: "Download PDF" }));
  expect(fetchMock).not.toHaveBeenCalled();
});

it("uses a safe fallback filename and revokes the downloaded object URL", async () => {
  const id = family();
  authorize(id);
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(pdfResponse())));
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:report") });
  const revoke = vi.fn();
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revoke });
  const anchor = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(vi.fn());
  const timeout = vi.spyOn(window, "setTimeout");
  render(<ReportExportButton family={id} />);
  fireEvent.click(screen.getByRole("button", { name: "Export PDF Report" }));
  fireEvent.click(screen.getByRole("button", { name: "Download PDF" }));
  await waitFor(() => { expect(anchor).toHaveBeenCalledOnce(); });
  const revokeTimer = timeout.mock.calls.find(([, delay]) => delay === 60_000)?.[0];
  if (typeof revokeTimer !== "function") throw new Error("Missing URL cleanup timer");
  revokeTimer();
  expect(revoke).toHaveBeenCalledWith("blob:report");
});

it("uses a generic error for malformed server detail and unexpected thrown values", async () => {
  const id = family();
  authorize(id);
  const fetchMock = vi.fn(() => Promise.resolve(new Response(JSON.stringify({ detail: { issue: 1 } }), {
    status: 500, headers: { "Content-Type": "application/json" },
  })));
  vi.stubGlobal("fetch", fetchMock);
  render(<ReportExportButton family={id} />);
  fireEvent.click(screen.getByRole("button", { name: "Export PDF Report" }));
  fireEvent.click(screen.getByRole("button", { name: "Download PDF" }));
  await waitFor(() => { expect(screen.getByRole("alert").textContent).toBe("PDF export failed."); });
  // The renderer boundary must also handle a non-Error rejection.
  // eslint-disable-next-line @typescript-eslint/prefer-promise-reject-errors
  fetchMock.mockImplementation(() => Promise.reject("unexpected value"));
  fireEvent.click(screen.getByRole("button", { name: "Download PDF" }));
  await waitFor(() => { expect(fetchMock).toHaveBeenCalledTimes(2); });
  expect(screen.getByRole("alert").textContent).toBe("PDF export failed.");
});

it("invalidates the workspace snapshot on edited fields and action buttons", () => {
  const id = family();
  setMAT1Active(false);
  const mounted = render(<ConnectionWorkspaceShell family={id} banner={<span>Fixture</span>}>
    <input aria-label="Editable dimension" defaultValue="1" />
    <button type="button">Apply preset</button>
    <span>Diagram</span>
  </ConnectionWorkspaceShell>);
  act(() => { authorize(id); });
  fireEvent.change(screen.getByLabelText("Editable dimension"), { target: { value: "2" } });
  expect(currentReportSnapshot(id).dirty).toBe(true);
  act(() => { authorize(id); });
  fireEvent.click(screen.getByRole("button", { name: "Apply preset" }));
  expect(currentReportSnapshot(id).dirty).toBe(true);
  act(() => { authorize(id); });
  fireEvent.click(screen.getByText("Diagram"));
  expect(currentReportSnapshot(id).dirty).toBe(false);
  mounted.unmount();
  setMAT1Catalog([{ id: "M", revision: "1", content_digest: "a".repeat(64),
    display_name: "Synthetic", company: "Test", resin: "VINYL_ESTER", source_kind: "TEST_DATA",
    missing: [], qualification: "UNQUALIFIED", properties: [] }]);
  setMAT1Active(true);
  // OR1-09: the shared MAT1 panel is bound only to a real capability family;
  // the legacy material-mode switch was removed with the single material authority.
  const panelId = "multi-row";
  const panel = render(<ConnectionWorkspaceShell family={panelId} banner={<span>Fixture</span>}><span>Body</span></ConnectionWorkspaceShell>);
  act(() => { authorize(panelId); });
  fireEvent.change(screen.getByLabelText("Connection default material"), { target: { value: "M" } });
  expect(currentReportSnapshot(panelId).dirty).toBe(true);
  act(() => { authorize(panelId); });
  fireEvent.click(screen.getByRole("button", { name: "New session material" }));
  expect(currentReportSnapshot(panelId).dirty).toBe(true);
  act(() => { authorize(panelId); });
  fireEvent.click(screen.getByText(/Predefined values are read-only owner-supplied data/));
  expect(currentReportSnapshot(panelId).dirty).toBe(false);
  panel.unmount();
  const plain = render(<ConnectionWorkspaceShell banner={<span>Fixture</span>}>
    <input aria-label="Plain field" /><button type="button">Plain action</button>
  </ConnectionWorkspaceShell>);
  fireEvent.change(screen.getByLabelText("Plain field"), { target: { value: "2" } });
  fireEvent.click(screen.getByRole("button", { name: "Plain action" }));
  plain.unmount();
});
