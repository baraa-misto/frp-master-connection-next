import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DirectEngineeringFace } from "../src/api/multirowContracts";
import { DirectEngineeringGeometryIssue } from "../src/features/DirectEngineeringGeometryIssue";
import { describeDirectWarning } from "../src/workspace/directWarning";
import raw from "./fixtures/directF3EngineeringFaces.json";

const records = raw as unknown as Record<"free" | "owner" | "web" | "heel", DirectEngineeringFace>;

describe("Direct physical engineering evidence", () => {
  it.each(["free", "owner", "web", "heel"] as const)("uses backend physical geometry for %s", (name) => {
    const record = records[name];
    const original = structuredClone(record);
    render(<DirectEngineeringGeometryIssue record={record} unit="in" />);
    expect(screen.getByRole("region", { name: "Physical engineering geometry" })).toBeVisible();
    expect(screen.getByRole("img")).toBeVisible();
    const table = screen.getByRole("table");
    expect(table).toHaveTextContent("Chapter 8 physical free-edge distance");
    expect(table).toHaveTextContent("0.750000");
    const dimension = screen.getByTestId("physical-boundary-dimension");
    expect(dimension).toHaveAttribute("x1", record.bolt_center_member_local[0]);
    if (name === "free") expect(screen.getByRole("img")).toHaveAccessibleName(/free-edge distance: 0.086 in; required 0.750 in/u);
    if (name === "web" || name === "heel") expect(screen.getByRole("img")).toHaveAccessibleName(/Washer seating/u);
    expect(record).toEqual(original);
  });

  it.each([
    "CHAPTER_8_EDGE_DISTANCE", "CHAPTER_8_END_DISTANCE", "HOLE_PHYSICAL_CONTAINMENT",
    "WASHER_SEATING", "COMPONENT_INTERFERENCE", "REVIEW_UNKNOWN",
  ])("labels the category %s without deriving a result", (kind) => {
    const check = records.free.checks[0];
    if (check === undefined) throw new Error("Backend check fixture required");
    const record = { ...records.free, checks: [{ ...check, check_kind: kind, pass_fail: "FAIL" }] };
    render(<DirectEngineeringGeometryIssue record={record} unit="mm" />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/mm; required/u);
    expect(screen.getByRole("table")).toHaveTextContent("FAIL");
    if (kind !== "REVIEW_UNKNOWN") {
      const warning = describeDirectWarning(`DIRECT_PHYSICAL_CONTAINMENT:B_R1_L1:member-b:TOP_FLANGE:${kind} — negative physical free side edge: available=0.086; required=0.75. unit=in.`);
      expect(warning.group).toBe("geometry");
      expect(warning.text).toContain("actual 0.086 in");
      expect(warning.text).not.toContain("contact-patch");
    }
  });

  it.each(["no-check", "no-boundary"])("keeps %s evidence explicitly unavailable", (kind) => {
    render(<DirectEngineeringGeometryIssue record={{ ...records.owner,
      ...(kind === "no-check" ? { checks: [] } : { boundaries: [] }),
    }} unit="in" />);
    expect(screen.getByRole("alert")).toHaveTextContent("physical geometry witness is unavailable");
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
