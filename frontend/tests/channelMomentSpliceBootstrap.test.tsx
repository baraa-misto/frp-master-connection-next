import { StrictMode } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../src/app/App";
import { CHANNEL_MOMENT_SPLICE_PREVIEW_PATH, previewChannelMomentSplice } from "../src/api/client";
import { loadChannelMomentSpliceBenchmark } from "../src/fixtures/channelMomentSpliceBenchmarks";
import type { SingleBoltSceneModel } from "../src/visualization/sceneModel";
import { ChannelMomentSpliceWorkspace } from "../src/workspace/ChannelMomentSpliceWorkspace";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import { previewResponseFixture } from "./fixtures";
import { wiMomentSplicePreviewFixture } from "./wiMomentSpliceFixtures";
import { channelMomentSpliceDesignFixture } from "./channelMomentSpliceFixtures";
import wire from "./fixtures/channelMomentSpliceWire.json";

// Only the browser/WebGL boundary is replaced. App, client, preview hook,
// scene adapter, controls and result trace consume real backend wire data.
vi.mock("../src/visualization/EngineeringScene", () => ({
  default: ({ model, displayMode }: { model: SingleBoltSceneModel; displayMode: string }) =>
    <div data-testid="canvas-boundary" data-mode={displayMode}>
      <span>{model.boxes.length} physical boxes</span>
      <span>{model.boxes.filter((item) => item.id.includes("SPLICE_PLATE")).length} splice plates</span>
      <span>{model.cylinders.filter((item) => item.kind === "BOLT").length} physical bolts</span>
      <span>{model.materialAxes.length} material regions</span>
      <span>{JSON.stringify(model.markers)}</span>
    </div>,
}));

const jsonResponse = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const channelType = "CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE";
const heading = "Moment connection — Channel beam moment splice";
let channelReply: () => Promise<Response>;
let requestedPaths: string[];

function openChannel(fromShear = false) {
  render(<StrictMode><App /></StrictMode>);
  if (fromShear) fireEvent.click(screen.getByRole("button", { name: /Shear Connections/ }));
  fireEvent.click(screen.getByRole("button", { name: /Moment Connections/ }));
  fireEvent.change(screen.getByLabelText("Connection type"), { target: { value: channelType } });
}

async function current() {
  await waitFor(() => { expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled(); });
  expect(screen.getByRole("heading", { level: 2, name: heading })).toBeVisible();
  expect(await screen.findByTestId("canvas-boundary")).toHaveTextContent("12 physical boxes6 splice plates24 physical bolts12 material regions");
}

