import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { MAT1CatalogRecord, MAT1Conditions } from "../src/state/mat1Session";

const record: MAT1CatalogRecord = {
  id: "ICE:POLY", revision: "RC0", content_digest: "A".repeat(64),
  display_name: "ICE polyester", company: "ICE", resin: "ISOPHTHALIC_POLYESTER",
  source_kind: "OWNER_SUPPLIED_NOMINAL_DATASET", missing: ["TG"], qualification: "OWNER_DATA",
  properties: [{ id: "tensile_strength_L", label: "Tensile L", symbol: "Ft,L", original: "33", unit: "ksi", basis: "NOMINAL_AS_SUPPLIED" }],
};

const conditions: MAT1Conditions = {
  sustained_temperature: { value: "90", unit: "degF" }, maximum_temperature: { value: "90", unit: "degF" },
  glass_transition_temperature: null, moisture: "REFERENCE", chemical: "NONE_DECLARED", load_case_name: "LC-1",
  time_effect_category: "WIND_TORNADO_SEISMIC", source_reference_condition: "UNKNOWN",
  chemical_substance: "", chemical_concentration: "", chemical_contact_form: "", chemical_duration: "",
  uv_weathering: "UNKNOWN", freeze_thaw: "UNKNOWN", protective_measures: "", exposure_notes: "",
  action_provenance: "", live_load_subtype: "", full_amplitude_duration: "", design_period: "",
  service_period: "", fatigue_cycles: "",
};

type Store = typeof import("../src/state/mat1Session");
let store: Store;

beforeEach(async () => {
  vi.resetModules();
  vi.stubGlobal("crypto", { randomUUID: () => "fixed-uuid" });
  store = await import("../src/state/mat1Session");
});
afterEach(() => { vi.unstubAllGlobals(); });

