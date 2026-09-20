import type {
  ClipAngleBoltTrace,
  ClipAngleDesignResponse,
  ClipAngleInterfaceResult,
  ClipAnglePreviewResponse,
  ClipAngleQuantity,
  ClipAngleRequest,
  ClipAngleVisualization,
} from "../src/api/clipAngleContracts";
import { loadClipAngleC2Benchmark } from "../src/fixtures/clipAngleBenchmarks";

export const MATERIAL_AXIS_SUPPORT_MATRIX = [
  { targetId: "W_COLUMN_FLANGE", family: "WIDE_FLANGE_I", selectedSurface: "FLANGE_POS_OUTER", elements: ["WEB", "TOP_FLANGE", "BOTTOM_FLANGE"] },
  { targetId: "W_BEAM_FLANGE", family: "WIDE_FLANGE_I", selectedSurface: "FLANGE_POS_OUTER", elements: ["WEB", "TOP_FLANGE", "BOTTOM_FLANGE"] },
  { targetId: "W_COLUMN_WEB", family: "WIDE_FLANGE_I", selectedSurface: "WEB_POS_FACE", elements: ["WEB", "TOP_FLANGE", "BOTTOM_FLANGE"] },
  { targetId: "CHANNEL_COLUMN_WEB", family: "CHANNEL", selectedSurface: "WEB_OUTER", elements: ["WEB", "TOP_FLANGE", "BOTTOM_FLANGE"] },
  { targetId: "ANGLE_COLUMN_LEG", family: "ANGLE", selectedSurface: "LEG_Y_OUTER", elements: ["LEG_1", "LEG_2"] },
  { targetId: "RECTANGULAR_HOLLOW_COLUMN_WALL", family: "RECTANGULAR_HOLLOW_SECTION", selectedSurface: "Z_POS_FACE", elements: ["TOP_WALL", "BOTTOM_WALL", "SIDE_WALL_1", "SIDE_WALL_2"] },
  { targetId: "SOLID_RECTANGULAR_COLUMN_FACE", family: "SOLID_RECTANGULAR_SECTION", selectedSurface: "Z_POS_FACE", elements: ["PLATE"] },
] as const;

export const MATERIAL_AXIS_CONNECTED_PROFILE_MATRIX = [
  { family: "FLAT_PLATE", elements: ["PLATE"] },
  { family: "WIDE_FLANGE_I", elements: ["WEB", "TOP_FLANGE", "BOTTOM_FLANGE"] },
  { family: "CHANNEL", elements: ["WEB", "TOP_FLANGE", "BOTTOM_FLANGE"] },
  { family: "ANGLE", elements: ["LEG_1", "LEG_2"] },
  { family: "RECTANGULAR_HOLLOW_SECTION", elements: ["TOP_WALL", "BOTTOM_WALL", "SIDE_WALL_1", "SIDE_WALL_2"] },
  { family: "SOLID_RECTANGULAR_SECTION", elements: ["PLATE"] },
] as const;

type MaterialAxisVisualization = Pick<
  ClipAngleVisualization,
  | "boxes"
  | "connected_member_material_regions"
  | "connected_member_profile_family"
  | "support_material_regions"
  | "support_profile"
  | "support_target_id"
>;

export function withConnectedMaterialGeometry<T extends MaterialAxisVisualization>(
  source: T,
  entry: (typeof MATERIAL_AXIS_CONNECTED_PROFILE_MATRIX)[number],
): T {
  const result = structuredClone(source);
  const ownerId = "clip-angle-connected-member";
  const template = result.boxes.find((value) => value.owner_id === ownerId);
  const material = result.connected_member_material_regions[0];
  if (template === undefined || material === undefined) {
    throw new Error("Connected material-axis fixture requires physical and material templates.");
  }
  const ownerQualified = template.physical_element_id?.startsWith(`${ownerId}:`) === true;
  const qualified = (value: string) => ownerQualified ? `${ownerId}:${value}` : value;
  result.connected_member_profile_family = entry.family;
  result.boxes = [
    ...result.boxes.filter((value) => value.owner_id !== ownerId),
    ...entry.elements.map((element, index) => ({
      ...template,
      id: `MEMBER:${ownerId}:${element}:${String(index)}`,
      role: element,
      physical_element_id: qualified(element),
      material_region_id: qualified(`${element}_REGION`),
      center: [
        template.center[0],
        template.center[1],
        { ...template.center[2], value: String(index) },
      ] as const,
    })),
  ];
  result.connected_member_material_regions = entry.elements.map((element) => ({
    ...material,
    id: `${ownerId}:${element}:material-axes`,
    physical_element_id: element,
    material_region_id: `${element}_REGION`,
  }));
  return result;
}

