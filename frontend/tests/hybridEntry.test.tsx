import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AppShell } from "../src/app/AppShell";
import type { TwoBoltRequest } from "../src/api/directTwoBolt";

vi.mock("../src/workspace/DirectHybridWorkspace", () => ({ DirectHybridWorkspace: ({ initialNative, onNative }: { initialNative: TwoBoltRequest; onNative: () => void }) => <section aria-label="Actual hybrid entry"><p>{initialNative.legacy.row_count} rows; {initialNative.alignment}; actual editable native inputs</p><button onClick={onNative}>Return native</button></section> }));
vi.mock("../src/visualization/EngineeringScene", () => ({ default: () => <p>Viewer test boundary</p> }));
afterEach(() => { window.history.replaceState(null, "", "/"); vi.unstubAllGlobals(); });

it("opens the common Direct workspace and routes other actual bolt arrangements through their preserved controls", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Preview unavailable in entry unit test" }), { status: 422 })));
  window.history.replaceState(null, "", "/?workspace=direct-hybrid");
  render(<AppShell />);
  expect(screen.getByRole("region", { name: "Actual hybrid entry" })).toHaveTextContent("2 rows; BRACE");
  fireEvent.click(screen.getByRole("button", { name: "Return native" }));
  fireEvent.change(await screen.findByLabelText("Row count"), { target: { value: "2" } });
  expect(screen.getByRole("region", { name: "Actual hybrid entry" })).toBeVisible();
});
