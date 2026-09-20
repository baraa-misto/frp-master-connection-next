import { render, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { TeeConnectorWorkspace } from "../src/workspace/TeeConnectorWorkspace";
import { ClipAngleConnectorWorkspace } from "../src/workspace/ClipAngleConnectorWorkspace";
import { PairedClipAngleConnectorWorkspace } from "../src/workspace/PairedClipAngleConnectorWorkspace";
import { MultiMemberTeeWorkspace } from "../src/workspace/MultiMemberTeeWorkspace";
import {
  loadTeeWorkspaceDefault, loadClipAngleWorkspaceDefault,
  loadPairedClipAngleWorkspaceDefault, loadMultiMemberTeeWorkspaceDefault,
} from "../src/fixtures/connectionWorkspaceDefaults";

const calls = vi.hoisted(() => ({ tee: vi.fn(), clip: vi.fn(), paired: vi.fn(), multi: vi.fn(), design: vi.fn() }));
vi.mock("../src/api/client", async (importOriginal) => ({
  ...await importOriginal<typeof import("../src/api/client")>(),
  previewTeeConnector: calls.tee, previewClipAngle: calls.clip,
  previewPairedClipAngle: calls.paired, previewMultiMemberTee: calls.multi,
  evaluateTeeConnector: calls.design, evaluateClipAngle: calls.design,
  evaluatePairedClipAngle: calls.design, evaluateMultiMemberTee: calls.design,
}));
vi.mock("../src/visualization/VisualizationPanel", () => ({ VisualizationPanel: () => <div>Scene</div> }));
beforeEach(() => {
  for (const call of Object.values(calls)) call.mockReset().mockImplementation(() => new Promise(() => { /* request remains pending */ }));
});

it.each([
  ["Tee", TeeConnectorWorkspace, loadTeeWorkspaceDefault, calls.tee],
  ["Single clip", ClipAngleConnectorWorkspace, loadClipAngleWorkspaceDefault, calls.clip],
  ["Paired clip", PairedClipAngleConnectorWorkspace, loadPairedClipAngleWorkspaceDefault, calls.paired],
  ["Multi-member Tee", MultiMemberTeeWorkspace, loadMultiMemberTeeWorkspaceDefault, calls.multi],
] as const)("%s startup and remount send the exact controlled default for preview only", async (_name, Workspace, factory, preview) => {
  const first = render(<Workspace />);
  await waitFor(() => { expect(preview).toHaveBeenCalled(); });
  expect(preview.mock.calls[0]?.[0]).toEqual(factory("US_CUSTOMARY"));
  expect(calls.design).not.toHaveBeenCalled();
  first.unmount();
  preview.mockClear();
  render(<Workspace />);
  await waitFor(() => { expect(preview).toHaveBeenCalled(); });
  expect(preview.mock.calls[0]?.[0]).toEqual(factory("US_CUSTOMARY"));
  expect(calls.design).not.toHaveBeenCalled();
});
