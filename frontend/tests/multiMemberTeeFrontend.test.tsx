import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationTransportError } from "../src/api/client";
import type { MultiMemberTeeRequest, MultiMemberTeeSlotId } from "../src/api/multiMemberTeeContracts";
import {
  initialMultiMemberTeeProfile,
  initialMultiMemberTeeSupport,
  loadMultiMemberTeeBenchmark,
} from "../src/fixtures/multiMemberTeeBenchmarks";
import { buildMultiMemberTeeSceneModel, collectTriangleMeshPoints } from "../src/visualization/multiMemberTeeSceneModel";
import { MultiMemberTeeWorkspace } from "../src/workspace/MultiMemberTeeWorkspace";
import { MultiMemberTeeProfileEditor } from "../src/workspace/MultiMemberTeeProfileEditor";
import { ShearConnectionsWorkspace } from "../src/workspace/ShearConnectionsWorkspace";
import { useMultiMemberTeePreview } from "../src/workspace/multiMemberTeeWorkflow";
import { SupportingMemberEditor } from "../src/workspace/SupportingMemberEditor";
import { multiMemberTeeDesign, multiMemberTeePreview, multiMemberTeeVisualization } from "./multiMemberTeeFixtures";

// Retain the explicit historical node inputs for the existing interaction regressions.
vi.mock("../src/fixtures/connectionWorkspaceDefaults", async (importOriginal) => ({
  ...await importOriginal<typeof import("../src/fixtures/connectionWorkspaceDefaults")>(),
  loadMultiMemberTeeWorkspaceDefault: loadMultiMemberTeeBenchmark,
}));

const mocks = vi.hoisted(() => ({ preview: vi.fn(), design: vi.fn() }));
vi.mock("../src/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/api/client")>()),
  previewMultiMemberTee: mocks.preview,
  evaluateMultiMemberTee: mocks.design,
}));
vi.mock("../src/visualization/VisualizationPanel", () => ({
  VisualizationPanel: ({ model, selection, onSelect }: {
    readonly model: import("../src/visualization/sceneModel").SingleBoltSceneModel;
    readonly selection: { kind: string; id: string };
    readonly onSelect: (selection: { kind: "MEMBER"; id: string }) => void;
  }) => <div data-testid="node-viewer" data-members={model.boxes.filter((item) => item.ownerRole === "BRACE").length} data-bolt-groups={new Set(model.cylinders.filter((item) => item.kind === "BOLT").map((item) => item.interfaceId)).size} data-material-regions={model.materialAxes.length} data-selection={`${selection.kind}:${selection.id}`}><button type="button" onClick={() => { onSelect({ kind: "MEMBER", id: "multi-member-tee:lower_brace" }); }}>Pick lower member</button></div>,
}));
vi.mock("../src/workspace/SingleBoltEngineeringWorkspace", () => ({ SingleBoltEngineeringWorkspace: () => <div>Frozen Direct workspace</div> }));
vi.mock("../src/workspace/TeeConnectorWorkspace", () => ({ TeeConnectorWorkspace: () => <div>Frozen single-member Tee workspace</div> }));
vi.mock("../src/workspace/ClipAngleConnectorWorkspace", () => ({ ClipAngleConnectorWorkspace: () => <div>Accepted Single Clip-Angle workspace</div> }));
vi.mock("../src/workspace/PairedClipAngleConnectorWorkspace", () => ({ PairedClipAngleConnectorWorkspace: () => <div>Accepted Paired Clip-Angle workspace</div> }));

function latestPreviewRequest(): MultiMemberTeeRequest {
  return mocks.preview.mock.calls.at(-1)?.[0] as MultiMemberTeeRequest;
}

const SLOT_CASES = [
  ["Upper only", ["UPPER_BRACE"]],
  ["Middle only", ["MIDDLE_BEAM"]],
  ["Lower only", ["LOWER_BRACE"]],
  ["Upper and Middle", ["UPPER_BRACE", "MIDDLE_BEAM"]],
  ["Upper and Lower", ["UPPER_BRACE", "LOWER_BRACE"]],
  ["Middle and Lower", ["MIDDLE_BEAM", "LOWER_BRACE"]],
  ["all three", ["UPPER_BRACE", "MIDDLE_BEAM", "LOWER_BRACE"]],
] as const;

