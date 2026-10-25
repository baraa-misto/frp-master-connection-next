import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { enteredCase, sourceExample } from "../src/api/hybridWorkflow";
import type { HybridInputs } from "../src/api/hybridWorkflow";
import type { TwoBoltRequest } from "../src/api/directTwoBolt";
import { DirectPhysicalInputs } from "../src/workspace/DirectPhysicalInputs";
import native from "./fixtures/hybridLiveNativeInputs.json";

function initial(): HybridInputs {
  const starter: HybridInputs = {
    contract: "HYB2-D3-P1-LIVE", workspace_id: "physical-controls", revision: 0,
    connection: "CURRENT_NATIVE", alignment: "BRACE", geometry: null,
    native_request: native as unknown as TwoBoltRequest,
    include_native_lrfd: true, asd_cases: [], lrfd_cases: [], source_profile: "UNMATCHED",
    bearing_face: "UNKNOWN", washer_od: null, native_edge_distance: null,
  };
  const value = sourceExample(starter);
  value.lrfd_cases = [enteredCase("independent")];
  return value;
}
function Controlled({ value }: { readonly value: HybridInputs }) {
  const [draft, setDraft] = useState(value);
  return <><DirectPhysicalInputs value={draft} onChange={setDraft} /><output data-testid="physical-input-record">{JSON.stringify(draft)}</output></>;
}
function current(): HybridInputs { return JSON.parse(screen.getByTestId("physical-input-record").textContent) as HybridInputs; }
function change(label: string, value: string) { fireEvent.change(screen.getByLabelText(label), { target: { value } }); }

it("starts with explicit unknown ends, root/contact and receiving actions without favorable geometry", () => {
  render(<Controlled value={initial()} />);
  expect(screen.getByLabelText("+LW receiving end")).toHaveValue("UNKNOWN");
  expect(screen.getByLabelText("−LW receiving end")).toHaveValue("UNKNOWN");
  expect(screen.getByLabelText("Actual interface gap")).toHaveValue("");
  expect(screen.getByLabelText("Clear flat receiving outstand (excluding root/fillet)")).toHaveValue("");
  expect(screen.getByLabelText("Original ASCE standard-hole unit column")).toHaveValue("US_CUSTOMARY_PRINTED");
  expect(current().physical_context?.receiving_actions).toEqual([]);
  expect(screen.getByText(/Additional receiving-member actions/).closest("details")).not.toHaveAttribute("open");
});

it("edits measured ends/contact and all additional actions, preserving null versus a declared zero", () => {
  render(<Controlled value={initial()} />);
  change("+LW receiving end", "FREE");
  change("+LW receiving end distance", "5");
  change("−LW receiving end", "CONTINUOUS");
  change("Actual interface gap", "0");
  change("Clear flat receiving outstand (excluding root/fillet)", "1.5");
  for (const axis of ["LW force", "CW force", "TT force", "LW moment", "CW moment", "TT moment"]) change("independent Additional " + axis, "0");
  expect(current().physical_context).toMatchObject({
    positive_end: { condition: "FREE", distance: { value: "5", unit: "in" } },
    negative_end: { condition: "CONTINUOUS", distance: null },
    clear_flat_outstand: { value: "1.5", unit: "in" }, interface_gap: { value: "0", unit: "in" },
  });
  change("independent Additional CW force", "1e-88");
  expect(current().physical_context?.receiving_actions[0]?.components[1]?.value).toBe("1e-88");
  change("independent Additional CW force", "");
  expect(current().physical_context?.receiving_actions[0]?.components[1]).toBeNull();
  change("Actual interface gap", ""); change("Clear flat receiving outstand (excluding root/fillet)", "");
  change("+LW receiving end distance", "");
  expect(current().physical_context?.positive_end.distance).toBeNull();
  change("+LW receiving end", "UNKNOWN");
  expect(screen.queryByLabelText("+LW receiving end distance")).not.toBeInTheDocument();
  change("Original ASCE standard-hole unit column", "");
  expect(current().physical_context?.hole_source).toBeNull();
  change("Original ASCE standard-hole unit column", "SI_PRINTED");
  expect(current().physical_context?.hole_source).toBe("SI_PRINTED");
  expect(current().geometry?.hole.value).toBe(".563");
});

it("uses SI action labels for newly entered quantities while retaining an established action unit", () => {
  const body = initial();
  if (body.geometry === null || body.physical_context === undefined) throw new Error("Physical fixture required");
  body.geometry.vertical_bolt_pitch.unit = "mm";
  body.physical_context.receiving_actions = [{ case_id: "independent", components: [{ value: "2", unit: "kip" }, null, null, null, null, null] }];
  render(<Controlled value={body} />);
  change("independent Additional LW force", "3");
  change("independent Additional CW force", "4");
  change("independent Additional LW moment", "5");
  const actions = current().physical_context?.receiving_actions[0]?.components;
  expect(actions?.[0]).toEqual({ value: "3", unit: "kip" });
  expect(actions?.[1]).toEqual({ value: "4", unit: "N" });
  expect(actions?.[3]).toEqual({ value: "5", unit: "N-mm" });
});
