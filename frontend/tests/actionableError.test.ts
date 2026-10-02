import { expect, it } from "vitest";
import { actionableErrorDetail } from "../src/workspace/actionableError";

it("keeps API validation failures actionable without trusting arbitrary response shapes", () => {
  for (const input of [null, "error", 3, {}, { detail: null }, { detail: [] }, { detail: [null, {}, { msg: 3 }]}]) {
    expect(actionableErrorDetail(input)).toBeNull();
  }
  expect(actionableErrorDetail({ detail: "source required" })).toBe("source required");
  expect(actionableErrorDetail({ detail: [
    { loc: ["body", "rows", 2], msg: "too many" },
    { msg: "missing" }, { loc: "not-an-array", msg: "invalid location" },
    { loc: ["fourth"], msg: "not shown" },
  ] })).toBe("body → rows → 2: too many Input: missing Input: invalid location");
});
