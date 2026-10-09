import { useEffect, useState, type ReactNode } from "react";
import {
  ASCE_SHAPE_BASIS, mat1DefaultId, setMAT1DirectConditions, setMAT1DirectMaterial, useMAT1,
  type MAT1Conditions,
} from "../state/mat1Session";
import { ASCEShapeBasisSummary } from "./ASCEShapeBasisSummary";
import { adoptDirectConditions, DIRECT_LOAD_CLASSIFICATIONS, updateDirectTemperature } from "./directMaterialConditions";
import { materialConditionIssues } from "./materialConditionValidation";

function Help({ label, children }: { readonly label: string; readonly children: ReactNode }) {
  return <details className="mc1-help"><summary aria-label={`Help: ${label}`}>?</summary><p>{children}</p></details>;
}

export function DirectMaterialsPanel({ children }: { readonly children: ReactNode }) {
  const state = useMAT1();
  const adoption = adoptDirectConditions(state.conditions).adoption;
  const [displayUnit, setDisplayUnit] = useState<"degF" | "degC">(state.conditions.sustained_temperature.unit);
  useEffect(() => {
    if (state.directConditions !== null) return;
    const adopted = adoptDirectConditions(state.conditions);
    setMAT1DirectConditions(adopted.conditions);
  }, [state.conditions, state.directConditions]);
  const conditions = state.directConditions ?? state.conditions;
  const temperature = conditions.design_temperature ?? conditions.sustained_temperature;
  const displayedTemperature = temperature.unit === displayUnit || temperature.value.trim() === ""
    ? temperature.value
    : String(Number((displayUnit === "degC" ? (Number(temperature.value) - 32) * 5 / 9 : Number(temperature.value) * 9 / 5 + 32).toFixed(6)));
  const selectedId = mat1DefaultId("multi-row");
  const record = state.catalog.find((item) => item.id === selectedId);
  const session = selectedId === null ? undefined : state.custom[selectedId];
  const selected = record ?? session;
  const issues = materialConditionIssues(conditions);
  const update = (changes: Partial<MAT1Conditions>): void => { setMAT1DirectConditions({ ...conditions, ...changes }); };
  return <section className="mat1-material-panel mc1-panel" aria-label="Direct Materials and Project Conditions">
    <h3>Materials and Project Conditions</h3>
    {state.catalogError === null ? null : <p role="alert">{state.catalogError}</p>}
    <h4>Environmental and Material Adjustment Conditions</h4>
    <div className="mc1-grid">
      <div><label>FRP material<select value={selectedId ?? ""} onChange={(event) => { setMAT1DirectMaterial(event.currentTarget.value || null); }}>
        <option value="">Choose FRP material</option>
        {state.catalog.filter((item) => item.property_basis === ASCE_SHAPE_BASIS).map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}
        {Object.values(state.custom).map((item) => <option key={item.id} value={item.id}>Session · {item.display_name}</option>)}
      </select></label><Help label="FRP material">ASCE minimum characteristic shape properties. Supplied material must conform to the selected specification. Selection does not qualify the complete connection.</Help></div>
      <div><label>Resin system<output>{selected === undefined ? "Choose FRP material" : selected.resin.replaceAll("_", " ").toLowerCase()}</output></label><Help label="Resin system">Resolved from the selected material record; temperature factors use this resin system.</Help></div>
      <div><label>Design Temperature<input inputMode="decimal" aria-invalid={issues.design_temperature !== undefined} value={displayedTemperature} onChange={(event) => { setMAT1DirectConditions(updateDirectTemperature(conditions, { value: event.currentTarget.value, unit: displayUnit })); }} /></label>
        <label className="mc1-unit">Temperature unit<select value={displayUnit} onChange={(event) => { setDisplayUnit(event.currentTarget.value as "degF" | "degC"); }}><option value="degF">°F</option><option value="degC">°C</option></select></label>
        <Help label="Design Temperature">Highest expected service temperature. Conservatively assumed sustained for resistance adjustment and used for required Tg. Above 140°F requires a test-based temperature factor. Unit switching changes only the display; the stored physical value is preserved until edited.</Help></div>
      <div><label>Moisture condition<select value={conditions.moisture === "REFERENCE" || conditions.moisture === "SUSTAINED_MOISTURE" ? conditions.moisture : ""} onChange={(event) => { update({ moisture: event.currentTarget.value as MAT1Conditions["moisture"] }); }}><option value="" disabled>Choose actual moisture</option><option value="REFERENCE">Dry</option><option value="SUSTAINED_MOISTURE">Sustained moisture</option></select></label><Help label="Moisture condition">Dry uses the reference condition. Sustained moisture applies the established moisture adjustments to strength and modulus. Unknown legacy conditions require an explicit selection.</Help></div>
      <div><label>Chemical environment<select value={conditions.chemical === "NONE_DECLARED" || conditions.chemical === "SPECIFIED" ? conditions.chemical : ""} onChange={(event) => {
        const { chemical_strength_factor: priorFactor, ...withoutFactor } = conditions;
        setMAT1DirectConditions(event.currentTarget.value === "NONE_DECLARED" ? { ...withoutFactor, chemical: "NONE_DECLARED" } : { ...conditions, chemical: "SPECIFIED", chemical_strength_factor: priorFactor ?? "" });
      }}><option value="" disabled>Choose chemical environment</option><option value="NONE_DECLARED">None</option><option value="SPECIFIED">Custom adjustment</option></select></label><Help label="Chemical environment">Custom C_CH is engineer-specified, dimensionless, greater than zero and at most 1.00; strength only. It is not certified chemical test evidence. Modulus chemical applicability remains unresolved; independent supported checks may proceed.</Help></div>
      {conditions.chemical === "SPECIFIED" ? <div><label>Chemical strength factor C_CH<input inputMode="decimal" aria-invalid={issues.chemical_strength_factor !== undefined} value={conditions.chemical_strength_factor ?? ""} onChange={(event) => { update({ chemical_strength_factor: event.currentTarget.value }); }} /></label><p>Strength only · chemical-modulus applicability unresolved.</p></div> : null}
    </div>
    <section className="mc1-load-classification" aria-label="Factored load classification">
      <h4>Load Combination Classification</h4>
      <div className="mc1-grid"><div className="mc1-wide"><label>Load Combination Classification<select value={conditions.time_effect_category} onChange={(event) => {
        const category = event.currentTarget.value;
        const selectedClass = DIRECT_LOAD_CLASSIFICATIONS.find(([id]) => id === category);
        update({ time_effect_category: category, live_load_subtype: selectedClass?.[2] ?? "",
          full_amplitude_duration: category === "LONG_TERM_OPERATING" ? "MORE_THAN_ONE_YEAR" : conditions.full_amplitude_duration });
      }}><option value="">Choose load classification</option>{DIRECT_LOAD_CLASSIFICATIONS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label><Help label="Load Combination Classification">Classify the loads present in this submitted factored combination. The time-effect factor λ adjusts resistance, not load. Dead only, impact, storage, long-term operating, other live, snow/rain/flood/ice, and wind/tornado/seismic retain their established factors. Long-term operating declares full operating amplitude for more than one year. Mixed loads require engineering classification; the app does not generate or combine loads.</Help></div></div>
    </section>
    {adoption === null ? null : <p role="status">{adoption}</p>}
    {Object.keys(issues).length === 0 ? null : <section aria-label="INPUTS NEEDED"><strong>Inputs needed</strong><ul>{Object.entries(issues).map(([key, value]) => <li key={key}>{value}</li>)}</ul></section>}
    {record?.property_basis === ASCE_SHAPE_BASIS ? <ASCEShapeBasisSummary record={record} conditions={conditions} compact /> : null}
    <details className="mc1-advanced"><summary>Advanced Material Details</summary>{children}</details>
  </section>;
}
