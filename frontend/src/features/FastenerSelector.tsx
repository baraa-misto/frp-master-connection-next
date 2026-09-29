/** Shared versioned fastener editor. The selected record is session-only. */
import type { SingleBoltEvaluationRequest } from "../api/contracts";
import type { FastenerSelection } from "../state/mat1Session";
import { defaultFastenerSelection } from "../state/mat1Session";

type Snapshot = SingleBoltEvaluationRequest["fastener_snapshot"];

let nextSessionId = 0;

function createSessionFastener(defaultSnapshot: Snapshot, copy: boolean): FastenerSelection {
  nextSessionId += 1;
  const snapshot = structuredClone(defaultSnapshot);
  snapshot.id = `USER_FASTENER_${String(nextSessionId)}`;
  snapshot.locked = false;
  snapshot.display_name = copy ? "F593 copy — user-defined" : "User-defined fastener";
  snapshot.bolt_specification = copy ? defaultSnapshot.bolt_specification : "USER_DEFINED";
  snapshot.alloy_group = copy ? defaultSnapshot.alloy_group : "USER_DEFINED";
  snapshot.alloys = copy ? [...defaultSnapshot.alloys] : ["USER_DEFINED"];
  snapshot.condition = copy ? defaultSnapshot.condition : "USER_DEFINED";
  snapshot.nut_specification = copy ? defaultSnapshot.nut_specification : "USER_DEFINED";
  snapshot.washer_material_basis = copy ? defaultSnapshot.washer_material_basis : "USER_DEFINED";
  snapshot.installation_condition = copy ? defaultSnapshot.installation_condition : "USER_DEFINED";
  snapshot.fnt = null;
  snapshot.fnt_source_classification = "SOURCE_PENDING";
  snapshot.fnt_qualification_status = "SOURCE_PENDING";
  snapshot.source_notes = [copy
    ? "Copied geometry and identity fields from the F593 preset; no strength or qualification inherited."
    : "User-defined session fastener; source and qualification require review."];
  return {
    kind: "SESSION", contract: "FASTENER-OR1-RC1", revision: "1",
    source_label: "User-supplied session data", fnt_source_basis: "", snapshot,
  };
}

