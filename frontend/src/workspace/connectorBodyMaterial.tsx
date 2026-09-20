import type { ConnectorBodyMaterial } from "../api/stainlessActivation";
import { EvaluationTransportError } from "../api/client";
import type { useConnectorBodyMaterial } from "./useConnectorBodyMaterial";

export function ConnectorBodyMaterialControl({ material, onChange }: {
  readonly material: ConnectorBodyMaterial; readonly onChange: (value: ConnectorBodyMaterial) => void;
}) {
  return <section className="sidebar-group-body" aria-label="Connector body material selection">
    <label className="field-control"><span>Connector Body Material</span>
      <select aria-label="Connector Body Material" value={material} onChange={event => {
        const value = event.currentTarget.value;
        if (value === "FRP" || value === "SS316") onChange(value);
      }}><option value="FRP">FRP</option><option value="SS316">316 Stainless Steel</option></select>
    </label>
    <p className="sidebar-note">One material for all connector bodies. Primary members remain FRP; fasteners and foundation retain independent authority.</p>
    {material === "SS316" ? <p className="sidebar-note">Conditional activation: response, product, section and local-method qualification are required. No custom stainless properties. Run Design Check explicitly.</p> : null}
  </section>;
}

export function ConnectorBodyMaterialResult({ state }: {
  readonly state: ReturnType<typeof useConnectorBodyMaterial>;
}) {
  if (state.material === "FRP") return null;
  return <section className="source-card" aria-label="Stainless connector-body design">
    <h3>316 Stainless Steel connector bodies — conditional activation</h3>
    <p>Geometry and native reference traces below retain historical FRP labels. They do not qualify stainless response or supply governing stainless connector-body resistance.</p>
    {state.stale ? <p role="status">Stainless design is stale. Run Design Check for the current geometry and actions.</p> : null}
    {state.busy ? <p role="status">Running stainless design check…</p> : null}
    {state.error === null ? null : <div role="alert"><p>{state.error.message}</p>
      {state.error instanceof EvaluationTransportError ? <pre>{JSON.stringify(state.error.detail, null, 2)}</pre> : null}</div>}
    {state.response === null ? <p>No current stainless design. Selection and preview do not calculate resistance.</p> : <>
      <p><strong>{state.response.status}</strong></p>
      <p>Activation fingerprint: {state.response.fingerprint}</p>
      {state.response.blockers.map((reason, index) => <p key={`${String(index)}:${reason}`}>{reason}</p>)}
      {state.response.bodies.map(body => <article key={body.body_id}>
        <h4>{body.body_id} · {body.body_form} · 316 Stainless Steel</h4>
        <p>{body.activation} · No FRP connector-body resistance used</p>
        {body.blockers.map((reason, index) => <p key={`${String(index)}:${reason}`}>{reason}</p>)}
        <p>Body fingerprint: {body.fingerprint}</p>
        <p>Frozen provider fingerprints: {body.provider_fingerprints.length === 0 ? "Not evaluated: required authority unavailable" : body.provider_fingerprints.join("; ")}</p>
      </article>)}
      <details><summary>Native non-body checks and complete activation trace</summary>
        <pre>{JSON.stringify({ checks: state.response.native_non_body_checks, trace: state.response.trace }, null, 2)}</pre>
      </details>
    </>}
  </section>;
}
