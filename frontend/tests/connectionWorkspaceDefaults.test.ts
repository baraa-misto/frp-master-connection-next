import { describe, expect, it } from "vitest";
import {
  loadTeeWorkspaceDefault, loadClipAngleWorkspaceDefault,
  loadPairedClipAngleWorkspaceDefault, loadMultiMemberTeeWorkspaceDefault,
} from "../src/fixtures/connectionWorkspaceDefaults";
import { loadTeeBenchmark } from "../src/fixtures/teeBenchmarks";
import { loadClipAngleC2Benchmark } from "../src/fixtures/clipAngleBenchmarks";
import { loadPairedClipAngleBenchmark } from "../src/fixtures/pairedClipAngleBenchmarks";
import * as multi from "../src/fixtures/multiMemberTeeBenchmarks";

describe.each(["US_CUSTOMARY", "SI"] as const)("Owner startup defaults %s", (units) => {
  const q = (us: string, si: string) => ({ value: units === "SI" ? si : us, unit: units === "SI" ? "mm" : "in" });
  const wide = {
    depth: q("8", "203.2"), flange_width: q("6", "152.4"),
    web_thickness: q("0.375", "9.525"), flange_thickness: q("0.375", "9.525"),
  };
  it("uses custom Tee dimensions, 45 degrees and two stem/four flange bolts without changing the historical fixture", () => {
    const historical = loadTeeBenchmark(units);
    const before = structuredClone(historical);
    const current = loadTeeWorkspaceDefault(units);
    expect(current.support_profile).toMatchObject(wide);
    expect(current.connected_member_profile).toMatchObject({
      size_basis: "CUSTOM_DIMENSIONS", profile_family: "ANGLE",
      dimensions: { leg_y: q("4", "101.6"), leg_z: q("4", "101.6"), thickness: q("0.5", "12.7") },
    });
    expect(current.brace_inclination_degrees).toBe("45");
    expect(current.interface_a_layout).toMatchObject({ row_count: 2, bolts_per_row: 1, vertical_offset: q("2", "50.8") });
    expect(current.interface_b_layout).toMatchObject({ row_count: 2, bolts_per_row: 2 });
    expect(current.bolt_diameter).toEqual(q("0.5", "12.7"));
    expect(current.connector_dimensions).toEqual(historical.connector_dimensions);
    expect(current.connected_member_end_trim_enabled).toBe(true);
    expect(current.connected_member_end_clearance).toEqual(q("0", "0"));
    expect(loadTeeBenchmark(units)).toEqual(before);
    expect(loadTeeWorkspaceDefault(units)).toEqual(current);
  });

  it("sets both clip modes to exact maximum extrusion and retains their distinct physical group ownership", () => {
    const single = loadClipAngleWorkspaceDefault(units);
    const paired = loadPairedClipAngleWorkspaceDefault(units);
    const historicalSingle = loadClipAngleC2Benchmark(units);
    const historicalPaired = loadPairedClipAngleBenchmark(units);
    for (const request of [single, paired]) {
      expect(request.support_profile).toMatchObject(wide);
      expect(request.connected_member_profile).toMatchObject({ profile_family: "WIDE_FLANGE_I", size_basis: "CUSTOM_DIMENSIONS", selected_profile_surface: "WEB_POS_FACE", dimensions: wide });
      expect(request.connected_member_inclination_degrees).toBe("0");
      expect(request.connector_dimensions.connector_length).toEqual(q("7.25", "184.15"));
      expect(request.bolt_diameter).toEqual(q("0.5", "12.7"));
    }
    for (const layout of [single.interface_a_layout, single.interface_b_layout, paired.common_member_layout, paired.mirrored_support_layout]) {
      expect(layout).toMatchObject({ row_count: 2, bolts_per_row: 1, pitch: q("2", "50.8"), negative_end_distance: q("2.625", "66.675"), positive_end_distance: q("2.625", "66.675") });
    }
    expect({ ...single.connector_dimensions, connector_length: historicalSingle.connector_dimensions.connector_length }).toEqual(historicalSingle.connector_dimensions);
    expect({ ...paired.connector_dimensions, connector_length: historicalPaired.connector_dimensions.connector_length }).toEqual(historicalPaired.connector_dimensions);
    expect(loadClipAngleC2Benchmark(units)).toEqual(historicalSingle);
    expect(loadPairedClipAngleBenchmark(units)).toEqual(historicalPaired);
    expect(loadClipAngleWorkspaceDefault(units)).toEqual(single);
    expect(loadPairedClipAngleWorkspaceDefault(units)).toEqual(paired);
  });

  it("keeps one shared Tee with six stem bolts and three two-bolt flange stations", () => {
    const historical = multi.loadMultiMemberTeeBenchmark(units);
    const request = loadMultiMemberTeeWorkspaceDefault(units);
    expect(request.support_profile).toMatchObject(wide);
    expect(request.connector_dimensions).toEqual(historical.connector_dimensions);
    expect(request.support_group).toMatchObject({ row_count: 3, bolts_per_row: 2, pitch: q("7.5", "190.5"), gauge: historical.support_group.gauge });
    expect(request.bolt_diameter).toEqual(q("0.5", "12.7"));
    expect(request.upper_brace).toMatchObject({ inclination_degrees: "30", anchor_v: q("7.5", "190.5") });
    expect(request.lower_brace).toMatchObject({ inclination_degrees: "-30", anchor_v: q("-7.5", "-190.5") });
    expect(request.middle_beam).toMatchObject({ inclination_degrees: "0", profile: { dimensions: { depth: q("6", "152.4"), flange_width: q("3", "76.2"), web_thickness: q("0.25", "6.35"), flange_thickness: q("0.25", "6.35") } } });
    for (const key of ["upper_brace", "middle_beam", "lower_brace"] as const) {
      expect(request[key]?.bolt_group).toMatchObject({ row_count: 2, bolts_per_row: 1 });
      expect(request[key]?.action).toEqual(historical[key].action);
    }
    for (const slot of [request.upper_brace, request.lower_brace]) {
      expect(slot).toMatchObject({ trim_enabled: true, trim_clearance: q("0", "0"), profile: { size_basis: "CUSTOM_DIMENSIONS", dimensions: { leg_y: q("4", "101.6"), leg_z: q("4", "101.6"), thickness: q("0.5", "12.7") } } });
    }
    expect(multi.loadMultiMemberTeeBenchmark(units)).toEqual(historical);
    expect(loadMultiMemberTeeWorkspaceDefault(units)).toEqual(request);
  });
});
