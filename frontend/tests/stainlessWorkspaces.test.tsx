import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentType } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import * as native from "../src/api/client";
import * as wall from "../src/api/wiWallMomentClient";
import * as support from "../src/api/wiFrpSupportMomentClient";
import * as angle from "../src/api/angleColumnMomentBaseClient";
import * as column from "../src/api/columnMomentBaseClient";
import type { AngleBaseRequest, AngleBaseResponse } from "../src/api/angleColumnMomentBaseContracts";
import type { ColumnMomentBaseRequest, ColumnMomentBaseResponse } from "../src/api/columnMomentBaseContracts";
import { ACTIVATION_AUTHORITY, type BodyRoute } from "../src/api/stainlessActivation";
import { ClipAngleConnectorWorkspace } from "../src/workspace/ClipAngleConnectorWorkspace";
import { TeeConnectorWorkspace } from "../src/workspace/TeeConnectorWorkspace";
import { PairedClipAngleConnectorWorkspace } from "../src/workspace/PairedClipAngleConnectorWorkspace";
import { BeamConcretePairedAngleWorkspace } from "../src/workspace/BeamConcretePairedAngleWorkspace";
import { ColumnBaseWebAngleWorkspace } from "../src/workspace/ColumnBaseWebAngleWorkspace";
import { MultiMemberTeeWorkspace } from "../src/workspace/MultiMemberTeeWorkspace";
import { WebSpliceWorkspace } from "../src/workspace/WebSpliceWorkspace";
import { WIMomentSpliceWorkspace } from "../src/workspace/WIMomentSpliceWorkspace";
import { ChannelMomentSpliceWorkspace } from "../src/workspace/ChannelMomentSpliceWorkspace";
import { WIWallMomentWorkspace } from "../src/workspace/WIWallMomentWorkspace";
import { WIFrpSupportMomentWorkspace } from "../src/workspace/WIFrpSupportMomentWorkspace";
import { AngleColumnMomentBaseWorkspace } from "../src/workspace/AngleColumnMomentBaseWorkspace";
import { ColumnMomentBaseWorkspace } from "../src/workspace/ColumnMomentBaseWorkspace";
import { clipAnglePreviewFixture, clipAngleDesignFixture } from "./clipAngleFixtures";
import { teePreviewFixture, teeDesignFixture } from "./teeFixtures";
import { pairedClipAnglePreviewFixture, pairedClipAngleDesignFixture } from "./pairedClipAngleFixtures";
import { beamConcretePreviewFixture, beamConcreteDesignFixture } from "./beamConcretePairedAngleFixtures";
import { columnBasePreviewFixture, columnBaseDesignFixture } from "./columnBaseWebAngleFixtures";
import { multiMemberTeePreview, multiMemberTeeDesign } from "./multiMemberTeeFixtures";
import { webSpliceRC2PreviewFixture, webSpliceRC2DesignFixture } from "./webSpliceFixtures";
import { wiMomentSplicePreviewFixture, wiMomentSpliceDesignFixture } from "./wiMomentSpliceFixtures";
import { channelMomentSplicePreviewFixture, channelMomentSpliceDesignFixture } from "./channelMomentSpliceFixtures";
import { wallPreviewFixture, wallDesignFixture } from "./wiWallMomentFixtures";
import { frpPreviewFixture, frpDesignFixture } from "./wiFrpSupportMomentFixtures";
import angleData from "./fixtures/angleColumnMomentBase.json";
import columnData from "./fixtures/columnMomentBase.json";