export function FastenerSelector({ defaultSnapshot, selection, onSelect }: {
  readonly defaultSnapshot: Snapshot;
  readonly selection: FastenerSelection;
  readonly onSelect: (selection: FastenerSelection) => void;
}) {
  const update = (current: Extract<FastenerSelection, { kind: "SESSION" }>, changes: Partial<Snapshot>, metadata: Partial<Extract<FastenerSelection, { kind: "SESSION" }>> = {}) => {
    onSelect({ ...current, ...metadata, revision: String(Number(current.revision) + 1),
      snapshot: { ...current.snapshot, ...changes } });
  };
  const custom = selection.kind === "SESSION" ? selection : null;
  return <section className="fastener-selection" aria-label="Selected fastener">
    <label>Fastener source <select value={selection.kind} onChange={(event) => {
      onSelect(event.currentTarget.value === "DEFAULT" ? defaultFastenerSelection : createSessionFastener(defaultSnapshot, false));
    }}><option value="DEFAULT">ASTM F593-17 Group 2 — 316/316L (Fnt source pending)</option><option value="SESSION">User-defined fastener</option></select></label>
    <div className="benchmark-actions"><button type="button" onClick={() => { onSelect(createSessionFastener(defaultSnapshot, true)); }}>Copy default as custom</button></div>
    {custom === null ? <p>ASTM F593 tensile-strength source is required for the selected alloy/condition. The matching F594 nut, washer basis, installation state and geometry remain recorded.</p> : <>
      <p>Custom Fnt enables numerical bolt checks only. It does not qualify this fastener as ASTM F593.</p>
      <div className="field-grid">
        <label>Fastener name <input value={custom.snapshot.display_name} onChange={(event) => { update(custom, { display_name: event.currentTarget.value }); }} /></label>
        <label>Source / manufacturer <input value={custom.source_label} onChange={(event) => { update(custom, {}, { source_label: event.currentTarget.value }); }} /></label>
        <label>Specification / grade <input value={custom.snapshot.bolt_specification} onChange={(event) => { update(custom, { bolt_specification: event.currentTarget.value }); }} /></label>
        <label>Alloy group <input value={custom.snapshot.alloy_group} onChange={(event) => { update(custom, { alloy_group: event.currentTarget.value }); }} /></label>
        <label>Alloy(s) <input value={custom.snapshot.alloys.join(", ")} onChange={(event) => { update(custom, { alloys: event.currentTarget.value.split(",").map((item) => item.trim()).filter(Boolean) }); }} /></label>
        <label>Condition <input value={custom.snapshot.condition} onChange={(event) => { update(custom, { condition: event.currentTarget.value }); }} /></label>
        <label>Diameter minimum ({custom.snapshot.diameter_min.unit}) <input inputMode="decimal" value={custom.snapshot.diameter_min.value} onChange={(event) => { update(custom, { diameter_min: { ...custom.snapshot.diameter_min, value: event.currentTarget.value } }); }} /></label>
        <label>Diameter maximum ({custom.snapshot.diameter_max.unit}) <input inputMode="decimal" value={custom.snapshot.diameter_max.value} onChange={(event) => { update(custom, { diameter_max: { ...custom.snapshot.diameter_max, value: event.currentTarget.value } }); }} /></label>
        <label>Fnt ({custom.snapshot.fnt?.unit ?? "ksi"}) <input inputMode="decimal" value={custom.snapshot.fnt?.value ?? ""} onChange={(event) => {
          const value = event.currentTarget.value;
          update(custom, { fnt: value === "" ? null : { value, unit: custom.snapshot.fnt?.unit ?? "ksi" },
            fnt_source_classification: value === "" ? "SOURCE_PENDING" : "USER_DEFINED",
            fnt_qualification_status: value === "" ? "SOURCE_PENDING" : "DEVELOPMENT_ONLY" });
        }} /></label>
        <label>Fnt source basis <input value={custom.fnt_source_basis} onChange={(event) => { update(custom, {}, { fnt_source_basis: event.currentTarget.value }); }} /></label>
        <label>Shear-plane threads <select value={custom.snapshot.shear_plane_thread_statuses[0]?.status ?? "EXCLUDED"} onChange={(event) => { update(custom, { shear_plane_thread_statuses: [{ location_id: "SHEAR_PLANE_1", status: event.currentTarget.value }], number_of_shear_planes: 1 }); }}><option value="EXCLUDED">Excluded</option><option value="INCLUDED">Included</option><option value="UNKNOWN">Unknown</option></select></label>
        <label>Nut specification <input value={custom.snapshot.nut_specification} onChange={(event) => { update(custom, { nut_specification: event.currentTarget.value }); }} /></label>
        <label>Washer basis <input value={custom.snapshot.washer_material_basis} onChange={(event) => { update(custom, { washer_material_basis: event.currentTarget.value }); }} /></label>
        {(() => {
          const washer = custom.snapshot.washer_geometry;
          return washer === null ? null : <>
            <label>Washer outside diameter ({washer.outside_diameter.unit}) <input inputMode="decimal" value={washer.outside_diameter.value} onChange={(event) => { update(custom, { washer_geometry: { ...washer, outside_diameter: { ...washer.outside_diameter, value: event.currentTarget.value } } }); }} /></label>
            <label>Washer thickness ({washer.thickness.unit}) <input inputMode="decimal" value={washer.thickness.value} onChange={(event) => { update(custom, { washer_geometry: { ...washer, thickness: { ...washer.thickness, value: event.currentTarget.value } } }); }} /></label>
            <label><input type="checkbox" checked={washer.under_head} onChange={(event) => { update(custom, { washer_geometry: { ...washer, under_head: event.currentTarget.checked } }); }} /> Washer under head</label>
            <label><input type="checkbox" checked={washer.under_nut} onChange={(event) => { update(custom, { washer_geometry: { ...washer, under_nut: event.currentTarget.checked } }); }} /> Washer under nut</label>
          </>;
        })()}
        <label>Installation condition <input value={custom.snapshot.installation_condition} onChange={(event) => { update(custom, { installation_condition: event.currentTarget.value }); }} /></label>
        <label>Revision notes <textarea value={custom.snapshot.source_notes.join("\n")} onChange={(event) => { update(custom, { source_notes: event.currentTarget.value.split("\n") }); }} /></label>
      </div>
    </>}
  </section>;
}
