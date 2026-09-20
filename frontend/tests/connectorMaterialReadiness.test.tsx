import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ConnectorMaterialReadiness } from "../src/features/ConnectorMaterialReadiness";
import { parseMaterialReadiness } from "../src/api/connectorMaterialReadiness";

const family = { route_id: "direct", product_id: "DIRECT_REFERENCE", category: "SHEAR", disposition: "NO_CONNECTOR_BODY" };
const envelope = { contract: "CME-1-RC1", resistance_evaluated: false, result: { SS316: "STAINLESS_CONDITIONAL_PROVIDER_AVAILABLE", families: [family] } };
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("loads conditional coverage without changing any design or material", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(envelope)));
  vi.stubGlobal("fetch", fetcher);
  render(<ConnectorMaterialReadiness />);
  expect(fetcher).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("Connector Material Readiness"));
  expect(screen.getByText(/Structural members: FRP only/)).toBeVisible();
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Read current family coverage" }));
  expect(screen.getByRole("button", { name: "Loading readiness…" })).toBeDisabled();
  expect(await screen.findByText("NO_CONNECTOR_BODY")).toBeVisible();
  expect(fetcher.mock.calls).toEqual([["/api/v1/connector-materials/capabilities"]]);
});

it.each(["http", "network", "json", "contract"])("reports %s failure and allows safe retry", async kind => {
  const fetcher = vi.fn();
  if (kind === "network") fetcher.mockRejectedValueOnce(new Error("offline"));
  else fetcher.mockResolvedValueOnce(new Response(kind === "json" ? "{" : JSON.stringify({}), { status: kind === "http" ? 503 : 200 }));
  fetcher.mockResolvedValueOnce(new Response(JSON.stringify(envelope)));
  vi.stubGlobal("fetch", fetcher);
  render(<ConnectorMaterialReadiness />);
  fireEvent.click(screen.getByText("Connector Material Readiness"));
  fireEvent.click(screen.getByRole("button"));
  expect(await screen.findByRole("alert")).toHaveTextContent("No design or material change was made");
  await waitFor(() => { expect(screen.getByRole("button")).toBeEnabled(); });
  fireEvent.click(screen.getByRole("button"));
  expect(await screen.findByText("NO_CONNECTOR_BODY")).toBeVisible();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("rejects malformed contracts or unqualified PASS claims rather than reporting readiness", () => {
  for (const value of [null, [], {}, { ...envelope, contract: "other" }, { ...envelope, resistance_evaluated: true }, { ...envelope, result: null }, { ...envelope, result: { SS316: "PASS", families: [] } }, { ...envelope, result: { SS316: "PROVIDER_NOT_IMPLEMENTED", families: null } }]) {
    expect(() => parseMaterialReadiness(value)).toThrow("Invalid readiness response");
  }
  for (const value of [null, [], {}, ...Object.keys(family).map(key => ({ ...family, [key]: 1 }))]) {
    expect(() => parseMaterialReadiness({ ...envelope, result: { ...envelope.result, families: [value] } })).toThrow("Invalid family readiness record");
  }
  expect(parseMaterialReadiness(envelope)).toEqual([family]);
});
