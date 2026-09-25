import { useEffect, useState } from "react";

import {
  applyMAT1ToOwners,
  clearMAT1Sessions,
  createMAT1Session,
  deleteMAT1Session,
  editMAT1Session,
  mat1FamilyKey,
  setMAT1Active,
  setMAT1Catalog,
  setMAT1CatalogError,
  setMAT1Conditions,
  setMAT1ConditionOverride,
  setMAT1Default,
  setMAT1Override,
  setMAT1PreviewOwners,
  useMAT1,
} from "../state/mat1Session";
import type {
  MAT1CatalogRecord,
  MAT1Conditions,
  MAT1Property,
  MAT1SessionProperty,
} from "../state/mat1Session";

const readable = (text: string): string => text.replaceAll("_", " ");
const linkedFamilies = new Set([
  "multi-row", "tee-connector", "clip-angle", "paired-clip-angle",
  "multi-member-tee", "beam-concrete-paired-angle",
]);

export function MAT1MaterialsPanel({ family }: { readonly family: string }) {
  const state = useMAT1();
  const [message, setMessage] = useState("");
  const [showProperties, setShowProperties] = useState(false);
  const [showConditions, setShowConditions] = useState(false);
  const [showAdjustments, setShowAdjustments] = useState(false);
  const [candidate, setCandidate] = useState<unknown>(null);

  useEffect(() => {
    if (!state.active || state.catalog.length > 0 || state.catalogError !== null) return;
    const controller = new AbortController();
    void fetch("/api/v1/frp-materials/catalog", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Material catalog HTTP ${String(response.status)}`);
        const body = await response.json() as { records?: MAT1CatalogRecord[] };
        if (!Array.isArray(body.records)) throw new Error("Material catalog response is invalid.");
        setMAT1Catalog(body.records);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setMAT1CatalogError(String(error));
      });
    return () => { controller.abort(); };
  }, [state.active, state.catalog.length, state.catalogError]);

  const previewInput = state.previewInputs[family];
  useEffect(() => {
    if (!state.active || previewInput === undefined || state.previewOwnerKeys[family] === previewInput) return;
    const controller = new AbortController();
    void fetch("/api/v1/frp-materials/family/owners", {
      method: "POST", headers: { "Content-Type": "application/json" }, signal: controller.signal,
      body: JSON.stringify({ contract: "MAT1-OWNER-PREVIEW-RC0", family_id: family, legacy_request: JSON.parse(previewInput) as unknown }),
    }).then(async (response) => {
      if (!response.ok) throw new Error(`Material owner preview HTTP ${String(response.status)}`);
      const result = await response.json() as { owners?: string[]; design_check_performed?: boolean };
      if (!Array.isArray(result.owners) || result.design_check_performed !== false) throw new Error("Invalid material owner preview.");
      setMAT1PreviewOwners(family, previewInput, result.owners);
    }).catch((error: unknown) => { if (!controller.signal.aborted) setMessage(String(error)); });
    return () => { controller.abort(); };
  }, [family, previewInput, state.active, state.previewOwnerKeys]);

  const selectedCatalog = state.catalog.find((item) => item.id === state.defaultId);
  const selectedSession = state.defaultId === null ? undefined : state.custom[state.defaultId];
  const selected = selectedCatalog ?? selectedSession;
  const trace = state.designTraces[family] as { material_ledgers?: Record<string, unknown>[]; overall_status?: string } | undefined;
  const owners = Array.from(new Set([
    ...(state.previewOwners[family] ?? []),
    ...Object.keys(state.overrides[family] ?? {}),
    ...(trace?.material_ledgers ?? []).map((item) => item.component_id).filter((item): item is string => typeof item === "string"),
  ])).sort();
  const current = state.designKeys[family] === mat1FamilyKey(family);
  const ledgers = current ? trace?.material_ledgers ?? [] : [];
  const displayedProperties: readonly MAT1Property[] = selectedCatalog?.properties
    ?? Object.entries(selectedSession?.properties ?? {}).map(([id, property]) => ({
      id, label: property.label, symbol: property.symbol, original: property.value,
      unit: property.unit, basis: property.basis,
    }));

  function updateConditions(changes: Partial<MAT1Conditions>): void {
    setMAT1Conditions({ ...state.conditions, ...changes });
  }

  function updateOwnerConditions(owner: string, base: MAT1Conditions, changes: Partial<MAT1Conditions>): void {
    setMAT1ConditionOverride(family, owner, { ...base, ...changes });
  }

  async function inspectFactors(): Promise<void> {
    if (selected === undefined || !completeConditions(state.conditions) || displayedProperties.length === 0) {
      setMessage("Select a material, complete the conditions, and enter at least one property.");
      return;
    }
    const material = "kind" in selected ? selected : {
      kind: "CATALOG", id: selected.id, revision: selected.revision,
      content_digest: selected.content_digest,
    };
    try {
      const response = await fetch("/api/v1/frp-materials/factor-candidates", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contract: "MAT1-FACTOR-RC0", material, conditions: state.conditions,
          component_id: family, property_ids: displayedProperties.map((item) => item.id),
        }),
      });
      const body = await response.json() as unknown;
      if (!response.ok) throw new Error(`Factor inspection HTTP ${String(response.status)}`);
      setCandidate(body);
      setShowAdjustments(true);
      setMessage("Numerical candidates only; source and qualification gates remain open.");
    } catch (error) { setMessage(String(error)); }
  }

  return <section className="mat1-material-panel" aria-label="FRP Materials and Design Conditions">
    <details>
      <summary>FRP Materials &amp; Design Conditions <small>{state.active ? selected?.display_name ?? "Unassigned" : "Legacy compatibility"}</small></summary>
      <p>Predefined values are read-only owner-supplied data. Session materials disappear on reload, tab close, or Clear session materials.</p>
      <label>Material mode <select value={state.active ? "MAT1" : "LEGACY"} onChange={(event) => { setMAT1Active(event.currentTarget.value === "MAT1"); }}><option value="LEGACY">Legacy controlled material</option><option value="MAT1">Versioned material selection</option></select></label>
      {state.catalogError === null ? null : <p role="alert">{state.catalogError}</p>}
      {state.active ? <>
        <label>Connection default material <select value={state.defaultId ?? ""} onChange={(event) => { setMAT1Default(event.currentTarget.value || null); setCandidate(null); }}>
          <option value="">Unassigned — design unavailable</option>
          {state.catalog.map((record) => <option key={record.id} value={record.id}>{record.company} · {readable(record.resin)} · {record.revision}</option>)}
          {Object.values(state.custom).map((record) => <option key={record.id} value={record.id}>Session · {record.display_name} · revision {record.revision}</option>)}
        </select></label>
        {selected === undefined ? null : <p>Source: {selectedCatalog === undefined ? "User-supplied session data" : "Owner-supplied nominal dataset"}. Catalog presence is not manufacturer or statistical qualification.</p>}
        <div className="benchmark-actions">
          <button type="button" onClick={() => { const id = createMAT1Session(); setMAT1Default(id); setShowProperties(true); }}>New session material</button>
          <button type="button" disabled={selected === undefined} onClick={selected === undefined ? undefined : () => { const id = createMAT1Session(selected); setMAT1Default(id); setShowProperties(true); }}>Copy as session material</button>
          <button type="button" onClick={() => { clearMAT1Sessions(); setMessage("Session materials cleared. Affected assignments are unassigned and stale."); }}>Clear session materials</button>
          {Object.values(state.custom).map((item) => <button key={item.id} type="button" onClick={() => { setMessage(deleteMAT1Session(item.id) ? "Session material deleted." : "Reassign components before deleting this material."); }}>Delete {item.display_name}</button>)}
        </div>
        {selectedSession === undefined ? null : <div className="mat1-session-editor">
          <label>Session material name <input value={selectedSession.display_name} onChange={(event) => { editMAT1Session(selectedSession.id, { display_name: event.currentTarget.value }); }} /></label>
          <label>Company/source label <input value={selectedSession.company} onChange={(event) => { editMAT1Session(selectedSession.id, { company: event.currentTarget.value }); }} /></label>
          <label>Resin <select value={selectedSession.resin} onChange={(event) => { editMAT1Session(selectedSession.id, { resin: event.currentTarget.value as MAT1CatalogRecord["resin"] }); }}><option value="ISOPHTHALIC_POLYESTER">Isophthalic polyester</option><option value="VINYL_ESTER">Vinyl ester</option><option value="OTHER">Other — temperature model required</option></select></label>
          <label>Add property <select value="" onChange={(event) => {
            const seed = state.catalog[0]?.properties.find((item) => item.id === event.currentTarget.value);
            if (seed === undefined) return;
            editMAT1Session(selectedSession.id, { properties: { ...selectedSession.properties, [seed.id]: { label: seed.label, symbol: seed.symbol, value: "", unit: seed.unit, basis: "UNKNOWN" } } });
          }}><option value="">Choose property</option>{(state.catalog[0]?.properties ?? []).filter((item) => !(item.id in selectedSession.properties)).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        </div>}
        <button type="button" onClick={() => { setShowProperties(!showProperties); }}>View properties</button>
        {showProperties ? <table><caption>Original material properties; no qualification implied</caption><thead><tr><th>Property</th><th>Symbol</th><th>Original value</th><th>Unit</th><th>Basis</th></tr></thead><tbody>{displayedProperties.map((item) => <tr key={item.id}><th>{item.label}</th><td>{item.symbol}</td><td>{selectedSession === undefined ? item.original : <input aria-label={`${item.label} value`} value={item.original} onChange={(event) => {
          const changed: MAT1SessionProperty = { label: item.label, symbol: item.symbol, value: event.currentTarget.value, unit: item.unit, basis: item.basis };
          editMAT1Session(selectedSession.id, { properties: { ...selectedSession.properties, [item.id]: changed } });
        }} />}</td><td>{item.unit}</td><td>{selectedSession === undefined ? item.basis : <select aria-label={`${item.label} source basis`} value={item.basis} onChange={(event) => {
          const changed: MAT1SessionProperty = { label: item.label, symbol: item.symbol, value: item.original, unit: item.unit, basis: event.currentTarget.value };
          editMAT1Session(selectedSession.id, { properties: { ...selectedSession.properties, [item.id]: changed } });
        }}><option value="UNKNOWN">Unknown</option><option value="NOMINAL_AS_SUPPLIED">Nominal as supplied</option><option value="BASIS_UNSPECIFIED">Basis unspecified</option><option value="MEAN">Mean</option><option value="CHARACTERISTIC">Characteristic</option><option value="ALLOWABLE">Allowable</option><option value="ALREADY_ADJUSTED">Already adjusted</option></select>}</td></tr>)}</tbody></table> : null}
        <details open={showConditions} onToggle={(event) => { setShowConditions(event.currentTarget.open); }}><summary>Design Conditions</summary>
          <label>Sustained material temperature <input value={state.conditions.sustained_temperature.value} onChange={(event) => {
            const value = event.currentTarget.value;
            updateConditions({ sustained_temperature: { ...state.conditions.sustained_temperature, value }, maximum_temperature: state.conditions.maximum_temperature.value === state.conditions.sustained_temperature.value ? { ...state.conditions.maximum_temperature, value } : state.conditions.maximum_temperature });
          }} /></label>
          <label>Temperature unit <select value={state.conditions.sustained_temperature.unit} onChange={(event) => { const unit = event.currentTarget.value as "degF" | "degC"; updateConditions({ sustained_temperature: { value: "", unit }, maximum_temperature: { value: "", unit }, glass_transition_temperature: null }); setMessage("Re-enter temperatures in the selected unit."); }}><option value="degF">°F</option><option value="degC">°C</option></select></label>
          <label>Maximum material temperature <input value={state.conditions.maximum_temperature.value} onChange={(event) => { updateConditions({ maximum_temperature: { ...state.conditions.maximum_temperature, value: event.currentTarget.value } }); }} /></label>
          <label>Glass transition temperature (Tg; optional evidence) <input value={state.conditions.glass_transition_temperature?.value ?? ""} onChange={(event) => { updateConditions({ glass_transition_temperature: event.currentTarget.value === "" ? null : { value: event.currentTarget.value, unit: state.conditions.sustained_temperature.unit } }); }} /></label>
          <label>Moisture <select value={state.conditions.moisture} onChange={(event) => { updateConditions({ moisture: event.currentTarget.value as MAT1Conditions["moisture"] }); }}><option value="UNKNOWN">Unknown</option><option value="REFERENCE">Reference condition</option><option value="SUSTAINED_MOISTURE">Sustained moisture</option><option value="OTHER">Other documented condition</option></select></label>
          <label>Chemical exposure <select value={state.conditions.chemical} onChange={(event) => { updateConditions({ chemical: event.currentTarget.value as MAT1Conditions["chemical"] }); }}><option value="UNKNOWN">Unknown</option><option value="NONE_DECLARED">None declared</option><option value="SPECIFIED">Specified — source required</option></select></label>
          <label>Load case name <input value={state.conditions.load_case_name} onChange={(event) => { updateConditions({ load_case_name: event.currentTarget.value }); }} /></label>
          <label>Time effect category <select value={state.conditions.time_effect_category} onChange={(event) => { updateConditions({ time_effect_category: event.currentTarget.value }); }}><option value="">Select category</option><option value="DEAD_ONLY">Dead only</option><option value="IMPACT">Impact</option><option value="STORAGE">Storage</option><option value="LONG_TERM_OPERATING">Long-term operating</option><option value="OTHER_LIVE">Other live</option><option value="SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE">Snow / rain / flood / atmospheric ice</option><option value="WIND_TORNADO_SEISMIC">Wind / tornado / seismic</option></select></label>
          <label>Source reference condition <select value={state.conditions.source_reference_condition} onChange={(event) => { updateConditions({ source_reference_condition: event.currentTarget.value as MAT1Conditions["source_reference_condition"] }); }}><option value="UNKNOWN">Unknown</option><option value="REFERENCE">Reference</option><option value="ALREADY_ADJUSTED">Already adjusted</option></select></label>
          {state.conditions.chemical === "SPECIFIED" ? <div className="mat1-chemical-details">
            <label>Substance <input value={state.conditions.chemical_substance} onChange={(event) => { updateConditions({ chemical_substance: event.currentTarget.value }); }} /></label>
            <label>Concentration <input value={state.conditions.chemical_concentration} onChange={(event) => { updateConditions({ chemical_concentration: event.currentTarget.value }); }} /></label>
            <label>Contact form <input value={state.conditions.chemical_contact_form} onChange={(event) => { updateConditions({ chemical_contact_form: event.currentTarget.value }); }} /></label>
            <label>Duration <input value={state.conditions.chemical_duration} onChange={(event) => { updateConditions({ chemical_duration: event.currentTarget.value }); }} /></label>
          </div> : null}
          <label>UV / weathering <select value={state.conditions.uv_weathering} onChange={(event) => { updateConditions({ uv_weathering: event.currentTarget.value as MAT1Conditions["uv_weathering"] }); }}><option value="UNKNOWN">Unknown</option><option value="NONE_DECLARED">None declared</option><option value="SPECIFIED">Specified — source required</option></select></label>
          <label>Freeze–thaw <select value={state.conditions.freeze_thaw} onChange={(event) => { updateConditions({ freeze_thaw: event.currentTarget.value as MAT1Conditions["freeze_thaw"] }); }}><option value="UNKNOWN">Unknown</option><option value="NONE_DECLARED">None declared</option><option value="SPECIFIED">Specified — source required</option></select></label>
          <label>Protective measures <input value={state.conditions.protective_measures} onChange={(event) => { updateConditions({ protective_measures: event.currentTarget.value }); }} /></label>
          <label>Exposure notes <textarea value={state.conditions.exposure_notes} onChange={(event) => { updateConditions({ exposure_notes: event.currentTarget.value }); }} /></label>
          <label>Action provenance <input value={state.conditions.action_provenance} onChange={(event) => { updateConditions({ action_provenance: event.currentTarget.value }); }} /></label>
          <label>Live-load subtype <input value={state.conditions.live_load_subtype} onChange={(event) => { updateConditions({ live_load_subtype: event.currentTarget.value }); }} /></label>
          <label>Full-amplitude operating duration <input value={state.conditions.full_amplitude_duration} onChange={(event) => { updateConditions({ full_amplitude_duration: event.currentTarget.value }); }} /></label>
          <label>Design period <input value={state.conditions.design_period} onChange={(event) => { updateConditions({ design_period: event.currentTarget.value }); }} /></label>
          <label>Service period <input value={state.conditions.service_period} onChange={(event) => { updateConditions({ service_period: event.currentTarget.value }); }} /></label>
          <label>Fatigue cycles <input value={state.conditions.fatigue_cycles} onChange={(event) => { updateConditions({ fatigue_cycles: event.currentTarget.value }); }} /></label>
          <p>Exposure, fatigue and service-period entries are recorded only until an applicable source-bound check evaluates them.</p>
        </details>
        <section aria-label="Physical FRP component assignments">
          <h4>FRP component assignments</h4>
          {owners.length === 0 ? <p>Canonical physical owners load from the backend preview. Until then all FRP owners use the connection default.</p> : null}
          {linkedFamilies.has(family) ? <p>Linked-material method: the existing native interface assumes the same material and conditions for its FRP layers. Change the connection default for this group; independent overrides require a different qualified method.</p> : null}
          {owners.map((owner) => {
            const override = state.conditionOverrides[family]?.[owner];
            const effective = override ?? state.conditions;
            return <div key={owner} className="mat1-owner-assignment">
              <label>{owner}<select disabled={linkedFamilies.has(family)} value={state.overrides[family]?.[owner] === null ? "__UNASSIGNED" : state.overrides[family]?.[owner] ?? ""} onChange={(event) => { const value = event.currentTarget.value; setMAT1Override(family, owner, value === "" ? undefined : value === "__UNASSIGNED" ? null : value); }}><option value="">Uses connection default</option><option value="__UNASSIGNED">Unassigned — design unavailable</option>{state.catalog.map((item) => <option value={item.id} key={item.id}>{item.display_name}</option>)}{Object.values(state.custom).map((item) => <option value={item.id} key={item.id}>{item.display_name}</option>)}</select></label>
              {!linkedFamilies.has(family) ? <details><summary>{override === undefined ? "Use connection design conditions" : "Component condition override"}</summary>
                <label><input type="checkbox" checked={override !== undefined} onChange={(event) => { setMAT1ConditionOverride(family, owner, event.currentTarget.checked ? state.conditions : null); }} /> Override conditions for {owner}</label>
                {override === undefined ? null : <div>
                  <label>Sustained material temperature ({effective.sustained_temperature.unit}) <input value={effective.sustained_temperature.value} onChange={(event) => { updateOwnerConditions(owner, effective, { sustained_temperature: { ...effective.sustained_temperature, value: event.currentTarget.value } }); }} /></label>
                  <label>Maximum material temperature ({effective.maximum_temperature.unit}) <input value={effective.maximum_temperature.value} onChange={(event) => { updateOwnerConditions(owner, effective, { maximum_temperature: { ...effective.maximum_temperature, value: event.currentTarget.value } }); }} /></label>
                  <label>Moisture <select value={effective.moisture} onChange={(event) => { updateOwnerConditions(owner, effective, { moisture: event.currentTarget.value as MAT1Conditions["moisture"] }); }}><option value="UNKNOWN">Unknown</option><option value="REFERENCE">Reference</option><option value="SUSTAINED_MOISTURE">Sustained moisture</option><option value="OTHER">Other</option></select></label>
                  <label>Chemical exposure <select value={effective.chemical} onChange={(event) => { updateOwnerConditions(owner, effective, { chemical: event.currentTarget.value as MAT1Conditions["chemical"] }); }}><option value="UNKNOWN">Unknown</option><option value="NONE_DECLARED">None declared</option><option value="SPECIFIED">Specified</option></select></label>
                  <label>Source reference condition <select value={effective.source_reference_condition} onChange={(event) => { updateOwnerConditions(owner, effective, { source_reference_condition: event.currentTarget.value as MAT1Conditions["source_reference_condition"] }); }}><option value="UNKNOWN">Unknown</option><option value="REFERENCE">Reference</option><option value="ALREADY_ADJUSTED">Already adjusted</option></select></label>
                </div>}
              </details> : null}
            </div>;
          })}
          <p>Compatible FRP targets: {owners.join(", ") || "pending preview"}</p>
          <button type="button" disabled={selected === undefined || owners.length === 0} onClick={selected === undefined ? undefined : () => { applyMAT1ToOwners(family, owners, selected.id); }}>Apply selected material to compatible FRP components</button>
        </section>
        <button type="button" onClick={() => { void inspectFactors(); }}>Inspect factor candidates</button>
        <button type="button" onClick={() => { setShowAdjustments(!showAdjustments); }}>Material adjustment trace</button>
        {showAdjustments ? <div className="mat1-adjustments"><p>{current ? `Design status: ${trace?.overall_status ?? "SOURCE_REQUIRED"}` : "Design result stale or not run."}</p><p>Computed candidates are diagnostic until source and applicability gates are resolved.</p><pre>{JSON.stringify(current ? ledgers : candidate, null, 2)}</pre></div> : null}
      </> : null}
      {message === "" ? null : <p role="status">{message}</p>}
    </details>
  </section>;
}

function completeConditions(value: MAT1Conditions): boolean {
  return value.sustained_temperature.value !== "" && value.maximum_temperature.value !== ""
    && value.load_case_name.trim() !== "" && value.time_effect_category !== "";
}
