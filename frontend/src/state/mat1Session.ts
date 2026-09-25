import { useSyncExternalStore } from "react";

export interface MAT1Property {
  readonly id: string;
  readonly label: string;
  readonly symbol: string;
  readonly original: string;
  readonly unit: string;
  readonly basis: string;
}

export interface MAT1CatalogRecord {
  readonly id: string;
  readonly revision: string;
  readonly content_digest: string;
  readonly display_name: string;
  readonly company: string;
  readonly resin: "ISOPHTHALIC_POLYESTER" | "VINYL_ESTER" | "OTHER";
  readonly source_kind: string;
  readonly missing: readonly string[];
  readonly properties: readonly MAT1Property[];
  readonly qualification: string;
}

export interface MAT1SessionProperty {
  readonly label: string;
  readonly symbol: string;
  readonly value: string;
  readonly unit: string;
  readonly basis: string;
}

export interface MAT1SessionRecord {
  readonly kind: "SESSION";
  readonly id: string;
  readonly revision: string;
  readonly display_name: string;
  readonly company: string;
  readonly resin: MAT1CatalogRecord["resin"];
  readonly properties: Readonly<Record<string, MAT1SessionProperty>>;
  readonly copied_from: string | null;
}

export interface MAT1Conditions {
  readonly sustained_temperature: { readonly value: string; readonly unit: "degF" | "degC" };
  readonly maximum_temperature: { readonly value: string; readonly unit: "degF" | "degC" };
  readonly glass_transition_temperature: { readonly value: string; readonly unit: "degF" | "degC" } | null;
  readonly moisture: "REFERENCE" | "SUSTAINED_MOISTURE" | "OTHER" | "UNKNOWN";
  readonly chemical: "NONE_DECLARED" | "SPECIFIED" | "UNKNOWN";
  readonly load_case_name: string;
  readonly time_effect_category: string;
  readonly source_reference_condition: "REFERENCE" | "ALREADY_ADJUSTED" | "UNKNOWN";
  readonly chemical_substance: string;
  readonly chemical_concentration: string;
  readonly chemical_contact_form: string;
  readonly chemical_duration: string;
  readonly uv_weathering: "NONE_DECLARED" | "SPECIFIED" | "UNKNOWN";
  readonly freeze_thaw: "NONE_DECLARED" | "SPECIFIED" | "UNKNOWN";
  readonly protective_measures: string;
  readonly exposure_notes: string;
  readonly action_provenance: string;
  readonly live_load_subtype: string;
  readonly full_amplitude_duration: string;
  readonly design_period: string;
  readonly service_period: string;
  readonly fatigue_cycles: string;
}

interface MAT1State {
  readonly catalog: readonly MAT1CatalogRecord[];
  readonly catalogError: string | null;
  readonly active: boolean;
  readonly defaultId: string | null;
  readonly custom: Readonly<Record<string, MAT1SessionRecord>>;
  readonly overrides: Readonly<Record<string, Readonly<Record<string, string | null>>>>;
  readonly conditions: MAT1Conditions;
  readonly conditionOverrides: Readonly<Record<string, Readonly<Record<string, MAT1Conditions>>>>;
  readonly designKeys: Readonly<Record<string, string>>;
  readonly designTraces: Readonly<Record<string, unknown>>;
  readonly previewInputs: Readonly<Record<string, string>>;
  readonly previewOwners: Readonly<Record<string, readonly string[]>>;
  readonly previewOwnerKeys: Readonly<Record<string, string>>;
}

const initialConditions: MAT1Conditions = {
  sustained_temperature: { value: "", unit: "degF" },
  maximum_temperature: { value: "", unit: "degF" },
  glass_transition_temperature: null,
  moisture: "UNKNOWN",
  chemical: "UNKNOWN",
  load_case_name: "",
  time_effect_category: "",
  source_reference_condition: "UNKNOWN",
  chemical_substance: "", chemical_concentration: "", chemical_contact_form: "", chemical_duration: "",
  uv_weathering: "UNKNOWN", freeze_thaw: "UNKNOWN", protective_measures: "", exposure_notes: "",
  action_provenance: "", live_load_subtype: "", full_amplitude_duration: "", design_period: "",
  service_period: "", fatigue_cycles: "",
};

let current: MAT1State = {
  catalog: [], catalogError: null, active: false, defaultId: null,
  custom: {}, overrides: {}, conditions: initialConditions, conditionOverrides: {},
  designKeys: {}, designTraces: {},
  previewInputs: {}, previewOwners: {}, previewOwnerKeys: {},
};
const listeners = new Set<() => void>();
const notify = (next: MAT1State): void => { current = next; listeners.forEach((listener) => { listener(); }); };
const subscribe = (listener: () => void): (() => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };

export const mat1Snapshot = (): MAT1State => current;
export const useMAT1 = (): MAT1State => useSyncExternalStore(subscribe, mat1Snapshot);

export function setMAT1Catalog(records: readonly MAT1CatalogRecord[]): void {
  notify({ ...current, catalog: [...records], catalogError: null });
}

export function setMAT1CatalogError(message: string): void {
  notify({ ...current, catalogError: message });
}

export function setMAT1Active(active: boolean): void {
  notify({ ...current, active });
}

export function setMAT1Default(id: string | null): void {
  notify({ ...current, active: true, defaultId: id });
}

