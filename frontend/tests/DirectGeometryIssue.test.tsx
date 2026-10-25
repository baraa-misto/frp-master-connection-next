import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { DirectGeometryIssue } from "../src/features/DirectGeometryIssue";
import { clearanceWitness } from "./directGeometryIssueFixtures";

it("draws only the authenticated boundary dimension and separately identifies footprints", () => {
  const original = structuredClone(clearanceWitness);
  render(<DirectGeometryIssue record={clearanceWitness} unit="in" />);
  expect(screen.getByRole("img")).toHaveAccessibleName("Backend boundary dimension: 0.086 in; required 0.750 in");
  const line = screen.getByTestId("canonical-boundary-dimension");
  expect(line).toHaveAttribute("x1", "0.086");
  expect(line).toHaveAttribute("x2", "0");
  expect(line).toHaveAttribute("y1", "2");
  expect(line).toHaveAttribute("y2", "2");
  expect(screen.getByText(/Hole radius 0.2815 in; washer radius 0.5000 in/)).toBeVisible();
  expect(screen.getByText(/Bolt-to-bolt spacing is a separate/)).toBeVisible();
  expect(screen.getByRole("table")).toHaveTextContent("E27.914000");
  expect(clearanceWitness).toEqual(original);
});

it("identifies missing controlling evidence without deriving a substitute dimension", () => {
  render(<DirectGeometryIssue record={{ ...clearanceWitness, controlling_boundary_id: "MISSING" }} unit="mm" />);
  expect(screen.getByRole("alert")).toHaveTextContent("controlling boundary is unavailable");
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});
