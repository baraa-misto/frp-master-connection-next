import { useEffect, useState } from "react";
import { inspectMAT1Factors, loadMAT1Owners } from "../api/mat1Service";
import { workspaceCapability } from "../domain/workspaceCapabilities";
import { materialConditionIssues } from "./materialConditionValidation";

import {
  applyMAT1ToOwners,
  clearMAT1Sessions,
  createMAT1Session,
  deleteMAT1Session,
  editMAT1Session,
  mat1FamilyKey,
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
const convertTemperature = (value: string, unit: "degF" | "degC"): string => {
  if (value.trim() === "") return "";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return value;
  return String(Number((unit === "degC" ? (parsed - 32) * 5 / 9 : parsed * 9 / 5 + 32).toFixed(6)));
};
const loadClassifications = [
  ["DEAD_ONLY", "Dead load only", ""],
  ["IMPACT", "Live — impact", "IMPACT"],
  ["STORAGE", "Live — storage", "STORAGE"],
  ["LONG_TERM_OPERATING", "Live — long-term operating", "LONG_TERM_OPERATING"],
  ["OTHER_LIVE", "Live — other", "OTHER_LIVE"],
  ["SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE", "Snow, rain, flood, or atmospheric ice", ""],
  ["WIND_TORNADO_SEISMIC", "Wind, tornado, or seismic", ""],
] as const;
export function MAT1MaterialsPanel({ family }: { readonly family: string }) {
  const state = useMAT1();
  const linkedMaterial = workspaceCapability(family)?.material_assignment_mode === "LINKED";
  const [feedback, setFeedback] = useState<{ key: string; text: string } | null>(null);
  const [showProperties, setShowProperties] = useState(false);
  const [showConditions, setShowConditions] = useState(true);
  const [showAdjustments, setShowAdjustments] = useState(false);
  const [candidate, setCandidate] = useState<unknown>(null);

  const previewInput = state.previewInputs[family];
  const feedbackKey = `${mat1FamilyKey(family)}:${previewInput ?? ""}`;
  const setMessage = (text: string): void => { setFeedback({ key: `${mat1FamilyKey(family)}:${previewInput ?? ""}`, text }); };
  useEffect(() => {
    if (!state.active || previewInput === undefined || state.previewOwnerKeys[family] === previewInput) return;
    const controller = new AbortController();
    const ownerFeedbackKey = `${mat1FamilyKey(family)}:${previewInput}`;
    void loadMAT1Owners(family, JSON.parse(previewInput) as unknown, controller.signal).then((owners) => {
      if (controller.signal.aborted) return;
      setMAT1PreviewOwners(family, previewInput, owners);
      setFeedback(null);
    }).catch((error: unknown) => { if (!controller.signal.aborted) setFeedback({ key: ownerFeedbackKey, text: String(error) }); });
    return () => { controller.abort(); };
  }, [family, previewInput, state.active, state.previewOwnerKeys]);

  const selectedCatalog = state.catalog.find((item) => item.id === state.defaultId);
  const selectedSession = state.defaultId === null ? undefined : state.custom[state.defaultId];
  const selected = selectedCatalog ?? selectedSession;
  const trace = state.designTraces[family] as { material_ledgers?: Record<string, unknown>[]; overall_status?: string; material_sources?: { temperature_applicability?: { default: string; tg_evidence: string } } } | undefined;
  const owners = Array.from(new Set([
    ...(state.previewOwners[family] ?? []),
    ...Object.keys(state.overrides[family] ?? {}),
    ...(trace?.material_ledgers ?? []).map((item) => item.component_id).filter((item): item is string => typeof item === "string"),
  ])).sort();
  const current = state.designKeys[family] === mat1FamilyKey(family);
  const thermal = current ? trace?.material_sources?.temperature_applicability : undefined;
  const message = feedback?.key === feedbackKey && !(current && trace !== undefined && feedback.text.startsWith("Error:")) ? feedback.text : "";
  const inputIssues = materialConditionIssues(state.conditions);
  const ledgers = current ? trace?.material_ledgers ?? [] : [];
  const diagnosticOnly = ledgers.some((ledger) => typeof ledger.property_id === "string" && ledger.property_id.includes("strength") && ledger.adjusted_candidate === null);
  const factorRows = Array.from(new Map(ledgers.map((ledger) => {
    const property = typeof ledger.property_id === "string" ? ledger.property_id : "Property";
    const role = property.includes("modulus") ? "Modulus" : property.includes("strength") ? "Strength" : readable(property);
    const key = [role, ledger.cm, ledger.ct, ledger.cch, ledger.lambda_factor].join(":");
    return [key, { role, cm: ledger.cm, ct: ledger.ct, cch: ledger.cch, lambda: role === "Modulus" ? "Not applicable to modulus" : ledger.lambda_factor }] as const;
  })).values());
  const factorText = (value: unknown): string =>
    typeof value === "string" || typeof value === "number" || typeof value === "boolean"
      ? String(value)
      : "Source required";
  const displayedProperties: readonly MAT1Property[] = selectedCatalog?.properties
    ?? Object.entries(selectedSession?.properties ?? {}).map(([id, property]) => ({
      id, label: property.label, symbol: property.symbol, original: property.value,
      unit: property.unit, basis: property.basis,
    }));

  function updateConditions(changes: Partial<MAT1Conditions>): void {
    setMessage("");
    setMAT1Conditions({ ...state.conditions, ...changes });
  }

  function updateOwnerConditions(owner: string, base: MAT1Conditions, changes: Partial<MAT1Conditions>): void {
    setMAT1ConditionOverride(family, owner, { ...base, ...changes });
  }

  async function inspectFactors(): Promise<void> {
    if (selected === undefined || !completeConditions(state.conditions) || displayedProperties.length === 0) {
      setMessage(state.conditions.load_case_name.trim() === "" ? "Enter a load-case name before viewing calculated factors." : "Select a material, complete the project conditions, and enter at least one property before viewing calculated factors.");
      return;
    }
    const material = "kind" in selected ? selected : {
      kind: "CATALOG" as const, id: selected.id, revision: selected.revision,
      content_digest: selected.content_digest,
    };
    const factorFeedbackKey = feedbackKey;
    try {
      const body = await inspectMAT1Factors({
        material, conditions: state.conditions,
        component_id: family, property_ids: displayedProperties.map((item) => item.id),
      }, new AbortController().signal);
      setCandidate(body);
      setShowAdjustments(true);
      setFeedback({ key: factorFeedbackKey, text: "Numerical candidates only; source and qualification gates remain open." });
    } catch (error) { setFeedback({ key: factorFeedbackKey, text: String(error) }); }
  }

  return <section className="mat1-material-panel" aria-label="FRP Materials and Design Conditions">
    <details open>
      <summary>Materials and project conditions <small>{selected?.display_name ?? "Material unavailable"}</small></summary>
      <p>Predefined values are read-only owner-supplied data. Session materials disappear on reload, tab close, or Clear session materials.</p>
      <p>Selected material: <strong>{selected?.company ?? "Unavailable"} · {selected === undefined ? "Unknown resin" : readable(selected.resin)}</strong>. Select a documented material and enter actual service conditions before checking.</p>
      {state.catalogError === null ? null : <p role="alert">{state.catalogError}</p>}
      {state.active ? <>
        <label>Connection default material <select value={state.defaultId ?? ""} onChange={(event) => { setMAT1Default(event.currentTarget.value || null); setCandidate(null); }}>
          <option value="">Unassigned — design unavailable</option>
          {state.catalog.map((record) => <option key={record.id} value={record.id}>{record.company} · {readable(record.resin)} · {record.revision}</option>)}
          {Object.values(state.custom).map((record) => <option key={record.id} value={record.id}>Session · {record.display_name} · revision {record.revision}</option>)}
        </select></label>
        {selected === undefined ? null : <>
          <p>Property basis: <strong>{selectedCatalog?.property_basis ?? (selectedCatalog === undefined ? "USER_DEFINED" : "DEVELOPMENT_NOMINAL")}</strong>. Catalog selection binds the stored design properties; it does not change their source basis.</p>
          {selectedCatalog !== undefined && (selectedCatalog.property_basis === undefined || selectedCatalog.property_basis === "DEVELOPMENT_NOMINAL") ? <p>Material basis needed: the current ICE seed has nominal development values. A controlled product/revision, characteristic statistical basis and reference conditioning are needed for approved design properties.</p> : null}
          <section className="information-status" aria-label="Specification / procurement notes"><h4>Specification / procurement notes</h4><p>Design material: {selected.display_name} / {selected.revision}. Project material shall conform to this selected specification. Per-connection supplier proof is not required by this workflow.</p></section>
        </>}
        <div className="benchmark-actions">
          <button type="button" onClick={() => { const id = createMAT1Session(); setMAT1Default(id); setShowProperties(true); }}>New session material</button>
          <button type="button" disabled={selected === undefined} onClick={selected === undefined ? undefined : () => { const id = createMAT1Session(selected); setMAT1Default(id); setShowProperties(true); }}>Copy as session material</button>
          <details><summary>Advanced Engineering Diagnostics · session management</summary><button type="button" onClick={() => { clearMAT1Sessions(); setMessage("Session materials cleared. Affected assignments are unassigned and stale."); }}>Clear session materials</button>
          {Object.values(state.custom).map((item) => <button key={item.id} type="button" onClick={() => { setMessage(deleteMAT1Session(item.id) ? "Session material deleted." : "Reassign components before deleting this material."); }}>Delete {item.display_name}</button>)}</details>
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
        <details open={showConditions} onToggle={(event) => { setShowConditions(event.currentTarget.open); }}><summary>Project conditions and load case</summary>
          <label>Sustained operating material temperature <input aria-label="Sustained operating material temperature" aria-invalid={inputIssues.sustained_temperature !== undefined} value={state.conditions.sustained_temperature.value} onChange={(event) => {
            const value = event.currentTarget.value;
            updateConditions({ sustained_temperature: { ...state.conditions.sustained_temperature, value }, maximum_temperature: state.conditions.maximum_temperature.value === state.conditions.sustained_temperature.value ? { ...state.conditions.maximum_temperature, value } : state.conditions.maximum_temperature });
          }} /></label>
          <label>Temperature unit <select value={state.conditions.sustained_temperature.unit} onChange={(event) => { const unit = event.currentTarget.value as "degF" | "degC"; updateConditions({ sustained_temperature: { value: convertTemperature(state.conditions.sustained_temperature.value, unit), unit }, maximum_temperature: { value: convertTemperature(state.conditions.maximum_temperature.value, unit), unit }, glass_transition_temperature: state.conditions.glass_transition_temperature === null ? null : { value: convertTemperature(state.conditions.glass_transition_temperature.value, unit), unit } }); }}><option value="degF">°F</option><option value="degC">°C</option></select></label>
          <label>Maximum expected material temperature <input aria-label="Maximum expected material temperature" aria-invalid={inputIssues.maximum_temperature !== undefined} value={state.conditions.maximum_temperature.value} onChange={(event) => { updateConditions({ maximum_temperature: { ...state.conditions.maximum_temperature, value: event.currentTarget.value } }); }} /></label>
          <p>Sustained temperature is used for temperature adjustment of design properties where applicable. Maximum expected temperature is used to check material temperature applicability, including Tg limits.</p>
          <p aria-label="Tg applicability"><strong>Tg applicability: {thermal?.default.replaceAll("_", " ") ?? "NOT CONFIRMED"}</strong>{thermal?.tg_evidence === "USER_SUPPLIED" ? " — numerical comparison on entered Tg; controlled product evidence is still required." : " — TEMPERATURE APPLICABILITY NOT CONFIRMED. Glass-transition-temperature data are not available for this material record. Supported calculations may run, but maximum-temperature applicability cannot be confirmed."}</p>
          <label>Moisture <select value={state.conditions.moisture} onChange={(event) => { updateConditions({ moisture: event.currentTarget.value as MAT1Conditions["moisture"] }); }}><option value="UNKNOWN">Unknown</option><option value="REFERENCE">Reference condition</option><option value="SUSTAINED_MOISTURE">Sustained moisture</option><option value="OTHER">Other documented condition</option></select></label>
          <label>Chemical exposure <select value={state.conditions.chemical} onChange={(event) => { updateConditions({ chemical: event.currentTarget.value as MAT1Conditions["chemical"] }); }}><option value="UNKNOWN">Unknown</option><option value="NONE_DECLARED">None declared</option><option value="SPECIFIED">Specified — source required</option></select></label>
          <label>Load case name (required) <input required aria-invalid={state.conditions.load_case_name.trim() === ""} value={state.conditions.load_case_name} onChange={(event) => { updateConditions({ load_case_name: event.currentTarget.value }); }} /></label>
          {state.conditions.load_case_name.trim() === "" ? <p role="alert">Enter a load-case name before running Design Check or viewing calculated factors.</p> : null}
          <label>Load present in this submitted combination <select value={state.conditions.time_effect_category} onChange={(event) => { const category = event.currentTarget.value; const selectedClass = loadClassifications.find(([id]) => id === category); updateConditions({ time_effect_category: category, live_load_subtype: selectedClass?.[2] ?? "" }); }}><option value="">Select the load classification</option>{loadClassifications.map(([id, label]) => <option value={id} key={id}>{label}</option>)}</select></label>
          {state.conditions.time_effect_category === "LONG_TERM_OPERATING" ? <label>Full nominal operating amplitude <select value={state.conditions.full_amplitude_duration} onChange={(event) => { updateConditions({ full_amplitude_duration: event.currentTarget.value }); }}><option value="">Select documented duration</option><option value="MORE_THAN_ONE_YEAR">More than one year</option><option value="ONE_YEAR_OR_LESS">One year or less — choose another live classification</option></select></label> : null}
          {Object.keys(inputIssues).length === 0 ? null : <section aria-label="INPUTS NEEDED"><strong>INPUTS NEEDED</strong><ul>{Object.entries(inputIssues).map(([field, text]) => <li key={field}>{text}</li>)}</ul></section>}<p>Enter one already-factored member-end load combination at a time. This selection determines its time-effect factor; the app does not generate building loads or combine nominal cases.</p>
          <details><summary>Advanced material source evidence and exposure notes</summary>
          <label>Source reference condition <select value={state.conditions.source_reference_condition} onChange={(event) => { updateConditions({ source_reference_condition: event.currentTarget.value as MAT1Conditions["source_reference_condition"] }); }}><option value="UNKNOWN">Unknown</option><option value="REFERENCE">Documented reference condition</option><option value="ALREADY_ADJUSTED">Documented already adjusted</option></select></label>
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
          <label>Design period <input value={state.conditions.design_period} onChange={(event) => { updateConditions({ design_period: event.currentTarget.value }); }} /></label>
          <label>Service period <input value={state.conditions.service_period} onChange={(event) => { updateConditions({ service_period: event.currentTarget.value }); }} /></label>
          <label>Fatigue cycles <input value={state.conditions.fatigue_cycles} onChange={(event) => { updateConditions({ fatigue_cycles: event.currentTarget.value }); }} /></label>
          <p>Exposure, fatigue and service-period entries are recorded only until an applicable source-bound check evaluates them.</p>
          </details>
        </details>
        <section aria-label="Calculated factors and design basis">
          <h4>Calculated factors / Design basis</h4>
          {factorRows.length === 0 ? <p>Run Design Check to see the backend factors for the selected material and this load combination.</p>
            : <><p>Read-only factors from the last current calculation. The time factor applies to strength checks in this submitted load combination.</p>
              <div className="table-scroll"><table><thead><tr><th>Property role</th><th>Moisture C<sub>M</sub></th><th>Temperature C<sub>T</sub></th><th>Chemical C<sub>CH</sub></th><th>Time λ</th></tr></thead><tbody>{factorRows.map((row) => <tr key={[row.role, row.cm, row.ct, row.cch, row.lambda].join(":")}><th>{row.role}</th><td>{factorText(row.cm)}</td><td>{factorText(row.ct)}</td><td>{factorText(row.cch)}</td><td>{factorText(row.lambda)}</td></tr>)}</tbody></table></div>
              {diagnosticOnly ? <p role="status"><strong>Diagnostic only — adjusted resistance unavailable.</strong> Unresolved exposure factors retain original declared values only for partial numerical diagnostics. Final GREEN is unavailable.</p> : null}<p>Numerical factors do not establish the source or qualification of the selected material.</p></>}
        </section>
        {linkedMaterial ? <p>Selected FRP material applies to the angle brace and supporting W member.</p> : null}
        <details><summary>Advanced Engineering Diagnostics · FRP component assignments and factor trace</summary><section aria-label="Physical FRP component assignments">
          <h4>FRP component assignments</h4>
          {owners.length === 0 ? <p>Canonical physical owners load from the backend preview. Until then all FRP owners use the connection default.</p> : null}
          {linkedMaterial ? <p>Linked-material method: the existing native interface assumes the same material and conditions for its FRP layers. Change the connection default for this group; independent overrides require a different qualified method.</p> : null}
          {owners.map((owner) => {
            const override = state.conditionOverrides[family]?.[owner];
            const effective = override ?? state.conditions;
            return <div key={owner} className="mat1-owner-assignment">
              <label>{owner}<select disabled={linkedMaterial} value={state.overrides[family]?.[owner] === null ? "__UNASSIGNED" : state.overrides[family]?.[owner] ?? ""} onChange={(event) => { const value = event.currentTarget.value; setMAT1Override(family, owner, value === "" ? undefined : value === "__UNASSIGNED" ? null : value); }}><option value="">Uses connection default</option><option value="__UNASSIGNED">Unassigned — design unavailable</option>{state.catalog.map((item) => <option value={item.id} key={item.id}>{item.display_name}</option>)}{Object.values(state.custom).map((item) => <option value={item.id} key={item.id}>{item.display_name}</option>)}</select></label>
              {!linkedMaterial ? <details><summary>{override === undefined ? "Use connection design conditions" : "Component condition override"}</summary>
                <label><input type="checkbox" checked={override !== undefined} onChange={(event) => { setMAT1ConditionOverride(family, owner, event.currentTarget.checked ? state.conditions : null); }} /> Override conditions for {owner}</label>
                {override === undefined ? null : <div>
                  <label>Sustained operating material temperature ({effective.sustained_temperature.unit}) <input value={effective.sustained_temperature.value} onChange={(event) => { updateOwnerConditions(owner, effective, { sustained_temperature: { ...effective.sustained_temperature, value: event.currentTarget.value } }); }} /></label>
                  <label>Maximum expected material temperature ({effective.maximum_temperature.unit}) <input value={effective.maximum_temperature.value} onChange={(event) => { updateOwnerConditions(owner, effective, { maximum_temperature: { ...effective.maximum_temperature, value: event.currentTarget.value } }); }} /></label>
                  <label>Moisture <select value={effective.moisture} onChange={(event) => { updateOwnerConditions(owner, effective, { moisture: event.currentTarget.value as MAT1Conditions["moisture"] }); }}><option value="UNKNOWN">Unknown</option><option value="REFERENCE">Reference</option><option value="SUSTAINED_MOISTURE">Sustained moisture</option><option value="OTHER">Other</option></select></label>
                  <label>Chemical exposure <select value={effective.chemical} onChange={(event) => { updateOwnerConditions(owner, effective, { chemical: event.currentTarget.value as MAT1Conditions["chemical"] }); }}><option value="UNKNOWN">Unknown</option><option value="NONE_DECLARED">None declared</option><option value="SPECIFIED">Specified</option></select></label>
                  <label>Source reference condition <select value={effective.source_reference_condition} onChange={(event) => { updateOwnerConditions(owner, effective, { source_reference_condition: event.currentTarget.value as MAT1Conditions["source_reference_condition"] }); }}><option value="UNKNOWN">Unknown</option><option value="REFERENCE">Reference</option><option value="ALREADY_ADJUSTED">Already adjusted</option></select></label>
                </div>}
              </details> : null}
            </div>;
          })}
          <p>Compatible FRP targets: {owners.join(", ") || "pending preview"}</p>
          {linkedMaterial ? null : <button type="button" disabled={selected === undefined || owners.length === 0} onClick={selected === undefined ? undefined : () => { applyMAT1ToOwners(family, owners, selected.id); }}>Apply selected material to compatible FRP components</button>}
        </section>
        <button type="button" onClick={() => { void inspectFactors(); }}>View calculated factors</button>
        <button type="button" onClick={() => { setShowAdjustments(!showAdjustments); }}>Material adjustment trace</button>
        {showAdjustments ? <div className="mat1-adjustments"><p>{current ? `Design status: ${trace?.overall_status ?? "SOURCE_REQUIRED"}` : "Design result stale or not run."}</p><p>Computed candidates are diagnostic until source and applicability gates are resolved.</p><pre>{JSON.stringify(current ? ledgers : candidate, null, 2)}</pre></div> : null}</details>
      </> : null}
      {message === "" ? null : <p role="status">{message}</p>}
    </details>
  </section>;
}

function completeConditions(value: MAT1Conditions): boolean {
  return Object.keys(materialConditionIssues(value)).length === 0;
}
