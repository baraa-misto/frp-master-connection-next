import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../src/app/App";
import { EvaluationTransportError } from "../src/api/client";
import type {
  SingleBoltEvaluationRequest,
  SingleBoltEvaluationResponse,
  SingleBoltPreviewRequest,
} from "../src/api/contracts";
import { PRIMARY_DESIGN_CATEGORIES } from "../src/domain/designCategories";
import { failureResponseFixture, previewResponseFixture, responseFixture } from "./fixtures";
import { wiMomentSpliceDesignFixture, wiMomentSplicePreviewFixture } from "./wiMomentSpliceFixtures";

const mocks = vi.hoisted(() => ({ evaluate: vi.fn(), preview: vi.fn(), momentDesign: vi.fn(), momentPreview: vi.fn() }));
const HOSTED_WINDOWS_COVERAGE_UI_TIMEOUT_MS = 20_000;

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return {
    ...actual,
    evaluateSingleBolt: mocks.evaluate,
    previewSingleBolt: mocks.preview,
    evaluateWIMomentSplice: mocks.momentDesign,
    previewWIMomentSplice: mocks.momentPreview,
  };
});

vi.mock("../src/visualization/EngineeringScene", () => ({
  default: ({ view, onSelect }: {
    readonly view: string;
    readonly onSelect: (selection: { kind: "MEMBER" | "BOLT" | "CONTACT"; id: string }) => void;
  }) => (
    <div data-testid="mock-engineering-scene" data-view={view}>
      Mock Canvas
      <button type="button" onClick={() => { onSelect({ kind: "MEMBER", id: "member-b" }); }}>Select W model</button>
      <button type="button" onClick={() => { onSelect({ kind: "CONTACT", id: "patch-b" }); }}>Select contact model</button>
      <button type="button" onClick={() => { onSelect({ kind: "BOLT", id: "bolt-1" }); }}>Select bolt model</button>
    </div>
  ),
}));

function openShear() {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: /Shear Connections/ }));
}

function requiredAt<Item>(values: readonly Item[], index: number): Item {
  const value = values[index];
  if (value === undefined) throw new Error(`Missing test item ${String(index)}.`);
  return value;
}

function previewReflectingRequest(request: SingleBoltPreviewRequest) {
  const result = previewResponseFixture();
  const action = requiredAt(request.joint_assembly.member_end_actions, 0);
  const values = {
    FX: action.force.x,
    FY: action.force.y,
    FZ: action.force.z,
    MX: action.moment.x,
    MY: action.moment.y,
    MZ: action.moment.z,
  } as const;
  const visualization = result.visualization;
  if (visualization === null) throw new Error("Preview visualization fixture is required.");
  for (const arrow of visualization.applied_action_directions) {
    const value = values[arrow.component];
    const numeric = Number(value);
    arrow.signed_value = value;
    arrow.is_zero = numeric === 0;
    arrow.sense = numeric === 0 ? "ZERO" : numeric < 0 ? "NEGATIVE" : "POSITIVE";
  }
  const angle = request.geometry_template?.brace_to_column_directed_angle_deg;
  if (angle !== undefined && visualization.connection_orientation !== null) {
    visualization.connection_orientation.brace_to_column_directed_angle_degrees = angle;
    const numeric = Number(angle);
    const acute = Math.min(numeric, 180 - numeric);
    result.material_relationships = result.material_relationships.map((value) =>
      value.layer_id === "layer-B"
        ? {
            ...value,
            theta_degrees: String(acute),
            direction_family: acute <= 5 ? "LONGITUDINAL" : "TRANSVERSE",
          }
        : value,
    );
  }
  return result;
}

async function evaluateWith(response: SingleBoltEvaluationResponse = responseFixture()) {
  mocks.evaluate.mockResolvedValueOnce(response);
  const button = await currentDesignButton();
  fireEvent.click(button);
  await screen.findByRole("heading", { name: /Section 2.3.2 qualification required/i });
}

async function currentDesignButton(): Promise<HTMLButtonElement> {
  const timeEffect = screen.getByLabelText(/time-effect category/);
  if ((timeEffect as HTMLSelectElement).value === "") {
    fireEvent.change(timeEffect, { target: { value: "WIND_TORNADO_SEISMIC" } });
  }
  for (const factor of ["CM", "CT", "CCH"]) {
    const input = screen.getByLabelText(factor);
    if ((input as HTMLInputElement).value === "") {
      fireEvent.change(input, { target: { value: "1" } });
    }
  }
  const button = screen.getByRole("button", { name: "Run Design Check" });
  await waitFor(() => { expect(button).toBeEnabled(); });
  return button as HTMLButtonElement;
}

