import type {
  PairedBoltGroupResult,
  PairedClipAngleDesignResponse,
  PairedClipAnglePreviewResponse,
  PairedClipAngleVisualization,
} from "../src/api/pairedClipAngleContracts";
import { loadPairedClipAngleBenchmark } from "../src/fixtures/pairedClipAngleBenchmarks";
import { clipAnglePreviewFixture } from "./clipAngleFixtures";

function group(
  id: PairedBoltGroupResult["group_id"],
  physicalName: string,
  placement: ReturnType<typeof clipAnglePreviewFixture>["result"]["interface_a"]["placement"],
  demand: ReturnType<typeof clipAnglePreviewFixture>["result"]["interface_a"]["demand"],
): PairedBoltGroupResult {
  return {
    group_id: id,
    physical_name: physicalName,
    placement,
    demand,
    resistance: null,
    layer_demands: id === "COMMON_MEMBER_THROUGH_BOLT_GROUP"
      ? placement.bolts.flatMap((bolt) => [
          { bolt_id: bolt.bolt_id, layer_id: "POSITIVE_CONNECTED_LEG", parent_total_force: { u: { ...bolt.width_coordinate, unit: "kip" }, v: { ...bolt.width_coordinate, unit: "kip" } }, fraction_of_total: "0.5", force_u: { ...bolt.width_coordinate, unit: "kip" }, force_v: { ...bolt.width_coordinate, unit: "kip" }, total_force_magnitude: { ...bolt.width_coordinate, value: "0.5", unit: "kip" }, parent_demand_fingerprint: "a".repeat(64), symmetry_proof_fingerprint: "b".repeat(64) },
          { bolt_id: bolt.bolt_id, layer_id: "CONNECTED_MEMBER", parent_total_force: { u: { ...bolt.width_coordinate, unit: "kip" }, v: { ...bolt.width_coordinate, unit: "kip" } }, fraction_of_total: "1", force_u: { ...bolt.width_coordinate, unit: "kip" }, force_v: { ...bolt.width_coordinate, unit: "kip" }, total_force_magnitude: { ...bolt.width_coordinate, value: "1", unit: "kip" }, parent_demand_fingerprint: "a".repeat(64), symmetry_proof_fingerprint: "b".repeat(64) },
          { bolt_id: bolt.bolt_id, layer_id: "NEGATIVE_CONNECTED_LEG", parent_total_force: { u: { ...bolt.width_coordinate, unit: "kip" }, v: { ...bolt.width_coordinate, unit: "kip" } }, fraction_of_total: "0.5", force_u: { ...bolt.width_coordinate, unit: "kip" }, force_v: { ...bolt.width_coordinate, unit: "kip" }, total_force_magnitude: { ...bolt.width_coordinate, value: "0.5", unit: "kip" }, parent_demand_fingerprint: "a".repeat(64), symmetry_proof_fingerprint: "b".repeat(64) },
        ] as const)
      : [],
    result_fingerprint: id.slice(0, 1).toLowerCase().repeat(64),
  };
}

