import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, assert, expect, it, vi } from "vitest";
import * as legacyClient from "../src/api/dctnClient";
import { convertDCTN3BUnits, isDCTN3BRequest, loadDCTN3BDefaults, requestDCTN3B } from "../src/api/dctn3bClient";
import type { DCTN3BRequest, DCTN3BResponse, DCTNRequest, DCTNResponse } from "../src/api/dctnContracts";
import { buildDCTN3BScene } from "../src/visualization/dctnSceneModel";
import { useDCTNPreview } from "../src/workspace/dctnWorkflow";
import fixture from "./dctn3bNativeFixtures.json";
import legacyFixture from "./dctnNativeFixtures.json";

const data = fixture as unknown as { request: DCTN3BRequest; siRequest: DCTN3BRequest; preview: DCTN3BResponse; siPreview: DCTN3BResponse; design: DCTN3BResponse; shearPreview: DCTN3BResponse; shearDesign: DCTN3BResponse };
const signal = () => new AbortController().signal;
const copy = <T,>(value: T): T => structuredClone(value);
const first = <T,>(items: readonly T[]): T => { const item = items[0]; assert(item !== undefined); return item; };
const reply = (value: unknown) => { const r = new Response(); vi.spyOn(r, "json").mockResolvedValue(copy(value)); return r; };
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("uses explicit 3B transport for defaults, conversion, P-only and shear results", async () => {
  vi.stubGlobal("fetch", vi.fn()
    .mockResolvedValueOnce(reply(data.request)).mockResolvedValueOnce(reply(data.siRequest))
    .mockResolvedValueOnce(reply(data.siRequest)).mockResolvedValueOnce(reply(data.request))
    .mockResolvedValueOnce(reply(data.preview)).mockResolvedValueOnce(reply(data.design))
    .mockResolvedValueOnce(reply(data.shearPreview)).mockResolvedValueOnce(reply(data.shearDesign)));
  expect(await loadDCTN3BDefaults("VERTICAL_ONLY", false, signal())).toEqual(data.request);
  expect(await loadDCTN3BDefaults("VERTICAL_ONLY", true, signal())).toEqual(data.siRequest);
  expect(await convertDCTN3BUnits(data.request, true, signal())).toEqual(data.siRequest);
  expect(await convertDCTN3BUnits(data.siRequest, false, signal())).toEqual(data.request);
  expect(await requestDCTN3B("preview", data.request, signal())).toEqual(data.preview);
  expect(await requestDCTN3B("design-check", data.request, signal())).toEqual(data.design);
  expect(await requestDCTN3B("preview", data.shearPreview.result.preview.input, signal())).toEqual(data.shearPreview);
  expect(await requestDCTN3B("design-check", data.shearPreview.result.preview.input, signal())).toEqual(data.shearDesign);
});

it.each(["null", "contract", "datum", "members", "empty", "member_null", "start", "axial_force", "action", "hardware"])("rejects malformed 3B request %s", mode => {
  const request = copy(data.request) as unknown as Record<string, unknown>;
  const member = first(request.members as Record<string, unknown>[]);
  if (mode === "contract") request.contract = "DCTN-2-RC1";
  else if (mode === "datum") request.placement_datum = "CENTROID";
  else if (mode === "members") request.members = {};
  else if (mode === "empty") request.members = [];
  else if (mode === "member_null") request.members = [null];
  else if (mode === "start" || mode === "axial_force") member[mode] = {};
  else if (mode === "action") member.Qp = { value: "NaN", unit: "kip" };
  else if (mode === "hardware") request.fastener = {};
  expect(isDCTN3BRequest(mode === "null" ? null : request)).toBe(false);
});

it.each(["defaults", "units"])("rejects invalid 3B %s response without legacy fallback", async endpoint => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(legacyFixture.request)));
  await expect(endpoint === "defaults" ? loadDCTN3BDefaults("VERTICAL_ONLY", false, signal()) : convertDCTN3BUnits(data.request, true, signal())).rejects.toThrow("Invalid DCTN-3B");
});

