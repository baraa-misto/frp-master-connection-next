import type { DirectPhysicalInputs as PhysicalInputs, HybridCase, HybridInputs, HybridQuantity } from "../api/hybridWorkflow";

const ACTIONS = ["Additional LW force", "Additional CW force", "Additional TT force", "Additional LW moment", "Additional CW moment", "Additional TT moment"];

export function DirectPhysicalInputs({ value, onChange }: { readonly value: HybridInputs; readonly onChange: (next: HybridInputs) => void }) {
  const physical = value.physical_context;
  if (physical === undefined || value.geometry === null) return null;
  const unit = value.geometry.vertical_bolt_pitch.unit;
  const change = (next: PhysicalInputs) => { onChange({ ...value, physical_context: next }); };
  const quantity = (label: string, current: HybridQuantity | null, update: (q: HybridQuantity | null) => void) => <label className="field-control" key={label}><span>{label}</span><div className="hybrid-quantity"><input aria-label={label} inputMode="decimal" placeholder="Unknown" value={current?.value ?? ""} onChange={(e) => { update(e.currentTarget.value === "" ? null : { value: e.currentTarget.value, unit: current?.unit ?? unit }); }} /><span>{current?.unit ?? unit}</span></div></label>;
  return <fieldset><legend>Actual receiving member and contact</legend>
    <p>Receiving LW follows the member length; CW crosses the flange; TT follows the bolt stack. Distances below are measured from the common bolt-pair midpoint. A view crop is never an engineering end.</p>
    {(["positive_end", "negative_end"] as const).map((key) => {
      const label = key === "positive_end" ? "+LW receiving end" : "−LW receiving end";
      const end = physical[key];
      return <div key={key}><label className="field-control">{label}<select aria-label={label} value={end.condition} onChange={(e) => { change({ ...physical, [key]: { condition: e.currentTarget.value as typeof end.condition, distance: null } }); }}><option value="UNKNOWN">Unknown</option><option value="CONTINUOUS">Member continues (no free end)</option><option value="FREE">Actual free end</option></select></label>{end.condition === "FREE" ? quantity(label + " distance", end.distance, (distance) => { change({ ...physical, [key]: { ...end, distance } }); }) : null}</div>;
    })}
    {quantity("Clear flat receiving outstand (excluding root/fillet)", physical.clear_flat_outstand, (clear_flat_outstand) => { change({ ...physical, clear_flat_outstand }); })}
    {quantity("Actual interface gap", physical.interface_gap, (interface_gap) => { change({ ...physical, interface_gap }); })}
    <p>Clear flat outstand runs from the occupied flange free edge to the excluded root/fillet. Declare measured geometry; no nominal web or favorable fillet is assumed. Zero gap alone does not resolve secondary prying or bolt-axis transfer.</p>
    <label className="field-control">Original ASCE standard-hole unit column<select aria-label="Original ASCE standard-hole unit column" value={physical.hole_source ?? ""} onChange={(e) => { change({ ...physical, hole_source: e.currentTarget.value === "" ? null : e.currentTarget.value as PhysicalInputs["hole_source"] }); }}><option value="">Unknown</option><option value="US_CUSTOMARY_PRINTED">U.S. printed: bolt + 0.063 in</option><option value="SI_PRINTED">SI printed: bolt + 1.6 mm</option></select></label>
    <p>This source choice stays fixed when display units change; it never resizes the entered hole.</p>
    {value.lrfd_cases.map((load) => {
      const current = physical.receiving_actions.find((item) => item.case_id === load.case_id);
      const components: HybridCase["components"] = current?.components ?? [null, null, null, null, null, null];
      return <details key={load.case_id}><summary>Additional receiving-member actions — {load.case_id}</summary><p>Independent receiving/bypass actions in the receiving LW/CW/TT frame at the common midpoint, additional to the complementary connection action. Unknown is not zero. Nonzero bypass actions need a validated coupled model; independent supported checks remain available.</p>
        {components.map((q, index) => {
          const actionUnit = q?.unit ?? (unit === "mm" ? index < 3 ? "N" : "N-mm" : index < 3 ? "kip" : "kip-in");
          return <label className="field-control" key={ACTIONS[index]}>{ACTIONS[index]}<div className="hybrid-quantity"><input aria-label={load.case_id + " " + String(ACTIONS[index])} inputMode="decimal" placeholder="Unknown" value={q?.value ?? ""} onChange={(e) => {
            const next = [...components] as HybridCase["components"];
            next[index] = e.currentTarget.value === "" ? null : { value: e.currentTarget.value, unit: actionUnit };
            change({ ...physical, receiving_actions: [...physical.receiving_actions.filter((item) => item.case_id !== load.case_id), { case_id: load.case_id, components: next }] });
          }} /><span>{actionUnit}</span></div></label>;
        })}
      </details>;
    })}
  </fieldset>;
}