// Only the WebGL boundary is mocked. Real workspace state, preview workflows,
// material selection, explicit dispatch and stale-result handling are exercised.
vi.mock("../src/visualization/VisualizationPanel", () => ({ VisualizationPanel: () => <div>Viewer</div> }));
const matrix: readonly [BodyRoute, ComponentType][] = [
  ["clip-angle", ClipAngleConnectorWorkspace], ["tee-connector", TeeConnectorWorkspace],
  ["paired-clip-angle", PairedClipAngleConnectorWorkspace],
  ["beam-concrete-paired-angle", BeamConcretePairedAngleWorkspace],
  ["column-base-web-angles", ColumnBaseWebAngleWorkspace], ["multi-member-tee", MultiMemberTeeWorkspace],
  ["beam-web-splice", WebSpliceWorkspace], ["wi-major-axis-moment-splice", WIMomentSpliceWorkspace],
  ["channel-major-axis-moment-splice", ChannelMomentSpliceWorkspace],
  ["wi-beam-concrete-wall-moment", WIWallMomentWorkspace], ["wi-beam-frp-support-moment", WIFrpSupportMomentWorkspace],
  ["angle-column-two-leg-moment-base", AngleColumnMomentBaseWorkspace],
  ["wi-rhs-srs-column-moment-base", ColumnMomentBaseWorkspace],
];
const fp = "b".repeat(64);
const activated = (route: BodyRoute) => ({
  activation_authority: ACTIVATION_AUTHORITY, route_id: route, connector_body_material: "SS316",
  status: "ENGINEERING_REVIEW_REQUIRED", fingerprint: fp, blockers: ["TEST_RESPONSE_NOT_QUALIFIED"],
  bodies: [{ body_id: "TEST_BODY", body_form: "ANGLE", material: "SS316", activation: "ACTIVE_CONDITIONAL",
    fingerprint: fp, blockers: ["TEST_SECTION_NOT_QUALIFIED"], provider_fingerprints: [], frp_body_resistance_used: false }],
  native_non_body_checks: [], trace: { test_only: true },
});
beforeEach(() => {
  vi.spyOn(native, "previewClipAngle").mockResolvedValue(clipAnglePreviewFixture());
  vi.spyOn(native, "evaluateClipAngle").mockResolvedValue(clipAngleDesignFixture());
  vi.spyOn(native, "previewTeeConnector").mockResolvedValue(teePreviewFixture());
  vi.spyOn(native, "evaluateTeeConnector").mockResolvedValue(teeDesignFixture());
  vi.spyOn(native, "previewPairedClipAngle").mockResolvedValue(pairedClipAnglePreviewFixture());
  vi.spyOn(native, "evaluatePairedClipAngle").mockResolvedValue(pairedClipAngleDesignFixture());
  vi.spyOn(native, "previewBeamConcretePairedAngle").mockResolvedValue(beamConcretePreviewFixture());
  vi.spyOn(native, "evaluateBeamConcretePairedAngle").mockResolvedValue(beamConcreteDesignFixture());
  vi.spyOn(native, "previewColumnBaseWebAngle").mockResolvedValue(columnBasePreviewFixture());
  vi.spyOn(native, "evaluateColumnBaseWebAngle").mockResolvedValue(columnBaseDesignFixture());
  vi.spyOn(native, "previewMultiMemberTee").mockResolvedValue(multiMemberTeePreview());
  vi.spyOn(native, "evaluateMultiMemberTee").mockResolvedValue(multiMemberTeeDesign());
  vi.spyOn(native, "previewWebSplice").mockResolvedValue(webSpliceRC2PreviewFixture());
  vi.spyOn(native, "evaluateWebSplice").mockResolvedValue(webSpliceRC2DesignFixture());
  vi.spyOn(native, "previewWIMomentSplice").mockResolvedValue(wiMomentSplicePreviewFixture());
  vi.spyOn(native, "evaluateWIMomentSplice").mockResolvedValue(wiMomentSpliceDesignFixture());
  vi.spyOn(native, "previewChannelMomentSplice").mockResolvedValue(channelMomentSplicePreviewFixture());
  vi.spyOn(native, "evaluateChannelMomentSplice").mockResolvedValue(channelMomentSpliceDesignFixture());
  vi.spyOn(wall, "previewWIWallMoment").mockResolvedValue(wallPreviewFixture());
  vi.spyOn(wall, "designWIWallMoment").mockResolvedValue(wallDesignFixture());
  vi.spyOn(support, "previewWIFrpSupportMoment").mockResolvedValue(frpPreviewFixture());
  vi.spyOn(support, "designWIFrpSupportMoment").mockResolvedValue(frpDesignFixture());
  const a = structuredClone(angleData.equal_us) as unknown as {request: AngleBaseRequest; preview: AngleBaseResponse; design: AngleBaseResponse};
  vi.spyOn(angle, "loadAngleBasePreset").mockResolvedValue(a.request);
  vi.spyOn(angle, "requestAngleBase").mockImplementation(kind => Promise.resolve(kind === "preview" ? a.preview : a.design));
  const c = structuredClone(columnData.WI12_TWO_X) as unknown as {request: ColumnMomentBaseRequest; preview: ColumnMomentBaseResponse; design: ColumnMomentBaseResponse};
  vi.spyOn(column, "loadColumnMomentBasePreset").mockResolvedValue(c.request);
  vi.spyOn(column, "requestColumnMomentBase").mockImplementation(kind => Promise.resolve(kind === "preview" ? c.preview : c.design));
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it.each(matrix)("%s real workspace retains material, requires explicit design and invalidates round-tripped results", async (route, Workspace) => {
  const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(activated(route)))));
  vi.stubGlobal("fetch", fetcher);
  render(<Workspace />);
  const selector = await screen.findByRole("combobox", { name: "Connector Body Material" });
  expect(selector).toHaveValue("FRP");
  expect(within(selector).getAllByRole("option").map(x => x.textContent)).toEqual(["FRP", "316 Stainless Steel"]);
  const run = screen.getByRole("button", { name: "Run Design Check" });
  await waitFor(() => { expect(run).toBeEnabled(); });
  await act(async () => { fireEvent.click(run); await Promise.resolve(); });
  fireEvent.change(selector, { target: { value: "SS316" } });
  expect(fetcher).not.toHaveBeenCalled();
  expect(screen.getByText(/No current stainless design/)).toBeVisible();
  await act(async () => { fireEvent.click(run); await Promise.resolve(); });
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(fetcher.mock.calls[0]?.[0]).toBe(`/api/v1/calculations/${route}/design-check?connector_body_material=SS316`);
  expect(screen.getByText("TEST_SECTION_NOT_QUALIFIED")).toBeVisible();
  fireEvent.change(selector, { target: { value: "FRP" } });
  expect(screen.queryByText("TEST_SECTION_NOT_QUALIFIED")).toBeNull();
  fireEvent.change(selector, { target: { value: "SS316" } });
  expect(screen.getByText(/No current stainless design/)).toBeVisible();
  expect(fetcher).toHaveBeenCalledTimes(1);
  await act(async () => { fireEvent.click(run); await Promise.resolve(); });
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it.each([false, true])("a late multi-member Tee FRP completion (reject=%s) cannot replace stainless state", async rejects => {
  let finish: (() => void) | undefined;
  vi.mocked(native.evaluateMultiMemberTee).mockImplementation(() => new Promise((resolve, reject) => {
    finish = () => { if (rejects) reject(new Error("obsolete FRP")); else resolve(multiMemberTeeDesign()); };
  }));
  render(<MultiMemberTeeWorkspace />);
  const run = screen.getByRole("button", { name: "Run Design Check" });
  await waitFor(() => { expect(run).toBeEnabled(); });
  fireEvent.click(run);
  fireEvent.change(screen.getByRole("combobox", { name: "Connector Body Material" }), { target: { value: "SS316" } });
  await act(async () => { finish?.(); await Promise.resolve(); });
  expect(screen.queryByText("obsolete FRP")).toBeNull();
  expect(screen.getByText(/No current stainless design/)).toBeVisible();
});
