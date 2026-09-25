import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, expect, it, vi } from "vitest";

import { ACTIVATION_AUTHORITY, BODY_ROUTES, parseStainlessActivation, type BodyRoute } from "../src/api/stainlessActivation";
import * as transport from "../src/api/stainlessActivation";
import { setMAT1Active } from "../src/state/mat1Session";
import { ConnectorBodyMaterialControl, ConnectorBodyMaterialResult } from "../src/workspace/connectorBodyMaterial";
import { useConnectorBodyMaterial } from "../src/workspace/useConnectorBodyMaterial";

const fp = "a".repeat(64);
const response = (route: BodyRoute = "clip-angle") => ({
  activation_authority: ACTIVATION_AUTHORITY, route_id: route, connector_body_material: "SS316",
  status: "ENGINEERING_REVIEW_REQUIRED", fingerprint: fp, blockers: ["RESPONSE_SOURCE_REQUIRED"],
  bodies: [{ body_id: "BODY", body_form: "ANGLE", material: "SS316", activation: "ACTIVE_CONDITIONAL",
    fingerprint: fp, blockers: ["SECTION_SOURCE_REQUIRED"], provider_fingerprints: [], frp_body_resistance_used: false }],
  native_non_body_checks: [], trace: { scope: "independent hardware / FRP members / foundation" },
});
const wire = (route?: BodyRoute) => new Response(JSON.stringify(response(route)));
const invalidate = vi.fn();
function Harness({ route = "clip-angle" }: { readonly route?: BodyRoute }) {
  const [revision, setRevision] = useState(0);
  const state = useConnectorBodyMaterial(route, { action: revision }, revision, invalidate);
  return <>
    <ConnectorBodyMaterialControl material={state.material} onChange={state.choose} />
    <button onClick={() => { void state.run(); }}>Run Design Check</button>
    <button onClick={() => { setRevision(n => n + 1); }}>Edit action</button>
    <ConnectorBodyMaterialResult state={state} />
  </>;
}
function stainless() { fireEvent.change(screen.getByRole("combobox", { name: "Connector Body Material" }), { target: { value: "SS316" } }); }
function run() { fireEvent.click(screen.getByRole("button", { name: "Run Design Check" })); }
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); invalidate.mockClear(); });

it("defaults FRP; the one connection-wide selector never runs a calculation itself", () => {
  const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
  render(<Harness />);
  expect(screen.getByRole("combobox")).toHaveValue("FRP");
  expect(screen.getAllByRole("option").map(item => item.textContent)).toEqual(["FRP", "316 Stainless Steel"]);
  run();
  expect(fetcher).not.toHaveBeenCalled();
  stainless();
  expect(invalidate).toHaveBeenCalledExactlyOnceWith();
  expect(fetcher).not.toHaveBeenCalled();
  expect(screen.getByText(/Selection and preview do not calculate resistance/)).toBeVisible();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "SS316" } });
  expect(invalidate).toHaveBeenCalledTimes(1);
});

it.each(BODY_ROUTES)("explicit design uses the existing %s route with a material-only selection", async route => {
  const fetcher = vi.fn().mockResolvedValue(wire(route)); vi.stubGlobal("fetch", fetcher);
  render(<Harness route={route} />); stainless(); run();
  expect(await screen.findByText("ENGINEERING_REVIEW_REQUIRED")).toBeVisible();
  expect(screen.getByText("SECTION_SOURCE_REQUIRED")).toBeVisible();
  expect(screen.getByText(/No FRP connector-body resistance used/)).toBeVisible();
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(fetcher.mock.calls[0]?.[0]).toBe(`/api/v1/calculations/${route}/design-check?connector_body_material=SS316`);
  expect(fetcher.mock.calls[0]?.[1]).toMatchObject({ method: "POST", credentials: "same-origin", body: JSON.stringify({ action: 0 }) });
  fireEvent.click(screen.getByRole("button", { name: "Edit action" }));
  expect(screen.getByText(/Stainless design is stale/)).toBeVisible();
  expect(screen.queryByText("ENGINEERING_REVIEW_REQUIRED")).not.toBeInTheDocument();
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it("material round-trip aborts pending work and cannot resurrect the prior stainless result", async () => {
  let finish: ((value: Response) => void) | undefined;
  const fetcher = vi.fn().mockImplementation(() => new Promise<Response>(resolve => { finish = resolve; }));
  vi.stubGlobal("fetch", fetcher); render(<Harness />); stainless(); run();
  const options = fetcher.mock.calls[0]?.[1] as RequestInit;
  expect(options.signal?.aborted).toBe(false);
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "FRP" } });
  expect(options.signal?.aborted).toBe(true);
  stainless();
  await act(async () => { finish?.(wire()); await Promise.resolve(); });
  expect(screen.queryByText("ENGINEERING_REVIEW_REQUIRED")).not.toBeInTheDocument();
  expect(screen.getByText(/No current stainless design/)).toBeVisible();
});

