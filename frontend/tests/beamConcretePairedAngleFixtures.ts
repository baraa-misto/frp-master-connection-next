import type { BeamConcretePairedAngleDesignResponse, BeamConcretePairedAnglePreviewResponse, ExternalAnchorTrace, WallAnchorGroupResult, WallVector, WallWrench } from "../src/api/beamConcretePairedAngleContracts";
import type { ClipAngleQuantity } from "../src/api/clipAngleContracts";
import { loadBeamConcretePairedAngleBenchmark } from "../src/fixtures/beamConcretePairedAngleBenchmarks";
import { pairedClipAnglePreviewFixture } from "./pairedClipAngleFixtures";

function q(value: string, unit: string): ClipAngleQuantity {
  return { value, unit, canonical_value: value, canonical_unit: unit };
}
function vector(values: readonly [string, string, string], unit: string): WallVector {
  return { h: q(values[0], unit), v: q(values[1], unit), n: q(values[2], unit) };
}
function wrench(reference: readonly [string, string, string], force: readonly [string, string, string], moment: readonly [string, string, string]): WallWrench {
  return { reference_hvn: vector(reference, "in"), force_hvn: vector(force, "kip"), moment_hvn: vector(moment, "kip-in"), provenance: "EXACT_REFERENCE_TRANSLATION" };
}
function anchor(id: string, group: ExternalAnchorTrace["group_id"], h: string, v: string): ExternalAnchorTrace {
  return { anchor_id: id, group_id: group, coordinate_hvn: vector([h, v, "0"], "in"), wall_edge_distances: { negative_h: q("26", "in"), positive_h: q("22", "in"), negative_v: q("23", "in"), positive_v: q("25", "in") }, shank_start_hvn: vector([h, v, "0.5"], "in"), shank_end_hvn: vector([h, v, "-4"], "in"), hardware_configuration: "EXTERIOR_NUT_WASHER_WITH_BLIND_EMBEDDED_SHANK", capacity_status: "EXTERNAL_DESIGN_REQUIRED" };
}
function wallGroup(group: ExternalAnchorTrace["group_id"], h: string, momentN: string, anchors: readonly ExternalAnchorTrace[]): WallAnchorGroupResult {
  return { group_id: group, centroid_hvn: vector([h, "0", "0"], "in"), anchors, wrench: wrench([h, "0", "0"], ["0", "-2", "0"], ["8", "0", momentN]), nominal_demand: null, demand_label: "EXTERNAL_DESIGN_REQUIRED — BRANCH MOMENT CANNOT BE EQUILIBRATED BY A 1×1 INTERNAL DISTRIBUTION", force_equilibrium: true, moment_equilibrium: true, geometry_fingerprint: "a".repeat(64), result_fingerprint: "b".repeat(64) };
}

