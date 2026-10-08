import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { DirectQualification } from "../src/features/DirectQualification";
import { mat1FamilyKey, mat1Snapshot, setDirectQualificationRecordId, acceptMAT1Design, setMAT1Active } from "../src/state/mat1Session";

beforeEach(() => {
  setMAT1Active(true);
  setDirectQualificationRecordId(null);
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), null);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ available_record_ids: [] }) }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const evaluation = () => ({ record_digest: "A".repeat(64), selected_record_id: "SYNTHETIC_QA", record_revision: 1,
  scope_match_state: "MATCHED", capacity_state: "CAPACITY_PASS", covered_response_ids: ["1", "2", "3", "4", "5"],
  mismatch_reasons: [] as string[], synthetic: true, laboratory: "SYNTHETIC QA laboratory", rdp_approval: "SYNTHETIC QA engineer",
  statistics: { accepted_n: 10, Ro: "10000", phi_p: "0.50866" }, Rd_q: { value: "5086.6", unit: "N" } });

it("keeps the empty approved catalog neutral and prohibits user approval", async () => {
  render(<DirectQualification stale={false} onSelectionChange={vi.fn()} />);
  await waitFor(() => { expect(fetch).toHaveBeenCalledOnce(); });
  expect(screen.getByText("QUALIFICATION REQUIRED")).toBeVisible();
  expect(screen.getByText(/No approved Section 2.3.2/)).toBeVisible();
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  expect(screen.queryByText(/Approve this record/)).not.toBeInTheDocument();
});

it("selects only installed records and invalidates the design identity", async () => {
  vi.mocked(fetch).mockResolvedValue({ ok: true, json: () => Promise.resolve({ available_record_ids: ["Q1", "Q2"] }) } as Response);
  const changed = vi.fn();
  render(<DirectQualification stale={false} onSelectionChange={changed} />);
  const selector = await screen.findByRole("combobox", { name: "Approved qualification record" });
  const key = mat1FamilyKey("multi-row");
  fireEvent.change(selector, { target: { value: "Q1" } });
  expect(mat1Snapshot().directQualificationRecordId).toBe("Q1");
  expect(mat1FamilyKey("multi-row")).not.toBe(key);
  fireEvent.change(selector, { target: { value: "" } });
  expect(mat1Snapshot().directQualificationRecordId).toBeNull();
  expect(changed).toHaveBeenCalledTimes(2);
});

it("shows bounded synthetic statistics without final status activation", () => {
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { qualification_evaluation: evaluation() });
  render(<DirectQualification stale={false} onSelectionChange={vi.fn()} />);
  expect(screen.getByText("SYNTHETIC QA — CANNOT QUALIFY PRODUCTION DESIGN")).toBeVisible();
  expect(screen.getByText("10000 N")).toBeVisible();
  expect(screen.getByText("0.5087")).toBeVisible();
  expect(screen.getByText("5 of 5")).toBeVisible();
  expect(screen.getByText(/final status integration pending/)).toBeVisible();
});

it("shows friendly mismatches, invalid statistics and unavailable strength", () => {
  const item = { ...evaluation(), synthetic: false, statistics: { accepted_n: 9, Ro: null, phi_p: null }, Rd_q: null,
    scope_match_state: "MISMATCH", capacity_state: "UNEVALUATED", mismatch_reasons: ["GEOMETRY MISMATCH", "STATISTICS INVALID"] };
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { qualification_evaluation: item });
  render(<DirectQualification stale={false} onSelectionChange={vi.fn()} />);
  expect(screen.getByText("GEOMETRY MISMATCH")).toBeVisible();
  expect(screen.getByText("STATISTICS INVALID")).toBeVisible();
  expect(screen.getAllByText("Unevaluated")).toHaveLength(3);
  expect(screen.queryByText(/CANNOT QUALIFY/)).not.toBeInTheDocument();
});

it("handles absent optional statistics without NaN", () => {
  const { statistics: ignored, ...item } = evaluation();
  expect(ignored.accepted_n).toBe(10);
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { qualification_evaluation: item });
  render(<DirectQualification stale={false} onSelectionChange={vi.fn()} />);
  expect(screen.getAllByText("Unevaluated")).toHaveLength(3);
  expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
});

it("hides stale records after geometry/material/hardware/action edits", () => {
  acceptMAT1Design("multi-row", mat1FamilyKey("multi-row"), { qualification_evaluation: evaluation() });
  const view = render(<DirectQualification stale onSelectionChange={vi.fn()} />);
  expect(screen.queryByText("10000 N")).not.toBeInTheDocument();
  expect(screen.getByText(/Run Design Check to evaluate/)).toBeVisible();
  view.rerender(<DirectQualification stale={false} onSelectionChange={vi.fn()} />);
  act(() => { setDirectQualificationRecordId("changed"); });
  expect(screen.queryByText("10000 N")).not.toBeInTheDocument();
});

it.each([{}, { available_record_ids: [3] }, { available_record_ids: ["Q", 3] }])("rejects malformed catalog %j", async (body) => {
  vi.mocked(fetch).mockResolvedValue({ ok: true, json: () => Promise.resolve(body) } as Response);
  render(<DirectQualification stale={false} onSelectionChange={vi.fn()} />);
  expect(await screen.findByRole("status")).toHaveTextContent("Check the local backend");
});

it("gives an actionable service failure", async () => {
  vi.mocked(fetch).mockResolvedValue({ ok: false } as Response);
  render(<DirectQualification stale={false} onSelectionChange={vi.fn()} />);
  expect(await screen.findByRole("status")).toHaveTextContent("reload the application");
});

it.each([true, false])("cancels late catalog completion on unmount (reject=%s)", async (reject) => {
  let finish!: (value: Response) => void;
  let fail!: (error: Error) => void;
  vi.mocked(fetch).mockReturnValue(new Promise<Response>((resolve, rejected) => { finish = resolve; fail = rejected; }));
  const view = render(<DirectQualification stale={false} onSelectionChange={vi.fn()} />);
  view.unmount();
  await act(async () => {
    await Promise.resolve();
    if (reject) fail(new Error("aborted"));
    else finish({ ok: true, json: () => Promise.resolve({ available_record_ids: ["Q"] }) } as Response);
  });
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
});
