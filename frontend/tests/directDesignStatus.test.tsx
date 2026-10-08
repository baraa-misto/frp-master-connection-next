import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { DirectDesignStatus } from "../src/features/DirectDesignStatus";
import { currentDirectDecision, directDecisionHeadline, type DirectDecision } from "../src/features/directDecision";
import { validateDirectDecisionCurrency } from "../src/features/directDecisionCurrency";
import { acceptMAT1Design, mat1FamilyKey, setDirectQualificationRecordId, setMAT1Active } from "../src/state/mat1Session";
import { acceptReportSnapshot, currentReportSnapshot, invalidateReportSnapshot, reportGeneration } from "../src/state/reportSession";

const decision = (color: DirectDecision["final_status"] = "YELLOW"): DirectDecision => ({
  contract: "DIRECT-STATUS-F9", final_status: color, final_status_reason: "Backend decision reason",
  governing_label: "Approved matching connection qualification", unresolved_requirements: ["Select approved evidence"],
  qualification_capacity_state: "UNEVALUATED", analytical_check_summary: {
    evaluated: 8, numerical_outcome: "PASS", highest_utilization: ".22269860632194155", counts: { REQUIRED_UNRESOLVED: 6 },
  },
});
beforeEach(() => {
  setMAT1Active(true); setDirectQualificationRecordId(null);
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), null);
  invalidateReportSnapshot("multi-row");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ current: true }) }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.useRealTimers(); });

it.each(["GREEN", "RED", "YELLOW", "GRAY"] as const)("renders only the backend %s decision and reason", (color) => {
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { final_decision: decision(color) });
  render(<DirectDesignStatus stale={false} onCurrencyInvalid={vi.fn()} />);
  expect(screen.getByRole("status")).toHaveClass(`status-${color.toLowerCase()}`);
  expect(screen.getByRole("heading")).toHaveTextContent(`${color} — Backend decision reason`);
  expect(screen.getByText("0.222699")).toBeVisible();
  fireEvent.click(screen.getByText("Remaining actions and decision diagnostics"));
  expect(screen.getByText("Select approved evidence")).toBeVisible();
});

it("never turns frontend counts or client qualification booleans into GREEN", () => {
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { qualification_evaluation: { activation_permitted: true }, calculated_count: 999 });
  render(<DirectDesignStatus stale={false} onCurrencyInvalid={vi.fn()} />);
  expect(screen.getByRole("heading")).toHaveTextContent("GRAY — not calculated / input needed");
  expect(screen.queryByText(/GREEN/)).not.toBeInTheDocument();
  expect(currentDirectDecision({ final_decision: { contract: "OTHER" } }, false, true)).toBeUndefined();
});

it("invalidates an old GREEN after an engineering edit but keeps camera-only presentation current", () => {
  const item = decision("GREEN");
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { final_decision: item });
  const view = render(<DirectDesignStatus stale={false} onCurrencyInvalid={vi.fn()} />);
  view.rerender(<DirectDesignStatus stale={false} onCurrencyInvalid={vi.fn()} />);
  expect(screen.getByRole("heading")).toHaveTextContent("GREEN");
  view.rerender(<DirectDesignStatus stale onCurrencyInvalid={vi.fn()} />);
  expect(screen.getByRole("heading")).toHaveTextContent("GRAY — stale");
  expect(currentDirectDecision({ final_decision: item }, false, false)).toBeUndefined();
  expect(directDecisionHeadline(undefined, false)).toContain("GRAY");
});

it("renders unavailable utilization and an evaluated qualification capacity without computing status", () => {
  const item = { ...decision("RED"), qualification_capacity_state: "CAPACITY_FAIL", analytical_check_summary: { ...decision().analytical_check_summary, highest_utilization: null } };
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { final_decision: item });
  render(<DirectDesignStatus stale={false} onCurrencyInvalid={vi.fn()} />);
  expect(screen.getByText("Unevaluated")).toBeVisible();
  expect(screen.getByText("CAPACITY FAIL")).toBeVisible();
});

function signedAuthority() {
  acceptReportSnapshot("multi-row", "s".repeat(32), "design", reportGeneration("multi-row"));
}

it("uses the signed backend handle for currency, rechecking on focus", async () => {
  signedAuthority();
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { final_decision: { ...decision(), qualification_record_identity: { digest: "D" } } });
  const invalid = vi.fn();
  render(<DirectDesignStatus stale={false} onCurrencyInvalid={invalid} />);
  await waitFor(() => { expect(fetch).toHaveBeenCalledOnce(); });
  const options = vi.mocked(fetch).mock.calls[0]?.[1];
  expect(JSON.parse(options?.body as string)).toEqual({ report_handle: "s".repeat(32) });
  expect(invalid).not.toHaveBeenCalled();
  vi.mocked(fetch).mockResolvedValueOnce({ ok: false } as Response);
  fireEvent.focus(window);
  await waitFor(() => { expect(invalid).toHaveBeenCalledOnce(); });
  expect(currentReportSnapshot("multi-row").dirty).toBe(true);
});

it("rechecks currency periodically and aborts late responses on unmount", async () => {
  vi.useFakeTimers(); signedAuthority();
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { final_decision: { ...decision(), qualification_record_identity: { digest: "D" } } });
  const invalid = vi.fn();
  const view = render(<DirectDesignStatus stale={false} onCurrencyInvalid={invalid} />);
  await act(async () => { await Promise.resolve(); });
  await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
  expect(fetch).toHaveBeenCalledTimes(2);
  let resolve!: (response: Response) => void;
  vi.mocked(fetch).mockReturnValueOnce(new Promise<Response>((r) => { resolve = r; }));
  fireEvent.focus(window); view.unmount();
  await act(async () => { resolve({ ok: false } as Response); await Promise.resolve(); });
  expect(invalid).not.toHaveBeenCalled();
});

it("does not inspect qualification currency for an already stale design", () => {
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { final_decision: { ...decision("GREEN"), qualification_record_identity: { digest: "D" } } });
  render(<DirectDesignStatus stale onCurrencyInvalid={vi.fn()} />);
  expect(fetch).not.toHaveBeenCalled();
});

it("fails closed without current signed authority", async () => {
  expect(await validateDirectDecisionCurrency(new AbortController().signal)).toBe(false);
  acceptReportSnapshot("multi-row", "draft", "input_only", reportGeneration("multi-row"));
  expect(await validateDirectDecisionCurrency(new AbortController().signal)).toBe(false);
});

it.each([{}, { current: false }, { current: "true" }])("rejects an invalid currency response %j", async (body) => {
  signedAuthority();
  vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(body) } as Response);
  expect(await validateDirectDecisionCurrency(new AbortController().signal)).toBe(false);
});

it("fails closed on a currency service or JSON failure", async () => {
  signedAuthority(); vi.mocked(fetch).mockRejectedValueOnce(new Error("offline"));
  expect(await validateDirectDecisionCurrency(new AbortController().signal)).toBe(false);
});