export function beamConcretePreviewFixture(status: "NOT_EVALUATED" | "FAIL" | "INVALID_GEOMETRY" = "NOT_EVALUATED"): BeamConcretePairedAnglePreviewResponse {
  const paired = pairedClipAnglePreviewFixture();
  const source = paired.result.visualization;
  if (source === null) throw new Error("Controlled paired visualization required.");
  const positiveAnchors = [anchor("POS-ANCHOR-R1-A1", "POSITIVE_WALL_ANCHOR_GROUP", "3", "0")];
  const negativeAnchors = [anchor("NEG-ANCHOR-R1-A1", "NEGATIVE_WALL_ANCHOR_GROUP", "-3", "0")];
  const positive = wallGroup("POSITIVE_WALL_ANCHOR_GROUP", "3", "6", positiveAnchors);
  const negative = wallGroup("NEGATIVE_WALL_ANCHOR_GROUP", "-3", "-6", negativeAnchors);
  const combined = wrench(["0", "0", "0"], ["0", "-4", "0"], ["16", "0", "0"]);
  const visualization = {
    schema_version: "0.1.0-draft" as const,
    wall_frame: { h_axis: ["1", "0", "0"] as const, v_axis: ["0", "1", "0"] as const, n_axis: ["0", "0", "1"] as const },
    boxes: [...source.boxes, { id: "concrete-wall-solid", owner_id: "concrete-wall", role: "CONCRETE_WALL", center: [q("0", "in"), q("4", "in"), q("0", "in")] as const, size_s: q("48", "in"), size_p: q("8", "in"), size_l: q("48", "in"), physical_element_id: null, material_region_id: null, basis: [["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"]] as const }],
    meshes: source.meshes,
    common_beam_bolts: source.common_member_bolts,
    external_anchors: [...positiveAnchors, ...negativeAnchors],
    common_bolt_diameter: q("0.5", "in"), common_hole_diameter: q("0.563", "in"),
    external_anchor_geometry: { nominal_diameter: q("0.5", "in"), hole_diameter: q("0.563", "in"), specified_embedment: q("4", "in"), washer_outside_diameter: q("1.0625", "in"), washer_thickness: q("0.109", "in"), system_classification: "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR" as const },
    material_regions: source.material_regions, beam_material_regions: source.connected_member_material_regions,
    reaction_shear: q("-4", "kip"), user_force_hvn: vector(["0", "-4", "0"], "kip"), user_moment_hvn: vector(["0", "0", "0"], "kip-in"), beam_reference_hvn: vector(["0", "0", "4"], "in"), wall_reference_hvn: vector(["0", "0", "0"], "in"),
    positive_branch_wrench: positive.wrench, negative_branch_wrench: negative.wrench, combined_wall_wrench: combined, selected_wall_surface_id: "CONCRETE_WALL:EXTERIOR_FACE" as const,
  };
  const invalid = status === "INVALID_GEOMETRY";
  const request = loadBeamConcretePairedAngleBenchmark("US_CUSTOMARY");
  const result = {
    request_id: request.request_id, orchestration_contract_version: "3.5A-R2-RC1" as const, preview_schema_version: "0.1.0-draft" as const,
    connector_kind: "BEAM_TO_CONCRETE_WALL_SYMMETRIC_PAIRED_CLIP_ANGLES" as const,
    symmetry_proof: { geometry_proven: !invalid, action_proven: true, equal_sharing_eligible: !invalid, reasons: invalid ? ["invalid"] : [] },
    common_beam_group: paired.result.common_member_group, positive_wall_group: positive, negative_wall_group: negative, combined_wall_wrench: combined,
    external_anchor_handoff: { handoff_fingerprint: "c".repeat(64), combined_wall_wrench: combined }, external_anchor_handoff_json: '{"handoff_fingerprint":"' + "c".repeat(64) + '"}',
    geometry_status: invalid ? "INVALID_GEOMETRY" as const : "VALID" as const, geometry_invalid_reasons: invalid ? ["ANCHOR_CENTER_OUTSIDE_FINITE_WALL"] : [], assembly_status: status,
    ordinary_pass_allowed: false as const, resistance_evaluated: false, design_check_ready: !invalid, external_design_required: true as const,
    limitations: [["CONCRETE_SUBSTRATE_RESISTANCE", "EXTERNAL_DESIGN_REQUIRED"], ["WALL_ANCHOR_INTERNAL_FORCE_DISTRIBUTION", "EXTERNAL_DESIGN_REQUIRED"]] as const, warnings: [], engineering_fingerprint: "d".repeat(64), application_fingerprint: "e".repeat(64), visualization: invalid ? null : visualization, handoff_mode: "BRANCH_RESOLVED" as const, branch_allocation_status: "RESOLVED" as const, common_group_normal_action: q("0", "kip"), action_reference_hvn: vector(["0", "0", "4"], "in"),
  };
  return { api_transport_schema_version: "0.1.0-draft", orchestration_contract_version: "3.5A-R2-RC1", preview_schema_version: "0.1.0-draft", request_id: request.request_id, geometry_status: result.geometry_status, geometry_invalid_reasons: result.geometry_invalid_reasons, assembly_status: status, ordinary_pass_allowed: false, resistance_evaluated: false, design_check_ready: !invalid, external_design_required: true, engineering_fingerprint: result.engineering_fingerprint, application_fingerprint: result.application_fingerprint, result };
}

export function beamConcreteDesignFixture(): BeamConcretePairedAngleDesignResponse {
  const preview = beamConcretePreviewFixture("FAIL").result;
  return { api_transport_schema_version: "0.1.0-draft", orchestration_contract_version: "3.5A-R2-RC1", request_id: preview.request_id, assembly_status: "FAIL", required_check_status: "NOT_EVALUATED", ordinary_pass_allowed: false, external_design_required: true, supported_beam_side_failure_present: true, result_fingerprint: "f".repeat(64), result: { preview } };
}