function activeSlotIds(request: MultiMemberTeeRequest): MultiMemberTeeSlotId[] {
  return [
    request.upper_brace === undefined ? null : "UPPER_BRACE",
    request.middle_beam === undefined ? null : "MIDDLE_BEAM",
    request.lower_brace === undefined ? null : "LOWER_BRACE",
  ].filter((value): value is MultiMemberTeeSlotId => value !== null);
}

async function withoutWindowErrors(action: () => Promise<void>): Promise<void> {
  const errors: unknown[] = [];
  const onError = (event: ErrorEvent) => { errors.push(event.error ?? event.message); };
  window.addEventListener("error", onError);
  try {
    await action();
    expect(errors).toEqual([]);
  } finally {
    window.removeEventListener("error", onError);
  }
}

describe("Stage 3.4B benchmark", () => {
  beforeEach(() => { mocks.preview.mockReset(); mocks.design.mockReset(); vi.unstubAllGlobals(); });

  it("loads exact independent U.S. and SI all-three fixtures without hidden IDs", () => {
    const us = loadMultiMemberTeeBenchmark("US_CUSTOMARY");
    const si = loadMultiMemberTeeBenchmark("SI");
    expect(us.connector_dimensions.connector_length).toEqual({ value: "30", unit: "in" });
    expect(si.connector_dimensions.connector_length).toEqual({ value: "762", unit: "mm" });
    expect(us.upper_brace.action.force_hvn).toMatchObject({ x: "3.4641016151377544", y: "2", unit: "kip" });
    expect(si.upper_brace.action.force_hvn).toMatchObject({ x: "15.4090916819145687953847410212", y: "8.896443230521", unit: "kN" });
    expect(Object.keys(us)).not.toContain("fingerprint");
  });

  it("builds exact strict defaults for all six profile families and seven supports", () => {
    const families = [
      "FLAT_PLATE", "ANGLE", "CHANNEL", "WIDE_FLANGE_I",
      "RECTANGULAR_HOLLOW_SECTION", "SOLID_RECTANGULAR_SECTION",
    ] as const;
    for (const system of ["US_CUSTOMARY", "SI"] as const) {
      for (const family of families) {
        const profile = initialMultiMemberTeeProfile(family, system, `profile-${family}`);
        expect(profile.profile_family).toBe(family);
        expect(profile.dimensions.member_length.unit).toBe(system === "SI" ? "mm" : "in");
      }
      for (const target of [
        "W_COLUMN_FLANGE", "W_BEAM_FLANGE", "W_COLUMN_WEB", "CHANNEL_COLUMN_WEB",
        "ANGLE_COLUMN_LEG", "RECTANGULAR_HOLLOW_COLUMN_WALL", "SOLID_RECTANGULAR_COLUMN_FACE",
      ] as const) {
        expect(initialMultiMemberTeeSupport(target, system).member_length.value).toBe(system === "SI" ? "406.4" : "16");
      }
    }
  });

  it("keeps impossible/missing profile fields and restricted support lists presentation-safe", () => {
    const profile = initialMultiMemberTeeProfile("ANGLE", "US_CUSTOMARY", "profile-angle");
    delete profile.dimensions.leg_z;
    const onProfileChange = vi.fn();
    render(<MultiMemberTeeProfileEditor label="Controlled Member" unitSystem="US_CUSTOMARY" profile={profile} onChange={onProfileChange} />);
    expect(screen.queryByLabelText("Controlled Member Leg Z")).not.toBeInTheDocument();
    const support = initialMultiMemberTeeSupport("W_COLUMN_FLANGE", "US_CUSTOMARY");
    render(<SupportingMemberEditor targetId="W_COLUMN_FLANGE" profile={support} allowedTargets={["W_COLUMN_FLANGE"]} onTargetChange={vi.fn()} onProfileChange={vi.fn()} />);
    const supportSelector = screen.getAllByLabelText("Supporting member").at(0);
    expect(supportSelector).toBeDefined();
    if (supportSelector === undefined) {
      throw new Error("Expected the restricted supporting-member selector.");
    }
    expect(within(supportSelector).getAllByRole("option")).toHaveLength(1);
  });
});

