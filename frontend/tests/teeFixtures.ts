import type { VisualizationSnapshot } from "../src/api/contracts";
import type {
  TeeConnectorDesignResponse,
  TeeConnectorPreviewResponse,
  TeeConnectorRequest,
  TeeConnectedMemberProfileTrace,
  TeeInterfaceResult,
  TeeInterfacePlacementTrace,
  TeeVisualization,
} from "../src/api/teeContracts";
import { visualizationFixture } from "./fixtures";

function connectedProfileTrace(): TeeConnectedMemberProfileTrace {
  return {
    profile_id: "tee-connected-brace-profile",
    member_id: "tee-brace",
    role: "BRACE",
    profile_family: "ANGLE",
    size_basis: "CUSTOM_DIMENSIONS",
    dimensions: { member_length: "8", leg_y: "4", leg_z: "3", thickness: "0.5" },
    profile_orientation: "ROTATION_0",
    selected_profile_surface: "LEG_Y_OUTER",
    material_kind: "PULTRUDED_FRP",
    member_profile_fingerprint: "c".repeat(64),
    profile_geometry_fingerprint: "d".repeat(64),
    surface_patch_id: "patch-a",
    physical_element_role: "LEG_Y",
    brace_inclination_degrees: "0",
    brace_inclination_sine: "0",
    brace_inclination_cosine: "1",
    brace_placement_frame: {
      origin: { x: "0", y: "0", z: "0" },
      x_axis: { x: "1", y: "0", z: "0" },
      y_axis: { x: "0", y: "1", z: "0" },
      z_axis: { x: "0", y: "0", z: "1" },
    },
  };
}

function movedBolt(
  source: VisualizationSnapshot["bolt"],
  id: string,
  row: number,
  line: number,
): VisualizationSnapshot["bolt"] {
  const bolt = structuredClone(source);
  bolt.bolt_location_id = id;
  const move = (point: { x: string; y: string; z: string }) => {
    point.y = String(Number(point.y) + row);
    point.z = String(Number(point.z) + line);
  };
  move(bolt.center);
  move(bolt.stack_start);
  move(bolt.stack_end);
  bolt.holes.forEach((hole) => {
    hole.id = `${id}:${hole.id}`;
    move(hole.start);
    move(hole.end);
  });
  bolt.washers.forEach((washer) => {
    washer.id = `${id}:${washer.id}`;
    move(washer.start);
    move(washer.end);
  });
  return bolt;
}

export function teeVisualizationFixture(): TeeVisualization {
  const first = visualizationFixture();
  const primitive = first.primitives[0];
  if (primitive === undefined) throw new Error("A box primitive fixture is required.");
  first.components.push({
    id: "tee-connector",
    label: "Pultruded FRP Tee connector",
    participant_kind: "CONNECTOR_COMPONENT",
    material_kind: "PULTRUDED_FRP",
    section_family: "TEE",
    frame_id: "CONNECTOR_LOCAL:tee-connector",
    connected_end: null,
    elements: [],
    deferred_primitive_ids: [],
  });
  first.primitives.push(
    {
      ...structuredClone(primitive),
      id: "tee-connector:FLANGE",
      label: "Tee flange",
      owner_id: "tee-connector",
      physical_element_id: "FLANGE",
      material_region_id: "FLANGE",
    },
    {
      ...structuredClone(primitive),
      id: "tee-connector:STEM",
      label: "Tee stem",
      owner_id: "tee-connector",
      physical_element_id: "STEM",
      material_region_id: "STEM",
    },
  );
  const second = visualizationFixture();
  second.interface_id = "TEE_INTERFACE_B_FLANGE_TO_SUPPORT";
  second.bolt_group_id = "tee-bolt-group-b";
  second.frames = second.frames.map((frame) => ({ ...frame, id: `${frame.id}:B` }));
  const make = (prefix: "A" | "B", source: VisualizationSnapshot) => [
    movedBolt(source.bolt, `${prefix}_B_R1_L1`, 0, 0),
    movedBolt(source.bolt, `${prefix}_B_R1_L2`, 0, 2),
    movedBolt(source.bolt, `${prefix}_B_R2_L1`, 2, 0),
    movedBolt(source.bolt, `${prefix}_B_R2_L2`, 2, 2),
  ];
  return {
    schema_version: "0.3.0-draft",
    base_connection: first,
    interface_b_connection: second,
    interface_zones: [...first.interface_zones, ...second.interface_zones],
    interface_a_bolts: make("A", first),
    interface_b_bolts: make("B", second),
    selected_support_surface_id: "patch-b",
    connected_member_profile: connectedProfileTrace(),
    selected_connected_surface_id: "LEG_Y_OUTER",
    selected_connected_surface_patch_id: "patch-a",
    support_target_id: "W_COLUMN_FLANGE",
    support_profile: {
      target_id: "W_COLUMN_FLANGE",
      profile_family: "WIDE_FLANGE_I",
      selected_profile_surface: "FLANGE_POS_OUTER",
    },
    rectangular_full_through_paths: [],
  };
}