export function withSupportMaterialGeometry<T extends MaterialAxisVisualization>(
  source: T,
  entry: (typeof MATERIAL_AXIS_SUPPORT_MATRIX)[number],
): T {
  const result = structuredClone(source);
  const template = result.boxes.find((value) => value.owner_id === "clip-angle-support");
  const material = result.support_material_regions[0];
  if (template === undefined || material === undefined) {
    throw new Error("Support material-axis fixture requires physical and material templates.");
  }
  result.support_target_id = entry.targetId;
  result.support_profile = {
    ...result.support_profile,
    target_id: entry.targetId,
    profile_family: entry.family,
    selected_surface: entry.selectedSurface,
  };
  result.boxes = [
    ...result.boxes.filter((value) => value.owner_id !== "clip-angle-support"),
    ...entry.elements.map((element, index) => ({
      ...template,
      id: `clip-angle-support:${element}:${String(index)}`,
      role: element,
      physical_element_id: element,
      material_region_id: `${element}_REGION`,
      center: [
        template.center[0],
        template.center[1],
        { ...template.center[2], value: String(index) },
      ] as const,
    })),
  ];
  result.support_material_regions = entry.elements.map((element) => ({
    ...material,
    id: `clip-angle-support:${element}:material-axes`,
    physical_element_id: element,
    material_region_id: `${element}_REGION`,
  }));
  return result;
}

function quantity(value: string, unit = "in"): ClipAngleQuantity {
  return { value, unit, canonical_value: value, canonical_unit: unit };
}

function point(x: string, y: string, z: string): ClipAngleBoltTrace["global_center"] {
  return [quantity(x), quantity(y), quantity(z)];
}

function sceneBox(
  id: string,
  ownerId: string,
  role: string,
  center: ClipAngleBoltTrace["global_center"],
  sizes: readonly [string, string, string],
  physicalElementId: string | null = null,
  materialRegionId: string | null = null,
  basis: ClipAngleVisualization["boxes"][number]["basis"] = [
    ["1", "0", "0"],
    ["0", "1", "0"],
    ["0", "0", "1"],
  ],
): ClipAngleVisualization["boxes"][number] {
  return {
    id,
    owner_id: ownerId,
    role,
    center,
    size_s: quantity(sizes[0]),
    size_p: quantity(sizes[1]),
    size_l: quantity(sizes[2]),
    physical_element_id: physicalElementId,
    material_region_id: materialRegionId,
    basis,
  };
}

function bolts(interfaceLetter: "A" | "B"): readonly ClipAngleBoltTrace[] {
  const widths = ["1.25", "3.25"];
  const lengths = ["-1", "1"];
  return lengths.flatMap((length, row) => widths.map((width, line) => {
    const a = interfaceLetter === "A";
    return {
      bolt_id: `CLIP-${interfaceLetter}-R${String(row + 1)}-B${String(line + 1)}`,
      row_id: `ROW_${String(row + 1)}`,
      bolt_line_id: `BOLT_LINE_${String(line + 1)}`,
      width_coordinate: quantity(width),
      length_coordinate: quantity(length),
      global_center: a ? point("0", width, length) : point(width, "0", length),
      axis: a ? ["1", "0", "0"] : ["0", "-1", "0"],
      layer_ids: a
        ? ["clip-angle-connected-member:SELECTED_PROFILE_REGION", "single-clip-angle-connector:CONNECTED_MEMBER_LEG"]
        : ["single-clip-angle-connector:SUPPORT_LEG", "clip-angle-support:SELECTED_W_FLANGE"],
      stack_start: a ? point("-0.375", width, length) : point(width, "0.5", length),
      stack_end: a ? point("0.5", width, length) : point(width, "-0.75", length),
    };
  }));
}

