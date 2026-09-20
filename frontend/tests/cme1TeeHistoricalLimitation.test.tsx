import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { TeeConnectorWorkspace } from "../src/workspace/TeeConnectorWorkspace";
import { ConnectorMaterialReadiness } from "../src/features/ConnectorMaterialReadiness";
import { teePreviewFixture } from "./teeFixtures";
import historicalCurrent from "../../backend/tests/golden/cme1_tee_current_startup.json";

// Exercise the exact frozen startup request, not the separately authorized successor default.
vi.mock("../src/fixtures/connectionWorkspaceDefaults", async (importOriginal) => ({
  ...await importOriginal<typeof import("../src/fixtures/connectionWorkspaceDefaults")>(),
  loadTeeWorkspaceDefault: () => structuredClone(historicalCurrent),
}));

vi.mock("../src/visualization/VisualizationPanel", () => ({ VisualizationPanel: () => <div>Existing valid Tee scene</div> }));
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("preserves the inherited invalid Angle startup, editing, readiness and existing valid benchmark recovery", async () => {
  const requests: unknown[] = [];
  const fetcher = vi.fn((url: string, options?: RequestInit) => {
    if (url.endsWith("/capabilities")) return Promise.resolve(new Response(JSON.stringify({ contract: "CME-1-RC1", resistance_evaluated: false, result: { SS316: "STAINLESS_CONDITIONAL_PROVIDER_AVAILABLE", families: [{ route_id: "tee-connector", product_id: "FRP_TEE", category: "SHEAR", disposition: "CONNECTOR_BODY_CONDITIONAL_ACTIVATION" }] } })));
    if (typeof options?.body !== "string") throw new Error("Expected native JSON request body");
    const request = JSON.parse(options.body) as typeof historicalCurrent;
    requests.push(request);
    if (request.connected_member_profile.profile_family === "ANGLE") return Promise.resolve(new Response(JSON.stringify({ detail: { code: "CANONICAL_TEE_MAPPING_INVALID", message: "Each connected-profile bolt path must select one finite opposing broad face." } }), { status: 422 }));
    return Promise.resolve(new Response(JSON.stringify(teePreviewFixture())));
  });
  vi.stubGlobal("fetch", fetcher);
  render(<><TeeConnectorWorkspace /><ConnectorMaterialReadiness /></>);
  await waitFor(() => { expect(screen.getByRole("alert")).toHaveTextContent("Each connected-profile bolt path"); });
  expect(requests[0]).toEqual(historicalCurrent);
  expect(screen.getByRole("button", { name: "Run Design Check" })).toBeDisabled();
  const leg = screen.getByRole("textbox", { name: /^Leg Y$/ });
  expect(leg).toBeEnabled();
  fireEvent.change(leg, { target: { value: "4.1" } });
  expect(leg).toHaveValue("4.1");
  fireEvent.click(screen.getByText("Connector Material Readiness"));
  fireEvent.click(screen.getByRole("button", { name: "Read current family coverage" }));
  expect(await screen.findByText("FRP_TEE (tee-connector)")).toBeVisible();
  expect(screen.getByText(/conditional activation/)).toBeVisible();
  expect(fetcher.mock.calls.every(([url]) => !url.includes("design-check") && !url.includes("/plan"))).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Load U.S. Tee benchmark" }));
  expect(await screen.findByText("Existing valid Tee scene")).toBeVisible();
  expect(screen.getByRole("button", { name: "Run Design Check" })).toBeEnabled();
  expect(fetcher.mock.calls.every(([url]) => !url.includes("design-check"))).toBe(true);
});