describe("Stage 4.1B-R1 real wire bootstrap", () => {
  beforeEach(() => {
    requestedPaths = [];
    channelReply = () => Promise.resolve(jsonResponse(wire.US_CUSTOMARY.response));
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.stubGlobal("fetch", vi.fn((input: string, init: RequestInit) => {
      requestedPaths.push(input);
      if (input === CHANNEL_MOMENT_SPLICE_PREVIEW_PATH) {
        const request = JSON.parse(init.body as string) as { unit_system: string };
        if (request.unit_system === "SI") return Promise.resolve(jsonResponse(wire.SI.response));
        return channelReply();
      }
      if (input.includes("channel-major-axis-moment-splice/design-check")) return Promise.resolve(jsonResponse(channelMomentSpliceDesignFixture()));
      if (input.includes("wi-major-axis-moment-splice")) return Promise.resolve(jsonResponse(wiMomentSplicePreviewFixture()));
      return Promise.resolve(jsonResponse(previewResponseFixture()));
    }));
  });
  afterEach(() => {
    expect(console.error).not.toHaveBeenCalled();
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it.each([false, true])("keeps the actual app root mounted through selector transitions (from shear=%s)", async (fromShear) => {
    openChannel(fromShear);
    await current();
    expect(screen.getByRole("heading", { level: 1, name: "FRP Master Connection" })).toBeVisible();
    for (const label of ["Slice 6 — Top Flange", "Slice 6 — Web", "Slice 6 — Bottom Flange", "Centroid / shear center", "Back / opening web branches", "Generated centroidal torsion"]) expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByTestId("canvas-boundary")).toHaveTextContent("CHANNEL_MOMENT_SPLICE_SHEAR_CENTER");
    fireEvent.change(screen.getByLabelText("Geometry display"), { target: { value: "XRAY" } });
    expect(screen.getByTestId("canvas-boundary")).toHaveAttribute("data-mode", "XRAY");
    fireEvent.change(screen.getByLabelText("Connection type"), { target: { value: "WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE" } });
    await screen.findByRole("heading", { level: 2, name: "Moment connection — W/I beam moment splice" });
    fireEvent.change(screen.getByLabelText("Connection type"), { target: { value: channelType } });
    await current();
    expect(requestedPaths.some((path) => path.endsWith("design-check"))).toBe(false);
  });

  it("mounts Channel directly with controlled pending state, then loads exact SI and US presets", async () => {
    let release: ((response: Response) => void) | undefined;
    channelReply = () => new Promise((resolve) => { release = resolve; });
    render(<ChannelMomentSpliceWorkspace />);
    expect(screen.getByRole("heading", { level: 2, name: heading })).toBeVisible();
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(screen.getByText("Updating backend preview…", { selector: "strong" })).toBeVisible();
    await act(async () => { release?.(jsonResponse(wire.US_CUSTOMARY.response)); await Promise.resolve(); });
    await current();
    fireEvent.click(screen.getByRole("button", { name: "Load 4.1B SI" }));
    await current();
    expect(screen.getByLabelText("Channel depth")).toHaveValue("203.2");
    channelReply = () => Promise.resolve(jsonResponse(wire.US_CUSTOMARY.response));
    fireEvent.click(screen.getByRole("button", { name: "Load 4.1B U.S." }));
    await current();
    expect(screen.getByLabelText("Channel depth")).toHaveValue("8");
    expect(screen.getByText(/ICE FRP \+ source-pending F593/)).toBeInTheDocument();
    expect(requestedPaths.some((path) => path.endsWith("design-check"))).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(requestedPaths.filter((path) => path.endsWith("design-check"))).toHaveLength(1); });
    await screen.findByText(/BACK_WEB_PLATE_BODY \/ 0\.82/);
    fireEvent.change(screen.getByLabelText("Major shear V_V"), { target: { value: "10" } });
    expect(screen.getByText(/Design results are stale\./)).toBeVisible();
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
  });

  it.each(["invalid", "http", "network", "malformed"])("retains the last-valid scene and disables design for %s responses", async (mode) => {
    openChannel();
    await current();
    const scene = screen.getByTestId("canvas-boundary").textContent;
    channelReply = () => mode === "network" ? Promise.reject(new TypeError("offline")) : Promise.resolve(jsonResponse(
      mode === "invalid" ? { ...wire.US_CUSTOMARY.response, geometry_status: "INVALID_GEOMETRY", design_check_ready: false, geometry_invalid_reasons: ["INVALID_GAP"] }
        : mode === "malformed" ? { ...wire.US_CUSTOMARY.response, result: { ...wire.US_CUSTOMARY.response.result, visualization: {} } }
          : { detail: "unavailable" }, mode === "http" ? 503 : 200));
    vi.useFakeTimers();
    fireEvent.change(screen.getByLabelText("Beam-end gap"), { target: { value: "100" } });
    await act(async () => { await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS); });
    vi.useRealTimers();
    expect(screen.getByText("Preview unavailable — showing last valid model", { selector: "strong" })).toBeVisible();
    expect(screen.getByTestId("canvas-boundary").textContent).toBe(scene);
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(requestedPaths.some((path) => path.endsWith("design-check"))).toBe(false);
    fireEvent.change(screen.getByLabelText("Beam-end gap"), { target: { value: "0" } });
    expect(screen.getAllByText(/positive decimals/).length).toBeGreaterThan(0);
    expect(screen.getByTestId("canvas-boundary").textContent).toBe(scene);
  });

  it.each(["http", "network"])("keeps the root alive on an initial %s failure and retries", async (mode) => {
    channelReply = () => mode === "network" ? Promise.reject(new TypeError("offline")) : Promise.resolve(jsonResponse({}, 503));
    openChannel();
    await screen.findByRole("alert");
    expect(screen.getByRole("heading", { level: 2, name: heading })).toBeVisible();
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    channelReply = () => Promise.resolve(jsonResponse(wire.US_CUSTOMARY.response));
    fireEvent.click(screen.getByRole("button", { name: "Retry preview" }));
    await current();
  });

  it("rejects absent or non-quantity reference vectors before scene construction", async () => {
    const base = wire.US_CUSTOMARY.response;
    const point = base.result.visualization.channel_shear_center_l_v_t;
    const malformed = [null, {}, { ...point, l: null }, { ...point, l: { value: 1, unit: "in" } }, { ...point, l: { value: "1", unit: 1 } }];
    for (const value of malformed) {
      channelReply = () => Promise.resolve(jsonResponse({ ...base, result: { ...base.result, visualization: { ...base.result.visualization, channel_shear_center_l_v_t: value } } }));
      await expect(previewChannelMomentSplice(loadChannelMomentSpliceBenchmark("US_CUSTOMARY"), new AbortController().signal)).rejects.toMatchObject({ kind: "RESPONSE" });
    }
    channelReply = () => Promise.resolve(jsonResponse({ ...base, result: { visualization: null } }));
    await expect(previewChannelMomentSplice(loadChannelMomentSpliceBenchmark("US_CUSTOMARY"), new AbortController().signal)).rejects.toMatchObject({ kind: "RESPONSE" });
  });
});