function interfaceResult(letter: "A" | "B"): ClipAngleInterfaceResult {
  const interfaceBolts = bolts(letter);
  return {
    interface_id: letter === "A"
      ? "CLIP_ANGLE_INTERFACE_A_CONNECTED_MEMBER_TO_CONNECTED_LEG"
      : "CLIP_ANGLE_INTERFACE_B_SUPPORT_LEG_TO_SUPPORT",
    physical_name: letter === "A"
      ? "Connected Member ↔ Clip-Angle Connected Leg"
      : "Clip-Angle Support Leg ↔ Support",
    bolt_group_id: `clip-angle-bolt-group-${letter.toLowerCase()}`,
    normal_component: quantity("0", "kip"),
    normal_action_supported: true,
    automatic_axis_tension_generated: false,
    prying_generated: false,
    demand: {
      availability: "CALCULATED",
      method_applicability: "ASCE_PRESCRIPTIVE",
      qualification: "QUALIFIED_ASCE_PRESCRIPTIVE",
      scenarios: [{
        residual_moment: quantity("0", "kip-in"),
        per_bolt: interfaceBolts.map((bolt) => ({
          bolt_id: bolt.bolt_id,
          total_force_magnitude: quantity("0.75", "kip"),
        })),
      }],
      input_fingerprint: letter.repeat(64),
      result_fingerprint: letter.toLowerCase().repeat(64),
    },
    resistance: null,
    placement: {
      interface_id: letter === "A"
        ? "CONNECTED_MEMBER_TO_CLIP_ANGLE"
        : "CLIP_ANGLE_TO_SUPPORT",
      bolt_group_id: `clip-angle-bolt-group-${letter.toLowerCase()}`,
      width_axis: letter === "A" ? ["0", "1", "0"] : ["1", "0", "0"],
      length_axis: ["0", "0", "1"],
      normal_axis: letter === "A" ? ["1", "0", "0"] : ["0", "-1", "0"],
      width_coordinates: [quantity("1.25"), quantity("3.25")],
      length_coordinates: [quantity("-1"), quantity("1")],
      bolts: interfaceBolts,
      clearances: {
        heel: quantity("0.4685"),
        free_edge: quantity("0.4685"),
        positive_length_end: quantity("2.7185"),
        negative_length_end: quantity("2.7185"),
        minimum: quantity("0.4685"),
        governing_bolt_id: `CLIP-${letter}-R1-B1`,
        governing_boundary_id: "HEEL",
        exact_deficit: null,
        geometry_valid: true,
      },
      geometry_fingerprint: letter.repeat(64),
    },
    interface_fingerprint: letter.repeat(64),
  };
}

export function minimalClipAngleRequest(): ClipAngleRequest {
  return loadClipAngleC2Benchmark("US_CUSTOMARY");
}

