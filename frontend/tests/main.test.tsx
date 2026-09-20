import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { mountApplication } from "../src/app/mountApplication";

describe("application bootstrap", () => {
  it("mounts the application into the root element", async () => {
    document.body.innerHTML = '<div id="root"></div>';
    vi.resetModules();
    const { applicationRoot } = await import("../src/main");
    expect(await screen.findByRole("heading", { level: 1, name: "FRP Master Connection" })).toBeVisible();
    applicationRoot.unmount();
  });

  it("fails clearly when the root element is missing", () => {
    expect(() => {
      mountApplication(null);
    }).toThrow("FRP Master Connection application root was not found.");
  });
});