describe("Multi-Member Tee scene composition", () => {
  it("collects exact triangle-mesh vertices when a transport snapshot contains them", () => {
    const points = [[0, 0, 0], [1, 0, 0], [0, 1, 0]] as const;
    expect(collectTriangleMeshPoints([{ id: "mesh", points } as never])).toEqual(points);
  });

  it("renders one shared Tee/support, every active physical member, four groups and owner-qualified selection", () => {
    const model = buildMultiMemberTeeSceneModel(multiMemberTeeVisualization());
    expect(new Set(model.boxes.map((item) => item.ownerId)).size).toBeGreaterThan(3);
    expect(model.boxes.some((item) => item.ownerId === "multi-member-tee:upper_brace")).toBe(true);
    expect(model.boxes.some((item) => item.ownerId === "multi-member-tee:middle_beam" && item.ownerRole === "OTHER")).toBe(true);
    expect(model.boxes.some((item) => item.ownerId === "multi-member-tee:lower_brace")).toBe(true);
    expect(model.boxes.filter((item) => item.ownerId === "multi-member-tee:upper_brace").every((item) => item.ownerRole === "BRACE")).toBe(true);
    expect(model.boxes.filter((item) => item.ownerId === "multi-member-tee:lower_brace").every((item) => item.ownerRole === "BRACE")).toBe(true);
    expect(new Set(model.cylinders.filter((item) => item.kind === "BOLT").map((item) => item.interfaceId))).toEqual(new Set(["UPPER_BRACE_TO_TEE_STEM", "MIDDLE_BEAM_TO_TEE_STEM", "LOWER_BRACE_TO_TEE_STEM", "TEE_INTERFACE_B_FLANGE_TO_SUPPORT"]));
    expect(model.zones.some((item) => item.participantId === "multi-member-tee:upper_brace")).toBe(true);
    expect(model.zones.some((item) => item.participantId !== "multi-member-tee:upper_brace")).toBe(true);
    expect(model.boundsRadius).toBeGreaterThan(1);
    expect(model.fitCenter).toEqual(model.boundsCenter);
  });

  it("supports one slot and fails closed for absent visualization slots", () => {
    const model = buildMultiMemberTeeSceneModel(multiMemberTeeVisualization(["MIDDLE_BEAM"]));
    expect(model.boxes.some((item) => item.ownerId === "multi-member-tee:middle_beam")).toBe(true);
    expect(() => buildMultiMemberTeeSceneModel({ schema_version: "0.1.0-draft", slots: [] })).toThrow("active slot");
    const unusual = multiMemberTeeVisualization(["UPPER_BRACE"]);
    const slot = unusual.slots[0];
    if (slot === undefined) throw new Error("fixture invariant");
    const modelWithStableFallback = buildMultiMemberTeeSceneModel({
      ...unusual,
      slots: [{ ...slot, slot_id: "OWNER_DEFINED_SLOT" as never }],
    });
    expect(modelWithStableFallback.boxes.some((item) => item.ownerLabel.startsWith("OWNER_DEFINED_SLOT"))).toBe(true);
  });
});

function WorkflowProbe({ revision }: { readonly revision: number }) {
  const state = useMultiMemberTeePreview(loadMultiMemberTeeBenchmark("US_CUSTOMARY"), revision);
  useEffect(() => undefined, [state]);
  return <div><span data-testid="workflow-state">{state.state}</span><span data-testid="workflow-result">{state.response?.engineering_fingerprint ?? "none"}</span><span data-testid="workflow-detail">{state.detail ?? "none"}</span><button type="button" onClick={state.retry}>Retry</button></div>;
}

