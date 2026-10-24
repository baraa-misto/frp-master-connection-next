import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { expect, it, vi } from "vitest";
import type { Alignment } from "../src/api/directTwoBolt";
import { DirectBoltAlignment } from "../src/features/DirectBoltAlignment";

it.each(["BRACE", "SUPPORT"] as const)("names the native %s radio group and keeps essential shaft/method distinctions visible", (alignment) => {
  render(<DirectBoltAlignment alignment={alignment} onChange={vi.fn()} />);
  const group = screen.getByRole("group", { name: "Bolt alignment" });
  expect(within(group).getAllByRole("radio")).toHaveLength(2);
  expect(within(group).getByRole("radio", { name: alignment === "BRACE" ? "Along brace (default)" : "Along supporting member" })).toBeChecked();
  expect(group).toHaveAccessibleDescription(/Alignment joins the two bolt centers.*Bolt shafts remain normal/);
  expect(screen.getByLabelText("Help: Bolt alignment")).toBeVisible();
  expect(screen.getByText(alignment === "BRACE" ? /supported method guards/ : /Structural design is not evaluated/)).toBeVisible();
});

it("reports one controlled change in each direction and never keeps a second local alignment", () => {
  const changed = vi.fn<(alignment: Alignment) => void>();
  const view = render(<DirectBoltAlignment alignment="BRACE" onChange={changed} />);
  fireEvent.click(screen.getByRole("radio", { name: "Along supporting member" }));
  expect(changed.mock.calls).toEqual([["SUPPORT"]]);
  expect(screen.getByRole("radio", { name: "Along brace (default)" })).toBeChecked();
  view.rerender(<DirectBoltAlignment alignment="SUPPORT" onChange={changed} />);
  fireEvent.click(screen.getByRole("radio", { name: "Along brace (default)" }));
  expect(changed.mock.calls).toEqual([["SUPPORT"], ["BRACE"]]);
});

it("uses distinct native names so independent component instances do not uncheck one another", () => {
  function Independent({ initial }: { initial: Alignment }) {
    const [alignment, setAlignment] = useState(initial);
    return <DirectBoltAlignment alignment={alignment} onChange={setAlignment} />;
  }
  render(<><Independent initial="BRACE" /><Independent initial="BRACE" /></>);
  const groups = screen.getAllByRole("group", { name: "Bolt alignment" });
  const firstGroup = groups[0], secondGroup = groups[1];
  if (firstGroup === undefined || secondGroup === undefined) throw new Error("Independent groups required");
  const first = within(firstGroup).getByRole("radio", { name: "Along supporting member" });
  const second = within(secondGroup).getByRole("radio", { name: "Along brace (default)" });
  expect(first.getAttribute("name")).not.toBe(second.getAttribute("name"));
  fireEvent.click(first);
  expect(first).toBeChecked(); expect(second).toBeChecked();
});