it.each(["null", "schema", "contract", "request", "status", "result", "preview", "design", "duplicate_shaft", "missing_shaft", "duplicate_member", "missing_member", "wrong_member", "interpretation"])("rejects malformed 3B result %s", mode => {
  const r = copy(data.preview);
  const loose = r as unknown as Record<string, unknown>;
  if (mode === "schema") loose.api_transport_schema_version = "DCTN-2-API-RC1";
  else if (mode === "contract") loose.contract = "DCTN-2-RC1";
  else if (mode === "request") loose.request_id = "STALE";
  else if (mode === "status") loose.demand_status = null;
  else if (mode === "result") loose.result = null;
  else if (mode === "preview") loose.result = { preview: {}, design: null };
  else if (mode === "design") loose.result = { preview: r.result.preview, design: {} };
  else if (mode === "duplicate_shaft") (r.result.preview.geometry as unknown as Record<string, unknown>).shafts = [...r.result.preview.geometry.shafts, first(r.result.preview.geometry.shafts)];
  else if (mode === "missing_shaft") (r.result.preview.geometry as unknown as Record<string, unknown>).shafts = [];
  else if (mode === "duplicate_member") (r.result.preview.demand as unknown as Record<string, unknown>).members = [...r.result.preview.demand.members, first(r.result.preview.demand.members)];
  else if (mode === "missing_member") (r.result.preview.demand as unknown as Record<string, unknown>).members = [];
  else if (mode === "wrong_member") (first(r.result.preview.demand.members) as unknown as Record<string, unknown>).member_id = "D1";
  else if (mode === "interpretation") (first(first(r.result.preview.demand.members).transported) as unknown as Record<string, unknown>).interpretation = "ALLOCATED_RESPONSE";
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(mode === "null" ? null : r)));
  return expect(requestDCTN3B("preview", data.request, signal())).rejects.toThrow("DCTN-3B");
});

it.each([-1, 0, 1])("renders all signed components %s from the same backend snapshot", sign => {
  const preview = copy(data.shearPreview.result.preview);
  const member = first(preview.input.members);
  for (const field of ["P", "Qp", "Qq"] as const) member[field].value = String(sign * (field === "P" ? 10 : field === "Qp" ? 2 : 3));
  const scene = buildDCTN3BScene(preview);
  expect(scene.appliedArrows).toHaveLength(sign === 0 ? 0 : 3);
  if (sign !== 0) {
    expect(scene.appliedArrows.map(a => a.axis)).toEqual([
      { x: 0 * sign, y: 0 * sign, z: sign }, { x: sign, y: 0 * sign, z: 0 * sign },
      { x: 0 * sign, y: sign, z: 0 * sign },
    ]);
    expect(scene.appliedArrows.map(a => a.signedValue)).toEqual([10 * sign, 2 * sign, 3 * sign]);
    expect(scene.appliedArrows.map(a => a.axialLoadingSense)).toEqual([sign < 0 ? "COMPRESSION" : "TENSION", null, null]);
    expect(scene.appliedArrows.map(a => a.referencePointId)).toEqual(["V:START", "V:START", "V:START"]);
    expect(scene.appliedArrows.map(a => a.componentLabel)).toEqual(["V P", "V Qp", "V Qq"]);
  }
  expect(scene.snapshotVersion).toBe("DCTN-3B-RC1");
  expect(scene.frames.every(f => f.label.includes("u/p/q"))).toBe(true);
});

it("renders native S.I. coordinates without altering snapshot or trace", () => {
  const before = JSON.stringify(data.siPreview);
  const model = buildDCTN3BScene(data.siPreview.result.preview);
  expect(model.boxes).not.toHaveLength(0);
  expect(JSON.stringify(data.siPreview)).toBe(before);
  expect(first(model.appliedArrows).unit).toBe("kN");
});

it.each(["frame", "input"])("fails closed when a native action %s is missing", mode => {
  const p = copy(data.preview.result.preview);
  if (mode === "input") p.input.members = [];
  else (p.geometry as unknown as Record<string, unknown>).members = p.geometry.members.filter(m => m.physical_id !== "V");
  expect(() => buildDCTN3BScene(p)).toThrow("native action frame");
});

it("retains the explicitly historical preview hook", async () => {
  const old = legacyFixture as unknown as { request: DCTNRequest; preview: DCTNResponse };
  vi.spyOn(legacyClient, "requestDCTN").mockResolvedValue(old.preview);
  const hook = renderHook(() => useDCTNPreview(old.request, 0));
  await waitFor(() => { expect(hook.result.current.current).toBe(true); });
  act(() => { hook.unmount(); });
});