describe("Multi-Member Tee latest-preview workflow", () => {
  beforeEach(() => { vi.useFakeTimers(); mocks.preview.mockReset(); });
  afterEach(() => { vi.useRealTimers(); });

  it("debounces edits, keeps last valid geometry for invalid/error states, ignores stale and retries", async () => {
    mocks.preview.mockResolvedValueOnce(multiMemberTeePreview());
    const view = render(<WorkflowProbe revision={0} />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByTestId("workflow-state")).toHaveTextContent("CURRENT_VALID");
    mocks.preview.mockResolvedValueOnce(multiMemberTeePreview("INVALID_GEOMETRY"));
    view.rerender(<WorkflowProbe revision={1} />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByTestId("workflow-state")).toHaveTextContent("CURRENT_INVALID_SHOWING_LAST_VALID");
    mocks.preview.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "offline"));
    view.rerender(<WorkflowProbe revision={2} />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByTestId("workflow-state")).toHaveTextContent("PREVIEW_FAILED_SHOWING_LAST_VALID");
    mocks.preview.mockResolvedValueOnce(multiMemberTeePreview());
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByTestId("workflow-state")).toHaveTextContent("CURRENT_VALID");
  });

  it("reports first-response invalid/error states and ignores aborted or obsolete responses", async () => {
    mocks.preview.mockResolvedValueOnce({ ...multiMemberTeePreview("INVALID_GEOMETRY"), result: { ...multiMemberTeePreview("INVALID_GEOMETRY").result, warnings: [] } });
    const invalid = render(<WorkflowProbe revision={0} />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByTestId("workflow-state")).toHaveTextContent("NO_VALID_PREVIEW");
    expect(screen.getByTestId("workflow-detail")).toHaveTextContent("Backend rejected current geometry.");
    invalid.unmount();
    mocks.preview.mockRejectedValueOnce(new Error("unexpected"));
    const failed = render(<WorkflowProbe revision={0} />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByTestId("workflow-state")).toHaveTextContent("NO_VALID_PREVIEW");
    expect(screen.getByTestId("workflow-detail")).toHaveTextContent("Preview failed.");
    failed.unmount();
    mocks.preview.mockRejectedValueOnce(new EvaluationTransportError("VALIDATION", 422, "field invalid"));
    const validation = render(<WorkflowProbe revision={0} />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByTestId("workflow-state")).toHaveTextContent("NO_VALID_PREVIEW");
    validation.unmount();
    mocks.preview.mockRejectedValueOnce(new DOMException("aborted", "AbortError"));
    render(<WorkflowProbe revision={0} />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByTestId("workflow-state")).toHaveTextContent("PREVIEW_PENDING");
  });

  it("uses latest-response-wins after superseding a pending request", async () => {
    let settle: ((value: ReturnType<typeof multiMemberTeePreview>) => void) | undefined;
    mocks.preview.mockImplementationOnce(() => new Promise((resolve) => { settle = resolve; }));
    const view = render(<WorkflowProbe revision={0} />);
    await act(async () => { await vi.runAllTimersAsync(); });
    mocks.preview.mockResolvedValueOnce(multiMemberTeePreview());
    view.rerender(<WorkflowProbe revision={1} />);
    await act(async () => { settle?.(multiMemberTeePreview()); await vi.runAllTimersAsync(); });
    expect(screen.getByTestId("workflow-state")).toHaveTextContent("CURRENT_VALID");
  });
});

