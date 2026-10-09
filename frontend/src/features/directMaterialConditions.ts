import type { MAT1Conditions } from "../state/mat1Session";

type Temperature = MAT1Conditions["sustained_temperature"];
const decimalPattern = /^([+-]?)(\d+(?:\.\d*)?|\.\d+)(?:e([+-]?\d+))?$/i;

export function validDesignTemperature(value: string): boolean {
  return decimalPattern.test(value.trim()) && Number.isFinite(Number(value));
}

export function validChemicalStrengthFactor(value: string): boolean {
  if (typeof value !== "string") return false;
  const match = decimalPattern.exec(value.trim());
  if (match === null) return false;
  const [sign, representation, exponentText] = match.slice(1) as [string, string, string?];
  if (sign === "-") return false;
  const [whole, fraction = ""] = representation.split(".") as [string, string?];
  const digits = (whole + fraction).replace(/^0+/, "");
  if (digits === "") return false;
  const exponent = Number(exponentText ?? "0");
  if (!Number.isSafeInteger(exponent)) return false;
  const position = digits.length - fraction.length + exponent;
  return position < 1 || (position === 1 && /^10*$/.test(digits));
}

type DecimalTerm = readonly [bigint, bigint];
function temperatureTerms(temperature: Temperature): readonly DecimalTerm[] | null {
  if (temperature.value.trim() === "" || !Number.isFinite(Number(temperature.value))) return null;
  const match = decimalPattern.exec(temperature.value.trim());
  if (match === null) return null;
  const [sign, representation, exponentText] = match.slice(1) as [string, string, string?];
  const [whole, fraction = ""] = representation.split(".") as [string, string?];
  const coefficient = BigInt(whole + fraction) * (sign === "-" ? -1n : 1n);
  const exponent = BigInt(exponentText ?? "0") - BigInt(fraction.length);
  // Five times Fahrenheit, as sparse exact decimal terms; no factors are calculated.
  return temperature.unit === "degC" ? [[coefficient * 9n, exponent], [160n, 0n]] : [[coefficient * 5n, exponent]];
}

function compareTemperatures(left: readonly DecimalTerm[], right: readonly DecimalTerm[]): number {
  let terms = [...left, ...right.map(([coefficient, exponent]): DecimalTerm => [-coefficient, exponent])].filter(([coefficient]) => coefficient !== 0n);
  const order = ([coefficient, exponent]: DecimalTerm): bigint => exponent + BigInt(coefficient.toString().replace("-", "").length);
  while (terms.length > 1) {
    terms.sort((a, b) => order(a) > order(b) ? -1 : order(a) < order(b) ? 1 : 0);
    const [first, second] = terms as [DecimalTerm, DecimalTerm, ...DecimalTerm[]];
    // At most four terms. A >2-decade lead cannot be cancelled by the remaining terms.
    // Close terms require powers bounded by their input digit counts, even for huge exponents.
    if (order(first) - order(second) > 2n) return first[0] > 0n ? 1 : -1;
    const exponent = first[1] < second[1] ? first[1] : second[1];
    const coefficient = first[0] * 10n ** (first[1] - exponent) + second[0] * 10n ** (second[1] - exponent);
    terms = [...terms.slice(2), [coefficient, exponent] as const].filter(([value]) => value !== 0n);
  }
  return terms.reduce((_sign, [coefficient]) => coefficient > 0n ? 1 : -1, 0);
}

export function adoptDirectConditions(legacy: MAT1Conditions): { readonly conditions: MAT1Conditions; readonly adoption: string | null } {
  const sustained = temperatureTerms(legacy.sustained_temperature);
  const maximum = temperatureTerms(legacy.maximum_temperature);
  const higher = maximum !== null && (sustained === null || compareTemperatures(maximum, sustained) > 0)
    ? legacy.maximum_temperature : legacy.sustained_temperature;
  const differ = sustained !== null && maximum !== null && compareTemperatures(maximum, sustained) !== 0;
  return { conditions: {
    ...legacy, direct_policy: "SHEAR01-DIRECT-MC1", design_temperature: higher,
    sustained_temperature: higher, maximum_temperature: higher,
    load_case_name: legacy.load_case_name.trim() === "" || legacy.load_case_name === "LC-1" ? "DIRECT-FACTORED-ACTION" : legacy.load_case_name,
  }, adoption: differ ? `New Design Temperature adopts the higher prior value: ${higher.value} ${higher.unit === "degF" ? "°F" : "°C"}. Run a new Design Check; historical signed reports keep both original temperatures.` : null };
}

export function updateDirectTemperature(conditions: MAT1Conditions, temperature: Temperature): MAT1Conditions {
  return { ...conditions, design_temperature: temperature, sustained_temperature: temperature, maximum_temperature: temperature };
}

export const DIRECT_LOAD_CLASSIFICATIONS = [
  ["DEAD_ONLY", "Dead load only", ""],
  ["IMPACT", "Live — impact", "IMPACT"],
  ["STORAGE", "Live — storage", "STORAGE"],
  ["LONG_TERM_OPERATING", "Live — long-term operating: full operating amplitude for more than one year", "LONG_TERM_OPERATING"],
  ["OTHER_LIVE", "Live — other", "OTHER_LIVE"],
  ["SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE", "Snow, rain, flood, or atmospheric ice", ""],
  ["WIND_TORNADO_SEISMIC", "Wind, tornado, or seismic", ""],
] as const;
