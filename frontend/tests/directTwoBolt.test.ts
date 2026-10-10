import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { Mock } from "vitest";
import fixture from "./fixtures/directTwoBoltGeometry.json";
import type { MultiRowConnectionRequest } from "../src/api/multirowContracts";
import { designTwoBolt, editedTwoBolt, exportGeometry, INITIAL_TWO_BOLT, previewTwoBolt, twoBoltRequest } from "../src/api/directTwoBolt";
import type { GeometryResponse } from "../src/api/directTwoBolt";

const mocks = vi.hoisted(() => ({
  envelope: vi.fn(), acceptDesign: vi.fn(() => true), acceptReport: vi.fn(), invalidate: vi.fn(),
}));
vi.mock("../src/api/mat1Transport", () => ({ buildMAT1DesignEnvelope: mocks.envelope }));
vi.mock("../src/state/mat1Session", () => ({ mat1FamilyKey: () => "CURRENT-MAT1", acceptMAT1Design: mocks.acceptDesign }));
vi.mock("../src/state/reportSession", () => ({
  acceptReportSnapshot: mocks.acceptReport, invalidateReportSnapshot: mocks.invalidate, reportGeneration: () => 7,
}));
const legacy = fixture.request.legacy as unknown as MultiRowConnectionRequest;
let fetchMock: Mock<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>;
beforeEach(() => {
  vi.clearAllMocks(); mocks.acceptDesign.mockReturnValue(true);
  mocks.envelope.mockImplementation(() => { throw new Error("Explicit conditions incomplete"); });
  fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(); vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { vi.unstubAllGlobals(); });
const response = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status });
const request = () => twoBoltRequest(legacy, { ...INITIAL_TWO_BOLT }, "CURRENT");

it("leaves geometry independent of incomplete conditions and retains the current typed layout", () => {
  const built = request();
  expect(built.legacy).toBe(legacy);
  expect(built).not.toHaveProperty("material_request");
  expect(built.spacing).toEqual(legacy.pitch);
  expect(editedTwoBolt(INITIAL_TWO_BOLT)).toBe(false);
  for (const change of [{ alignment: "SUPPORT" as const }, { spacing: "2" }, { longitudinal: ".1" }, { transverse: ".1" }, { angleRoot: ".1" }, { supportRoot: ".1" }]) {
    expect(editedTwoBolt({ ...INITIAL_TWO_BOLT, ...change })).toBe(true);
  }
});
it("uses the existing MAT1 envelope and exact neutralized legacy payload for a fresh design", () => {
  const material = structuredClone(fixture.request.material_request);
  mocks.envelope.mockReturnValue({ request: material });
  const built = twoBoltRequest(legacy, {
    ...INITIAL_TWO_BOLT, spacing: "2.25", alignment: "SUPPORT", search: true, searchLimit: "1",
    angleRoot: ".1", supportRoot: ".2", geometrySource: "Measured test dimensions",
  }, "CURRENT");
  expect(built.legacy).toBe(material.legacy_request);
  expect(built.material_request).toBe(material);
  expect(built.midpoint_search?.minimum.support_longitudinal.value).toBe("-1");
  expect(built.angle_root_encroachment?.value).toBe(".1");
  expect(built.support_root_encroachment?.value).toBe(".2");
  expect(built.manufactured_geometry_source).toBe("Measured test dimensions");
});
it("accepts only the current versioned preview", async () => {
  fetchMock.mockResolvedValue(response({ ...fixture.response, revision: "CURRENT" }));
  const data = await previewTwoBolt(request(), new AbortController().signal);
  expect(data.geometry.centers).toEqual(fixture.response.geometry.centers);
  expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/direct-two-bolt/preview");
  for (const change of [{ contract: "OTHER" }, { revision: "STALE" }, { geometry_fingerprint: null }]) {
    fetchMock.mockResolvedValue(response({ ...fixture.response, revision: "CURRENT", ...change }));
    await expect(previewTwoBolt(request(), new AbortController().signal)).rejects.toThrow("incompatible preview");
  }
  fetchMock.mockResolvedValue(response(null));
  await expect(previewTwoBolt(request(), new AbortController().signal)).rejects.toThrow("incompatible preview");
});
it("returns actionable service and backend input errors without raw Failed to fetch", async () => {
  fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
  await expect(previewTwoBolt(request(), new AbortController().signal)).rejects.toThrow("Check the local backend");
  const aborted = new DOMException("Cancelled", "AbortError");
  fetchMock.mockRejectedValue(aborted);
  await expect(previewTwoBolt(request(), new AbortController().signal)).rejects.toBe(aborted);
  for (const [detail, expected] of [
    ["Wrong spacing", "Wrong spacing"], [{ message: "Unmapped layout" }, "Unmapped layout"],
    [[{ message: "Typed validation" }], "Review the geometry inputs"], [null, "Review the geometry inputs"],
  ] as const) {
    fetchMock.mockResolvedValue(response({ detail }, 422));
    await expect(previewTwoBolt(request(), new AbortController().signal)).rejects.toThrow(expected);
  }
  fetchMock.mockResolvedValue(new Response("HTML upstream failure", { status: 502 }));
  await expect(previewTwoBolt(request(), new AbortController().signal)).rejects.toThrow("unreadable error. Retry");
});

