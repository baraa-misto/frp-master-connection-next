import { useState } from "react";
import { parseMaterialReadiness } from "../api/connectorMaterialReadiness";
import type { MaterialReadinessFamily } from "../api/connectorMaterialReadiness";

export function ConnectorMaterialReadiness() {
  const [families, setFamilies] = useState<MaterialReadinessFamily[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  async function load() {
    setBusy(true);
    setError(false);
    try {
      const response = await fetch("/api/v1/connector-materials/capabilities");
      if (!response.ok) throw new Error("Readiness unavailable");
      const body: unknown = await response.json();
      setFamilies(parseMaterialReadiness(body));
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }
  return <details className="selection-panel">
    <summary>Connector Material Readiness</summary>
    <p>Structural members: FRP only. Current FRP support: native, existing scope.</p>
    <p>316 Stainless Steel connector bodies: conditional activation. Selection is not a claim of qualified capacity; unsupported configurations remain explicitly blocked.</p>
    <p>Fastener and foundation materials remain separate. Reinforcement requires its own applicability authority.</p>
    <button type="button" disabled={busy} onClick={() => { void load(); }}>{busy ? "Loading readiness…" : "Read current family coverage"}</button>
    {error && <p role="alert">Readiness could not be verified. No design or material change was made.</p>}
    {families && <table><caption>Read-only native family migration inventory</caption>
      <thead><tr><th>Family</th><th>Category</th><th>Material disposition</th></tr></thead>
      <tbody>{families.map(family => <tr key={family.route_id}><td>{family.product_id} ({family.route_id})</td><td>{family.category}</td><td>{family.disposition}</td></tr>)}</tbody>
    </table>}
    <p>Whole-connection qualification, FRP member checks and external support/foundation checks remain independent. No custom stainless properties or source certification can be entered here.</p>
  </details>;
}