function interfaceResult(prefix: "a" | "b", normal = "0"): TeeInterfaceResult {
  const quantity = (value: string) => ({ value, unit: "in" });
  const placement: TeeInterfacePlacementTrace = {
    datum_id: prefix === "a" ? "TEE_STEM_CENTER_DATUM_A" : "TEE_FLANGE_CENTER_DATUM_B",
    datum_point: { x: "0", y: "0", z: "0" },
    vertical_axis: { x: "0", y: "1", z: "0" },
    horizontal_axis: { x: "1", y: "0", z: "0" },
    normal_axis: { x: "0", y: "0", z: "1" },
    placement_mode: "EDGE_DISTANCE_CONTROLLED",
    vertical_offset: quantity("-2"),
    horizontal_offset: quantity(prefix === "a" ? "0" : "-1"),
    equivalent_edge_distances: {
      row_count: 2,
      bolts_per_row: 2,
      pitch: "2",
      gauge: "2",
      unloaded_end_distance: "1",
      loaded_end_distance: "1",
      negative_side_distance: "1",
      positive_side_distance: "1",
      placement_mode: "EDGE_DISTANCE_CONTROLLED",
      vertical_offset: null,
      horizontal_offset: null,
    },
    clearances: {
      vertical_positive: quantity("0.7185"),
      vertical_negative: quantity("0.7185"),
      horizontal_positive: quantity("0.7185"),
      horizontal_negative: quantity("0.7185"),
      minimum: quantity("0.7185"),
      governing_bolt_id: `${prefix.toUpperCase()}_B_R1_L1`,
      governing_boundary_id: `${prefix}:VERTICAL_NEGATIVE`,
      exact_deficit: null,
      geometry_valid: true,
      minimum_complete_hole_containment: prefix === "a" ? quantity("1.2815") : null,
      tee_positive_end_coordinate: quantity("4"),
      tee_negative_end_coordinate: quantity("-4"),
      tee_positive_end_complete_hole_clearance: quantity("2.7185"),
      tee_negative_end_complete_hole_clearance: quantity("0.7185"),
      governing_tee_end_id: "TEE_NEGATIVE_L_END",
      governing_tee_end_bolt_id: `${prefix.toUpperCase()}_B_R1_L1`,
      minimum_tee_end_complete_hole_clearance: quantity("0.7185"),
    },
    physical_geometry_fingerprint: prefix.repeat(64),
    method_compatibility: "COMPATIBLE",
    bolt_centers_hvn: [
      { x: "-1", y: "-1", z: "0" },
      { x: "1", y: "-1", z: "0" },
      { x: "-1", y: "1", z: "0" },
      { x: "1", y: "1", z: "0" },
    ],
  };
  return {
    interface_id: prefix === "a"
      ? "TEE_INTERFACE_A_BRACE_TO_STEM"
      : "TEE_INTERFACE_B_FLANGE_TO_SUPPORT",
    bolt_group_id: `tee-bolt-group-${prefix}`,
    normal_component: {
      value: normal,
      unit: "kip",
    },
    automatic_axis_tension_generated: false,
    normal_action_supported: normal === "0",
    preview: {
      automatic_demand_result: { availability: "CALCULATED" },
    } as TeeInterfaceResult["preview"],
    design: null,
    interface_fingerprint: prefix.repeat(64),
    placement,
  };
}