export function setMAT1Conditions(conditions: MAT1Conditions): void {
  const conditionOverrides = Object.fromEntries(Object.entries(current.conditionOverrides).map(([family, owners]) => [
    family,
    Object.fromEntries(Object.entries(owners).map(([owner, value]) => [owner, {
      ...value, time_effect_category: conditions.time_effect_category,
      load_case_name: conditions.load_case_name,
      action_provenance: conditions.action_provenance,
    }])),
  ]));
  notify({ ...current, conditions, conditionOverrides });
}

export function setMAT1Override(family: string, owner: string, id: string | null | undefined): void {
  const owners = { ...current.overrides[family] };
  if (id === undefined) {
    notify({ ...current, overrides: { ...current.overrides, [family]: Object.fromEntries(Object.entries(owners).filter(([key]) => key !== owner)) } });
    return;
  }
  notify({
    ...current,
    overrides: {
      ...current.overrides,
      [family]: { ...owners, [owner]: id },
    },
  });
}

export function applyMAT1ToOwners(family: string, owners: readonly string[], id: string): void {
  const selected = materialSelection(id);
  if (selected === null || owners.length === 0) throw new Error("Select a material and compatible FRP owners.");
  const updated = { ...current.overrides[family] };
  for (const owner of owners) updated[owner] = id;
  notify({ ...current, overrides: { ...current.overrides, [family]: updated } });
}

export function setMAT1ConditionOverride(family: string, owner: string, value: MAT1Conditions | null): void {
  const next = value === null
    ? Object.fromEntries(Object.entries(current.conditionOverrides[family] ?? {}).filter(([key]) => key !== owner))
    : { ...current.conditionOverrides[family], [owner]: value };
  notify({ ...current, conditionOverrides: { ...current.conditionOverrides, [family]: next } });
}

export function rememberMAT1Preview(family: string, input: string): void {
  if (current.previewInputs[family] === input) return;
  notify({ ...current, previewInputs: { ...current.previewInputs, [family]: input } });
}

export function setMAT1PreviewOwners(family: string, input: string, owners: readonly string[]): void {
  if (current.previewInputs[family] !== input) return;
  notify({ ...current, previewOwners: { ...current.previewOwners, [family]: [...owners] }, previewOwnerKeys: { ...current.previewOwnerKeys, [family]: input } });
}

export function createMAT1Session(source?: MAT1CatalogRecord | MAT1SessionRecord): string {
  const id = `SESSION:${crypto.randomUUID()}`;
  const copied = source === undefined ? {} : "kind" in source
    ? structuredClone(source.properties)
    : Object.fromEntries(source.properties.map((item) => [item.id, {
      label: item.label, symbol: item.symbol, value: item.original,
      unit: item.unit, basis: item.basis,
    }]));
  const record: MAT1SessionRecord = {
    kind: "SESSION", id, revision: "1",
    display_name: source === undefined ? "New session material" : `${source.display_name} copy`,
    company: source === undefined ? "User" : source.company,
    resin: source?.resin ?? "OTHER",
    properties: copied,
    copied_from: source?.id ?? null,
  };
  notify({ ...current, custom: { ...current.custom, [id]: record } });
  return id;
}

export function editMAT1Session(id: string, changes: Partial<Pick<MAT1SessionRecord, "display_name" | "company" | "resin" | "properties">>): void {
  const record = current.custom[id];
  if (record === undefined) throw new Error("Session material no longer exists.");
  const updated = { ...record, ...changes, revision: String(Number(record.revision) + 1) };
  notify({ ...current, custom: { ...current.custom, [id]: updated } });
}

export function deleteMAT1Session(id: string): boolean {
  if (current.defaultId === id || Object.values(current.overrides).some((owners) => Object.values(owners).includes(id))) return false;
  const custom = Object.fromEntries(Object.entries(current.custom).filter(([key]) => key !== id));
  notify({ ...current, custom });
  return true;
}

export function clearMAT1Sessions(): void {
  const overrides = Object.fromEntries(Object.entries(current.overrides).map(([family, owners]) => [
    family,
    Object.fromEntries(Object.entries(owners).map(([owner, id]) => [owner, id !== null && id in current.custom ? null : id])),
  ]));
  notify({ ...current, custom: {}, defaultId: current.defaultId !== null && current.defaultId in current.custom ? null : current.defaultId, overrides });
}

export function materialSelection(id: string | null): object | null {
  if (id === null) return null;
  const custom = current.custom[id];
  if (custom !== undefined) return custom;
  const catalog = current.catalog.find((item) => item.id === id);
  return catalog === undefined ? null : {
    kind: "CATALOG", id: catalog.id, revision: catalog.revision,
    content_digest: catalog.content_digest,
  };
}

export function mat1FamilyKey(family: string): string {
  if (!current.active) return "LEGACY";
  const owners = current.overrides[family] ?? {};
  return JSON.stringify({
    family, defaultMaterial: materialSelection(current.defaultId),
    overrides: Object.fromEntries(Object.entries(owners).map(([owner, id]) => [owner, materialSelection(id)])),
    conditions: current.conditions, conditionOverrides: current.conditionOverrides[family] ?? {},
    previewInput: current.previewInputs[family] ?? null,
  });
}

export function acceptMAT1Design(family: string, key: string, trace: unknown): boolean {
  if (mat1FamilyKey(family) !== key) return false;
  notify({
    ...current,
    designKeys: { ...current.designKeys, [family]: key },
    designTraces: { ...current.designTraces, [family]: trace },
  });
  return true;
}
