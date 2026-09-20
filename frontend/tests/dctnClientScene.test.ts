import { afterEach, describe, expect, it, vi } from "vitest";
import { convertDCTNUnits, isDCTNRequest, loadDCTNDefaults, requestDCTN } from "../src/api/dctnClient";
import type { DCTNRequest, DCTNResponse } from "../src/api/dctnContracts";
import { buildDCTNScene } from "../src/visualization/dctnSceneModel";
import { clearDCTNQualification, dctnKey, editDCTNMember, finiteDCTNRequest } from "../src/workspace/dctnWorkflow";
import fixture from "./dctnNativeFixtures.json";

const data = fixture as unknown as { request: DCTNRequest; siRequest: DCTNRequest; preview: DCTNResponse; design: DCTNResponse; siPreview: DCTNResponse; wiPreview: DCTNResponse };
const signal = () => new AbortController().signal;
const clone = <T,>(value: T) => structuredClone(value);
const first = <T,>(values: readonly T[]): T => {
  const value = values[0];
  if (value === undefined) throw new Error("Required native fixture element missing");
  return value;
};
const reply = (value: unknown, status = 200) => {
  const response = new Response(null, { status, headers: { "Content-Type": "application/json" } });
  // Return the parsed native response directly. A JS stringify/reparse mock
  // would erase native IEEE negative zero before the production client sees it.
  vi.spyOn(response, "json").mockResolvedValue(clone(value));
  return response;
};
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("DCTN actual native transport fixtures", () => {
  it("loads exact defaults, native conversion and both response kinds", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(reply(data.request)).mockResolvedValueOnce(reply(data.siRequest)).mockResolvedValueOnce(reply(data.siRequest)).mockResolvedValueOnce(reply(data.request)).mockResolvedValueOnce(reply(data.preview)).mockResolvedValueOnce(reply(data.design));
    vi.stubGlobal("fetch", fetcher);
    expect(await loadDCTNDefaults("VERTICAL_ONLY", false, signal())).toEqual(data.request);
    expect(await loadDCTNDefaults("VERTICAL_ONLY", true, signal())).toEqual(data.siRequest);
    expect(await convertDCTNUnits(data.request, true, signal())).toEqual(data.siRequest);
    expect(await convertDCTNUnits(data.siRequest, false, signal())).toEqual(data.request);
    expect(await requestDCTN("preview", data.request, signal())).toEqual(data.preview);
    expect(await requestDCTN("design-check", data.request, signal())).toEqual(data.design);
    expect(fetcher.mock.calls[0]?.[0]).toContain("unit_system=US");
    expect(fetcher.mock.calls[1]?.[0]).toContain("unit_system=SI");
    expect(fetcher.mock.calls[4]?.[1]).toMatchObject({ method: "POST", credentials: "same-origin", body: JSON.stringify(data.request) });
    expect(data.request.fastener.hole_diameter.value).toBe("0.563");
    expect(data.siRequest.fastener.hole_diameter.value).toBe("14.3002");
  });
  it.each(["network", "abort", "unreadable", "validation", "http"])("reports %s without fabricating a result", async mode => {
    const error = new DOMException("cancel", "AbortError");
    const mock = vi.fn();
    if (mode === "network") mock.mockRejectedValue(new Error("offline"));
    else if (mode === "abort") mock.mockRejectedValue(error);
    else if (mode === "unreadable") mock.mockResolvedValue(new Response("not json"));
    else mock.mockResolvedValue(reply({ detail: "rejected" }, mode === "validation" ? 422 : 503));
    vi.stubGlobal("fetch", mock);
    const promise = requestDCTN("preview", data.request, signal());
    if (mode === "abort") await expect(promise).rejects.toBe(error);
    else await expect(promise).rejects.toThrow();
  });
  it.each(["defaults", "units"])("rejects malformed %s", async endpoint => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply({})));
    await expect(endpoint === "defaults" ? loadDCTNDefaults("VERTICAL_ONLY", false, signal()) : convertDCTNUnits(data.request, true, signal())).rejects.toThrow("Invalid DCTN");
    expect(isDCTNRequest(null)).toBe(false);
    expect(isDCTNRequest([])).toBe(false);
    const malformed = clone(data.request); first(malformed.members).inclination_deg = "NaN";
    expect(isDCTNRequest(malformed)).toBe(false);
  });
  it.each(["schema", "request", "result", "geometry", "design", "duplicate", "missing_shaft", "rational_zero", "corner"])("fails closed on malformed %s", async field => {
    const r = clone(data.preview);
    const loose = r as unknown as Record<string, unknown>;
    if (field === "schema") loose.api_transport_schema_version = "untrusted";
    else if (field === "request") loose.request_id = "stale";
    else if (field === "result") loose.result = null;
    else if (field === "geometry") (r.result.preview.geometry as unknown as Record<string, unknown>).members = [{}];
    else if (field === "design") (r.result as unknown as Record<string, unknown>).design = {};
    else if (field === "duplicate") (r.result.preview.geometry as unknown as Record<string, unknown>).shafts = [...r.result.preview.geometry.shafts, r.result.preview.geometry.shafts[0]];
    else if (field === "missing_shaft") (r.result.preview.geometry as unknown as Record<string, unknown>).shafts = [];
    else if (field === "rational_zero") (first(r.result.preview.geometry.members).u[0] as unknown as Record<string, unknown>).denominator = "0";
    else (first(r.result.preview.geometry.members).placement as unknown as Record<string, unknown>).deferred_features = [{}];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(r)));
    await expect(requestDCTN("preview", data.request, signal())).rejects.toThrow();
  });
});

