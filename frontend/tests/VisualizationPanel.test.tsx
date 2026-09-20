import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { actionLabelKey, type ProjectedActionLabel } from "../src/visualization/actionLabelContract";
import { buildDirectSideLapConcreteSceneModel } from "../src/visualization/directSideLapConcreteSceneModel";
import type { SceneDisplayMode, SceneVisibility } from "../src/visualization/EngineeringScene";
import { buildSingleBoltSceneModel } from "../src/visualization/sceneModel";
import { VisualizationPanel } from "../src/visualization/VisualizationPanel";
import { responseFixture, visualizationFixture } from "./fixtures";
import { directSideLapPreviewFixture } from "./directSideLapConcreteFixtures";

const sceneProps = vi.hoisted(() => ({
  renders: 0,
  current: null as null | {
    view: string;
    displayMode: SceneDisplayMode;
    visibility: SceneVisibility;
    resetNonce: number;
    interfaceHighlight: { readonly interfaceId: string; readonly label: string } | null;
    onCameraOrientationChange: (value: {
      x: readonly [number, number];
      y: readonly [number, number];
      z: readonly [number, number];
    }) => void;
    onActionLabelProjectionChange: (
      projections: readonly ProjectedActionLabel[],
    ) => void;
  },
}));

const noSelectionChange = () => undefined;

vi.mock("../src/visualization/EngineeringScene", () => ({
  default: (props: typeof sceneProps.current) => {
    sceneProps.renders += 1;
    sceneProps.current = props;
    return <div data-testid="scene-props" />;
  },
}));