describe("Stage 2.3R application and workspace", () => {
  beforeEach(() => {
    mocks.evaluate.mockReset();
    mocks.preview.mockReset();
    mocks.momentDesign.mockReset();
    mocks.momentPreview.mockReset();
    mocks.momentPreview.mockResolvedValue(wiMomentSplicePreviewFixture());
    mocks.momentDesign.mockResolvedValue(wiMomentSpliceDesignFixture());
    mocks.preview.mockImplementation((request: SingleBoltPreviewRequest) => {
      const result = previewResponseFixture();
      if (request.explicit_resolved_demand === null) {
        result.design_check_ready = false;
        result.design_check_blocking_reasons = ["EXPLICIT_RESOLVED_BOLT_DEMAND_REQUIRED"];
      }
      return Promise.resolve(result);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders exactly the two governed categories with no default selection", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "FRP Master Connection" })).toBeVisible();
    expect(screen.getByText(/Stage 2\.6B/)).toBeVisible();
    const controls = within(screen.getByLabelText("Primary design categories")).getAllByRole("button");
    expect(controls).toHaveLength(2);
    expect(controls.every((value) => value.getAttribute("aria-pressed") === "false")).toBe(true);
    expect(screen.getByRole("heading", { name: "No primary category selected" })).toBeVisible();
    expect(screen.queryByText(/Brace Connections|Axial Connections/)).not.toBeInTheDocument();
    expect(PRIMARY_DESIGN_CATEGORIES).toHaveLength(2);
  });

  it("opens the governed W/I major-axis moment-splice workspace", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /Moment Connections/ }));
    expect(await screen.findByRole("heading", { name: "Moment connection — W/I beam moment splice" })).toBeVisible();
    expect(screen.getByRole("option", { name: "W/I Beam Moment Splice" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Stair Stringer Miter Connection" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Stair connections" })).toContainElement(screen.getByRole("option", { name: "Stair Stringer Miter Connection" }));
    expect(screen.getByLabelText("Major-axis moment M_T")).toHaveValue("100");
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled();
    expect(mocks.momentPreview).toHaveBeenCalledTimes(1);
  });

  it("opens the real Shear workspace with scope, session warning, classification, and source cards", () => {
    openShear();
    expect(screen.getByRole("heading", { name: "Connection engineering workspace" })).toBeVisible();
    expect(screen.getByText("Session only")).toBeVisible();
    expect(screen.getByText(/Session only .* not saved/)).toBeVisible();
    expect(screen.getAllByText("Shear Connections").length).toBeGreaterThan(0);
    expect(screen.queryByRole("option", { name: "Stair Stringer Miter Connection" })).toBeNull();
    for (const label of ["Brace to column flange", "One brace", "One selected bolt", "One row"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    expect(screen.getByText("Angle brace")).toBeVisible();
    expect(screen.getByText("W column")).toBeVisible();
    fireEvent.click(screen.getByText("Materials"));
    expect(screen.getByRole("heading", { name: "ICE Locked Pultruded FRP" })).toBeVisible();
    for (const property of ["Ft,L", "Ft,T", "Fbr,L", "Fbr,T", "Fsh,LT"]) {
      expect(screen.getByText(property)).toBeVisible();
    }
    expect(screen.queryByText("Fc,T")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Fastener"));
    expect(screen.getByRole("heading", { name: "316/316L stainless fastener" })).toBeVisible();
    expect(screen.getByText(/Fnt source pending/)).toBeVisible();
    expect(screen.getByRole("heading", { name: "Connection viewer" })).toBeVisible();
    expect(screen.getByText(/browser does not reconstruct calculation geometry/)).toBeVisible();
  });

  it("loads exact J1 U.S. and SI input profiles without a production expected result", () => {
    openShear();
    fireEvent.click(screen.getByRole("button", { name: "Load verified J1 — U.S." }));
    expect(screen.getByLabelText("Case label")).toHaveValue("Verified J1 — U.S.");
    expect(screen.getByLabelText("Bolt diameter")).toHaveValue("0.5");
    expect(screen.getAllByText("in").length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: /Detailed calculation results/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load verified J1 — SI" }));
    expect(screen.getByLabelText("Case label")).toHaveValue("Verified J1 — SI");
    expect(screen.getByLabelText("Unit system")).toHaveValue("SI");
    expect(screen.getByLabelText("Bolt diameter")).toHaveValue("12.7");
    expect(screen.getByLabelText("Thickness")).toHaveValue("9.525");
    expect(screen.getByLabelText("Bolt-to-brace-end distance e1")).toHaveValue("50.8");
    expect(screen.getByLabelText("Brace view length")).toHaveValue("101.6");
    fireEvent.focus(screen.getByLabelText("Thickness"));
    expect(screen.getByLabelText("Thickness")).toHaveValue("9.524999999999999");
    fireEvent.blur(screen.getByLabelText("Thickness"));
    expect(screen.getByLabelText("Thickness")).toHaveValue("9.525");
    expect(screen.getAllByText("mm").length).toBeGreaterThan(0);
  });

  it("requires explicit unit-reset confirmation after edits and never live converts strings", () => {
    openShear();
    fireEvent.change(screen.getByLabelText("Case label"), { target: { value: "Edited exact strings" } });
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true).mockReturnValueOnce(true);
    fireEvent.change(screen.getByLabelText("Unit system"), { target: { value: "SI" } });
    expect(screen.getByLabelText("Unit system")).toHaveValue("US_CUSTOMARY");
    expect(screen.getByLabelText("Case label")).toHaveValue("Edited exact strings");
    fireEvent.change(screen.getByLabelText("Unit system"), { target: { value: "SI" } });
    expect(screen.getByLabelText("Unit system")).toHaveValue("SI");
    expect(screen.getByLabelText("Case label")).toHaveValue("Verified J1 — SI");
    expect(confirm).toHaveBeenCalledTimes(2);
    fireEvent.change(screen.getByLabelText("Unit system"), { target: { value: "SI" } });
    expect(confirm).toHaveBeenCalledTimes(2);
    fireEvent.change(screen.getByLabelText("Case label"), { target: { value: "Edited SI strings" } });
    fireEvent.change(screen.getByLabelText("Unit system"), { target: { value: "US_CUSTOMARY" } });
    expect(screen.getByLabelText("Unit system")).toHaveValue("US_CUSTOMARY");
    expect(confirm).toHaveBeenCalledTimes(3);
  });

  it("exposes and updates supported angle, W, bolt, washer, thread, lap, action, demand, and factor inputs", () => {
    openShear();
    fireEvent.click(screen.getByRole("button", { name: "Load verified J1 — U.S." }));
    const textEdits: Readonly<Record<string, string>> = {
      "Leg y": "3.4",
      "Leg z": "3.1",
      Thickness: "0.38",
      d: "4.1",
      bf: "6.4",
      tw: "0.38",
      tf: "0.51",
      "Bolt diameter": "0.51",
      "Standard hole display": "0.57",
      "Washer outside diameter": "1.01",
      "Washer thickness": "0.052",
      "Column view extent below connection": "5.3",
      "Column view extent above connection": "5.4",
      "Brace-to-column angle": "60",
      "Brace view length": "4.5",
      "Bolt-to-brace-end distance e1": "2.1",
      "P / Fx": "-0.8",
      "Vy / Fy": "0.1",
      "Vz / Fz": "0.2",
      "T / Mx": "0.3",
      My: "0.4",
      Mz: "0.5",
      "In-plane Fx": "0.8",
      "In-plane Fy": "0.2",
      "Bolt-axis tension": "0.1",
      "Externally supplied prying": "0.2",
      CM: "0.9",
      CT: "0.95",
      CCH: "0.99",
    };
    for (const [label, value] of Object.entries(textEdits)) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
      expect(screen.getByLabelText(label)).toHaveValue(value);
    }
    fireEvent.change(screen.getByLabelText("Lap configuration"), { target: { value: "DOUBLE_LAP" } });
    const bearingControls = screen.getAllByLabelText(/Bearing threads/);
    fireEvent.change(requiredAt(bearingControls, 0), { target: { value: "INCLUDED" } });
    fireEvent.change(requiredAt(bearingControls, 1), { target: { value: "UNKNOWN" } });
    fireEvent.change(screen.getByLabelText("Shear-plane threads"), { target: { value: "INCLUDED" } });
    fireEvent.change(screen.getByLabelText("Layer loading sense"), { target: { value: "COMPRESSION" } });
    fireEvent.click(screen.getByText("Factors"));
    fireEvent.change(screen.getByLabelText(/time-effect category/), { target: { value: "OTHER" } });
    expect(screen.getByLabelText("Lap configuration")).toHaveValue("DOUBLE_LAP");
    expect(screen.getByLabelText("Shear-plane threads")).toHaveValue("INCLUDED");
  });

  it("shows the automatic source while preserving the one-bolt design boundary", async () => {
    openShear();
    fireEvent.click(screen.getByRole("button", { name: "Automatic from member-end force" }));
    expect(screen.getByText(/backend from the member-end force and its canonical reference point/)).toBeVisible();
    expect(screen.getByText(/Select at least two rows/)).toBeVisible();
    await waitFor(() => { expect(mocks.preview).toHaveBeenCalledTimes(2); });
    const submitted = mocks.preview.mock.calls[1]?.[0] as SingleBoltPreviewRequest | undefined;
    expect(submitted?.explicit_resolved_demand).not.toBeNull();
    expect(submitted?.geometry).toBeUndefined();
    expect(submitted?.geometry_template?.brace_to_column_directed_angle_deg).toBe("45");
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(mocks.evaluate).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Explicit resolved connection demand/ }));
    expect(screen.getByText("The connection demand is independently resolved.")).toBeVisible();
    fireEvent.click(screen.getByText("Advanced independently resolved demand"));
    expect(screen.getByText(/Use only when one-bolt demand was independently resolved/)).toBeVisible();
    expect(screen.getByLabelText("In-plane Fx")).toBeInTheDocument();
  });

  it("submits explicit orientation semantics, updates the angle layer, and marks results stale", async () => {
    openShear();
    fireEvent.click(screen.getByText("Connection Orientation / Geometry"));
    expect(screen.getByLabelText("W column flange connection face")).toHaveValue("EXTERIOR");
    expect(screen.getByLabelText("Connected angle leg")).toHaveValue("LEG_1");
    expect(screen.getByLabelText("Outstanding angle leg")).toHaveValue("POSITIVE_INTERFACE_Z");
    mocks.evaluate.mockResolvedValueOnce(responseFixture());
    fireEvent.click(await currentDesignButton());
    await screen.findByRole("heading", { name: /Section 2.3.2 qualification required/i });
    expect(screen.getByLabelText("Selected object")).toHaveTextContent("W Column Flange contact face");
    fireEvent.change(screen.getByLabelText("W column flange connection face"), {
      target: { value: "WEB_SIDE" },
    });
    expect(screen.getByText("Design results are stale — run Design Check to update.")).toBeVisible();
    fireEvent.change(screen.getByLabelText("Connected angle leg"), {
      target: { value: "LEG_2" },
    });
    expect(screen.getByLabelText("Bearing threads · Angle Connected Leg")).toBeInTheDocument();
    expect(screen.getByLabelText("Bearing threads · W Column Flange")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Outstanding angle leg"), {
      target: { value: "NEGATIVE_INTERFACE_Z" },
    });
    mocks.evaluate.mockResolvedValueOnce(responseFixture());
    fireEvent.click(await currentDesignButton());
    await waitFor(() => { expect(mocks.evaluate).toHaveBeenCalledTimes(2); });
    const submitted = mocks.evaluate.mock.calls[1]?.[0] as SingleBoltEvaluationRequest;
    expect(submitted.geometry_template).toMatchObject({
      column_flange_connection_side: "WEB_SIDE",
      angle_connected_leg: "LEG_2",
      outstanding_leg_side: "NEGATIVE_INTERFACE_Z",
    });
    expect(submitted.material_assignments.find((item) => item.participant_id === "member-a")).toMatchObject({
      physical_element_id: "LEG_2",
      material_region_id: "LEG_2",
    });
  });

  it("communicates live server-invalid interference and blocks design", async () => {
    const invalid = previewResponseFixture();
    invalid.geometry_status = "PREVIEW_INVALID_GEOMETRY";
    invalid.design_check_ready = false;
    invalid.design_check_blocking_reasons = ["INVALID_GEOMETRY"];
    invalid.geometry_issues = [{
      code: "INVALID_GEOMETRY",
      message: "Invalid geometry — Angle Brace outstanding leg intersects W Column Flange.",
      identities: ["ANGLE_W_MEMBER_INTERFERENCE", "member-a", "LEG_2", "member-b", "TOP_FLANGE"],
    }];
    const orientation = invalid.visualization?.connection_orientation;
    if (orientation === null) throw new Error("Orientation fixture is required.");
    if (orientation === undefined) throw new Error("Visualization fixture is required.");
    orientation.geometry_valid = false;
    orientation.interference_classifications = ["ANGLE_W_MEMBER_INTERFERENCE"];
    orientation.interference_participant_ids = ["member-a", "member-b"];
    orientation.interference_physical_element_ids = ["LEG_2", "TOP_FLANGE"];
    mocks.preview.mockResolvedValueOnce(invalid);
    openShear();
    expect((await screen.findAllByText("Invalid geometry")).length).toBeGreaterThan(0);
    expect(screen.getByText(/outstanding leg intersects W Column Flange/)).toBeVisible();
    expect(screen.queryByText(/^Pass$/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(mocks.evaluate).not.toHaveBeenCalled();
  });

  it("synchronizes supported model selections with the presentation sidebar", async () => {
    openShear();
    await evaluateWith();
    fireEvent.click(screen.getByRole("button", { name: "Select W model" }));
    expect(screen.getByLabelText("Selected object")).toHaveTextContent("W column");
    fireEvent.click(screen.getByRole("button", { name: "Select contact model" }));
    expect(screen.getByLabelText("Selected object")).toHaveTextContent("W Column Flange contact face");
    const members = screen.getByText("Members");
    fireEvent.click(members);
    fireEvent.click(members);
    expect(screen.getByLabelText("Selected object")).toHaveTextContent("Angle brace");
    fireEvent.click(screen.getByRole("button", { name: "Select bolt model" }));
    expect(screen.getByLabelText("Selected object")).toHaveTextContent("Bolt 1");
    const boltGroup = screen.getByText("Bolt / Interface");
    fireEvent.click(boltGroup);
    fireEvent.click(boltGroup);
    expect(screen.getByLabelText("Selected object")).toHaveTextContent("Bolt 1");
    const orientationGroup = screen.getByText("Connection Orientation / Geometry");
    fireEvent.click(orientationGroup);
    fireEvent.click(orientationGroup);
    expect(screen.getByLabelText("Selected object")).toHaveTextContent("W Column Flange contact face");
  });

  it("shows loading state then renders server-authoritative qualification, table, trace, issues, and viewer", async () => {
    openShear();
    let resolveRequest: ((value: SingleBoltEvaluationResponse) => void) | undefined;
    mocks.evaluate.mockImplementationOnce(() => new Promise((resolve) => { resolveRequest = resolve; }));
    fireEvent.click(await currentDesignButton());
    expect(screen.getByRole("button", { name: "Running design check…" })).toBeDisabled();
    resolveRequest?.(responseFixture());
    expect(await screen.findByRole("heading", { name: "Section 2.3.2 Qualification Required." })).toBeVisible();
    expect(screen.getByText(/not an ordinary whole-joint PASS/i)).toBeVisible();
    fireEvent.click(screen.getByText("Advanced / Diagnostics"));
    expect(screen.getByText("abc123")).toBeVisible();
    expect(screen.getByText("Net Section Tension")).toBeVisible();
    expect(screen.getByText("Whole-connection qualification remains required.")).toBeVisible();
    expect(screen.getAllByText("Details and exact values").length).toBeGreaterThan(0);
    expect(screen.getAllByText("0.700 (70.0%)").length).toBeGreaterThan(0);
    expect(await screen.findByTestId("mock-engineering-scene")).toHaveAttribute("data-view", "3D");
    expect(screen.getByRole("img")).toHaveAccessibleDescription(/Solid standard-shape members/);
  });

  it("supports all five camera views, reset, axes/action toggles, zero visibility, and selected/all member frames", { timeout: HOSTED_WINDOWS_COVERAGE_UI_TIMEOUT_MS }, async () => {
    openShear();
    await evaluateWith();
    const scene = await screen.findByTestId("mock-engineering-scene");
    for (const view of ["Front", "Top", "Side 1", "Side 2", "3D"]) {
      fireEvent.click(screen.getByRole("button", { name: view }));
      expect(scene).toHaveAttribute("data-view", view);
    }
    fireEvent.click(screen.getByRole("button", { name: "Fit Connection" }));
    fireEvent.click(screen.getByRole("button", { name: "Reset view" }));
    fireEvent.change(screen.getByLabelText("Geometry display"), { target: { value: "XRAY" } });
    expect(screen.getByLabelText("Geometry display")).toHaveValue("XRAY");
    fireEvent.click(screen.getByText("Overlays"));
    for (const label of [
      "Corner global X / Y / Z triad",
      "Full model-space global axes",
      "Selected contact surface",
      "Connector local axes",
      "Interface-local axes",
      "Bolt-group axes",
      "Material axes (LW / CW / TT)",
      "Reference points and START / END",
      "Bolt axis and round holes",
      "Positive sign-convention arrows",
      "Applied signed force / moment arrows",
      "Show zero actions",
    ]) {
      const toggle = screen.getByLabelText(label);
      const initiallyChecked = (toggle as HTMLInputElement).checked;
      fireEvent.click(toggle);
      expect((toggle as HTMLInputElement).checked).toBe(!initiallyChecked);
      fireEvent.click(toggle);
      expect((toggle as HTMLInputElement).checked).toBe(initiallyChecked);
    }
    fireEvent.change(screen.getByLabelText("Member local axes"), { target: { value: "ALL" } });
    expect(screen.getByLabelText("Member local axes")).toHaveValue("ALL");
    fireEvent.change(screen.getByLabelText("Member local axes"), { target: { value: "OFF" } });
  });

  it("keeps results current and makes no API call through repeated view, fit, reset, overlay, and selection stress", { timeout: HOSTED_WINDOWS_COVERAGE_UI_TIMEOUT_MS }, async () => {
    openShear();
    await evaluateWith();
    fireEvent.click(screen.getByText("Overlays"));
    const viewButtons = ["3D", "Front", "Top", "Side 1", "Side 2"].map((view) =>
      screen.getByRole("button", { name: view }),
    );
    const fitButton = screen.getByRole("button", { name: "Fit Connection" });
    const resetButton = screen.getByRole("button", { name: "Reset view" });
    const cornerTriad = screen.getByLabelText("Corner global X / Y / Z triad");
    const materialAxes = screen.getByLabelText("Material axes (LW / CW / TT)");
    const selectableModels = ["Select W model", "Select contact model", "Select bolt model"].map(
      (name) => screen.getByRole("button", { name }),
    );
    mocks.preview.mockClear();
    for (let cycle = 0; cycle < 4; cycle += 1) {
      for (const viewButton of viewButtons) fireEvent.click(viewButton);
      fireEvent.click(fitButton);
      fireEvent.click(resetButton);
      fireEvent.click(cornerTriad);
      fireEvent.click(cornerTriad);
      fireEvent.click(materialAxes);
      expect(screen.getByLabelText("Material axes legend")).toBeInTheDocument();
      fireEvent.click(materialAxes);
      expect(screen.queryByLabelText("Material axes legend")).not.toBeInTheDocument();
      for (const selectableModel of selectableModels) fireEvent.click(selectableModel);
    }
    expect(mocks.evaluate).toHaveBeenCalledTimes(1);
    expect(mocks.preview).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: /Section 2\.3\.2 qualification required/i })).toBeVisible();
    expect(screen.getByText("Selected: Bolt 1")).toBeVisible();
    expect(screen.queryByText("Inputs changed — reevaluate.")).not.toBeInTheDocument();
  });

  it("presents frame, material, reference, START/END, negative direction, zero, and source data outside WebGL", async () => {
    openShear();
    await evaluateWith();
    expect(screen.getByText("Frame inspector")).toBeInTheDocument();
    expect(screen.getByText("Material-direction inspector")).toBeInTheDocument();
    expect(screen.getByText("Reference-point and applied-action inspector")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Frame inspector"));
    expect(screen.getAllByText("Right-handed orthonormal").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText("Material-direction inspector"));
    expect(screen.getByText(/LW\(/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Reference-point and applied-action inspector"));
    expect(screen.getByText("Angle brace START · connected end")).toBeInTheDocument();
    expect(screen.getByText("Angle brace END")).toBeInTheDocument();
    expect(screen.getByText(/FX: -0.7 kip/)).toBeInTheDocument();
    expect(screen.getByText(/NEGATIVE · MEMBER_LOCAL:member-a/)).toBeInTheDocument();
    expect(screen.getAllByText(/ZERO · MEMBER_LOCAL/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/8-7/).length).toBeGreaterThan(0);
  });

  it("renders explicit null action, unit, status, component, and layer values deterministically", async () => {
    const previewVariant = previewResponseFixture();
    const previewArrow = requiredAt(
      requiredAt([previewVariant.visualization], 0)?.applied_action_directions ?? [],
      0,
    );
    Object.assign(previewArrow, { signed_value: null, unit: null });
    mocks.preview.mockResolvedValueOnce(previewVariant);
    openShear();
    const variant = responseFixture();
    const firstArrow = requiredAt(variant.visualization.applied_action_directions, 0);
    Object.assign(firstArrow, { signed_value: null, unit: null });
    const firstResult = requiredAt(variant.results, 0);
    Object.assign(firstResult, { availability: null });
    Object.assign(firstResult.plan, { component_id: null, layer_id: null });
    mocks.evaluate.mockResolvedValueOnce(variant);
    fireEvent.click(await currentDesignButton());
    await screen.findByRole("heading", { name: /Section 2.3.2 qualification required/i });
    expect(screen.getAllByText("Bolt").length).toBeGreaterThan(0);
    expect(screen.getByText(/FX:/)).toBeInTheDocument();
  });

  it("retains but clearly stales design results only after engineering input changes", async () => {
    openShear();
    await evaluateWith();
    fireEvent.change(screen.getByLabelText("Bolt diameter"), { target: { value: "0.52" } });
    expect(screen.getByText("Design results are stale — run Design Check to update.")).toBeVisible();
    expect(screen.getByRole("heading", { name: /Section 2.3.2 qualification required/i })).toBeVisible();
    await evaluateWith();
    fireEvent.change(screen.getByLabelText("Case label"), { target: { value: "Changed label" } });
    expect(screen.queryByText("Design results are stale — run Design Check to update.")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Brace-to-column angle"), { target: { value: "60" } });
    expect(screen.getByText("Design results are stale — run Design Check to update.")).toBeVisible();
    expect(screen.getByRole("heading", { name: /Section 2.3.2 Qualification Required/i })).toBeVisible();
  });

  it("previews 4, 5, 8, and 12 inch view extents without staling current design", { timeout: HOSTED_WINDOWS_COVERAGE_UI_TIMEOUT_MS }, async () => {
    openShear();
    await evaluateWith();
    mocks.preview.mockClear();
    for (const length of ["5", "8", "12", "4"]) {
      fireEvent.change(screen.getByLabelText("Brace view length"), {
        target: { value: length },
      });
      await waitFor(() => { expect(mocks.preview).toHaveBeenCalledTimes(1); });
      const submitted = requiredAt(mocks.preview.mock.calls, 0)[0] as SingleBoltPreviewRequest;
      expect(submitted.view_extents?.brace_view_length.value).toBe(length);
      mocks.preview.mockClear();
      expect(screen.queryByText(/Design results are stale/)).not.toBeInTheDocument();
      expect(screen.getByRole("heading", { name: /Section 2\.3\.2 qualification required/i })).toBeVisible();
    }
    expect(mocks.evaluate).toHaveBeenCalledTimes(1);

    fireEvent.change(screen.getByLabelText("Bolt-to-brace-end distance e1"), {
      target: { value: "2.5" },
    });
    expect(screen.getByText(/Design results are stale .* run Design Check to update/)).toBeVisible();
  });

  it("accepts 120, 150, and 175 directed angles and shows separate server material relationships", { timeout: HOSTED_WINDOWS_COVERAGE_UI_TIMEOUT_MS }, async () => {
    mocks.preview.mockImplementation((request: SingleBoltPreviewRequest) =>
      Promise.resolve(previewReflectingRequest(request)),
    );
    openShear();
    await evaluateWith();
    mocks.evaluate.mockClear();
    mocks.preview.mockClear();
    for (const [geometryAngle, relationship] of [
      ["120", /60\.0° · Transverse/],
      ["150", /30\.0° · Transverse/],
      ["175", /5\.0° · Longitudinal/],
    ] as const) {
      fireEvent.change(screen.getByLabelText("Brace-to-column angle"), {
        target: { value: geometryAngle },
      });
      await waitFor(() => {
        expect(screen.getAllByText(relationship).length).toBeGreaterThan(0);
      });
      expect(screen.getAllByText(`${geometryAngle}.0° directed`)).toHaveLength(2);
      const submitted = requiredAt(
        mocks.preview.mock.calls,
        mocks.preview.mock.calls.length - 1,
      )[0] as SingleBoltPreviewRequest;
      expect(submitted.geometry_template?.brace_to_column_directed_angle_deg).toBe(geometryAngle);
    }
    expect(screen.getByText(/Design results are stale .* run Design Check to update/)).toBeVisible();
    expect(mocks.evaluate).not.toHaveBeenCalled();
  });

  it("edits applied force and moment labels through the same sidebar load state", { timeout: HOSTED_WINDOWS_COVERAGE_UI_TIMEOUT_MS }, async () => {
    mocks.preview.mockImplementation((request: SingleBoltPreviewRequest) =>
      Promise.resolve(previewReflectingRequest(request)),
    );
    openShear();
    await evaluateWith();
    mocks.preview.mockClear();
    const forceLabel = await screen.findByRole("button", {
      name: "Edit Member Fx applied load value",
    });
    fireEvent.click(forceLabel);
    const forceEditor = screen.getByLabelText("Edit Member Fx value");
    expect(forceEditor).toHaveValue("0.7");
    fireEvent.change(forceEditor, { target: { value: "-1.200" } });
    fireEvent.keyDown(forceEditor, { key: "Enter" });
    expect(screen.getByLabelText("P / Fx")).toHaveValue("-1.2");
    expect(screen.getByText(/Design results are stale .* run Design Check to update/)).toBeVisible();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Edit Member Fx applied load value" })).toHaveTextContent("−1.20 kip");
    });
    expect(mocks.evaluate).toHaveBeenCalledTimes(1);

    mocks.preview.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Edit Member Mz applied load value" }));
    const momentEditor = screen.getByLabelText("Edit Member Mz value");
    fireEvent.change(momentEditor, { target: { value: "-0.500" } });
    fireEvent.blur(momentEditor);
    expect(screen.getByLabelText("Mz")).toHaveValue("-0.5");
    await waitFor(() => { expect(mocks.preview).toHaveBeenCalledTimes(1); });
    expect(screen.getByRole("button", { name: "Edit Member Mz applied load value" })).toHaveTextContent(
      "−0.50 kip-in",
    );

    mocks.preview.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Edit Member Fx applied load value" }));
    const invalid = screen.getByLabelText("Edit Member Fx value");
    fireEvent.change(invalid, { target: { value: "-" } });
    expect(mocks.preview).not.toHaveBeenCalled();
    fireEvent.keyDown(invalid, { key: "Escape" });
    expect(screen.getByLabelText("P / Fx")).toHaveValue("-1.2");
    expect(mocks.preview).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("P / Fx"), { target: { value: "0" } });
    await waitFor(() => { expect(mocks.preview).toHaveBeenCalledTimes(1); });
    expect(screen.queryByRole("button", { name: "Edit Member Fx applied load value" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Overlays"));
    fireEvent.click(screen.getByLabelText("Show zero actions"));
    expect(screen.getByRole("button", { name: "Edit Member Fx applied load value" })).toHaveTextContent(
      "+0.00 kip",
    );
    expect(mocks.evaluate).toHaveBeenCalledTimes(1);
  });

  it("waits locally on incomplete numeric text without preview or design calls", { timeout: HOSTED_WINDOWS_COVERAGE_UI_TIMEOUT_MS }, async () => {
    openShear();
    await waitFor(() => { expect(mocks.preview).toHaveBeenCalledTimes(1); });
    mocks.preview.mockClear();
    fireEvent.change(screen.getByLabelText("Brace-to-column angle"), { target: { value: "0" } });
    expect((await screen.findAllByText("Waiting for valid input")).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(mocks.preview).not.toHaveBeenCalled();
    expect(mocks.evaluate).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Brace-to-column angle"), { target: { value: "90" } });
    fireEvent.change(screen.getByLabelText("Brace view length"), { target: { value: "0" } });
    expect(screen.getAllByText("Waiting for valid input").length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Brace view length"), { target: { value: "4" } });
    fireEvent.change(screen.getByLabelText("Brace-to-column angle"), { target: { value: "NaN" } });
    expect(screen.getAllByText("Waiting for valid input").length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Brace-to-column angle"), { target: { value: "180" } });
    expect(screen.getAllByText("Waiting for valid input").length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Brace-to-column angle"), { target: { value: "45" } });
    for (const label of [
      "Column view extent below connection",
      "Column view extent above connection",
      "Bolt-to-brace-end distance e1",
      "Standard hole display",
    ]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: "0" } });
      expect(screen.getAllByText("Waiting for valid input").length).toBeGreaterThan(0);
      fireEvent.change(screen.getByLabelText(label), { target: { value: "1" } });
    }
    fireEvent.change(screen.getByLabelText("Standard hole display"), { target: { value: "NaN" } });
    expect(screen.getAllByText("Waiting for valid input").length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Standard hole display"), { target: { value: "0.563" } });
    fireEvent.change(screen.getByLabelText("P / Fx"), { target: { value: "NaN" } });
    expect(screen.getAllByText("Waiting for valid input").length).toBeGreaterThan(0);
    expect(mocks.preview).not.toHaveBeenCalled();
    expect(mocks.evaluate).not.toHaveBeenCalled();
  });

  it("shows only server-returned material relationship data after preview", async () => {
    const missingAngle = previewResponseFixture();
    missingAngle.material_relationships = [];
    mocks.preview.mockResolvedValueOnce(missingAngle);
    openShear();
    expect((await screen.findAllByText("Server returned no resolved angle")).length).toBeGreaterThan(0);

    const angleOnly = previewResponseFixture();
    const columnMapping = angleOnly.material_relationships.find((item) => item.layer_id === "layer-B");
    if (columnMapping === undefined) throw new Error("Column material relationship fixture required.");
    columnMapping.direction_family = null as never;
    mocks.preview.mockResolvedValueOnce(angleOnly);
    fireEvent.change(screen.getByLabelText("Bolt diameter"), { target: { value: "0.51" } });
    await waitFor(() => { expect(mocks.preview).toHaveBeenCalledTimes(2); });
    expect(await screen.findByText("45.0°", { selector: "strong" })).toBeInTheDocument();
  });

  it("renders backend-returned web-side and negative-leg orientation labels", async () => {
    const webSide = previewResponseFixture();
    const orientation = webSide.visualization?.connection_orientation;
    if (orientation === null || orientation === undefined) throw new Error("Orientation fixture required.");
    orientation.connection_side = "WEB_SIDE";
    orientation.outstanding_leg_side = "NEGATIVE_INTERFACE_Z";
    mocks.preview.mockResolvedValueOnce(webSide);

    openShear();

    expect((await screen.findAllByText(/Interior \/ web-side/)).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("− interface side")).length).toBeGreaterThan(0);
  });

  it("keeps design-only validation separate from preview requests", async () => {
    openShear();
    await waitFor(() => { expect(mocks.preview).toHaveBeenCalledTimes(1); });
    mocks.preview.mockClear();
    fireEvent.change(screen.getByLabelText(/time-effect category/), { target: { value: "" } });

    expect(screen.getByRole("button", { name: "Run Design Check" })).toHaveAttribute(
      "title",
      "Select a time-effect category.",
    );
    expect(mocks.preview).not.toHaveBeenCalled();
  });

  it("renders a fail-closed design response independently from valid model status", async () => {
    const invalidDesign = responseFixture();
    invalidDesign.aggregate_status = "INVALID_GEOMETRY";
    invalidDesign.results = [];
    invalidDesign.governing_check_ids = [];
    openShear();
    mocks.evaluate.mockResolvedValueOnce(invalidDesign);

    fireEvent.click(await currentDesignButton());

    expect((await screen.findAllByText("Invalid geometry")).length).toBeGreaterThan(0);
  });

  it("shows preview failure without replacing it with a design status and supports retry", async () => {
    mocks.preview.mockRejectedValueOnce(new EvaluationTransportError("NETWORK", null, "offline"));
    openShear();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Preview unavailable");
    expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
    expect(screen.getByText("Connection viewer")).toBeVisible();
    mocks.preview.mockResolvedValueOnce(previewResponseFixture());
    fireEvent.click(screen.getByRole("button", { name: "Retry preview" }));
    await waitFor(() => { expect(screen.getAllByText("Valid geometry").length).toBeGreaterThan(0); });
    expect(mocks.evaluate).not.toHaveBeenCalled();
  });

  it("obsoletes both successful and failed in-flight design responses after an engineering edit", async () => {
    let resolveDesign: ((value: SingleBoltEvaluationResponse) => void) | undefined;
    mocks.evaluate.mockImplementationOnce(() => new Promise((resolve) => { resolveDesign = resolve; }));
    openShear();
    fireEvent.click(await currentDesignButton());
    fireEvent.change(screen.getByLabelText("Bolt diameter"), { target: { value: "0.52" } });
    resolveDesign?.(responseFixture());
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: /Section 2.3.2 qualification required/i })).not.toBeInTheDocument();
    });

    let rejectDesign: ((reason: unknown) => void) | undefined;
    mocks.evaluate.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectDesign = reject; }));
    await waitFor(() => { expect(screen.getAllByText("Valid geometry").length).toBeGreaterThan(0); });
    fireEvent.click(await currentDesignButton());
    fireEvent.change(screen.getByLabelText("Bolt diameter"), { target: { value: "0.53" } });
    rejectDesign?.(new EvaluationTransportError("HTTP", 503, "obsolete"));
    await waitFor(() => { expect(screen.queryByText("obsolete")).not.toBeInTheDocument(); });
  });

  it("treats an aborted design request as silent", async () => {
    mocks.evaluate.mockRejectedValueOnce(new DOMException("stopped", "AbortError"));
    openShear();
    fireEvent.click(await currentDesignButton());
    await waitFor(() => { expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled(); });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("distinguishes network, validation, identity, generic HTTP, response, and unexpected client errors", async () => {
    openShear();
    const cases = [
      new EvaluationTransportError("NETWORK", null, "offline"),
      new EvaluationTransportError("VALIDATION", 422, "bad input"),
      new EvaluationTransportError("IDENTITY", 403, "identity"),
      new EvaluationTransportError("HTTP", 503, "service"),
      new EvaluationTransportError("RESPONSE", 200, "contract"),
      new DOMException("socket", "NetworkError"),
      "unexpected",
    ];
    for (const error of cases) {
      mocks.evaluate.mockRejectedValueOnce(error);
    fireEvent.click(await currentDesignButton());
      const alert = await screen.findByRole("alert");
      expect(alert).toBeVisible();
    }
  });

  it("presents valid HTTP 200 numerical failure as engineering status rather than transport error", async () => {
    openShear();
    mocks.evaluate.mockResolvedValueOnce(failureResponseFixture());
    fireEvent.click(await currentDesignButton());
    expect(await screen.findByRole("heading", { name: "Known numerical failure" })).toBeVisible();
    expect(screen.getAllByText("Fail").length).toBeGreaterThan(0);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("presents engineering review and ordinary aggregate text only when the server returns them", async () => {
    openShear();
    const review = responseFixture();
    review.aggregate_status = "READY";
    review.qualification_flags = ["ENGINEERING_REVIEW_REQUIRED"];
    review.issues = [];
    mocks.evaluate.mockResolvedValueOnce(review);
    fireEvent.click(await currentDesignButton());
    expect(await screen.findByRole("heading", { name: "Engineering review required" })).toBeVisible();
    fireEvent.change(screen.getByLabelText("Bolt diameter"), { target: { value: "0.53" } });
    const ordinary = responseFixture();
    ordinary.aggregate_status = "READY";
    ordinary.qualification_flags = [];
    ordinary.issues = [];
    ordinary.calculation_fingerprint = null;
    ordinary.governing_check_ids = [];
    mocks.evaluate.mockResolvedValueOnce(ordinary);
    fireEvent.click(await currentDesignButton());
    expect(await screen.findByRole("heading", { name: "Ready" })).toBeVisible();
    fireEvent.click(screen.getByText("Advanced / Diagnostics"));
    expect(screen.getByText("Not available")).toBeVisible();
    expect(screen.getByText("None returned")).toBeVisible();
  });

  it("uses semantic keyboard-focusable controls and never writes browser persistence", async () => {
    const local = vi.spyOn(Storage.prototype, "setItem");
    openShear();
    const evaluate = await currentDesignButton();
    evaluate.focus();
    expect(evaluate).toHaveFocus();
    expect(screen.getByLabelText("Case label").tagName).toBe("INPUT");
    expect(screen.getByLabelText("Unit system").tagName).toBe("SELECT");
    expect(local).not.toHaveBeenCalled();
  });
});
