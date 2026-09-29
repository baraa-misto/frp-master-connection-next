import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { expect, it } from "vitest";
import { FastenerSelector } from "../src/features/FastenerSelector";
import { loadJ1Benchmark } from "../src/fixtures/j1Benchmarks";
import { defaultFastenerSelection, type FastenerSelection } from "../src/state/mat1Session";

const preset = loadJ1Benchmark("US_CUSTOMARY").fastener_snapshot;

function ControlledSelector({ defaultSnapshot = preset, initialSelection = defaultFastenerSelection }: { readonly defaultSnapshot?: typeof preset; readonly initialSelection?: FastenerSelection }) {
  const [selection, setSelection] = useState<FastenerSelection>(initialSelection);
  return <><FastenerSelector defaultSnapshot={defaultSnapshot} selection={selection} onSelect={setSelection} />
    <output data-testid="selected-fastener">{JSON.stringify(selection)}</output></>;
}

function selected(): FastenerSelection {
  return JSON.parse(screen.getByTestId("selected-fastener").textContent) as FastenerSelection;
}

it("keeps F593 strength source pending and creates an unlocked user-defined session record", () => {
  render(<ControlledSelector />);
  expect(screen.getByText(/ASTM F593 tensile-strength source is required/)).toBeVisible();
  fireEvent.change(screen.getByLabelText("Fastener source"), { target: { value: "SESSION" } });
  expect(selected()).toMatchObject({ kind: "SESSION", snapshot: {
    locked: false, bolt_specification: "USER_DEFINED", fnt: null,
    fnt_source_classification: "SOURCE_PENDING", fnt_qualification_status: "SOURCE_PENDING",
  } });
  fireEvent.change(screen.getByLabelText(/Fnt \(/), { target: { value: "75" } });
  fireEvent.change(screen.getByLabelText("Fnt source basis"), { target: { value: "QA-only supplied value" } });
  expect(selected()).toMatchObject({ kind: "SESSION", fnt_source_basis: "QA-only supplied value", snapshot: {
    fnt: { value: "75", unit: "ksi" }, fnt_source_classification: "USER_DEFINED",
    fnt_qualification_status: "DEVELOPMENT_ONLY",
  } });
  fireEvent.change(screen.getByLabelText(/Fnt \(/), { target: { value: "" } });
  expect(selected()).toMatchObject({ kind: "SESSION", snapshot: {
    fnt: null, fnt_source_classification: "SOURCE_PENDING", fnt_qualification_status: "SOURCE_PENDING",
  } });
  fireEvent.change(screen.getByLabelText("Fastener source"), { target: { value: "DEFAULT" } });
  expect(selected()).toEqual(defaultFastenerSelection);
});

it("keeps an absent custom washer geometry explicit instead of inventing one", () => {
  render(<ControlledSelector defaultSnapshot={{ ...preset, washer_geometry: null }} />);
  fireEvent.change(screen.getByLabelText("Fastener source"), { target: { value: "SESSION" } });
  expect(selected()).toMatchObject({ kind: "SESSION", snapshot: { washer_geometry: null } });
  expect(screen.queryByLabelText(/Washer outside diameter/)).not.toBeInTheDocument();
});

it("copies known geometry without copying strength and edits all session hardware fields", () => {
  render(<ControlledSelector />);
  fireEvent.click(screen.getByRole("button", { name: "Copy default as custom" }));
  expect(selected()).toMatchObject({ kind: "SESSION", snapshot: {
    bolt_specification: preset.bolt_specification, fnt: null, locked: false,
  } });
  const edits = [
    ["Fastener name", "Project bolt"], ["Source / manufacturer", "Project lab"],
    ["Specification / grade", "QA Grade"], ["Alloy group", "QA Alloy"],
    ["Alloy(s)", "A, B"], ["Condition", "QA condition"],
    [/Diameter minimum/, "0.5"], [/Diameter maximum/, "1.25"],
    ["Nut specification", "QA nut"], ["Washer basis", "QA washer"],
    [/Washer outside diameter/, "2.0"], [/Washer thickness/, "0.2"],
    ["Installation condition", "QA installed"], ["Revision notes", "note one\nnote two"],
  ] as const;
  for (const [label, value] of edits) fireEvent.change(screen.getByLabelText(label), { target: { value } });
  fireEvent.change(screen.getByLabelText("Shear-plane threads"), { target: { value: "INCLUDED" } });
  fireEvent.click(screen.getByLabelText("Washer under head"));
  fireEvent.click(screen.getByLabelText("Washer under nut"));
  expect(selected()).toMatchObject({ kind: "SESSION", source_label: "Project lab", snapshot: {
    display_name: "Project bolt", bolt_specification: "QA Grade", alloy_group: "QA Alloy",
    alloys: ["A", "B"], condition: "QA condition", diameter_min: { value: "0.5" },
    diameter_max: { value: "1.25" }, nut_specification: "QA nut",
    washer_material_basis: "QA washer", washer_geometry: {
      outside_diameter: { value: "2.0" }, thickness: { value: "0.2" },
      under_head: !preset.washer_geometry?.under_head, under_nut: !preset.washer_geometry?.under_nut,
    }, installation_condition: "QA installed", source_notes: ["note one", "note two"],
    shear_plane_thread_statuses: [{ location_id: "SHEAR_PLANE_1", status: "INCLUDED" }],
  } });
  expect(Number(selected().revision)).toBeGreaterThan(1);
});

it("preserves an already supplied Fnt unit when editing a session record", () => {
  const current: FastenerSelection = {
    kind: "SESSION", contract: "FASTENER-OR1-RC1", revision: "4",
    source_label: "Lab", fnt_source_basis: "User evidence",
    snapshot: { ...structuredClone(preset), locked: false, id: "USER_FASTENER_UNIT", fnt: { value: "500", unit: "MPa" }, shear_plane_thread_statuses: [] },
  };
  render(<ControlledSelector initialSelection={current} />);
  expect(screen.getByLabelText("Shear-plane threads")).toHaveValue("EXCLUDED");
  fireEvent.change(screen.getByLabelText(/Fnt \(/), { target: { value: "510" } });
  expect(selected()).toMatchObject({ revision: "5", snapshot: { fnt: { value: "510", unit: "MPa" } } });
});
