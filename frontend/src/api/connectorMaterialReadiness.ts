export interface MaterialReadinessFamily { route_id: string; product_id: string; category: string; disposition: string }
const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export function parseMaterialReadiness(value: unknown): MaterialReadinessFamily[] {
  if (!record(value) || value.contract !== "CME-1-RC1" || value.resistance_evaluated !== false
    || !record(value.result) || value.result.SS316 !== "STAINLESS_CONDITIONAL_PROVIDER_AVAILABLE"
    || !Array.isArray(value.result.families)) throw new Error("Invalid readiness response");
  return value.result.families.map((family: unknown) => {
    if (!record(family) || typeof family.route_id !== "string" || typeof family.product_id !== "string"
      || typeof family.category !== "string" || typeof family.disposition !== "string") {
      throw new Error("Invalid family readiness record");
    }
    return { route_id: family.route_id, product_id: family.product_id, category: family.category, disposition: family.disposition };
  });
}