it("an old action response never replaces a later explicit design", async () => {
  const finishes: ((value: Response) => void)[] = [];
  const fetcher = vi.fn().mockImplementation(() => new Promise<Response>(resolve => { finishes.push(resolve); }));
  vi.stubGlobal("fetch", fetcher); render(<Harness />); stainless(); run();
  fireEvent.click(screen.getByRole("button", { name: "Edit action" })); run();
  await act(async () => { finishes[1]?.(wire()); await Promise.resolve(); });
  expect(screen.getByText("ENGINEERING_REVIEW_REQUIRED")).toBeVisible();
  await act(async () => { finishes[0]?.(new Response(JSON.stringify({ ...response(), status: "FAIL" }))); await Promise.resolve(); });
  expect(screen.queryByText("FAIL")).not.toBeInTheDocument();
  expect(screen.getByText("ENGINEERING_REVIEW_REQUIRED")).toBeVisible();
});

it.each(["network", "http", "validation", "identity", "json", "contract"])("keeps %s errors explicit and permits a new explicit run", async kind => {
  const fetcher = vi.fn();
  if (kind === "network") fetcher.mockRejectedValueOnce(new Error("offline"));
  else fetcher.mockResolvedValueOnce(new Response(kind === "json" ? "{" : JSON.stringify({ detail: "CONTROLLED_ERROR" }), {
    status: kind === "http" ? 503 : kind === "validation" ? 422 : kind === "identity" ? 403 : 200,
  }));
  fetcher.mockResolvedValueOnce(wire()); vi.stubGlobal("fetch", fetcher);
  render(<Harness />); stainless(); run();
  expect(await screen.findByRole("alert")).toBeVisible();
  expect(screen.queryByText("ENGINEERING_REVIEW_REQUIRED")).not.toBeInTheDocument();
  run();
  await waitFor(() => { expect(screen.getByText("ENGINEERING_REVIEW_REQUIRED")).toBeVisible(); });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("rejects FRP fallback, mismatched route, duplicate bodies and false complete PASS", () => {
  const valid = response();
  expect(parseStainlessActivation(valid, "clip-angle")).toEqual(valid);
  for (const invalid of [null, {}, { ...valid, connector_body_material: "FRP" }, { ...valid, route_id: "tee-connector" },
    { ...valid, status: "PASS" }, { ...valid, bodies: [] }, { ...valid, bodies: [valid.bodies[0], valid.bodies[0]] },
    { ...valid, bodies: [{ ...valid.bodies[0], frp_body_resistance_used: true }] },
    { ...valid, bodies: [{ ...valid.bodies[0], provider_fingerprints: ["untrusted"] }] }]) {
    expect(() => parseStainlessActivation(invalid, "clip-angle")).toThrow();
  }
});

it("rejects no-body transport and preserves abort identity without manufacturing an error result", async () => {
  const signal = new AbortController().signal;
  setMAT1Active(true);
  await expect(transport.evaluateStainlessActivation("clip-angle", {}, signal)).rejects.toThrow("MAT1 stainless-body member material routing is unavailable");
  setMAT1Active(false);
  await expect(transport.evaluateStainlessActivation("single-bolt" as BodyRoute, {}, signal)).rejects.toThrow("NOT_APPLICABLE");
  const aborted = new DOMException("cancelled", "AbortError");
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(aborted));
  await expect(transport.evaluateStainlessActivation("clip-angle", {}, signal)).rejects.toBe(aborted);
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("offline", "NetworkError")));
  await expect(transport.evaluateStainlessActivation("clip-angle", {}, signal)).rejects.toThrow("could not be reached");
  expect(() => parseStainlessActivation({ ...response(), status: "PASS", blockers: [] }, "clip-angle")).toThrow("Incomplete");
});

it("renders qualified provider identity, rejects an undeclared option, and keeps internal errors explicit", async () => {
  const valid = { ...response(), status: "PASS", blockers: [], bodies: [
    { ...response().bodies[0], blockers: [], provider_fingerprints: [fp] },
  ] };
  const send = vi.spyOn(transport, "evaluateStainlessActivation").mockResolvedValue(parseStainlessActivation(valid, "clip-angle"));
  render(<Harness />);
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "undeclared" } });
  expect(invalidate).not.toHaveBeenCalled();
  stainless(); run();
  expect(await screen.findByText("PASS")).toBeVisible();
  expect(screen.getByText(`Frozen provider fingerprints: ${fp}`)).toBeVisible();
  send.mockRejectedValueOnce("non-Error internal rejection");
  run();
  expect(await screen.findByRole("alert")).toHaveTextContent("Unexpected stainless design failure.");
});

it("ignores a rejected obsolete stainless request after material selection changes", async () => {
  let reject: ((error: Error) => void) | undefined;
  vi.spyOn(transport, "evaluateStainlessActivation").mockImplementation(() => new Promise((_resolve, fail) => { reject = fail; }));
  render(<Harness />); stainless(); run();
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "FRP" } });
  await act(async () => { reject?.(new Error("obsolete")); await Promise.resolve(); });
  expect(screen.queryByRole("alert")).toBeNull();
});
