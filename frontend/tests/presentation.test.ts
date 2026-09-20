import { describe, expect, it } from "vitest";

import {
  exactQuantity,
  formatDecimal,
  formatEditableDecimal,
  formatDisplayQuantity,
  formatQuantity,
  formatUtilization,
  friendlyEnum,
  friendlyIdentifier,
} from "../src/workspace/presentation";

describe("Stage 2.3R presentation-only engineering formatting", () => {
  it("converts supported multi-row quantities for display and preserves unknown raw units", () => {
    expect(formatDisplayQuantity({ value: "2", unit: "in" }, "SI")).toBe("50.8 mm");
    expect(formatDisplayQuantity({ value: "22.2411080763025", unit: "kN" }, "US_CUSTOMARY")).toBe("5 kip");
    expect(formatDisplayQuantity({ value: "44482.216152605", unit: "N" }, "US_CUSTOMARY")).toBe("10 kip");
    expect(formatDisplayQuantity({ value: "44482.216152605", unit: "N" }, "SI")).toBe("44.48222 kN");
    expect(formatDisplayQuantity({ value: "raw", unit: "custom" }, "SI")).toBe("raw custom");
    expect(formatDisplayQuantity(null, "SI")).toBe("—");
  });

  it("uses engineer-friendly labels while retaining unknown stable IDs", () => {
    expect(friendlyIdentifier("member-a")).toBe("Angle brace");
    expect(friendlyIdentifier("member-b")).toBe("W column");
    expect(friendlyIdentifier("bolt-1")).toBe("Selected bolt");
    expect(friendlyIdentifier("B_R2_L3")).toBe("Bolt · Row 2 · Line 3");
    expect(friendlyIdentifier("ROW_2")).toBe("Row 2");
    expect(friendlyIdentifier("BOLT_LINE_3")).toBe("Bolt Line 3");
    expect(friendlyIdentifier("custom-stable-id")).toBe("custom-stable-id");
    expect(friendlyIdentifier(null)).toBe("Bolt");
    expect(friendlyEnum("NET_SECTION_TENSION")).toBe("Net Section Tension");
    expect(friendlyEnum("")).toBe("");
    expect(friendlyEnum(null)).toBe("Not evaluated");
  });

  it("rounds presentation values only and preserves exact transport strings", () => {
    const quantity = { value: "1.234567890123", unit: "kip" };
    expect(formatDecimal(quantity.value)).toBe("1.235");
    expect(formatDecimal("0.12345", 2)).toBe("0.12");
    expect(formatDecimal("not-a-number")).toBe("not-a-number");
    expect(formatEditableDecimal("9.524999999999999")).toBe("9.525");
    expect(formatEditableDecimal("12.700000000000003")).toBe("12.7");
    expect(formatEditableDecimal("1.23456", 4)).toBe("1.2346");
    expect(formatEditableDecimal("not-a-number")).toBe("not-a-number");
    expect(formatDecimal(null)).toBe("—");
    expect(formatQuantity(quantity)).toBe("1.235 kip");
    expect(formatQuantity(null)).toBe("—");
    expect(formatUtilization("0.87654321")).toBe("0.877 (87.7%)");
    expect(formatUtilization("pending")).toBe("pending");
    expect(formatUtilization(null)).toBe("—");
    expect(exactQuantity(quantity)).toBe("1.234567890123 kip");
    expect(exactQuantity(null)).toBe("—");
  });
});
