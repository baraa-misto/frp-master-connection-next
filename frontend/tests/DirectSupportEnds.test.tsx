import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DirectSupportEnds, DirectSupportViewerCue, supportEndValidation } from "../src/features/DirectSupportEnds";
import type { DirectSupportEndAuthority, DirectSupportEndInput } from "../src/api/multirowContracts";
import { directSupportPresentation } from "../src/visualization/directSupportPresentation";
import { visualizationFixture } from "./fixtures";

function Harness({ initial = { condition: "UNSPECIFIED" }, unit = "in" }: { readonly initial?: DirectSupportEndInput; readonly unit?: "in" | "mm" }) {
  const [value, setValue] = useState(initial);
  return <><DirectSupportEnds value={value} unit={unit} onChange={setValue} /><output aria-label="Signed end declaration">{JSON.stringify(value)}</output></>;
}

function authority(condition: DirectSupportEndInput["condition"]): DirectSupportEndAuthority {
  const negative = condition === "FINITE_BOTH_ENDS" || condition === "FINITE_NEGATIVE_END_ONLY";
  const positive = condition === "FINITE_BOTH_ENDS" || condition === "FINITE_POSITIVE_END_ONLY";
  return { condition, component_id: "member-a", length_unit: "in",
    negative_end_distance: negative ? { value: "4", unit: "in" } : null,
    positive_end_distance: positive ? { value: "12", unit: "in" } : null,
    negative_end_member_local_station: negative ? "-4" : null,
    positive_end_member_local_station: positive ? "12" : null,
  };
}

describe("Direct explicit W geometry input and report-only display", () => {
  it("requires an explicit project condition and reveals only selected real end fields", () => {
    render(<Harness />);
    expect(screen.getByText(/INPUT NEEDED/u)).toBeInTheDocument();
    const selector = screen.getByRole("combobox", { name: "Supporting W — longitudinal extent" });
    fireEvent.change(selector, { target: { value: "CONTINUOUS_THROUGH_CONNECTION" } });
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    fireEvent.change(selector, { target: { value: "FINITE_POSITIVE_END_ONLY" } });
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "12" } });
    expect(screen.getByRole("textbox")).toHaveAccessibleName(/above/u);
    fireEvent.change(selector, { target: { value: "FINITE_BOTH_ENDS" } });
    expect(screen.getByRole("textbox", { name: /above/u })).toHaveValue("12");
    fireEvent.change(screen.getByRole("textbox", { name: /below/u }), { target: { value: "4" } });
    fireEvent.change(selector, { target: { value: "FINITE_NEGATIVE_END_ONLY" } });
    expect(screen.getByRole("textbox")).toHaveValue("4");
    expect(screen.getByLabelText("Signed end declaration")).not.toHaveTextContent("positive_end_distance");
    fireEvent.change(selector, { target: { value: "UNSPECIFIED" } });
    expect(screen.getByText(/INPUT NEEDED/u)).toBeInTheDocument();
  });

  it("uses canonical mm for an explicitly chosen SI real end", () => {
    render(<Harness initial={{ condition: "FINITE_BOTH_ENDS" }} unit="mm" />);
    fireEvent.change(screen.getByRole("textbox", { name: /above/u }), { target: { value: "304.8" } });
    fireEvent.change(screen.getByRole("textbox", { name: /below/u }), { target: { value: "101.6" } });
    expect(screen.getByLabelText("Signed end declaration")).toHaveTextContent('"unit":"mm"');
  });

  it.each(["UNSPECIFIED", "CONTINUOUS_THROUGH_CONNECTION", "FINITE_BOTH_ENDS", "FINITE_NEGATIVE_END_ONLY", "FINITE_POSITIVE_END_ONLY"] as const)("labels the viewer end authority %s without inventing ends", (condition) => {
    render(<DirectSupportViewerCue authority={authority(condition)} />);
    const cue = screen.getByLabelText("Supporting W real ends and view cuts");
    if (condition === "UNSPECIFIED") {
      expect(cue).toHaveTextContent("needs input");
      expect(cue).not.toHaveTextContent("continues");
    } else {
      expect(cue).toHaveTextContent(condition === "FINITE_BOTH_ENDS" || condition === "FINITE_POSITIVE_END_ONLY" ? "W physical end above" : "W continues above — view cut");
      expect(cue).toHaveTextContent(condition === "FINITE_BOTH_ENDS" || condition === "FINITE_NEGATIVE_END_ONLY" ? "W physical end below" : "W continues below — view cut");
    }
  });

  it.each(["", "0", "-1", "abc", "Infinity"])("rejects invalid finite-end input %s before sending a design request", (value) => {
    expect(supportEndValidation({ condition: "FINITE_POSITIVE_END_ONLY", positive_end_distance: { value, unit: "in" } })).toContain("positive distance");
  });

  it("allows continuous and positive declared distances without inventing a missing value", () => {
    expect(supportEndValidation({ condition: "CONTINUOUS_THROUGH_CONNECTION" })).toBeNull();
    expect(supportEndValidation({ condition: "FINITE_NEGATIVE_END_ONLY", negative_end_distance: { value: "4", unit: "in" } })).toBeNull();
  });

  it.each(["CONTINUOUS_THROUGH_CONNECTION", "FINITE_BOTH_ENDS", "FINITE_NEGATIVE_END_ONLY", "FINITE_POSITIVE_END_ONLY"] as const)("renders signed %s end stations without mutating engineering input", (condition) => {
    const original = visualizationFixture();
    const copy = structuredClone(original);
    const rendered = directSupportPresentation(original, authority(condition));
    expect(original).toEqual(copy);
    expect(rendered.bolt).toEqual(original.bolt);
    const relevant = rendered.primitives.filter((p) => p.owner_id === "member-a" && p.kind === "BOX");
    expect(relevant.length).toBeGreaterThan(0);
    for (const p of relevant) {
      if (authority(condition).negative_end_member_local_station !== null) expect(p.parameters.find((v) => v.name === "x_start")?.value).toBe("-4");
      if (authority(condition).positive_end_member_local_station !== null) expect(p.parameters.find((v) => v.name === "x_end")?.value).toBe("12");
    }
  });

  it.each(["x_start", "x_end", "center", "x_axis"])("rejects missing signed box placement %s instead of inventing geometry", (field) => {
    const visual = visualizationFixture();
    const box = visual.primitives.find((p) => p.owner_id === "member-a" && p.kind === "BOX");
    if (box === undefined) throw new Error("Expected physical fixture box");
    if (field === "center" || field === "x_axis") box[field] = null;
    else box.parameters = box.parameters.filter((p) => p.name !== field);
    expect(() => directSupportPresentation(visual, authority("CONTINUOUS_THROUGH_CONNECTION"))).toThrow("signed placement");
  });
});