describe("Stage 2.3R visualization controls", () => {
  beforeEach(() => {
    sceneProps.current = null;
    sceneProps.renders = 0;
  });

  it("starts solid with the governed clean overlay defaults", async () => {
    const rendered = render(<VisualizationPanel model={buildSingleBoltSceneModel(visualizationFixture())} selection={{ kind: "MEMBER", id: "member-a" }} onSelect={noSelectionChange} />);
    await screen.findByTestId("scene-props");
    expect(sceneProps.current).toMatchObject({
      view: "3D",
      displayMode: "SOLID",
      resetNonce: 0,
      visibility: {
        physicalGeometry: true,
        deferredGeometry: false,
        interfaceZones: false,
        selectedContactSurface: true,
        boltAndHoles: true,
        cornerGlobalTriad: true,
        globalAxes: false,
        memberAxes: "SELECTED",
        materialAxes: false,
        referencePoints: false,
        boltAxis: true,
        positiveDirections: false,
        appliedDirections: true,
        actionValues: true,
        zeroActions: false,
      },
    });
    expect(screen.getByLabelText("Global X Y Z orientation triad")).toBeInTheDocument();
    expect(screen.getByText("Axis / action legend")).toBeInTheDocument();
    expect(screen.getByText(/3D navigation: left-drag rotate/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Edit Member Fx applied load value" }));
    expect(screen.queryByLabelText("Edit Member Fx value")).not.toBeInTheDocument();
    const renderCount = sceneProps.renders;
    sceneProps.current?.onCameraOrientationChange({ x: [0, 1], y: [1, 0], z: [0, -1] });
    expect(sceneProps.renders).toBe(renderCount);
    expect(document.querySelector('[data-triad-line="X"]')).toHaveAttribute("x2", "42");
    expect(document.querySelector('[data-triad-line="X"]')).toHaveAttribute("y2", "67");
    fireEvent.click(screen.getByText("Overlays"));
    fireEvent.click(screen.getByLabelText("Corner global X / Y / Z triad"));
    sceneProps.current?.onCameraOrientationChange({ x: [1, 0], y: [0, 1], z: [0, 0] });
    fireEvent.click(screen.getByLabelText("Corner global X / Y / Z triad"));
    expect(document.querySelector('[data-triad-line="X"]')).toHaveAttribute("x2", "67");
    expect(document.querySelector('[data-triad-line="X"]')).toHaveAttribute("y2", "42");
    const explicitSnapshot = visualizationFixture();
    explicitSnapshot.connection_orientation = null;
    rendered.rerender(<VisualizationPanel model={buildSingleBoltSceneModel(explicitSnapshot)} selection={{ kind: "MEMBER", id: "member-a" }} onSelect={noSelectionChange} />);
    expect(screen.queryByText("Connection-orientation inspector")).not.toBeInTheDocument();
  });

  it("shows region-embedded material symbols and one accessible legend only while toggled on", async () => {
    render(
      <VisualizationPanel
        model={buildSingleBoltSceneModel(visualizationFixture())}
        selection={{ kind: "MEMBER", id: "member-a" }}
        onSelect={noSelectionChange}
      />,
    );
    await screen.findByTestId("scene-props");
    expect(screen.queryByLabelText("Material axes legend")).not.toBeInTheDocument();
    expect(document.querySelectorAll("[data-material-axis-symbol]")).toHaveLength(0);
    expect(screen.getByText(/Region-embedded material axes are hidden/)).toBeInTheDocument();
    const initialResetNonce = sceneProps.current?.resetNonce;
    const initialView = sceneProps.current?.view;

    fireEvent.click(screen.getByText("Overlays"));
    fireEvent.click(screen.getByLabelText("Material axes (LW / CW / TT)"));

    const legend = screen.getByLabelText("Material axes legend");
    expect(legend).toBeInTheDocument();
    expect(screen.getAllByLabelText("Material axes legend")).toHaveLength(1);
    expect(legend).toHaveTextContent("LW — Longitudinal");
    expect(legend).toHaveTextContent("CW — Crosswise");
    expect(legend).toHaveTextContent("TT — Through-thickness");
    expect(legend.querySelectorAll('[data-material-axis-symbol="LW"]')).toHaveLength(1);
    expect(legend.querySelectorAll('[data-material-axis-symbol="CW"]')).toHaveLength(1);
    expect(legend.querySelectorAll('[data-material-axis-symbol="TT"]')).toHaveLength(1);
    expect(legend.querySelector('[data-material-axis-symbol="LW"]')).toHaveClass("material-axis-legend-lw");
    expect(legend.querySelector('[data-material-axis-symbol="CW"]')).toHaveClass("material-axis-legend-cw");
    expect(legend.querySelector('[data-material-axis-symbol="TT"]')).toHaveClass("material-axis-legend-tt");
    expect(screen.getByText(/Region-embedded material axes are active/)).toBeInTheDocument();
    expect(sceneProps.current).toMatchObject({
      view: initialView,
      resetNonce: initialResetNonce,
      visibility: { materialAxes: true },
    });

    fireEvent.click(screen.getByLabelText("Material axes (LW / CW / TT)"));
    expect(screen.queryByLabelText("Material axes legend")).not.toBeInTheDocument();
    expect(document.querySelectorAll("[data-material-axis-symbol]")).toHaveLength(0);
    expect(sceneProps.current).toMatchObject({
      view: initialView,
      resetNonce: initialResetNonce,
      visibility: { materialAxes: false },
    });
  });

  it("keeps direct side-lap arrows and owner-qualified region axes stable through presentation controls", async () => {
    const visualization = structuredClone(directSideLapPreviewFixture().result.visualization);
    if (visualization === null) throw new Error("Direct side-lap visualization required.");
    visualization.user_force_lsn.l.value = "5";
    visualization.user_force_lsn.s.value = "-5";
    visualization.user_force_lsn.n.value = "3";
    const model = buildDirectSideLapConcreteSceneModel(visualization);
    const axesBefore = structuredClone(model.materialAxes);
    const arrowsBefore = structuredClone(model.appliedArrows);
    render(
      <VisualizationPanel
        model={model}
        selection={{ kind: "MEMBER", id: "clip-angle-connected-member" }}
        onSelect={noSelectionChange}
      />,
    );
    await screen.findByTestId("scene-props");
    expect(model.materialAxes).toHaveLength(3);
    expect(model.materialAxes.every((item) => item.presentation !== null)).toBe(true);

    fireEvent.click(screen.getByText("Overlays"));
    fireEvent.click(screen.getByLabelText("Material axes (LW / CW / TT)"));
    expect(sceneProps.current?.visibility.materialAxes).toBe(true);
    expect(screen.getByLabelText("Material axes legend")).toBeVisible();
    for (const view of ["Front", "Top", "Side 1", "Side 2", "3D"]) {
      fireEvent.click(screen.getByRole("button", { name: view }));
      expect(model.materialAxes).toEqual(axesBefore);
      expect(model.appliedArrows).toEqual(arrowsBefore);
    }
    fireEvent.change(screen.getByLabelText("Geometry display"), { target: { value: "XRAY" } });
    fireEvent.click(screen.getByRole("button", { name: "Fit Connection" }));
    expect(model.materialAxes).toEqual(axesBefore);
    expect(model.appliedArrows).toEqual(arrowsBefore);
    fireEvent.click(screen.getByRole("button", { name: "Reset view" }));
    expect(sceneProps.current).toMatchObject({
      view: "3D",
      displayMode: "SOLID",
      visibility: { materialAxes: false },
    });
  });

  it("shows a display-only physical-interface focus in the viewer legend", async () => {
    render(
      <VisualizationPanel
        model={buildSingleBoltSceneModel(visualizationFixture())}
        selection={{ kind: "MEMBER", id: "member-a" }}
        onSelect={noSelectionChange}
        interfaceHighlight={{
          interfaceId: "TEE_INTERFACE_A_BRACE_TO_STEM",
          label: "Brace to Tee Stem",
        }}
      />,
    );
    await screen.findByTestId("scene-props");
    expect(sceneProps.current?.interfaceHighlight).toEqual({
      interfaceId: "TEE_INTERFACE_A_BRACE_TO_STEM",
      label: "Brace to Tee Stem",
    });
    expect(screen.getByLabelText("Selected object")).toHaveTextContent(
      "Focus: Brace to Tee Stem",
    );
  });

  it("fits, changes view/display, exposes diagnostics, and resets presentation state", async () => {
    render(<VisualizationPanel model={buildSingleBoltSceneModel(visualizationFixture())} selection={{ kind: "CONTACT", id: "patch-b" }} onSelect={noSelectionChange} />);
    await screen.findByTestId("scene-props");
    fireEvent.click(screen.getByRole("button", { name: "Front" }));
    fireEvent.change(screen.getByLabelText("Geometry display"), { target: { value: "XRAY" } });
    fireEvent.click(screen.getByRole("button", { name: "Fit Connection" }));
    expect(sceneProps.current).toMatchObject({ view: "Front", displayMode: "XRAY", resetNonce: 1 });
    fireEvent.click(screen.getByText("Overlays"));
    for (const label of ["Physical geometry", "Deferred geometry", "Interface zones", "Bolts and holes"]) {
      fireEvent.click(screen.getByLabelText(label));
    }
    fireEvent.click(screen.getByLabelText("Material axes (LW / CW / TT)"));
    expect(sceneProps.current?.visibility.materialAxes).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Reset view" }));
    expect(sceneProps.current).toMatchObject({
      view: "3D",
      displayMode: "SOLID",
      resetNonce: 2,
      visibility: { materialAxes: false, memberAxes: "SELECTED" },
    });
    expect(screen.getByLabelText("Selected object")).toHaveTextContent("W Column Flange contact face");
  });

  it("surfaces server-returned property directions and angles without hiding exact values", () => {
    const response = responseFixture();
    const result = response.results[0];
    if (result === undefined) throw new Error("Expected a result fixture.");
    result.plan.component_id = "member-a";
    result.plan.layer_id = "layer-A";
    result.plan.selected_direction_family = "LONGITUDINAL";
    result.plan.theta_degrees = "45.00000000000001";
    const bearingResult = structuredClone(result);
    bearingResult.plan.check_id = "interface-1:bolt-1:layer-A:pin_bearing";
    bearingResult.plan.limit_state = "PIN_BEARING";
    response.results.unshift(bearingResult);
    const netOnlyResult = structuredClone(result);
    netOnlyResult.plan.check_id = "interface-1:bolt-1:layer-C:net_tension";
    netOnlyResult.plan.component_id = "member-c";
    netOnlyResult.plan.layer_id = "layer-C";
    netOnlyResult.plan.theta_degrees = "30";
    response.results.push(netOnlyResult);
    response.resolved_layers = [
      {
        layer_id: "layer-A",
        participant_id: "member-a",
        physical_element_id: "LEG_1",
        material_region_id: "LEG_1",
      },
      {
        layer_id: "layer-B",
        participant_id: "member-b",
        physical_element_id: "TOP_FLANGE",
        material_region_id: "FLANGES",
      },
      {
        layer_id: "layer-C",
        participant_id: "member-c",
        physical_element_id: "LEG_1",
        material_region_id: "LEG_1",
      },
    ];
    const material = response.visualization.material_directions[0];
    const globalFrame = response.visualization.frames[0];
    if (material === undefined || globalFrame === undefined) {
      throw new Error("Expected visualization diagnostic fixtures.");
    }
    response.visualization.material_directions.push({
      ...material,
      id: "member-b:TOP_FLANGE:material",
      component_id: "member-b",
      physical_element_id: "TOP_FLANGE",
      material_region_id: "FLANGES",
    });
    response.visualization.material_directions.push({
      ...material,
      id: "member-c:LEG_1:material",
      component_id: "member-c",
    });
    response.visualization.frames.push(
      {
        ...globalFrame,
        id: "JOINT_LOCAL:benchmark-assembly",
        label: "Raw joint label",
        kind: "JOINT_LOCAL",
        owner_id: "benchmark-assembly",
      },
      {
        ...globalFrame,
        id: "CONNECTOR_LOCAL:connector-1",
        label: "Connector retained label",
        kind: "CONNECTOR_LOCAL",
        owner_id: "connector-1",
      },
    );
    const orientation = response.visualization.connection_orientation;
    if (orientation === null) throw new Error("Orientation fixture required.");
    orientation.connection_side = "WEB_SIDE";
    orientation.outstanding_leg_side = "NEGATIVE_INTERFACE_Z";
    orientation.geometry_valid = false;

    render(
      <VisualizationPanel
        model={buildSingleBoltSceneModel(response.visualization)}
        results={response.results}
        resolvedLayers={response.resolved_layers}
        selection={{ kind: "BOLT", id: "bolt-1" }}
        onSelect={noSelectionChange}
      />,
    );
    fireEvent.click(screen.getByText("Material-direction inspector"));
    expect(screen.getAllByText("Angle Connected Leg").length).toBeGreaterThan(0);
    expect(screen.getByText("Bearing property direction: Longitudinal")).toBeInTheDocument();
    expect(screen.getAllByText("Net-tension property direction: Longitudinal")).toHaveLength(2);
    expect(screen.getByText("Force/material angle: 45.0°")).toBeInTheDocument();
    expect(screen.getByText(/raw angle 45\.00000000000001°/)).toBeInTheDocument();
    expect(screen.getAllByText("W Column Flange").length).toBeGreaterThan(0);
    expect(screen.getByText("Joint local")).toBeInTheDocument();
    expect(screen.getByText("Connector retained label")).toBeInTheDocument();
    expect(screen.getByText("Interior / web-side face")).toBeInTheDocument();
    expect(screen.getByText("− interface side")).toBeInTheDocument();
    expect(screen.getByText(/Invalid geometry/)).toBeInTheDocument();
    expect(screen.getByLabelText("Selected object")).toHaveTextContent("Bolt 1");
  });

  it("shows signed applied quantities and edits them accessibly without leaking pointer events", () => {
    const onChange = vi.fn();
    const values = {
      FX: "-0.7",
      FY: "0",
      FZ: "0.2",
      MX: "0",
      MY: "0",
      MZ: "1",
    } as const;
    const outsidePointer = vi.fn();
    document.addEventListener("pointerdown", outsidePointer);
    render(
      <VisualizationPanel
        model={buildSingleBoltSceneModel(visualizationFixture())}
        selection={{ kind: "MEMBER", id: "member-a" }}
        onSelect={noSelectionChange}
        appliedActionInputValues={values}
        onAppliedActionValueChange={onChange}
        actionSourceLabel="Member"
      />,
    );

    const forceButton = screen.getByRole("button", { name: "Edit Member Fx applied load value" });
    const momentButton = screen.getByRole("button", { name: "Edit Member Mz applied load value" });
    expect(screen.getByLabelText("Projected action labels")).toBeInTheDocument();
    expect(document.querySelector(".applied-action-labels")).not.toBeInTheDocument();
    expect(forceButton).toHaveAttribute("data-action-label-placement", "projected");
    expect(forceButton).toHaveAttribute("data-action-kind", "LINEAR");
    expect(momentButton).toHaveAttribute("data-action-kind", "ROTATIONAL");
    expect(forceButton).toHaveTextContent("−0.70 kip");
    expect(momentButton).toHaveTextContent("+1.00 kip-in");
    expect(screen.queryByRole("button", { name: "Edit Member Fy applied load value" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /positive convention/i })).not.toBeInTheDocument();
    fireEvent.pointerDown(forceButton);
    expect(outsidePointer).not.toHaveBeenCalled();

    fireEvent.click(forceButton);
    const forceEditor = screen.getByLabelText("Edit Member Fx value");
    fireEvent.change(forceEditor, { target: { value: "-1.200" } });
    fireEvent.keyDown(forceEditor, { key: "Enter" });
    fireEvent.keyDown(forceEditor, { key: "Enter" });
    fireEvent.blur(forceEditor);
    expect(onChange).toHaveBeenLastCalledWith("FX", "-1.200");

    fireEvent.click(screen.getByRole("button", { name: "Edit Member Mz applied load value" }));
    const momentEditor = screen.getByLabelText("Edit Member Mz value");
    fireEvent.change(momentEditor, { target: { value: "-0.5" } });
    fireEvent.blur(momentEditor);
    expect(onChange).toHaveBeenLastCalledWith("MZ", "-0.5");

    fireEvent.click(screen.getByRole("button", { name: "Edit Member Fz applied load value" }));
    const invalidEditor = screen.getByLabelText("Edit Member Fz value");
    fireEvent.change(invalidEditor, { target: { value: "-" } });
    fireEvent.blur(invalidEditor);
    expect(onChange).toHaveBeenCalledTimes(2);

    fireEvent.click(screen.getByRole("button", { name: "Edit Member Fz applied load value" }));
    const blankEditor = screen.getByLabelText("Edit Member Fz value");
    fireEvent.change(blankEditor, { target: { value: " " } });
    fireEvent.blur(blankEditor);
    expect(onChange).toHaveBeenCalledTimes(2);

    fireEvent.click(screen.getByText("Overlays"));
    fireEvent.click(screen.getByLabelText("Show zero actions"));
    expect(screen.getByRole("button", { name: "Edit Member Fy applied load value" })).toHaveTextContent(
      "+0.00 kip",
    );
    fireEvent.click(screen.getByLabelText("Action values"));
    expect(screen.queryByRole("button", { name: /applied load value/ })).not.toBeInTheDocument();
    document.removeEventListener("pointerdown", outsidePointer);
  });

  it("projects all six applied labels, tracks camera commands, and keeps source identity", async () => {
    const snapshot = visualizationFixture();
    const values = {
      FX: "0.7",
      FY: "-0.25",
      FZ: "1.2",
      MX: "0.5",
      MY: "-0.25",
      MZ: "1",
    } as const;
    for (const arrow of snapshot.applied_action_directions) {
      arrow.signed_value = values[arrow.component];
      arrow.is_zero = false;
      arrow.sense = values[arrow.component].startsWith("-") ? "NEGATIVE" : "POSITIVE";
    }
    const model = buildSingleBoltSceneModel(snapshot);
    render(
      <VisualizationPanel
        model={model}
        selection={{ kind: "MEMBER", id: "member-a" }}
        onSelect={noSelectionChange}
        appliedActionInputValues={values}
        onAppliedActionValueChange={vi.fn()}
        actionSourceLabel="Bolt 1"
      />,
    );
    await screen.findByTestId("scene-props");

    const components = ["FX", "FY", "FZ", "MX", "MY", "MZ"] as const;
    const projections = components.map((component, index): ProjectedActionLabel => ({
      key: actionLabelKey(
        "APPLIED",
        component,
        model.appliedArrows.find((arrow) => arrow.component === component)?.id,
      ),
      component,
      kind: component.startsWith("F") ? "LINEAR" : "ROTATIONAL",
      source: "APPLIED",
      x: 100 + index * 20,
      y: 200 + index * 10,
      visible: true,
    }));
    const fxProjection = projections[0];
    if (fxProjection === undefined) throw new Error("Fx projection fixture is required.");
    sceneProps.current?.onActionLabelProjectionChange(projections);

    for (const [index, component] of components.entries()) {
      const friendly = `${component.slice(0, 1)}${component.slice(1).toLowerCase()}`;
      const label = screen.getByRole("button", {
        name: `Edit Bolt 1 ${friendly} applied load value`,
      });
      expect(label).toHaveAttribute("data-action-component", component);
      expect(label).toHaveAttribute("data-action-source", "Bolt 1");
      expect(label).toHaveStyle({
        left: `${String(100 + index * 20)}px`,
        top: `${String(200 + index * 10)}px`,
        visibility: "visible",
      });
    }
    expect(screen.getByRole("button", { name: "Edit Bolt 1 Fx applied load value" })).toHaveTextContent(
      "Bolt 1 Fx =+0.70 kip",
    );
    expect(screen.getByRole("button", { name: "Edit Bolt 1 Fy applied load value" })).toHaveTextContent(
      "Bolt 1 Fy =−0.25 kip",
    );
    expect(screen.getByRole("button", { name: "Edit Bolt 1 Mx applied load value" })).toHaveTextContent(
      "Bolt 1 Mx =+0.50 kip-in",
    );

    sceneProps.current?.onActionLabelProjectionChange([
      { ...fxProjection, x: 310, y: 155 },
    ]);
    expect(screen.getByRole("button", { name: "Edit Bolt 1 Fx applied load value" })).toHaveStyle({
      left: "310px",
      top: "155px",
    });
    expect(document.querySelector('[data-action-source="Bolt 1"][data-action-component="MZ"]')).toHaveStyle({
      visibility: "hidden",
    });

    for (const view of ["Front", "Top", "Side 1", "Side 2"]) {
      fireEvent.click(screen.getByRole("button", { name: view }));
      sceneProps.current?.onActionLabelProjectionChange([
        {
          ...fxProjection,
          x: fxProjection.x + view.length,
          y: fxProjection.y + view.length,
        },
      ]);
      expect(screen.getByRole("button", { name: "Edit Bolt 1 Fx applied load value" })).toHaveAttribute(
        "data-projected-x",
        String(fxProjection.x + view.length),
      );
    }
    fireEvent.click(screen.getByRole("button", { name: "Fit Connection" }));
    fireEvent.click(screen.getByRole("button", { name: "Reset view" }));
    sceneProps.current?.onActionLabelProjectionChange([
      { ...fxProjection, x: 222, y: 111, visible: false },
    ]);
    expect(document.querySelector('[data-action-source="Bolt 1"][data-action-component="FX"]')).toHaveStyle({
      visibility: "hidden",
    });
  });

  it("keeps convention labels nonnumeric and noneditable and couples value visibility to arrows", async () => {
    render(
      <VisualizationPanel
        model={buildSingleBoltSceneModel(visualizationFixture())}
        selection={{ kind: "MEMBER", id: "member-a" }}
        onSelect={noSelectionChange}
      />,
    );
    await screen.findByTestId("scene-props");
    fireEvent.click(screen.getByText("Overlays"));
    fireEvent.click(screen.getByLabelText("Positive sign-convention arrows"));
    for (const value of ["+Fx", "+Fy", "+Fz", "+Mx", "+My", "+Mz"]) {
      const label = screen.getByText(value);
      expect(label.tagName).toBe("SPAN");
      expect(label).toHaveAttribute("data-action-source", "POSITIVE");
      expect(label).not.toHaveTextContent(/kip|\d/u);
    }
    expect(screen.queryByRole("button", { name: "+Fx" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Applied signed force / moment arrows"));
    expect(screen.queryByRole("button", { name: /applied load value/u })).not.toBeInTheDocument();
    expect(sceneProps.current?.visibility.appliedDirections).toBe(false);
    expect(screen.getByText("+Fx")).toBeVisible();
  });

  it("shows a defensive dash for a backend per-bolt vector without a numeric value", async () => {
    const base = buildSingleBoltSceneModel(visualizationFixture());
    const source = base.appliedArrows[0];
    if (source === undefined) throw new Error("Applied arrow fixture is required.");
    const model = {
      ...base,
      perBoltDemandArrows: [{
        ...source,
        id: "automatic-demand:B_R1_L1",
        signedValue: null,
        unit: "kip",
        referencePointId: "B_R1_L1",
      }],
    };
    render(
      <VisualizationPanel
        model={model}
        selection={{ kind: "BOLT", id: "B_R1_L1" }}
        onSelect={noSelectionChange}
      />,
    );
    await screen.findByTestId("scene-props");
    fireEvent.click(screen.getByText("Overlays"));
    fireEvent.click(screen.getByLabelText("Per-bolt demand vectors"));
    expect(screen.getByRole("list", { name: "Per-bolt demand vector values" })).toHaveTextContent(
      /Bolt .* Row 1 .* Line 1 — kip/u,
    );
  });

  it("cancels an applied action edit with Escape", () => {
    const onChange = vi.fn();
    const rendered = render(
      <VisualizationPanel
        model={buildSingleBoltSceneModel(visualizationFixture())}
        selection={{ kind: "MEMBER", id: "member-a" }}
        onSelect={noSelectionChange}
        appliedActionInputValues={{ FX: "-0.7", FY: "0", FZ: "0.2", MX: "0", MY: "0", MZ: "1" }}
        onAppliedActionValueChange={onChange}
      />,
    );
    const forceButton = screen.getByRole("button", { name: "Edit Member Fx applied load value" });
    forceButton.focus();
    fireEvent.click(forceButton);
    const editor = screen.getByLabelText("Edit Member Fx value");
    fireEvent.change(editor, { target: { value: "2" } });
    fireEvent.keyDown(editor, { key: "ArrowRight" });
    fireEvent.keyDown(editor, { key: "Escape" });
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Edit Member Fx applied load value" })).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Edit Member Fx applied load value" }));
    rendered.rerender(
      <VisualizationPanel
        model={buildSingleBoltSceneModel(visualizationFixture())}
        selection={{ kind: "MEMBER", id: "member-a" }}
        onSelect={noSelectionChange}
        appliedActionInputValues={{ FX: "-0.7", FY: "0", FZ: "0.2", MX: "0", MY: "0", MZ: "1" }}
      />,
    );
    expect(screen.queryByLabelText("Edit Member Fx value")).not.toBeInTheDocument();

    const unitlessSnapshot = visualizationFixture();
    const forceArrow = unitlessSnapshot.applied_action_directions.find(
      (value) => value.component === "FX",
    );
    if (forceArrow === undefined) throw new Error("Force arrow fixture is required.");
    forceArrow.unit = null;
    rendered.rerender(
      <VisualizationPanel
        model={buildSingleBoltSceneModel(unitlessSnapshot)}
        selection={{ kind: "MEMBER", id: "member-a" }}
        onSelect={noSelectionChange}
        appliedActionInputValues={{ FX: "-0.7", FY: "0", FZ: "0.2", MX: "0", MY: "0", MZ: "1" }}
        onAppliedActionValueChange={onChange}
      />,
    );
    expect(
      screen.getByLabelText("Edit Member Fx value").parentElement?.querySelector("small"),
    ).toBeEmptyDOMElement();
  });

  it("renders server-returned SI force and moment units without conversion", () => {
    const snapshot = visualizationFixture();
    snapshot.unit_system = "SI";
    snapshot.force_unit = "kN";
    snapshot.moment_unit = "kN-mm";
    for (const arrow of snapshot.applied_action_directions) {
      arrow.unit = arrow.kind === "LINEAR" ? "kN" : "kN-mm";
    }
    render(
      <VisualizationPanel
        model={buildSingleBoltSceneModel(snapshot)}
        selection={{ kind: "MEMBER", id: "member-a" }}
        onSelect={noSelectionChange}
      />,
    );
    expect(screen.getByRole("button", { name: "Edit Member Fx applied load value" })).toHaveTextContent(
      "−0.70 kN",
    );
    expect(screen.getByRole("button", { name: "Edit Member Mz applied load value" })).toHaveTextContent(
      "+1.00 kN-mm",
    );
  });

  it("inspects a backend-authored multi-row bolt, its checks, and external demand", () => {
    const base = buildSingleBoltSceneModel(visualizationFixture());
    const cylinders = base.cylinders.map((value) => value.kind === "BOLT"
      ? {
          ...value,
          label: "Bolt · Row 1 · Line 1",
          ownerBoltId: "B_R1_L1",
          rowId: "ROW_1",
          boltLineId: "BOLT_LINE_1",
          penetratedLayerIds: ["layer-A", "layer-B"],
        }
      : value);
    const firstArrow = base.appliedArrows[0];
    if (firstArrow === undefined) throw new Error("Applied-arrow fixture is required.");
    const demand = {
      ...firstArrow,
      id: "CONNECTION_DEMAND",
      signedValue: null,
      unit: null,
      frameId: "BOLT_GROUP_LOCAL:bolt-group-1",
    };
    render(
      <VisualizationPanel
        model={{ ...base, cylinders, connectionDemandArrows: [demand] }}
        selection={{ kind: "BOLT", id: "B_R1_L1" }}
        onSelect={noSelectionChange}
        selectedBoltChecks={[{
          id: "PIN_BEARING:layer-A:B_R1_L1",
          label: "Pin Bearing",
          status: "Pass",
          demand: "2.5 kip",
          utilization: "0.417 (41.7%)",
        }]}
      />,
    );

    expect(screen.getByLabelText("Selected object")).toHaveTextContent("Bolt · Row 1 · Line 1");
    expect(screen.getByText("Pin Bearing")).toBeVisible();
    expect(screen.getByText(/Pass.*demand 2\.5 kip.*utilization 0\.417/u)).toBeVisible();
    fireEvent.click(screen.getByText("Reference-point and applied-action inspector"));
    expect(screen.getByText(/Externally resolved connection demand:/u)).toBeVisible();
  });

  it("retains a stable bolt identity when the selected bolt is absent from the current model", () => {
    render(
      <VisualizationPanel
        model={buildSingleBoltSceneModel(visualizationFixture())}
        selection={{ kind: "BOLT", id: "B_R9_L8" }}
        onSelect={noSelectionChange}
      />,
    );
    expect(screen.getByLabelText("Selected object")).toHaveTextContent("Bolt · Row 9 · Line 8");
    expect(screen.queryByText("Selected-bolt inspector")).not.toBeInTheDocument();
  });
});