describe("MAT1 tab session and result identity", () => {
  it("keeps catalog data immutable, copies into a session and protects assigned deletion", () => {
    store.setMAT1Catalog([record]);
    expect(store.materialSelection(record.id)).toEqual({ kind: "CATALOG", id: record.id, revision: record.revision, content_digest: record.content_digest });
    expect(store.materialSelection("missing")).toBeNull();
    const id = store.createMAT1Session(record);
    expect(id).toBe("SESSION:fixed-uuid");
    expect(store.mat1Snapshot().custom[id]?.properties.tensile_strength_L?.value).toBe("33");
    store.editMAT1Session(id, { properties: { tensile_strength_L: { label: "Tensile L", symbol: "Ft,L", value: "40", unit: "ksi", basis: "CHARACTERISTIC" } } });
    expect(store.mat1Snapshot().custom[id]?.revision).toBe("2");
    expect(record.properties[0]?.original).toBe("33");
    expect(store.materialSelection(id)).toMatchObject({ kind: "SESSION", revision: "2" });
    store.setMAT1Default(id);
    expect(store.deleteMAT1Session(id)).toBe(false);
    store.clearMAT1Sessions();
    expect(store.mat1Snapshot().defaultId).toBeNull();
    expect(store.materialSelection(id)).toBeNull();
    expect(store.deleteMAT1Session(id)).toBe(true);
    expect(() => { store.editMAT1Session(id, { company: "none" }); }).toThrow("no longer exists");
  });

  it("keeps custom records and overrides in memory and rejects deletion while assigned", () => {
    store.setMAT1Catalog([record]);
    const id = store.createMAT1Session();
    expect(store.mat1Snapshot().custom[id]?.properties).toEqual({});
    store.editMAT1Session(id, { properties: { tensile_strength_L: { label: "Tensile L", symbol: "Ft,L", value: "30", unit: "ksi", basis: "UNKNOWN" } } });
    vi.stubGlobal("crypto", { randomUUID: () => "second-copy" });
    const copied = store.createMAT1Session(store.mat1Snapshot().custom[id]);
    store.editMAT1Session(id, { display_name: "Original renamed" });
    expect(store.mat1Snapshot().custom[copied]?.properties.tensile_strength_L?.value).toBe("30");
    expect(store.mat1Snapshot().custom[copied]?.display_name).not.toBe("Original renamed");
    store.setMAT1Override("clip-angle", "ANGLE", id);
    expect(store.deleteMAT1Session(id)).toBe(false);
    store.setMAT1Override("clip-angle", "ANGLE", undefined);
    expect(store.deleteMAT1Session(id)).toBe(true);
    store.setMAT1Override("clip-angle", "ANGLE", record.id);
    expect(store.mat1Snapshot().overrides["clip-angle"]?.ANGLE).toBe(record.id);
    store.setMAT1Override("clip-angle", "ANGLE", null);
    expect(store.mat1Snapshot().overrides["clip-angle"]?.ANGLE).toBeNull();
    store.clearMAT1Sessions();
    expect(store.mat1Snapshot().overrides["clip-angle"]?.ANGLE).toBeNull();
  });

  it("invalidates a design for assignment, conditions and preview changes", () => {
    store.setMAT1Catalog([record]);
    store.setMAT1Active(true);
    store.setMAT1Default(record.id);
    store.setMAT1Conditions(conditions);
    store.rememberMAT1Preview("clip-angle", '{"size":1}');
    const original = store.mat1FamilyKey("clip-angle");
    expect(store.acceptMAT1Design("clip-angle", original, { overall_status: "SOURCE_REQUIRED" })).toBe(true);
    expect(store.acceptMAT1Design("clip-angle", "old", {})).toBe(false);
    store.rememberMAT1Preview("clip-angle", '{"size":1}');
    expect(store.mat1FamilyKey("clip-angle")).toBe(original);
    store.rememberMAT1Preview("clip-angle", '{"size":2}');
    expect(store.mat1FamilyKey("clip-angle")).not.toBe(original);
    store.setMAT1PreviewOwners("clip-angle", '{"size":1}', ["stale"]);
    expect(store.mat1Snapshot().previewOwners["clip-angle"]).toBeUndefined();
    store.setMAT1PreviewOwners("clip-angle", '{"size":2}', ["B", "A"]);
    expect(store.mat1Snapshot().previewOwners["clip-angle"]).toEqual(["B", "A"]);
    store.setMAT1Override("clip-angle", "A", record.id);
    expect(store.mat1FamilyKey("clip-angle")).not.toBe(original);
    store.setMAT1Conditions({ ...conditions, moisture: "SUSTAINED_MOISTURE" });
    expect(store.mat1FamilyKey("clip-angle")).toContain("SUSTAINED_MOISTURE");
    store.setMAT1Active(false);
    expect(store.mat1FamilyKey("clip-angle")).toBe("LEGACY");
  });

  it("applies only to visible FRP owners and keeps per-owner load metadata aligned", () => {
    store.setMAT1Catalog([record]);
    store.setMAT1Default(record.id);
    store.setMAT1Conditions(conditions);
    store.setMAT1ConditionOverride("new-family", "A", null);
    expect(() => { store.applyMAT1ToOwners("beam-web-splice", [], record.id); }).toThrow("compatible FRP owners");
    expect(() => { store.applyMAT1ToOwners("beam-web-splice", ["A"], "missing"); }).toThrow("compatible FRP owners");
    store.applyMAT1ToOwners("beam-web-splice", ["A", "B"], record.id);
    expect(store.mat1Snapshot().overrides["beam-web-splice"]).toEqual({ A: record.id, B: record.id });
    store.setMAT1ConditionOverride("beam-web-splice", "A", { ...conditions, moisture: "OTHER" });
    store.setMAT1Conditions({ ...conditions, time_effect_category: "OTHER_LIVE", load_case_name: "LC-2", action_provenance: "factored" });
    expect(store.mat1Snapshot().conditionOverrides["beam-web-splice"]?.A).toMatchObject({ moisture: "OTHER", time_effect_category: "OTHER_LIVE", load_case_name: "LC-2", action_provenance: "factored" });
    store.setMAT1ConditionOverride("beam-web-splice", "A", null);
    expect(store.mat1Snapshot().conditionOverrides["beam-web-splice"]?.A).toBeUndefined();
    store.setMAT1CatalogError("network");
    expect(store.mat1Snapshot().catalogError).toBe("network");
    store.setMAT1Catalog([record]);
    expect(store.mat1Snapshot().catalogError).toBeNull();
  });
});
