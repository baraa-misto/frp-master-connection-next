import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { exportGeometry, GEOMETRY_BANNER, previewTwoBolt, twoBoltRequest } from "../api/directTwoBolt";
import type { GeometryResponse, TwoBoltOptions, TwoBoltRequest } from "../api/directTwoBolt";
import type { MultiRowConnectionRequest } from "../api/multirowContracts";
import { mat1FamilyKey, useMAT1 } from "../state/mat1Session";

export interface CurrentTwoBolt {
  sourceKey: string;
  request: TwoBoltRequest;
  preview: GeometryResponse;
}
interface Props {
  legacy: MultiRowConnectionRequest;
  options: TwoBoltOptions;
  onChange: (options: TwoBoltOptions) => void;
  onCurrent: (current: CurrentTwoBolt | null) => void;
}
function stateLabel(value: string): string {
  const labels: Record<string, string> = {
    FIT_FOR_STATED_GEOMETRY: "Fits stated geometry", CONDITIONAL: "Conditional — dimensions or access unresolved",
    DOES_NOT_FIT: "Does not fit", NOT_EVALUATED: "Not evaluated",
  };
  return labels[value] ?? value;
}

export function DirectTwoBoltGeometry({ legacy, options, onChange, onCurrent }: Props) {
  useMAT1();
  const inputKey = JSON.stringify([legacy, options, mat1FamilyKey("multi-row", false)]);
  const sequence = useRef(0);
  const currentKey = useRef(inputKey);
  useLayoutEffect(() => { currentKey.current = inputKey; }, [inputKey]);
  const [received, setReceived] = useState<{ key: string; current: CurrentTwoBolt | null; error: string } | null>(null);
  const current = received?.key === inputKey ? received.current : null;
  const error = received?.key === inputKey ? received.error : "";
  const [exportError, setExportError] = useState("");
  const [retry, setRetry] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [units, setUnits] = useState<"in" | "mm">("in");
  useEffect(() => {
    const controller = new AbortController();
    sequence.current += 1;
    const revision = String(sequence.current);
    void Promise.resolve().then(async () => {
      const request = twoBoltRequest(legacy, options, revision);
      return { request, preview: await previewTwoBolt(request, controller.signal) };
    }).then(({ request, preview }) => {
      if (controller.signal.aborted || currentKey.current !== inputKey) return;
      const result = { sourceKey: inputKey, request, preview };
      setReceived({ key: inputKey, current: result, error: "" }); onCurrent(result);
    }).catch((failure: unknown) => {
      if (controller.signal.aborted || currentKey.current !== inputKey) return;
      setReceived({ key: inputKey, current: null, error: failure instanceof Error ? failure.message : "Geometry preview unavailable. Retry." });
    });
    return () => { controller.abort(); };
    // inputKey binds the complete geometry, materials, conditions and options.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputKey, retry, onCurrent]);
  const update = (change: Partial<TwoBoltOptions>) => { currentKey.current = ""; onChange({ ...options, ...change }); };
  const download = async (target: CurrentTwoBolt) => {
    const key = inputKey;
    setExporting(true); setExportError("");
    try {
      const blob = await exportGeometry(target.request, target.preview);
      if (currentKey.current !== key) return;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = "Direct-Geometry-and-Constructability-Review.pdf";
      anchor.click(); URL.revokeObjectURL(url);
    } catch (failure) { setExportError(failure instanceof Error ? failure.message : "Geometry export unavailable. Retry."); }
    finally { setExporting(false); }
  };
  const value = (number: string) => (Number(number) * (units === "mm" ? 25.4 : 1)).toFixed(units === "mm" ? 3 : 5);
  return <section aria-label="Two-bolt geometry and constructability" className="two-bolt-geometry">
    <h3>Two-bolt geometry and constructability</h3>
    <div className="field-control"><div style={{ display: "flex", alignItems: "center", gap: ".35rem" }}><label htmlFor="direct-two-bolt-alignment">Bolt alignment</label><details className="mc1-help"><summary aria-label="Help: Bolt alignment">?</summary><p>Changes the line joining the two bolt centers. Bolt shafts remain normal to the selected interface. Supporting-member alignment is geometry-only in this stage.</p></details></div><select id="direct-two-bolt-alignment" value={options.alignment} onChange={(event) => { update({ alignment: event.currentTarget.value as TwoBoltOptions["alignment"] }); }}>
      <option value="BRACE">Along brace</option><option value="SUPPORT">Along supporting member</option>
    </select></div>
    <p>Same two bolt locations checked against both connected members. Brace alignment retains the existing default.</p>
    <label className="field-control"><span>Bolt spacing along selected alignment (in)</span><input inputMode="decimal" value={options.spacing} placeholder={"Current pitch: " + legacy.pitch.value + " " + legacy.pitch.unit} onChange={(event) => { update({ spacing: event.currentTarget.value }); }} /></label>
    <details><summary>Midpoint offset and bounded proposals</summary>
      <p>Offset from the submitted bolt-pair midpoint, measured in the supporting member frame. +u follows its longitudinal +x axis; +v follows its transverse +y axis. Applying a proposal moves the pair and requires a new evaluation.</p>
      <label className="field-control"><span>Midpoint offset +u (in)</span><input inputMode="decimal" value={options.longitudinal} onChange={(event) => { update({ longitudinal: event.currentTarget.value }); }} /></label>
      <label className="field-control"><span>Midpoint offset +v (in)</span><input inputMode="decimal" value={options.transverse} onChange={(event) => { update({ transverse: event.currentTarget.value }); }} /></label>
      <label className="field-control"><span>Search half-width in both directions (in)</span><input inputMode="decimal" value={options.searchLimit} onChange={(event) => { update({ searchLimit: event.currentTarget.value, search: false }); }} /></label>
      <button type="button" disabled={!Number.isFinite(Number(options.searchLimit)) || Number(options.searchLimit) <= 0} onClick={() => { update({ search: true }); }}>Find bounded midpoint proposals</button>
      {current?.preview.midpoint_regions.map((region, index) => <div key={region.assigned_strips.join(":")}>
        <p>Proposal {index + 1}: Δu {Number(region.proposed_offset[0]).toPrecision(6)} in, Δv {Number(region.proposed_offset[1]).toPrecision(6)} in from current midpoint. Separate rear outstand assignment retained.</p>
        <p>Outstand assignment: {region.assigned_strips.map((strip) => String(strip + 1)).join(" / ")}. Candidate: {stateLabel(region.candidate_geometry.aggregate_state)}. Minimum stated margin: {Math.min(...region.candidate_geometry.margins.map((margin) => Number(margin.value))).toPrecision(6)} in.</p>
        <details><summary>Proposal assumptions and moment-reference change</summary><ul>{region.candidate_geometry.unknowns.map((unknown) => <li key={unknown}>{unknown}</li>)}</ul><pre>{JSON.stringify(region.moment_diagnostic, null, 2)}</pre></details>
        <button type="button" onClick={() => { update({
          longitudinal: region.proposed_request_offset[0],
          transverse: region.proposed_request_offset[1], search: false,
        }); }}>Apply proposal {index + 1}</button>
      </div>)}
      {options.search && current?.preview.midpoint_regions.length === 0 ? <p>No feasible seating proposal in the specified search domain. This does not prove that every placement is impossible.</p> : null}
      <p>These are bounded seating proposals, not an installation or maximum-clearance proof. Unknown neighboring geometry remains unresolved.</p>
    </details>
    <details><summary>Declared cuts, neighboring body and access envelopes</summary>
      <p>Optional engineering geometry in inches. Leave unknowns blank. Enter a dimension origin such as measured, specified, or assumed for sensitivity; these records do not certify fabrication or installation.</p>
      <p>Angle cut: convex counterclockwise face-local u,v vertices separated by semicolons. The polygon is extruded along the selected face normal. It restricts the nominal member; it does not move either member.</p>
      <label className="field-control"><span>Angle cut polygon (u,v; u,v; … in)</span><input value={options.cutPolygon} onChange={(event) => { update({ cutPolygon: event.currentTarget.value }); }} /></label>
      <label className="field-control"><span>Angle cut dimension origin</span><input value={options.cutSource} onChange={(event) => { update({ cutSource: event.currentTarget.value }); }} /></label>
      <p>Neighbor: support-local lower u,v,w followed by upper u,v,w. This is a finite box envelope of an explicitly declared body.</p>
      <label className="field-control"><span>Neighbor box bounds (six values in)</span><input value={options.neighborBounds} onChange={(event) => { update({ neighborBounds: event.currentTarget.value }); }} /></label>
      <label className="field-control"><span>Neighbor dimension origin</span><input value={options.neighborSource} onChange={(event) => { update({ neighborSource: event.currentTarget.value }); }} /></label>
      <p>Each circular envelope uses radius, axial start, axial end. Axial distances follow the actual shaft axis from each station center. Approach, hex clocking and installation sequence beyond these cylinders remain unevaluated.</p>
      {([["Head envelope", "headEnvelope"], ["Nut envelope", "nutEnvelope"], ["Tool envelope", "toolEnvelope"]] as const).map(([label, field]) => <label className="field-control" key={field}><span>{label} (radius,start,end in)</span><input value={options[field]} onChange={(event) => { update({ [field]: event.currentTarget.value }); }} /></label>)}
      <label className="field-control"><span>Envelope dimension origin</span><input value={options.envelopeSource} onChange={(event) => { update({ envelopeSource: event.currentTarget.value }); }} /></label>
    </details>
    <details><summary>Hole specification and manufactured root geometry</summary><p>Leave unknown dimensions blank. A geometry-only hole specification is independent of the legacy declared hole basis; 9/16 in (0.5625) is distinct from 0.563 in. Additional root exclusions do not change resistance or qualification.</p>
      <label className="field-control"><span>Geometry-only hole diameter (in)</span><input inputMode="decimal" value={options.holeDiameter} onChange={(event) => { update({ holeDiameter: event.currentTarget.value }); }} /></label>
      <label className="field-control"><span>Angle root encroachment (in)</span><input inputMode="decimal" value={options.angleRoot} onChange={(event) => { update({ angleRoot: event.currentTarget.value }); }} /></label>
      <label className="field-control"><span>Supporting member root encroachment (in)</span><input inputMode="decimal" value={options.supportRoot} onChange={(event) => { update({ supportRoot: event.currentTarget.value }); }} /></label>
      <label className="field-control"><span>Manufactured geometry source</span><input value={options.geometrySource} onChange={(event) => { update({ geometrySource: event.currentTarget.value }); }} /></label>
    </details>
    {error === "" ? null : <div role="alert"><p>{error}</p><button type="button" onClick={() => { setRetry((n) => n + 1); }}>Retry geometry</button></div>}
    {exportError === "" ? null : <p role="alert">{exportError}</p>}
    {current === null ? <p role="status">{error === "" ? "Updating two-bolt geometry…" : "Current geometry unavailable"}</p> : <>
      {current.preview.structural_eligible ? <p>Identical legacy layout can be freshly evaluated with its existing engineering limits.</p> : <><strong>{GEOMETRY_BANNER}</strong><p>{current.preview.structural_reason}</p></>}
      <dl>{[
        ["Hole containment", current.preview.geometry.hole_state],
        ["Shaft / rear web", current.preview.geometry.shaft_state],
        ["Washer seating", current.preview.geometry.washer_state],
        ["Known obstructions", current.preview.geometry.obstruction_state],
        ["Head / nut bodies", current.preview.geometry.hardware_state],
        ["Installation access", current.preview.geometry.installation_state],
        ["Aggregate constructability", current.preview.geometry.aggregate_state],
      ].map(([label, state]) => <div key={label}><dt>{label}</dt><dd>{stateLabel(state ?? "")}</dd></div>)}</dl>
      <p>{current.preview.comparison.basis}</p><p>Other alignment: {current.preview.comparison.alignment === "BRACE" ? "Along brace" : "Along supporting member"} — {stateLabel(current.preview.comparison.geometry.aggregate_state)}.</p>
      <details><summary>Fixed-placement comparison coordinates and clearances</summary><p>Other pattern minimum signed margin: {Math.min(...current.preview.comparison.geometry.margins.map((margin) => Number(margin.value))).toPrecision(6)} in.</p>
        {current.preview.pair_input.faces.map((face, index) => <FaceView key={face.id} response={{ ...current.preview, geometry: current.preview.comparison.geometry }} faceIndex={index} units={units} />)}
      </details>
      <label className="field-control"><span>Geometry review display units</span><select value={units} onChange={(event) => { setUnits(event.currentTarget.value as "in" | "mm"); }}><option value="in">in</option><option value="mm">mm</option></select></label>
      <p>Pair spacing: {value(current.preview.pair_input.spacing)} {units}. Stations B1/B2 are geometry labels; they do not establish first-row engineering authority.</p>
      <p>The 3D view uses the same stations, declared convex cuts, neighboring boxes and hardware envelopes. Root exclusions are planar seating envelopes; a manufactured fillet profile is not represented.</p>
      {current.preview.pair_input.faces.map((face, index) => <FaceView key={face.id} response={current.preview} faceIndex={index} units={units} />)}
      <details><summary>Limitations and geometry audit</summary><ul>{current.preview.geometry.unknowns.map((unknown) => <li key={unknown}>{unknown}</li>)}</ul>
        <p>Fingerprint: {current.preview.geometry_fingerprint}</p>
        <table><thead><tr><th>Station / member</th><th>Envelope / boundary</th><th>Signed margin ({units})</th></tr></thead><tbody>
          {current.preview.geometry.margins.map((margin, index) => <tr key={index}><td>{margin.station} / {margin.owner}</td><td>{margin.role} / {margin.boundary}</td><td>{value(margin.value)}</td></tr>)}
        </tbody></table><pre>{JSON.stringify(current.preview.moment_diagnostic, null, 2)}</pre>
      </details>
      <button type="button" disabled={exporting} onClick={() => { void download(current); }}>{exporting ? "Preparing geometry review…" : "Export Geometry and Constructability Review"}</button>
    </>}
  </section>;
}

export function FaceView({ response, faceIndex, units }: { response: GeometryResponse; faceIndex: number; units: "in" | "mm" }) {
  const face = response.pair_input.faces[faceIndex];
  if (face === undefined) return null;
  const points = response.geometry.face_points.filter((point) => point.face_id === face.id);
  const radius = Number(response.pair_input.washer_radius);
  const us = points.map((point) => Number(point.local_center[0]));
  const vs = points.map((point) => Number(point.local_center[1]));
  for (const boundary of face.boundaries) {
    if (Number(boundary.b) === 0 && Number(boundary.a) !== 0) us.push(Number(boundary.limit) / Number(boundary.a));
    if (Number(boundary.a) === 0 && Number(boundary.b) !== 0) vs.push(Number(boundary.limit) / Number(boundary.b));
  }
  const u0 = Math.min(...us) - radius, u1 = Math.max(...us) + radius;
  const v0 = Math.min(...vs) - radius, v1 = Math.max(...vs) + radius;
  const scale = Math.min(430 / (u1 - u0), 165 / (v1 - v0));
  const x = (u: number) => 25 + (u - u0) * scale;
  const y = (v: number) => 195 - (v - v0) * scale;
  const display = (number: string) => (Number(number) * (units === "mm" ? 25.4 : 1)).toFixed(4);
  return <figure><figcaption>{faceIndex === 0 ? "Angle connected face" : "Supporting member face"} — same B1/B2 stations</figcaption>
    <svg role="img" aria-label={(faceIndex === 0 ? "Angle" : "Supporting member") + " face bolt geometry"} viewBox="0 0 480 230" style={{ width: "100%", maxWidth: 480 }}>
      <defs><clipPath id={"sab2-face-" + String(faceIndex)}><rect x="15" y="15" width="450" height="195" /></clipPath></defs>
      <g clipPath={"url(#sab2-face-" + String(faceIndex) + ")"}>
        {face.seating_strips.map(([lo, hi]) => <rect key={lo} x={x(u0)} y={y(Number(hi))} width={(u1 - u0) * scale} height={(Number(hi) - Number(lo)) * scale} fill="#dbe8e3" />)}
        {face.boundaries.map((boundary) => {
          const a = Number(boundary.a), b = Number(boundary.b), limit = Number(boundary.limit);
          return b === 0 ? <line key={boundary.id} x1={x(limit / a)} x2={x(limit / a)} y1={y(v0)} y2={y(v1)} stroke="#173e5b" /> :
            <line key={boundary.id} x1={x(u0)} x2={x(u1)} y1={y((limit - a * u0) / b)} y2={y((limit - a * u1) / b)} stroke="#173e5b" />;
        })}
        {points.map((point) => <g key={point.station} data-global-center={point.global_center.join(",")}>
          <circle cx={x(Number(point.local_center[0]))} cy={y(Number(point.local_center[1]))} r={radius * scale} fill="none" stroke="#bc681d" />
          <circle cx={x(Number(point.local_center[0]))} cy={y(Number(point.local_center[1]))} r={Number(response.pair_input.hole_radius) * scale} fill="none" stroke="#173e5b" />
          <text x={x(Number(point.local_center[0])) + 4} y={y(Number(point.local_center[1])) - 5} fontSize="11">{point.station}</text>
        </g>)}
      </g><text x="15" y="224" fontSize="10">Solid: physical boundaries · orange: washer · green: rear seating strips</text>
    </svg><ul>{points.map((point) => <li key={point.station}>{point.station}: u={display(point.local_center[0])}, v={display(point.local_center[1])} {units}</li>)}</ul>
  </figure>;
}