describe("Multi-Member Tee unified workspace", () => {
  beforeEach(() => { vi.useRealTimers(); mocks.preview.mockReset(); mocks.design.mockReset(); mocks.preview.mockResolvedValue(multiMemberTeePreview()); mocks.design.mockResolvedValue(multiMemberTeeDesign()); });

  it("adds a separate selector option while leaving frozen choices unchanged", () => {
    render(<ShearConnectionsWorkspace />);
    const selector = screen.getByLabelText("Connection type");
    expect(within(selector).getByRole("option", { name: "Brace/beam connection — Tee connector" })).toBeInTheDocument();
    fireEvent.change(selector, { target: { value: "MULTI_MEMBER_TEE" } });
    expect(screen.getByRole("heading", { name: /Upper: Angle · Middle: Wide-flange \/ I · Lower: Angle → W Column Flange/u })).toBeInTheDocument();
  });

  it("routes every accepted selector family and clears the prior workspace on each switch", async () => {
    render(<ShearConnectionsWorkspace />);
    const selector = screen.getByLabelText("Connection type");
    const routes = [
      ["FRP_TEE", "Frozen single-member Tee workspace"],
      ["MULTI_MEMBER_TEE", "Multi-member Tee connector"],
      ["FRP_TEE", "Frozen single-member Tee workspace"],
      ["SINGLE_CLIP_ANGLE", "Accepted Single Clip-Angle workspace"],
      ["SYMMETRIC_PAIRED_CLIP_ANGLES", "Accepted Paired Clip-Angle workspace"],
      ["DIRECT_REFERENCE", "Frozen Direct workspace"],
    ] as const;
    for (const [value, visibleText] of routes) {
      fireEvent.change(selector, { target: { value } });
      if (value === "MULTI_MEMBER_TEE") {
        expect(await screen.findByRole("heading", { name: /Upper: Angle/u })).toBeInTheDocument();
      } else {
        expect(await screen.findByText(visibleText)).toBeInTheDocument();
      }
    }
    expect(screen.queryByRole("heading", { name: /Upper: Angle/u })).not.toBeInTheDocument();
  });

  it("mounts complete controls and a stable viewer shell before the first preview resolves", () => {
    mocks.preview.mockReturnValue(new Promise(() => undefined));
    const { container } = render(<MultiMemberTeeWorkspace />);
    expect(screen.getByRole("heading", { name: /Upper: Angle · Middle: Wide-flange \/ I · Lower: Angle → W Column Flange/u })).toBeInTheDocument();
    expect(screen.getByLabelText("Enable Upper Member")).toBeChecked();
    expect(screen.getByLabelText("Enable Middle Member (horizontal)")).toBeChecked();
    expect(screen.getByLabelText("Enable Lower Member")).toBeChecked();
    expect(screen.getByRole("heading", { name: "Canonical Multi-Member Tee model unavailable" })).toBeInTheDocument();
    expect(container.querySelector(".persistent-connection-viewer")).not.toBeNull();
  });

  it("exposes six profiles in every slot and seven shared support targets without stale fields", async () => {
    render(<MultiMemberTeeWorkspace />);
    const expectedProfiles = [
      "FLAT_PLATE", "ANGLE", "CHANNEL", "WIDE_FLANGE_I",
      "RECTANGULAR_HOLLOW_SECTION", "SOLID_RECTANGULAR_SECTION",
    ];
    for (const label of [
      "Upper Member profile family",
      "Middle Member (horizontal) profile family",
      "Lower Member profile family",
    ]) {
      expect(within(screen.getByLabelText(label)).getAllByRole("option").map((item) => item.getAttribute("value"))).toEqual(expectedProfiles);
    }
    expect(within(screen.getByLabelText("Supporting member")).getAllByRole("option")).toHaveLength(7);
    expect(within(screen.getByLabelText("Supporting member")).queryByRole("option", { name: /Beam Web/u })).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Upper Member profile family"), { target: { value: "FLAT_PLATE" } });
    await waitFor(() => {
      expect(latestPreviewRequest().upper_brace).toMatchObject({
        inclination_degrees: "30",
        anchor_v: { value: "10" },
        profile: { profile_family: "FLAT_PLATE", dimensions: { width: { value: "6" }, thickness: { value: "0.5" } } },
      });
      const slot = latestPreviewRequest().upper_brace as { profile: { dimensions: Record<string, unknown> } };
      expect(slot.profile.dimensions).not.toHaveProperty("leg_y");
      expect(slot.profile.dimensions).not.toHaveProperty("web_thickness");
    });
    fireEvent.change(screen.getByLabelText("Middle Member (horizontal) profile family"), { target: { value: "FLAT_PLATE" } });
    await waitFor(() => { expect(latestPreviewRequest().middle_beam).toMatchObject({ inclination_degrees: "0", profile: { profile_family: "FLAT_PLATE" } }); });
    fireEvent.change(screen.getByLabelText("Middle Member (horizontal) profile family"), { target: { value: "ANGLE" } });
    await waitFor(() => {
      expect(latestPreviewRequest().middle_beam).toMatchObject({ inclination_degrees: "0", profile: { profile_family: "ANGLE" } });
      expect(screen.getByRole("heading", { name: /Upper: Flat plate · Middle: Angle · Lower: Angle → W Column Flange/u })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Supporting member"), { target: { value: "RECTANGULAR_HOLLOW_COLUMN_WALL" } });
    await waitFor(() => {
      expect(latestPreviewRequest()).toMatchObject({ support_target_id: "RECTANGULAR_HOLLOW_COLUMN_WALL", support_profile: { profile_family: "RECTANGULAR_HOLLOW_SECTION", wall_thickness: { value: "0.5" } } });
    });
    fireEvent.change(screen.getByLabelText("Supporting member"), { target: { value: "SOLID_RECTANGULAR_COLUMN_FACE" } });
    await waitFor(() => {
      const request = latestPreviewRequest();
      if (request.orchestration_contract_version !== "3.4B-RC1") throw new Error("expanded fixture invariant");
      expect(request.support_profile).toMatchObject({ profile_family: "SOLID_RECTANGULAR_SECTION" });
      expect(request.support_profile).not.toHaveProperty("wall_thickness");
      expect(screen.getByRole("heading", { name: /→ Solid Rectangular Column Face/u })).toBeInTheDocument();
    });
  });

  it.each([
    ["backend-invalid geometry", multiMemberTeePreview("INVALID_GEOMETRY")],
    ["request failure", new EvaluationTransportError("NETWORK", null, "node preview offline")],
    ["unknown response contract", new EvaluationTransportError("RESPONSE", 200, "unsupported node preview contract")],
  ] as const)("keeps the application mounted for %s", async (_case, outcome) => {
    if (outcome instanceof Error) mocks.preview.mockRejectedValue(outcome);
    else mocks.preview.mockResolvedValue(outcome);
    await withoutWindowErrors(async () => {
      render(<MultiMemberTeeWorkspace />);
      await waitFor(() => { expect(screen.getAllByText(outcome instanceof Error ? outcome.message : "CONNECTED_MEMBER_POSITIVE_VOLUME_INTERFERENCE").length).toBeGreaterThan(0); });
      expect(screen.getByRole("heading", { name: /Upper: Angle/u })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Canonical Multi-Member Tee model unavailable" })).toBeInTheDocument();
    });
  });

  it.each(SLOT_CASES)("renders the %s active-slot topology without hidden payloads", async (_case, slots) => {
    mocks.preview.mockImplementation((request: MultiMemberTeeRequest) => Promise.resolve(multiMemberTeePreview("NOT_EVALUATED", activeSlotIds(request))));
    await withoutWindowErrors(async () => {
      render(<MultiMemberTeeWorkspace />);
      const active = new Set<MultiMemberTeeSlotId>(slots);
      const disabled = (["UPPER_BRACE", "MIDDLE_BEAM", "LOWER_BRACE"] as const).filter((slot) => !active.has(slot));
      const labels: Readonly<Record<MultiMemberTeeSlotId, string>> = {
        UPPER_BRACE: "Upper Member",
        MIDDLE_BEAM: "Middle Member (horizontal)",
        LOWER_BRACE: "Lower Member",
      };
      for (const slot of disabled) fireEvent.click(screen.getByLabelText(`Enable ${labels[slot]}`));
      await waitFor(() => { expect(activeSlotIds(latestPreviewRequest())).toEqual([...slots]); });
      await waitFor(() => { expect(screen.getByTestId("node-viewer")).toHaveAttribute("data-bolt-groups", String(slots.length + 1)); });
      expect(latestPreviewRequest().upper_brace === undefined).toBe(!active.has("UPPER_BRACE"));
      expect(latestPreviewRequest().middle_beam === undefined).toBe(!active.has("MIDDLE_BEAM"));
      expect(latestPreviewRequest().lower_brace === undefined).toBe(!active.has("LOWER_BRACE"));
      if (disabled.length > 0) expect(screen.getAllByText(/No hidden request, geometry, bolt group, action, result, or fingerprint/u).length).toBeGreaterThan(0);
    });
  });

  it("keeps the persistent viewer container mounted when the current preview arrives", async () => {
    let settle: ((value: ReturnType<typeof multiMemberTeePreview>) => void) | undefined;
    mocks.preview.mockImplementationOnce(() => new Promise((resolve) => { settle = resolve; }));
    const { container } = render(<MultiMemberTeeWorkspace />);
    const shell = container.querySelector(".persistent-connection-viewer");
    expect(shell).not.toBeNull();
    await waitFor(() => { expect(settle).toBeTypeOf("function"); });
    act(() => { settle?.(multiMemberTeePreview()); });
    await waitFor(() => { expect(screen.getByTestId("node-viewer")).toBeInTheDocument(); });
    expect(container.querySelector(".persistent-connection-viewer")).toBe(shell);
  });

  it("shows actual current scene/equilibrium, omits disabled slots, edits groups and marks design stale", async () => {
    render(<MultiMemberTeeWorkspace />);
    await waitFor(() => { expect(screen.getByTestId("node-viewer")).toHaveAttribute("data-bolt-groups", "4"); });
    expect(screen.getByText("12.9282032302755088, 0, 0 kip")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(mocks.design).toHaveBeenCalledTimes(1); });
    expect(screen.getAllByText(/Not evaluated/u).length).toBeGreaterThan(0);
    const middle = screen.getByLabelText("Enable Middle Member (horizontal)");
    fireEvent.click(middle);
    await waitFor(() => { expect(latestPreviewRequest().middle_beam).toBeUndefined(); });
    expect(screen.getByText(/No hidden request, geometry, bolt group, action, result, or fingerprint/u)).toBeInTheDocument();
    expect(screen.getByText(/Design results are stale/u)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Upper Member bolt group rows"), { target: { value: "3" } });
    await waitFor(() => { expect(latestPreviewRequest().upper_brace?.bolt_group.row_count).toBe(3); });
  });

  it("supports SI loading, independent trim/action edits, selection and backend invalid feedback", async () => {
    mocks.preview.mockResolvedValueOnce(multiMemberTeePreview()).mockResolvedValue(multiMemberTeePreview("INVALID_GEOMETRY"));
    render(<MultiMemberTeeWorkspace />);
    await waitFor(() => { expect(screen.getByTestId("node-viewer")).toBeInTheDocument(); });
    fireEvent.click(screen.getByRole("button", { name: "Pick lower member" }));
    expect(screen.getByTestId("node-viewer")).toHaveAttribute("data-selection", "MEMBER:multi-member-tee:lower_brace");
    fireEvent.click(screen.getByLabelText("Upper Member trim"));
    fireEvent.change(screen.getByLabelText("Upper Member trim clearance"), { target: { value: "0.25" } });
    fireEvent.click(screen.getByLabelText("Upper Member trim"));
    fireEvent.change(screen.getByLabelText("Upper Member force_hvn x"), { target: { value: "5" } });
    await waitFor(() => { expect(screen.getAllByText(/CONNECTED_MEMBER_POSITIVE_VOLUME_INTERFERENCE/u).length).toBeGreaterThan(0); });
    expect(screen.getByTestId("node-viewer")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load expanded SI" }));
    await waitFor(() => { expect(latestPreviewRequest().unit_system).toBe("SI"); });
  });

  it("binds every shared geometry/group/member control to the one engineering request", async () => {
    render(<MultiMemberTeeWorkspace />);
    await waitFor(() => { expect(screen.getByTestId("node-viewer")).toBeInTheDocument(); });
    const edit = (label: string, value: string) => { fireEvent.change(screen.getByLabelText(label), { target: { value } }); };
    edit("Upper Member anchor H", "4");
    edit("Upper Member anchor V", "11");
    edit("Upper Member Member / view length", "14");
    edit("Upper Member inclination", "45");
    fireEvent.change(screen.getByLabelText("Upper Member profile roll"), { target: { value: "ROTATION_90" } });
    fireEvent.change(screen.getByLabelText("Upper Member contact face"), { target: { value: "LEG_Z_OUTER" } });
    edit("Upper Member bolt group bolts per row", "3");
    edit("Upper Member bolt group pitch", "2.5");
    edit("Upper Member bolt group gauge", "2.25");
    fireEvent.change(screen.getByLabelText("Middle Member (horizontal) profile roll"), { target: { value: "ROTATION_180" } });
    fireEvent.change(screen.getByLabelText("Middle Member (horizontal) contact face"), { target: { value: "WEB_NEG_FACE" } });
    edit("Tee Flange to Support rows", "3");
    edit("Tee Flange to Support bolts per row", "3");
    edit("Tee Flange to Support pitch", "2.75");
    edit("Tee Flange to Support gauge", "2.5");
    edit("Bolt diameter", "0.625");
    edit("Support member / view length", "42");
    edit("Tee Connector Length", "32");
    fireEvent.click(screen.getByText("Supporting Member", { selector: "summary span" }));
    fireEvent.click(screen.getByText("Connector", { selector: "summary span" }));
    fireEvent.click(screen.getByText("Upper Member", { selector: "summary span" }));
    await waitFor(() => {
      const latest = latestPreviewRequest();
      expect(latest.upper_brace).toMatchObject({ inclination_degrees: "45", profile_roll_degrees: "90", profile: { selected_profile_surface: "LEG_Z_OUTER" } });
      expect(latest.middle_beam).toMatchObject({ profile: { selected_profile_surface: "WEB_NEG_FACE" } });
      expect(latest.support_group).toMatchObject({ row_count: 3, bolts_per_row: 3 });
      expect(latest.bolt_diameter.value).toBe("0.625");
      expect(latest).toMatchObject({ support_profile: { member_length: { value: "42" } } });
      expect(latest.connector_dimensions.connector_length.value).toBe("32");
    });
    fireEvent.click(screen.getByLabelText("Enable Upper Member"));
    await waitFor(() => { expect(latestPreviewRequest().upper_brace).toBeUndefined(); });
    fireEvent.click(screen.getByText("Upper Member", { selector: "summary span" }));
    fireEvent.click(screen.getByLabelText("Enable Upper Member"));
    await waitFor(() => { expect(latestPreviewRequest().upper_brace).toBeDefined(); });
    fireEvent.click(screen.getByLabelText("Enable Lower Member"));
    await waitFor(() => { expect(latestPreviewRequest().lower_brace).toBeUndefined(); });
    fireEvent.click(screen.getByLabelText("Enable Lower Member"));
    await waitFor(() => { expect(latestPreviewRequest().lower_brace).toBeDefined(); });
  });

  it("surfaces explicit design transport failure without changing the current preview", async () => {
    mocks.design.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "design offline"));
    render(<MultiMemberTeeWorkspace />);
    await waitFor(() => { expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled(); });
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(screen.getByRole("alert")).toHaveTextContent("design offline"); });
    expect(screen.getByTestId("node-viewer")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load expanded U.S." }));
    await waitFor(() => { expect(latestPreviewRequest().unit_system).toBe("US_CUSTOMARY"); });
    mocks.design.mockRejectedValueOnce(new Error("unexpected"));
    await waitFor(() => { expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled(); });
    fireEvent.click(screen.getByRole("button", { name: "Run Design Check" }));
    await waitFor(() => { expect(screen.getByRole("alert")).toHaveTextContent("Design check failed."); });
  });
});