it("rejects missing edit targets and does not invent a missing diagonal partner", () => {
  const request = clone(data.request);
  expect(() => { editDCTNMember(request,"D1",()=>undefined,true); }).toThrow("active member is missing");
  editDCTNMember(request,"V",m=>{m.axial_force.value="2";},true);
  expect(request.members).toHaveLength(1);
  expect(first(request.members).axial_force.value).toBe("2");
});

it.each([null,{value:"1",unit:"kip"}])("validates nullable numerical design fields %j", async quantity => {
  const response = clone(data.design);
  const design = response.result.design as unknown as Record<string,unknown>;
  design.checks=[{check_id:"TEST_ONLY",owner_id:"V",status:"SOURCE_REQUIRED",demand:quantity,resistance:quantity,source_reference:""}];
  vi.stubGlobal("fetch",vi.fn().mockResolvedValue(reply(response)));
  expect(await requestDCTN("design-check",data.request,signal())).toEqual(response);
});

it("validates SI native geometry units through the response parser", async () => {
  vi.stubGlobal("fetch",vi.fn().mockResolvedValue(reply(data.siPreview)));
  expect(await requestDCTN("preview",data.siRequest,signal())).toEqual(data.siPreview);
});

describe("DCTN native geometry and physical hardware presentation", () => {
  it.each(["preview", "siPreview", "wiPreview"] as const)("renders %s with exact physical identities and exterior hardware only", key => {
    const p = data[key].result.preview;
    const scene = buildDCTNScene(p);
    const bolts = scene.cylinders.filter(c => c.kind === "BOLT");
    expect(bolts.map(c => c.id)).toEqual(p.geometry.shafts.map(s => s.bolt_id));
    expect(scene.cylinders.filter(c => c.kind === "WASHER")).toHaveLength(2 * bolts.length);
    expect(new Set(scene.cylinders.map(c => c.id)).size).toBe(scene.cylinders.length);
    expect(bolts.every(c => c.exactHardware?.source === p.input.fastener.hardware.geometry_source)).toBe(true);
    expect(scene.boxes.some(b => b.id.includes("DEFERRED_COLLISION_ONLY"))).toBe(false);
    expect(scene.frames).toHaveLength(p.geometry.members.length);
    expect(scene.materialAxes.every(a => a.materialRegionId.length > 0)).toBe(true);
    expect(scene.boundsRadius).toBeGreaterThan(0);
    if (key === "wiPreview") expect(bolts).toHaveLength(4);
    else { expect(bolts).toHaveLength(2); expect(scene.boxes.filter(b => b.deferred)).toHaveLength(4); }
  });
  it.each(["10", "-10", "0"])("renders signed axial %s from the accepted native member input", force => {
    const p = clone(data.preview.result.preview);
    first(p.input.members).axial_force.value = force;
    const scene = buildDCTNScene(p);
    if (force === "0") expect(scene.appliedArrows).toEqual([]);
    else {
      expect(scene.appliedArrows).toHaveLength(1);
      expect(scene.appliedArrows[0]).toMatchObject({ signedValue: Number(force), axis: { x: 0 * Math.sign(Number(force)), y: 0 * Math.sign(Number(force)), z: Math.sign(Number(force)) }, referencePointId: "V:START", axialLoadingSense: force === "10" ? "TENSION" : "COMPRESSION" });
    }
  });
  it("does not invent a missing member frame", () => {
    const p = clone(data.preview.result.preview);
    (p.geometry as unknown as Record<string, unknown>).members = p.geometry.members.filter(m => m.physical_id !== "V");
    expect(() => buildDCTNScene(p)).toThrow("member frame is missing");
  });
});

it("binds staleness to engineering inputs and clears geometry-bound qualification", () => {
  const request = clone(data.request), changed = clone(data.request);
  changed.request_id = "other";
  expect(dctnKey(request)).toBe(dctnKey(changed));
  first(changed.members).axial_force.value = "2";
  expect(dctnKey(request)).not.toBe(dctnKey(changed));
  request.channel.material_source_reference = request.fastener.source_reference = request.shared_channel_source_reference = "SOURCE";
  const member = first(request.members);
  member.material_source_reference = member.local_path_source_reference = "SOURCE";
  clearDCTNQualification(request);
  expect(JSON.stringify(request)).not.toContain("SOURCE");
  expect(finiteDCTNRequest(request)).toBe(true);
  member.axial_force.value = ""; expect(finiteDCTNRequest(request)).toBe(false);
  member.axial_force.value = "1"; member.inclination_deg = "NaN"; expect(finiteDCTNRequest(request)).toBe(false);
  member.inclination_deg = "0"; member.pattern.rows = Number.NaN; expect(finiteDCTNRequest(request)).toBe(false);
});