export function teePreviewFixture(
  status: TeeConnectorPreviewResponse["assembly_status"] = "NOT_EVALUATED",
): TeeConnectorPreviewResponse {
  const a = interfaceResult("a");
  const b = interfaceResult("b");
  const result = {
    request_id: "TEE-WORKSPACE-US_CUSTOMARY",
    orchestration_contract_version: "3.3C2-RC1" as const,
    preview_schema_version: "0.3.0-draft" as const,
    support_role: "COLUMN" as const,
    selected_support_flange: "POSITIVE_LOCAL_Z" as const,
    connector_dimensions: {
      connector_length: "8",
      flange_width: "6",
      flange_thickness: ".5",
      stem_depth: "4",
      stem_thickness: ".375",
    },
    tee_longitudinal_placement: {
      tee_longitudinal_datum_id: "TEE_TEMPLATE_LONGITUDINAL_DATUM" as const,
      datum_point: { x: "2.25", y: "0", z: "0" },
      longitudinal_axis: { x: "0", y: "0", z: "1" },
      connector_length_anchor: "CENTER" as const,
      connector_length_anchor_position: { value: "0", unit: "in" },
      body_center_coordinate: { value: "0", unit: "in" },
      positive_end_coordinate: { value: "4", unit: "in" },
      negative_end_coordinate: { value: "-4", unit: "in" },
      body_geometry_fingerprint: "e".repeat(64),
    },
    connected_member_profile: connectedProfileTrace(),
    connected_member_end_trim: {
      enabled: false,
      normalized_clearance: null,
      reference_plane_id: "TEE_FLANGE_INNER_CLEARANCE_PLANE" as const,
      reference_plane_origin: { x: "0.5", y: "0", z: "0" },
      reference_plane_normal: { x: "1", y: "0", z: "0" },
      cut_plane_id: null,
      cut_plane_origin: null,
      cut_plane_normal: null,
      measured_plane_clearance: null,
      interference_status: "CLEAR" as const,
      interfering_physical_element_ids: [],
      trimmed_member_geometry_identity: null,
      fabricated_trim_edge_ids: [],
      bolt_clearances: [],
      governing_bolt_id: null,
      governing_trim_edge_id: null,
      minimum_hole_edge_clearance: null,
      exact_deficit: null,
      recovery_guidance: null,
      geometry_valid: true,
    },
    material_authority: {
      connector_material_family: "PULTRUDED_FRP" as const,
      fastener_material_family: "STAINLESS_STEEL_316" as const,
      fastener_snapshot_id: "ASTM_F593_17_GROUP_2_316_316L" as const,
      metallic_bolt_eligibility: { status: "BLOCKED_EXPLICIT_FNT_REQUIRED" },
    },
    interface_a: a,
    interface_b: b,
    tee_body_resistance_status: "NOT_EVALUATED" as const,
    assembly_status: status,
    ordinary_pass_allowed: false as const,
    resistance_evaluated: false as const,
    design_check_ready: status !== "INVALID_GEOMETRY",
    warnings: [],
    engineering_fingerprint: "a".repeat(64),
    visualization: teeVisualizationFixture(),
    support_target_id: "W_COLUMN_FLANGE" as const,
    rectangular_full_through_paths: [],
    design_limitations: [],
  };
  return {
    api_transport_schema_version: "0.1.0-draft",
    orchestration_contract_version: "3.3C2-RC1",
    preview_schema_version: "0.3.0-draft",
    request_id: result.request_id,
    support_role: result.support_role,
    selected_support_flange: result.selected_support_flange,
    assembly_status: status,
    ordinary_pass_allowed: false,
    resistance_evaluated: false,
    design_check_ready: result.design_check_ready,
    warnings: [],
    engineering_fingerprint: result.engineering_fingerprint,
    result,
  };
}

export function teeDesignFixture(
  status: TeeConnectorDesignResponse["assembly_status"] = "NOT_EVALUATED",
): TeeConnectorDesignResponse {
  const preview = teePreviewFixture(status).result;
  const handoff = {
    coverage: "PARTIAL",
    overall_disposition: status === "FAIL" ? "FAIL" : "NOT_EVALUATED",
  };
  const a = {
    ...preview.interface_a,
    design: {
      automatic_handoff_results: [handoff],
      automatic_demand_result: preview.interface_a.preview.automatic_demand_result,
    } as TeeInterfaceResult["design"],
  };
  const b = {
    ...preview.interface_b,
    design: {
      automatic_handoff_results: [handoff],
      automatic_demand_result: preview.interface_b.preview.automatic_demand_result,
    } as TeeInterfaceResult["design"],
  };
  const result = {
    preview: { ...preview, interface_a: a, interface_b: b },
    interface_a: a,
    interface_b: b,
    tee_body_resistance_status: "NOT_EVALUATED" as const,
    assembly_status: status,
    ordinary_pass_allowed: false as const,
    supported_interface_failure_present: status === "FAIL",
    result_fingerprint: "b".repeat(64),
  };
  return {
    api_transport_schema_version: "0.1.0-draft",
    orchestration_contract_version: "3.3C2-RC1",
    request_id: preview.request_id,
    assembly_status: status,
    tee_body_resistance_status: "NOT_EVALUATED",
    ordinary_pass_allowed: false,
    supported_interface_failure_present: status === "FAIL",
    result_fingerprint: result.result_fingerprint,
    result,
  };
}

export function minimalTeeRequest(): TeeConnectorRequest {
  return { request_id: "TEE" } as TeeConnectorRequest;
}
