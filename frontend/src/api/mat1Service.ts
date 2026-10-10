/** Typed MAT1 service boundary. Workspace transports never own catalog requests. */
import type { MAT1CatalogRecord, MAT1Conditions } from "../state/mat1Session";

interface CatalogEnvelope {
  readonly contract: "MAT1-CATALOG-RC0";
  readonly records: readonly MAT1CatalogRecord[];
}

interface OwnerEnvelope {
  readonly contract: "MAT1-OWNER-PREVIEW-RC0";
  readonly family_id: string;
  readonly owners: readonly string[];
  readonly design_check_performed: false;
}

interface FactorEnvelope {
  readonly contract: "MAT1-FACTOR-RC0";
  readonly result_status: string;
  readonly record_id: string;
  readonly ledgers: readonly unknown[];
  readonly design_check_performed: false;
  readonly condition_basis?: {
    readonly status: string;
    readonly required_tg: { readonly value: string; readonly unit: "degF" };
    readonly required_tg_degC: string;
    readonly project_issues: readonly string[];
  };
}

type MaterialSelection =
  | { readonly kind: "CATALOG"; readonly id: string; readonly revision: string; readonly content_digest: string }
  | { readonly kind: "SESSION"; readonly id: string; readonly revision: string; readonly display_name: string; readonly company: string; readonly resin: string; readonly properties: Readonly<Record<string, unknown>>; readonly copied_from: string | null };

export interface FactorInspectionRequest {
  readonly material: MaterialSelection;
  readonly conditions: MAT1Conditions;
  readonly component_id: string;
  readonly property_ids: readonly string[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function requestJson(path: string, init: RequestInit): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, credentials: "same-origin" });
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new Error("MAT1 service could not be reached.", { cause: error });
  }
  if (!response.ok) {
    if (response.status === 422) throw new Error("Check the required material and project condition fields, then try again.", { cause: `MAT1 service HTTP ${String(response.status)}` });
    throw new Error("Unable to complete the material request. Try again or open Advanced Engineering Diagnostics for technical details.", { cause: `MAT1 service HTTP ${String(response.status)}` });
  }
  try {
    return await response.json() as unknown;
  } catch (error) {
    throw new Error("MAT1 service returned invalid JSON.", { cause: error });
  }
}

export async function loadMAT1Catalog(signal: AbortSignal): Promise<readonly MAT1CatalogRecord[]> {
  const body = await requestJson("/api/v1/frp-materials/catalog", { signal });
  if (!isRecord(body) || body.contract !== "MAT1-CATALOG-RC0" || !Array.isArray(body.records)
    || !body.records.every((item: unknown) => isRecord(item) && typeof item.id === "string"
      && typeof item.revision === "string" && typeof item.content_digest === "string"
      && typeof item.display_name === "string" && Array.isArray(item.properties))) {
    throw new Error("MAT1 catalog contract is invalid.");
  }
  return (body as unknown as CatalogEnvelope).records;
}

export async function loadMAT1Owners(family: string, legacyRequest: unknown, signal: AbortSignal): Promise<readonly string[]> {
  const body = await requestJson("/api/v1/frp-materials/family/owners", {
    method: "POST", headers: { "Content-Type": "application/json" }, signal,
    body: JSON.stringify({ contract: "MAT1-OWNER-PREVIEW-RC0", family_id: family, legacy_request: legacyRequest }),
  });
  if (!isRecord(body) || body.contract !== "MAT1-OWNER-PREVIEW-RC0" || body.family_id !== family
    || body.design_check_performed !== false || !Array.isArray(body.owners)
    || !body.owners.every((item: unknown) => typeof item === "string")) {
    throw new Error("MAT1 owner preview contract is invalid.");
  }
  return (body as unknown as OwnerEnvelope).owners;
}

export async function inspectMAT1Factors(request: FactorInspectionRequest, signal: AbortSignal): Promise<FactorEnvelope> {
  const body = await requestJson("/api/v1/frp-materials/factor-candidates", {
    method: "POST", headers: { "Content-Type": "application/json" }, signal,
    body: JSON.stringify({ contract: "MAT1-FACTOR-RC0", ...request,
      ...(request.conditions.direct_policy === "SHEAR01-DIRECT-MC1" ? { family_id: "multi-row" } : {}) }),
  });
  if (!isRecord(body) || body.contract !== "MAT1-FACTOR-RC0" || body.design_check_performed !== false
    || typeof body.record_id !== "string" || !Array.isArray(body.ledgers)) {
    throw new Error("MAT1 factor response contract is invalid.");
  }
  return body as unknown as FactorEnvelope;
}