export function clipAnglePreviewFixture(
  status: "FAIL" | "NOT_EVALUATED" | "INVALID_GEOMETRY" = "NOT_EVALUATED",
): ClipAnglePreviewResponse {
  const request = minimalClipAngleRequest();
  const interfaceA = interfaceResult("A");
  const interfaceB = interfaceResult("B");
  const visualization = status === "INVALID_GEOMETRY" ? null : {
    schema_version: "0.1.0-draft" as const,
    semantic_frame: {
      s_axis: ["1", "0", "0"] as const,
      p_axis: ["0", "1", "0"] as const,
      l_axis: ["0", "0", "1"] as const,
      handedness: "S_C cross P_C = L_C",
    },
    connected_member_profile_id: request.connected_member_profile.profile_id,
    connected_member_role: request.connected_member_profile.role,
    connected_member_profile_family: request.connected_member_profile.profile_family,
    connected_member_profile_orientation: request.connected_member_profile.profile_orientation,
    boxes: [
      sceneBox("clip-angle-connected-leg-solid", "single-clip-angle-connector", "CONNECTED_MEMBER_LEG", point("0.25", "2", "0"), ["0.5", "4", "8"]),
      sceneBox("clip-angle-support-leg-solid", "single-clip-angle-connector", "SUPPORT_LEG", point("2", "0.25", "0"), ["4", "0.5", "8"]),
      sceneBox("clip-angle-support-selected-flange", "clip-angle-support", "TOP_FLANGE", point("0", "-0.375", "0"), ["8", "0.75", "16"], "TOP_FLANGE", "FLANGES"),
      sceneBox("clip-angle-support-web", "clip-angle-support", "WEB", point("0", "-4", "0"), ["0.5", "6.5", "16"], "WEB", "WEB"),
      sceneBox("clip-angle-support-opposite-flange", "clip-angle-support", "BOTTOM_FLANGE", point("0", "-7.625", "0"), ["8", "0.75", "16"], "BOTTOM_FLANGE", "FLANGES"),
      sceneBox(
        "MEMBER:clip-angle-connected-member:PLATE:0",
        "clip-angle-connected-member",
        "PLATE",
        point("-0.1875", "4.5", "0"),
        ["8", "6", "0.375"],
        "PLATE",
        "PLATE",
        [["0", "1", "0"], ["0", "0", "1"], ["-1", "0", "0"]],
      ),
    ],
    meshes: [],
    interface_a_bolts: bolts("A"),
    interface_b_bolts: bolts("B"),
    bolt_diameter: quantity("0.5"),
    hole_diameter: quantity("0.563"),
    material_regions: [
      { region_id: "CLIP_ANGLE_CONNECTED_MEMBER_LEG_REGION", physical_element_id: "CONNECTED_MEMBER_LEG", lw: ["0", "0", "1"] as const, cw: ["0", "-1", "0"] as const, tt: ["1", "0", "0"] as const, source_id: "ICE_LOCKED_PULTRUDED_FRP", source_revision: "RC2" },
      { region_id: "CLIP_ANGLE_SUPPORT_LEG_REGION", physical_element_id: "SUPPORT_LEG", lw: ["0", "0", "1"] as const, cw: ["-1", "0", "0"] as const, tt: ["0", "-1", "0"] as const, source_id: "ICE_LOCKED_PULTRUDED_FRP", source_revision: "RC2" },
    ],
    connected_member_material_regions: [
      {
        id: "clip-angle-connected-member:PLATE:material-axes",
        physical_element_id: "PLATE",
        material_region_id: "PLATE",
        origin: point("0", "4.5", "0"),
        lw: ["0", "1", "0"] as const,
        cw: ["0", "0", "1"] as const,
        tt: ["1", "0", "0"] as const,
      },
    ],
    selected_support_surface_id: "clip-angle-support:POSITIVE_LOCAL_Z",
    selected_connected_surface_id: "clip-angle-connected-member:FACE_POS",
    trim: {
      enabled: false,
      reference_plane_id: "CLIP_ANGLE_SUPPORT_LEG_INNER_CLEARANCE_PLANE",
      reference_plane_origin: point("0", "0.5", "0"),
      reference_plane_normal: ["0", "1", "0"] as const,
      cut_plane_id: null,
      cut_plane_origin: null,
      cut_plane_normal: null,
      measured_plane_clearance: null,
      interference_status: "CLEAR",
      geometry_valid: true,
      trimmed_member_geometry_identity: null,
      fabricated_trim_edge_ids: [],
      fabricated_trim_edge_id: null,
      bolt_clearances: [],
      governing_bolt_id: null,
      governing_trim_edge_id: null,
      minimum_hole_edge_clearance: null,
      exact_deficit: null,
    },
    global_force: { x: quantity(request.global_force.x, "kip"), y: quantity(request.global_force.y, "kip"), z: quantity(request.global_force.z, "kip") },
    global_moment: { x: quantity("0", "kip-in"), y: quantity("0", "kip-in"), z: quantity("0", "kip-in") },
    global_reference_point: { x: quantity("2.25"), y: quantity("2.25"), z: quantity("0") },
    support_target_id: request.support_target_id,
    support_profile: {
      target_id: request.support_target_id,
      profile_id: request.support_profile.profile_id,
      profile_family: request.support_profile.profile_family,
      role: request.support_profile.role,
      dimensions: {
        member_length: "12",
        depth: "8",
        flange_width: "8",
        web_thickness: "0.5",
        flange_thickness: "0.5",
      },
      orientation: request.support_profile.profile_orientation,
      selected_surface: request.support_profile.selected_profile_surface,
    },
    support_material_regions: [
      {
        id: "clip-angle-support:WEB:material-axes",
        physical_element_id: "WEB",
        material_region_id: "WEB",
        origin: point("0", "-4", "0"),
        lw: ["0", "0", "1"] as const,
        cw: ["0", "-1", "0"] as const,
        tt: ["1", "0", "0"] as const,
      },
      {
        id: "clip-angle-support:TOP_FLANGE:material-axes",
        physical_element_id: "TOP_FLANGE",
        material_region_id: "FLANGES",
        origin: point("0", "-0.375", "0"),
        lw: ["0", "0", "1"] as const,
        cw: ["1", "0", "0"] as const,
        tt: ["0", "1", "0"] as const,
      },
      {
        id: "clip-angle-support:BOTTOM_FLANGE:material-axes",
        physical_element_id: "BOTTOM_FLANGE",
        material_region_id: "FLANGES",
        origin: point("0", "-7.625", "0"),
        lw: ["0", "0", "1"] as const,
        cw: ["1", "0", "0"] as const,
        tt: ["0", "1", "0"] as const,
      },
    ],
    rectangular_full_through_paths: [],
  };
  const result = {
    request_id: request.request_id,
    orchestration_contract_version: "3.3C2-RC1" as const,
    preview_schema_version: "0.1.0-draft" as const,
    connector_kind: "SINGLE_CLIP_ANGLE" as const,
    hand: request.hand,
    support_role: "W_COLUMN_FLANGE" as const,
    interface_a: interfaceA,
    interface_b: interfaceB,
    connector_body_required_check: "SINGLE_CLIP_ANGLE_CONNECTOR_BODY_RESISTANCE" as const,
    connector_body_status: "NOT_EVALUATED" as const,
    geometry_status: status === "INVALID_GEOMETRY" ? "INVALID_GEOMETRY" as const : "VALID" as const,
    geometry_invalid_reasons: status === "INVALID_GEOMETRY" ? ["Controlled invalid geometry"] : [],
    assembly_status: status,
    ordinary_pass_allowed: false as const,
    resistance_evaluated: false,
    design_check_ready: status !== "INVALID_GEOMETRY",
    warnings: status === "INVALID_GEOMETRY" ? ["Controlled invalid geometry"] : [],
    engineering_fingerprint: "c".repeat(64),
    visualization,
    support_target_id: request.support_target_id,
    rectangular_full_through_paths: [],
    design_limitations: [],
  };
  return {
    api_transport_schema_version: "0.1.0-draft",
    orchestration_contract_version: "3.3C2-RC1",
    preview_schema_version: "0.1.0-draft",
    request_id: request.request_id,
    geometry_status: result.geometry_status,
    geometry_invalid_reasons: result.geometry_invalid_reasons,
    assembly_status: status,
    ordinary_pass_allowed: false,
    resistance_evaluated: false,
    design_check_ready: result.design_check_ready,
    warnings: result.warnings,
    engineering_fingerprint: result.engineering_fingerprint,
    result,
  };
}

export function clipAngleDesignFixture(): ClipAngleDesignResponse {
  const preview = clipAnglePreviewFixture("FAIL").result;
  const withResistance = (value: ClipAngleInterfaceResult): ClipAngleInterfaceResult => ({
    ...value,
    resistance: {
      automatic_handoff_results: [{ overall_disposition: "FAIL", coverage: "COMPLETE" }],
      automatic_group_mode_integration: null,
    },
  });
  return {
    api_transport_schema_version: "0.1.0-draft",
    orchestration_contract_version: "3.3C2-RC1",
    request_id: preview.request_id,
    assembly_status: "FAIL",
    connector_body_status: "NOT_EVALUATED",
    ordinary_pass_allowed: false,
    supported_interface_failure_present: true,
    result_fingerprint: "d".repeat(64),
    result: {
      preview,
      interface_a: withResistance(preview.interface_a),
      interface_b: withResistance(preview.interface_b),
      assembly_status: "FAIL",
    },
  };
}
