import type { MAT1Conditions } from "../state/mat1Session";

/** Basic transport inputs only. Unknown exposure and source/qualification are not run blockers. */
export function materialConditionIssues(conditions: MAT1Conditions): Readonly<Record<string, string>> {
  const issues: Record<string, string> = {};
  for (const [key, label] of [["sustained_temperature", "sustained material temperature"], ["maximum_temperature", "maximum material temperature"]] as const) {
    const value = conditions[key].value;
    if (value.trim() === "" || !Number.isFinite(Number(value))) issues[key] = `Enter a finite ${label}.`;
  }
  const fahrenheit = (temperature: MAT1Conditions["sustained_temperature"]): number => temperature.unit === "degC" ? Number(temperature.value) * 9 / 5 + 32 : Number(temperature.value);
  if (!issues.sustained_temperature && !issues.maximum_temperature && fahrenheit(conditions.maximum_temperature) < fahrenheit(conditions.sustained_temperature)) {
    issues.maximum_temperature = "Maximum material temperature must be at least the sustained temperature.";
  }
  if (conditions.load_case_name.trim() === "") issues.load_case_name = "Enter a load-case name.";
  if (conditions.time_effect_category === "") issues.time_effect_category = "Select the load classification.";
  if (conditions.time_effect_category === "LONG_TERM_OPERATING" && conditions.full_amplitude_duration !== "MORE_THAN_ONE_YEAR") {
    issues.full_amplitude_duration = "Confirm more than one year at full operating amplitude, or choose the actual live-load classification.";
  }
  return issues;
}

export function materialConditionBlocker(conditions: MAT1Conditions): string | null {
  const issues = Object.values(materialConditionIssues(conditions));
  return issues.length === 0 ? null : issues.join(" ");
}