it("retains explicit cuts, neighbor boxes and all three optional access envelopes", () => {
  const options = { ...INITIAL_TWO_BOLT, holeDiameter: ".5625", cutPolygon: "0,-1.5;8,-1.5;8,2;0,2", cutSource: "Specified cut",
    neighborBounds: "0,0,1,1,1,2", neighborSource: "Measured box", headEnvelope: ".25,1,2", nutEnvelope: ".3,-2,-1", toolEnvelope: ".5,2,4", envelopeSource: "Specified access envelope" };
  const built = twoBoltRequest(legacy, options, "CURRENT");
  expect(built.end_cuts?.[0]?.member_id).toBe("member-a");
  expect(built.end_cuts?.[0]?.polygon).toHaveLength(4);
  expect(built.neighbors?.[0]?.support_local_upper[2]?.value).toBe("2");
  expect(built.hardware?.map((entry) => entry.kind)).toEqual(["HEAD", "NUT", "TOOL"]);
  expect(built.hole_diameter?.value).toBe(".5625");
  for (const change of [{ holeDiameter: ".563" }, { cutPolygon: options.cutPolygon }, { neighborBounds: options.neighborBounds }, { headEnvelope: options.headEnvelope }, { nutEnvelope: options.nutEnvelope }, { toolEnvelope: options.toolEnvelope }]) {
    expect(editedTwoBolt({ ...INITIAL_TWO_BOLT, ...change })).toBe(true);
  }
  for (const change of [{ neighborBounds: "0,0,1" }, { headEnvelope: ".25,NaN,2" }, { cutPolygon: "0,0;1" }]) {
    expect(() => twoBoltRequest(legacy, { ...options, ...change }, "CURRENT")).toThrow("finite values");
  }
  const absent = structuredClone(legacy); delete absent.physical_connection;
  expect(() => twoBoltRequest(absent, options, "CURRENT")).toThrow("physical Angle member");
  const foreign = structuredClone(legacy);
  if (foreign.physical_connection === undefined) throw new Error("Fixture missing physical connection");
  foreign.physical_connection.joint_assembly.members = foreign.physical_connection.joint_assembly.members.filter((m) => m.section.kind !== "ANGLE");
  expect(() => twoBoltRequest(foreign, options, "CURRENT")).toThrow("physical Angle member");
});
it("fresh design results use existing MAT1 and report currency and never accept superseded geometry", async () => {
  const client = { calculation_id: "FRESH" };
  fetchMock.mockResolvedValue(response({ result: { client_design: client }, report_handle: "H".repeat(64) }));
  expect(await designTwoBolt(request(), new AbortController().signal, () => true)).toEqual(client);
  expect(mocks.acceptDesign).toHaveBeenCalledWith("multi-row", "CURRENT-MAT1", { client_design: client });
  expect(mocks.acceptReport).toHaveBeenCalledWith("multi-row", "H".repeat(64), "design", 7);
  fetchMock.mockImplementation(() => Promise.resolve(response({ result: { native_design: client }, report_handle: "H".repeat(64) })));
  expect(await designTwoBolt(request(), new AbortController().signal, () => true)).toEqual(client);
  await expect(designTwoBolt(request(), new AbortController().signal, () => false)).rejects.toMatchObject({ name: "AbortError" });
  const controller = new AbortController(); controller.abort();
  await expect(designTwoBolt(request(), controller.signal, () => true)).rejects.toMatchObject({ name: "AbortError" });
  mocks.acceptDesign.mockReturnValue(false);
  await expect(designTwoBolt(request(), new AbortController().signal, () => true)).rejects.toMatchObject({ name: "AbortError" });
  mocks.acceptDesign.mockReturnValue(true);
  fetchMock.mockResolvedValue(response({ result: {}, report_handle: "H".repeat(64) }));
  await expect(designTwoBolt(request(), new AbortController().signal, () => true)).rejects.toThrow("omitted");
});
it("exports only a sealed geometry handle with the current typed request", async () => {
  fetchMock.mockResolvedValue(new Response("%PDF", { headers: { "Content-Type": "application/pdf" } }));
  const result = await exportGeometry(request(), fixture.response as unknown as GeometryResponse);
  expect(await result.text()).toBe("%PDF");
  const submitted = fetchMock.mock.calls[0]?.[1];
  if (submitted === undefined) throw new Error("Export did not submit a request");
  const body = JSON.parse(submitted.body as string) as { report_handle: string; current_request: { contract: string } };
  expect(body.report_handle).toBe("G".repeat(64));
  expect(body.current_request.contract).toBe("SHEAR01-DIRECT-SAB2-GEOMETRY-V1");
});
