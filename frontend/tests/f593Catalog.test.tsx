import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { F593CatalogSummary, type F593Resolution } from "../src/features/F593CatalogSummary";
import { defaultFastenerSelection, type FastenerSelection } from "../src/state/mat1Session";
import raw from "./fixtures/f593_f4_resolution.json";

const resolution = raw as F593Resolution;
const selection = defaultFastenerSelection as Extract<FastenerSelection, {kind:"CATALOG"}>;
const diameter = {value: "0.5", unit: "in"};
afterEach(() => {vi.unstubAllGlobals();});

it("shows only the current backend row and separates min/max provenance from design", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(resolution)));
  vi.stubGlobal("fetch", fetchMock);
  const onSelect = vi.fn();
  render(<F593CatalogSummary selection={selection} diameter={diameter} onSelect={onSelect} />);
  expect(screen.getByRole("status")).toHaveTextContent("Resolving current fastener");
  await screen.findByText("Catalog source resolved");
  expect(screen.getByText("100 ksi")).toBeVisible();
  expect(screen.getByText(/60 ksi/)).toBeVisible();
  expect(screen.getByText(/Specified tensile range/)).not.toBeVisible();
  fireEvent.click(screen.getByText("Controlled F593 catalog technical record"));
  expect(screen.getByText(/Specified tensile range/)).toHaveTextContent("100–150 ksi");
  expect(screen.queryByText(resolution.catalog_digest)).not.toBeInTheDocument();
  expect(screen.getByText(/Catalog SHA-256/)).toHaveTextContent(resolution.catalog_digest);
  fireEvent.click(screen.getByText("Predefined alloy and condition selection"));
  fireEvent.change(screen.getByLabelText("F593 alloy"), {target:{value:"316L"}});
  expect(onSelect).toHaveBeenLastCalledWith({...selection,alloy:"316L"});
  fireEvent.change(screen.getByLabelText("F593 condition"), {target:{value:"AF"}});
  expect(onSelect).toHaveBeenLastCalledWith({...selection,condition:"AF"});
  const request = fetchMock.mock.calls[0]?.[1] as RequestInit;
  expect(JSON.parse(request.body as string)).toEqual({selection,diameter});
});

it("keeps unsupported diameter gaps actionable and procurement information neutral", async () => {
  vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response(JSON.stringify({
    ...resolution, fnt:null, fnt_state:"SOURCE_REQUIRED", marking:null, selected_row:null,
    source_requirement:"No controlled cold-worked ASTM F593 table row for selected diameter.",
  }))));
  render(<F593CatalogSummary selection={selection} diameter={{value:".7",unit:"in"}} onSelect={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("No controlled cold-worked");
  expect(screen.getByLabelText("Fastener specification / procurement notes")).not.toHaveAttribute("role","alert");
});

it("displays SI values and leaves unknown threads unevaluated", async () => {
  vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response(JSON.stringify({
    ...resolution,display_fnt:{value:"689.475729316836",unit:"MPa"},
    shear_planes:[{plane_id:"SHEAR_PLANE_1",thread_status:"UNKNOWN",fnv:null,display_fnv:null,fnv_rule:"UNRESOLVED"}],
  }))));
  render(<F593CatalogSummary selection={{...selection,shear_thread_status:"UNKNOWN"}} diameter={{value:"12.7",unit:"mm"}} onSelect={vi.fn()} />);
  await screen.findByText("Catalog source resolved");
  expect(screen.getByText("689.476 MPa")).toBeVisible();
  expect(screen.getByText(/Thread location unresolved/)).toBeVisible();
});

it("does not invent display strengths when the backend omits display quantities", async () => {
  vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response(JSON.stringify({
    ...resolution, display_fnt:null,
    shear_planes:resolution.shear_planes.map((plane) => ({...plane,display_fnv:null})),
  }))));
  render(<F593CatalogSummary selection={selection} diameter={diameter} onSelect={vi.fn()} />);
  await screen.findByText("Catalog source resolved");
  expect(screen.getByText("Unavailable")).toBeVisible();
  expect(screen.getByText(/Bolt shear basis: Unavailable/)).toBeVisible();
  expect(screen.queryByText("100 ksi")).not.toBeInTheDocument();
});

it.each(["network","http","contract"])("presents actionable service errors for %s", async (failure) => {
  vi.stubGlobal("fetch",vi.fn().mockImplementation(() => failure === "network" ? Promise.reject(new TypeError("Failed to fetch"))
    : Promise.resolve(new Response(JSON.stringify(failure === "contract" ? {} : resolution), {status:failure === "http" ? 422 : 200}))));
  render(<F593CatalogSummary selection={selection} diameter={diameter} onSelect={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Check the diameter and local backend service");
  expect(screen.queryByText("Failed to fetch")).not.toBeInTheDocument();
});

it.each([false,true])("discards superseded resolution or rejection (%s) without stale strengths", async (reject) => {
  let finish: ((value:Response) => void) | undefined;
  let fail: ((error:Error) => void) | undefined;
  const first = new Promise<Response>((resolve,rejectPromise) => {finish=resolve;fail=rejectPromise;});
  const fetchMock = vi.fn().mockReturnValueOnce(first).mockResolvedValue(new Response(JSON.stringify({...resolution,condition:"CW2",marking:"F593H",fnt:{value:"85",unit:"ksi"},display_fnt:{value:"85",unit:"ksi"}})));
  vi.stubGlobal("fetch",fetchMock);
  const onSelect=vi.fn();
  const view = render(<F593CatalogSummary selection={selection} diameter={diameter} onSelect={onSelect} />);
  view.rerender(<F593CatalogSummary selection={selection} diameter={{value:".75",unit:"in"}} onSelect={onSelect} />);
  await screen.findByText("85 ksi");
  await act(async () => { if(reject) fail?.(new Error("Superseded")); else finish?.(new Response(JSON.stringify(resolution))); await first.catch(() => undefined); });
  await waitFor(() => {expect(screen.queryByText("100 ksi")).not.toBeInTheDocument();});
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
