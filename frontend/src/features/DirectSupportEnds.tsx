import type { DirectSupportEndAuthority, DirectSupportEndInput } from "../api/multirowContracts";

const SUPPORT_END_LABELS = {
  UNSPECIFIED: "Select condition",
  CONTINUOUS_THROUGH_CONNECTION: "Continuous through connection",
  FINITE_BOTH_ENDS: "Finite at both ends",
  FINITE_POSITIVE_END_ONLY: "Finite end above connection only",
  FINITE_NEGATIVE_END_ONLY: "Finite end below connection only",
} as const;

export function DirectSupportEnds({ value, unit, onChange }: {
  readonly value: DirectSupportEndInput;
  readonly unit: "in" | "mm";
  readonly onChange: (value: DirectSupportEndInput) => void;
}) {
  const below = value.condition === "FINITE_BOTH_ENDS" || value.condition === "FINITE_NEGATIVE_END_ONLY";
  const above = value.condition === "FINITE_BOTH_ENDS" || value.condition === "FINITE_POSITIVE_END_ONLY";
  return <section aria-label="Supporting W longitudinal extent">
    <label className="field-control"><span>Supporting W — longitudinal extent</span>
      <select value={value.condition} onChange={(event) => {
        const condition = event.currentTarget.value as DirectSupportEndInput["condition"];
        const next: DirectSupportEndInput = { condition };
        if (condition === "FINITE_BOTH_ENDS" || condition === "FINITE_NEGATIVE_END_ONLY") next.negative_end_distance = value.negative_end_distance ?? { value: "", unit };
        if (condition === "FINITE_BOTH_ENDS" || condition === "FINITE_POSITIVE_END_ONLY") next.positive_end_distance = value.positive_end_distance ?? { value: "", unit };
        onChange(next);
      }}>{Object.entries(SUPPORT_END_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>
    </label>
    {above ? <label className="field-control"><span>Distance from connection reference to W end above</span><input aria-label="Distance from connection reference to W end above" inputMode="decimal" value={value.positive_end_distance?.value ?? ""} onChange={(event) => { onChange({ ...value, positive_end_distance: { value: event.currentTarget.value, unit } }); }} /><small>{unit}</small></label> : null}
    {below ? <label className="field-control"><span>Distance from connection reference to W end below</span><input aria-label="Distance from connection reference to W end below" inputMode="decimal" value={value.negative_end_distance?.value ?? ""} onChange={(event) => { onChange({ ...value, negative_end_distance: { value: event.currentTarget.value, unit } }); }} /><small>{unit}</small></label> : null}
    <p className="sidebar-note">Real ends are measured from the fixed connection reference. View extents only change the displayed length.</p>
    {value.condition === "UNSPECIFIED" ? <p role="status">INPUT NEEDED — Specify whether the supporting W continues through the connection or has a nearby member end.</p> : <p>Supporting W longitudinal condition: {SUPPORT_END_LABELS[value.condition]}</p>}
  </section>;
}

export function DirectSupportViewerCue({ authority }: { readonly authority: DirectSupportEndAuthority }) {
  if (authority.condition === "UNSPECIFIED") return <div className="direct-support-end-cue" aria-label="Supporting W real ends and view cuts"><strong>Supporting W end condition needs input — displayed caps are view cuts</strong></div>;
  return <div className="direct-support-end-cue" aria-label="Supporting W real ends and view cuts">
    <span>{authority.positive_end_distance === null ? "↑ W continues above — view cut" : `W physical end above: ${authority.positive_end_distance.value} ${authority.positive_end_distance.unit}`}</span>
    <span>{authority.negative_end_distance === null ? "↓ W continues below — view cut" : `W physical end below: ${authority.negative_end_distance.value} ${authority.negative_end_distance.unit}`}</span>
  </div>;
}

// eslint-disable-next-line react-refresh/only-export-components -- pure input validation is tested directly
export function supportEndValidation(value: DirectSupportEndInput): string | null {
  for (const distance of [value.positive_end_distance, value.negative_end_distance]) {
    if (distance !== undefined && (!Number.isFinite(Number(distance.value)) || Number(distance.value) <= 0)) return "Enter a positive distance for each selected real W member end.";
  }
  return null;
}
