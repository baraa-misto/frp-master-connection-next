import { expect, it } from "vitest";
import { materialConditionBlocker, materialConditionIssues } from "../src/features/materialConditionValidation";
import { mat1Snapshot } from "../src/state/mat1Session";

it("requires basic inputs while permitting unknown exposure and missing source evidence", () => {
  const conditions = { ...mat1Snapshot().conditions, sustained_temperature: { value: "70", unit: "degF" as const }, maximum_temperature: { value: "70", unit: "degF" as const }, time_effect_category: "WIND_TORNADO_SEISMIC", load_case_name: "LC", moisture: "UNKNOWN" as const, chemical: "UNKNOWN" as const };
  expect(materialConditionBlocker(conditions)).toBeNull();
  expect(materialConditionBlocker({ ...conditions, maximum_temperature: { value: "30", unit: "degC" } })).toBeNull();
  expect(materialConditionIssues({ ...conditions, sustained_temperature: { value: "", unit: "degF" } })).toHaveProperty("sustained_temperature");
  expect(materialConditionIssues({ ...conditions, maximum_temperature: { value: "NaN", unit: "degF" } })).toHaveProperty("maximum_temperature");
  expect(materialConditionBlocker({ ...conditions, load_case_name: " ", time_effect_category: "" })).toContain("Select the load classification");
  expect(materialConditionIssues({ ...conditions, maximum_temperature: { value: "60", unit: "degF" } })).toHaveProperty("maximum_temperature");
  expect(materialConditionIssues({ ...conditions, time_effect_category: "LONG_TERM_OPERATING", full_amplitude_duration: "" })).toHaveProperty("full_amplitude_duration");
  expect(materialConditionBlocker({ ...conditions, time_effect_category: "LONG_TERM_OPERATING", full_amplitude_duration: "MORE_THAN_ONE_YEAR" })).toBeNull();
});