export function pairedClipAnglePreviewFixture(
  status: "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY" = "NOT_EVALUATED",
): PairedClipAnglePreviewResponse {
  const source = clipAnglePreviewFixture(status === "INVALID_GEOMETRY" ? status : "NOT_EVALUATED");
  const clip = source.result.visualization;
  const request = loadPairedClipAngleBenchmark("US_CUSTOMARY");
  const commonPlacement = structuredClone(source.result.interface_a.placement);
  const positivePlacement = structuredClone(source.result.interface_b.placement);
  const negativePlacement = structuredClone(source.result.interface_b.placement);
  commonPlacement.bolt_group_id = "COMMON_MEMBER_THROUGH_BOLT_GROUP";
  commonPlacement.bolts = commonPlacement.bolts.map((bolt) => ({
    ...bolt,
    bolt_id: bolt.bolt_id.replace("CLIP-A", "COMMON"),
    layer_ids: ["POSITIVE_CONNECTED_LEG", "CONNECTED_MEMBER", "NEGATIVE_CONNECTED_LEG"],
  }));
  positivePlacement.bolt_group_id = "POSITIVE_SUPPORT_BOLT_GROUP";
  positivePlacement.bolts = positivePlacement.bolts.map((bolt) => ({ ...bolt, bolt_id: bolt.bolt_id.replace("CLIP-B", "POS-SUPPORT") }));
  negativePlacement.bolt_group_id = "NEGATIVE_SUPPORT_BOLT_GROUP";
  negativePlacement.bolts = negativePlacement.bolts.map((bolt) => ({
    ...bolt,
    bolt_id: bolt.bolt_id.replace("CLIP-B", "NEG-SUPPORT"),
    global_center: [{ ...bolt.global_center[0], value: String(-Number(bolt.global_center[0].value)) }, bolt.global_center[1], bolt.global_center[2]],
  }));
  let visualization: PairedClipAngleVisualization | null = null;
  if (clip !== null) {
    const connector = clip.boxes.filter((box) => box.owner_id === "single-clip-angle-connector");
    const other = clip.boxes
      .filter((box) => box.owner_id !== "single-clip-angle-connector")
      .map((box) => box.owner_id === "clip-angle-connected-member"
        ? {
            ...box,
            physical_element_id: box.physical_element_id === null
              ? null
              : `${box.owner_id}:${box.physical_element_id}`,
            material_region_id: box.material_region_id === null
              ? null
              : `${box.owner_id}:${box.material_region_id}`,
          }
        : box);
    const positive = connector.map((box) => ({ ...box, id: `POSITIVE_CLIP_ANGLE:${box.id}`, owner_id: "POSITIVE_CLIP_ANGLE", physical_element_id: `POSITIVE_CLIP_ANGLE:${box.role}` }));
    const negative = connector.map((box) => ({
      ...box,
      id: `NEGATIVE_CLIP_ANGLE:${box.id}`,
      owner_id: "NEGATIVE_CLIP_ANGLE",
      physical_element_id: `NEGATIVE_CLIP_ANGLE:${box.role}`,
      center: [{ ...box.center[0], value: String(-Number(box.center[0].value)) }, box.center[1], box.center[2]] as const,
    }));
    visualization = {
      schema_version: "0.1.0-draft",
      semantic_frame: { ...clip.semantic_frame, symmetry_plane: "S_P = 0" },
      symmetry_plane: "S_P = 0",
      connected_member_profile_id: request.connected_member_profile.profile_id,
      connected_member_profile_family: request.connected_member_profile.profile_family,
      boxes: [...positive, ...negative, ...other],
      meshes: clip.meshes,
      common_member_bolts: commonPlacement.bolts,
      positive_support_bolts: positivePlacement.bolts,
      negative_support_bolts: negativePlacement.bolts,
      bolt_diameter: clip.bolt_diameter,
      hole_diameter: clip.hole_diameter,
      material_regions: [...positive, ...negative].map((box) => ({
        region_id: `${box.owner_id}:CLIP_ANGLE_${box.role}_REGION`,
        physical_element_id: box.physical_element_id,
        lw: ["0", "0", box.owner_id === "NEGATIVE_CLIP_ANGLE" ? "-1" : "1"] as const,
        cw: box.role === "CONNECTED_MEMBER_LEG"
          ? ["0", "-1", "0"] as const
          : [box.owner_id === "NEGATIVE_CLIP_ANGLE" ? "1" : "-1", "0", "0"] as const,
        tt: box.role === "CONNECTED_MEMBER_LEG"
          ? [box.owner_id === "NEGATIVE_CLIP_ANGLE" ? "-1" : "1", "0", "0"] as const
          : ["0", "-1", "0"] as const,
        source_id: "ICE_LOCKED_PULTRUDED_FRP",
        source_revision: "RC2",
      })),
      connected_member_material_regions: clip.connected_member_material_regions,
      selected_support_surface_id: clip.selected_support_surface_id,
      selected_connected_surface_id: clip.selected_connected_surface_id,
      trim: { ...clip.trim, reference_plane_id: "PAIRED_CLIP_ANGLE_SUPPORT_LEG_INNER_CLEARANCE_PLANE" },
      parent_force: { ...clip.global_force, z: { ...clip.global_force.z, value: "4" } },
      parent_moment: clip.global_moment,
      parent_reference_point: { ...clip.global_reference_point, x: { ...clip.global_reference_point.x, value: "0" } },
      branch_actions: [],
      support_target_id: request.support_target_id,
      support_profile: clip.support_profile,
      support_material_regions: clip.support_material_regions,
      rectangular_full_through_paths: [],
    };
  }
  const result = {
    request_id: request.request_id,
    orchestration_contract_version: "3.3C3-RC1" as const,
    preview_schema_version: "0.1.0-draft" as const,
    connector_kind: "SYMMETRIC_PAIRED_CLIP_ANGLES" as const,
    assembly_identity: "SYMMETRIC_PAIRED_CLIP_ANGLES" as const,
    symmetry_proof: { geometry_proven: status !== "INVALID_GEOMETRY", action_proven: true, equal_sharing_eligible: status !== "INVALID_GEOMETRY", reasons: status === "INVALID_GEOMETRY" ? ["PAIR_GEOMETRY_SYMMETRY_NOT_PROVEN"] : [] },
    branch_actions: [],
    common_member_group: group("COMMON_MEMBER_THROUGH_BOLT_GROUP", "Common Member Through-Bolt Group", commonPlacement, source.result.interface_a.demand),
    positive_support_group: group("POSITIVE_SUPPORT_BOLT_GROUP", "Positive Support Group", positivePlacement, source.result.interface_b.demand),
    negative_support_group: group("NEGATIVE_SUPPORT_BOLT_GROUP", "Negative Support Group", negativePlacement, source.result.interface_b.demand),
    material_regions: visualization?.material_regions ?? [],
    required_checks: ["PAIRED_CLIP_ANGLE_BODY_RESISTANCE", "COMMON_THROUGH_BOLT_DOUBLE_SHEAR_RESISTANCE", "PAIRED_CLIP_ANGLE_BRANCH_COMPATIBILITY", "PAIRED_FRP_CLIP_ANGLE_QUALIFICATION"],
    required_check_status: "NOT_EVALUATED" as const,
    geometry_status: status === "INVALID_GEOMETRY" ? "INVALID_GEOMETRY" as const : "VALID" as const,
    geometry_invalid_reasons: status === "INVALID_GEOMETRY" ? ["Controlled invalid geometry"] : [],
    assembly_status: status,
    ordinary_pass_allowed: false as const,
    resistance_evaluated: false,
    design_check_ready: status !== "INVALID_GEOMETRY",
    warnings: [],
    canonical_input_fingerprint: "c".repeat(64),
    connector_geometry_fingerprint: "d".repeat(64),
    engineering_fingerprint: "e".repeat(64),
    visualization,
    rectangular_full_through_paths: [],
    limitations: [],
    support_target_id: request.support_target_id,
  };
  return { api_transport_schema_version: "0.1.0-draft", orchestration_contract_version: "3.3C3-RC1", preview_schema_version: "0.1.0-draft", request_id: request.request_id, geometry_status: result.geometry_status, geometry_invalid_reasons: result.geometry_invalid_reasons, assembly_status: status, ordinary_pass_allowed: false, resistance_evaluated: false, design_check_ready: result.design_check_ready, warnings: [], engineering_fingerprint: result.engineering_fingerprint, result };
}

export function pairedClipAngleDesignFixture(): PairedClipAngleDesignResponse {
  const preview = pairedClipAnglePreviewFixture("FAIL").result;
  return { api_transport_schema_version: "0.1.0-draft", orchestration_contract_version: "3.3C3-RC1", request_id: preview.request_id, assembly_status: "FAIL", required_check_status: "NOT_EVALUATED", ordinary_pass_allowed: false, supported_interface_failure_present: true, result_fingerprint: "f".repeat(64), result: { preview: { ...preview, resistance_evaluated: true }, assembly_status: "FAIL", required_check_status: "NOT_EVALUATED", ordinary_pass_allowed: false, supported_interface_failure_present: true, result_fingerprint: "f".repeat(64) } };
}
