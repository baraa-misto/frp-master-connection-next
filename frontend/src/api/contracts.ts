export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { readonly [key: string]: JsonValue };

export interface QuantityDTO {
  value: string;
  unit: string;
}

export interface DecimalVector3DTO {
  x: string;
  y: string;
  z: string;
  unit: string;
}

export interface DirectionVector3DTO {
  x: string;
  y: string;
  z: string;
}

export interface FrameDTO {
  origin: DecimalVector3DTO;
  x_direction: DirectionVector3DTO;
  local_z_reference: DirectionVector3DTO;
}

export interface MemberSectionDTO {
  kind: "ANGLE" | "WIDE_FLANGE" | "I_SECTION" | "PLATE";
  width?: QuantityDTO;
  thickness: QuantityDTO;
  leg_y?: QuantityDTO;
  leg_z?: QuantityDTO;
  overall_depth?: QuantityDTO;
  flange_width?: QuantityDTO;
  web_thickness?: QuantityDTO;
  flange_thickness?: QuantityDTO;
}

export interface MemberDTO {
  id: string;
  label: string;
  role: string;
  connected_end: "START" | "END";
  material_kind: string;
  material_orientation: {
    lengthwise_axis: string;
    crosswise_axis: string;
    through_thickness_axis: string;
  } | null;
  section: MemberSectionDTO;
}

export interface MemberEndActionDTO {
  id: string;
  member_id: string;
  member_end: "START" | "END";
  load_combination_id: string;
  coordinate_frame_kind: string;
  coordinate_frame_owner_id: string | null;
  reference_point: {
    kind: string;
    owner_id: string | null;
    position: DecimalVector3DTO | null;
  };
  force: DecimalVector3DTO;
  moment: DecimalVector3DTO;
  convention: string;
}

export interface ExplicitResolvedDemandDTO {
  interface_id: string;
  bolt_group_id: string;
  bolt_location_id: string;
  id: string;
  load_combination_id: string;
  source_member_id: string;
  source_action_id: string;
  source_kind: "EXPLICIT_RESOLVED_BOLT_DEMAND";
  factored_action_confirmed: boolean;
  coordinate_frame_reference: string;
  resolved_frame: FrameDTO;
  source_reference_point_id: string;
  resolved_global_reference_point: DecimalVector3DTO;
  in_plane_force_vector: DecimalVector3DTO;
  bolt_axis_tensile_demand: QuantityDTO;
  externally_supplied_prying_demand: QuantityDTO;
  loading_sense: "TENSION" | "COMPRESSION";
  provenance: string[];
  distribution_status: "EXPLICITLY_RESOLVED";
}

export interface FRPPropertyEntryDTO {
  kind: string;
  value: QuantityDTO;
  behavior: string;
  source_classification: string;
  qualification_status: string;
  source_document: string;
  source_revision: string;
  applicability_metadata: string[];
  engineer_notes: string[];
  use_in_chapter_8_equations: boolean;
}

export interface SingleBoltEvaluationRequest {
  calculation_id: string;
  joint_assembly: {
    id: string;
    label: string;
    design_category: "SHEAR";
    unit_system: "US_CUSTOMARY" | "SI";
    members: MemberDTO[];
    load_combinations: { id: string; label: string; input_basis: string }[];
    member_end_actions: MemberEndActionDTO[];
  };
  geometry?: {
    joint_frame: FrameDTO;
    member_placements: {
      member_id: string;
      start: DecimalVector3DTO;
      end: DecimalVector3DTO;
      local_z_reference: DirectionVector3DTO;
      section_offset_y: QuantityDTO;
      section_offset_z: QuantityDTO;
    }[];
    interface: {
      id: string;
      label: string;
      participant_a_id: string;
      participant_b_id: string;
      transfer_intent: string;
      first_side: Record<string, JsonValue>;
      second_side: Record<string, JsonValue>;
      origin_local_y: QuantityDTO;
      origin_local_z: QuantityDTO;
      in_plane_reference: DirectionVector3DTO;
      distance_tolerance: QuantityDTO;
      angular_tolerance: string;
    };
    bolt_group: {
      id: string;
      label: string;
      primary_interface_id: string;
      origin_y: QuantityDTO;
      origin_z: QuantityDTO;
      in_plane_reference: DirectionVector3DTO;
      locations: { id: string; local_position: DecimalVector3DTO }[];
      paths: {
        bolt_location_id: string;
        layers: {
          id: string;
          participant_id: string;
          physical_element_id: string;
          entry_patch_id: string;
          exit_patch_id: string;
          entry_face_role: string;
          exit_face_role: string;
          interface_side: string;
          zone_id: string;
          hole_diameter: QuantityDTO;
        }[];
      }[];
    };
  };
  geometry_template?: {
    kind: "BRACE_TO_COLUMN_FLANGE";
    brace_to_column_directed_angle_deg: string;
    bolt_to_brace_end_distance: QuantityDTO;
    hole_diameter: QuantityDTO;
    column_flange_connection_side: "EXTERIOR" | "WEB_SIDE";
    angle_connected_leg: "LEG_1" | "LEG_2";
    outstanding_leg_side: "POSITIVE_INTERFACE_Z" | "NEGATIVE_INTERFACE_Z";
  };
  interface_id: string;
  bolt_group_id: string;
  bolt_location_id: string;
  load_combination_id: string;
  source_action_id: string | null;
  explicit_resolved_demand: ExplicitResolvedDemandDTO | null;
  material_snapshots: {
    id: string;
    display_name: string;
    locked: boolean;
    basis: string;
    qualification_statuses: string[];
    properties: FRPPropertyEntryDTO[];
    explicitly_missing: string[];
  }[];
  material_assignments: {
    participant_id: string;
    physical_element_id: string;
    material_region_id: string;
    material_snapshot_id: string;
    bearing_thread_status: string;
    element_form: string;
    potential_perpendicular_element_exemption: boolean;
  }[];
  fastener_snapshot: {
    id: string;
    display_name: string;
    locked: boolean;
    bolt_specification: string;
    alloy_group: string;
    alloys: string[];
    condition: string;
    nut_specification: string;
    washer_material_basis: string;
    installation_condition: string;
    diameter_min: QuantityDTO;
    diameter_max: QuantityDTO;
    fnt: QuantityDTO | null;
    fnt_source_classification: string;
    fnt_qualification_status: string;
    shear_plane_thread_statuses: { location_id: string; status: string }[];
    bearing_layer_thread_statuses: { location_id: string; status: string }[];
    number_of_shear_planes: number;
    washer_geometry: {
      outside_diameter: QuantityDTO;
      thickness: QuantityDTO;
      under_head: boolean;
      under_nut: boolean;
    } | null;
    source_notes: string[];
  };
  bolt_diameter: QuantityDTO;
  published_code_unit_basis: string;
  time_effect_category: string;
  end_use_factors: {
    cm: string;
    ct: string;
    cch: string;
    source_reference: string;
    approval_metadata: string[];
  };
  lap_configuration: string;
  whole_connection_requires_section_2_3_2: boolean;
}

export type SingleBoltPreviewRequest = Omit<
  SingleBoltEvaluationRequest,
  | "fastener_snapshot"
  | "published_code_unit_basis"
  | "time_effect_category"
  | "end_use_factors"
  | "whole_connection_requires_section_2_3_2"
> & {
  view_extents?: ConnectionViewExtentsDTO;
  fastener_snapshot: {
    id: string;
    washer_geometry: SingleBoltEvaluationRequest["fastener_snapshot"]["washer_geometry"];
  };
};

export interface ConnectionViewExtentsDTO {
  brace_view_length: QuantityDTO;
  column_view_extent_below: QuantityDTO;
  column_view_extent_above: QuantityDTO;
}

export interface PointSnapshot {
  x: string;
  y: string;
  z: string;
  unit: string;
}

export interface DirectionSnapshot {
  x: string;
  y: string;
  z: string;
}

export interface SnapshotFrame {
  id: string;
  label: string;
  kind: string;
  owner_id: string | null;
  frame: {
    origin: PointSnapshot;
    x_axis: DirectionSnapshot;
    y_axis: DirectionSnapshot;
    z_axis: DirectionSnapshot;
  };
  inspection: Record<string, JsonValue>;
}

export interface SnapshotParameter {
  name: string;
  value: string;
}

export interface SnapshotPrimitive {
  id: string;
  label: string;
  kind: string;
  owner_id: string;
  frame_id: string;
  physical_element_id: string | null;
  material_region_id: string | null;
  center: PointSnapshot | null;
  x_axis: DirectionSnapshot | null;
  y_axis: DirectionSnapshot | null;
  z_axis: DirectionSnapshot | null;
  parameters: SnapshotParameter[];
  points: PointSnapshot[];
  resolution_status: string;
}

export interface MaterialDirectionSnapshot {
  id: string;
  component_id: string;
  physical_element_id: string;
  material_region_id: string;
  origin: PointSnapshot;
  lengthwise: DirectionSnapshot | null;
  crosswise: DirectionSnapshot | null;
  through_thickness: DirectionSnapshot | null;
  resolution_status: string;
  reason: string | null;
}

export interface ReferencePointSnapshot {
  id: string;
  label: string;
  kind: string;
  owner_id: string | null;
  position: PointSnapshot;
  frame_id: string;
  member_end: "START" | "END" | null;
  connected: boolean | null;
  provenance: string | null;
}

export interface ActionDirectionSnapshot {
  component: "FX" | "FY" | "FZ" | "MX" | "MY" | "MZ";
  kind: "LINEAR" | "ROTATIONAL";
  axis: DirectionSnapshot;
  reference_point_id: string;
  frame_id: string;
  signed_value: string | null;
  unit: string | null;
  sense: "POSITIVE" | "NEGATIVE" | "ZERO" | null;
  is_zero: boolean;
  member_end: "START" | "END" | null;
  axial_loading_sense: "TENSION" | "COMPRESSION" | "ZERO" | null;
}

export interface VisualizationSnapshot {
  snapshot_version: string;
  assembly_id: string;
  interface_id: string;
  bolt_group_id: string;
  bolt_location_id: string;
  unit_system: "US_CUSTOMARY" | "SI";
  length_unit: string;
  force_unit: string;
  moment_unit: string;
  frames: SnapshotFrame[];
  components: {
    id: string;
    label: string;
    participant_kind: string;
    material_kind: string;
    section_family: string;
    frame_id: string;
    connected_end: "START" | "END" | null;
    elements: Record<string, JsonValue>[];
    deferred_primitive_ids: string[];
  }[];
  primitives: SnapshotPrimitive[];
  view_extension_primitives: SnapshotPrimitive[];
  material_directions: MaterialDirectionSnapshot[];
  interface_zones: {
    id: string;
    label: string;
    interface_id: string;
    side: string;
    participant_kind: string;
    participant_id: string;
    patch_id: string;
    geometry_kind: string;
    center: PointSnapshot;
    normal: DirectionSnapshot;
    corners: PointSnapshot[];
    parameters: SnapshotParameter[];
  }[];
  connection_orientation: {
    connection_side: "EXTERIOR" | "WEB_SIDE";
    connected_leg: "LEG_1" | "LEG_2";
    outstanding_leg_side: "POSITIVE_INTERFACE_Z" | "NEGATIVE_INTERFACE_Z";
    supporting_member_id: string;
    selected_flange_element_id: string;
    selected_flange_surface_id: string;
    selected_flange_surface_role: string;
    connected_member_id: string;
    selected_angle_surface_id: string;
    selected_angle_surface_role: string;
    selected_contact_normal: DirectionSnapshot;
    brace_to_column_directed_angle_degrees: string;
    plan_angle_degrees: string;
    interference_classifications: string[];
    interference_participant_ids: string[];
    interference_physical_element_ids: string[];
    geometry_valid: boolean;
  } | null;
  bolt: {
    bolt_group_id: string;
    bolt_location_id: string;
    center: PointSnapshot;
    axis: DirectionSnapshot;
    stack_start: PointSnapshot;
    stack_end: PointSnapshot;
    bolt_diameter: string;
    holes: {
      id: string;
      participant_id: string;
      physical_element_id: string;
      start: PointSnapshot;
      end: PointSnapshot;
      diameter: string;
    }[];
    washers: {
      id: string;
      location: "UNDER_HEAD" | "UNDER_NUT";
      start: PointSnapshot;
      end: PointSnapshot;
      outside_diameter: string;
    }[];
  };
  reference_points: ReferencePointSnapshot[];
  positive_action_directions: ActionDirectionSnapshot[];
  applied_action_directions: ActionDirectionSnapshot[];
}

export interface QuantityResult {
  value: string;
  unit: string;
}

export interface CalculationResultDTO {
  plan: {
    check_id: string;
    limit_state: string;
    component_id: string | null;
    layer_id: string | null;
    source_section: string;
    source_equation: string | null;
    readiness_status: string;
    selected_direction_family: string | null;
    required_property_kind: string | null;
    qualification_flags: string[];
    warnings: string[];
    required: boolean;
    [key: string]: JsonValue;
  };
  availability: string;
  numerical_comparison: string;
  demand: QuantityResult | null;
  nominal_resistance: QuantityResult | null;
  design_resistance: QuantityResult | null;
  utilization: string | null;
  equation_trace: Record<string, JsonValue> | null;
  source_snapshot: Record<string, JsonValue>;
  warnings: string[];
}

export interface ResolvedLayerDTO {
  layer_id: string;
  participant_id: string;
  physical_element_id: string;
  material_region_id: string;
  [key: string]: JsonValue;
}

export interface SingleBoltEvaluationResponse {
  api_transport_schema_version: "0.5.0-draft";
  project_schema_version: string;
  calculation_contract_version: string;
  calculation_engine_version: string;
  engineering_rule_set_version: string;
  calculation_id: string;
  assembly_id: string;
  interface_id: string;
  bolt_group_id: string;
  bolt_location_id: string;
  load_combination_id: string;
  unit_system: "US_CUSTOMARY" | "SI";
  calculation_fingerprint: string | null;
  material_assignments: Record<string, JsonValue>[];
  fastener: Record<string, JsonValue>;
  resolved_layers: ResolvedLayerDTO[];
  source_action_trace: Record<string, JsonValue> | null;
  resolved_demand: Record<string, JsonValue> | null;
  plans: Record<string, JsonValue>[];
  results: CalculationResultDTO[];
  aggregate_status: string | null;
  governing_check_ids: string[];
  qualification_flags: string[];
  issues: { code: string; message: string; identities: string[] }[];
  warnings: string[];
  source_references: Record<string, JsonValue>[];
  visualization: VisualizationSnapshot;
}

export type PreviewGeometryStatus =
  | "PREVIEW_VALID"
  | "PREVIEW_INVALID_GEOMETRY"
  | "PREVIEW_INCOMPLETE_INPUT"
  | "PREVIEW_UNSUPPORTED";

export interface SingleBoltPreviewResponse {
  preview_schema_version: "0.2.0-draft";
  project_schema_version: string;
  calculation_id: string;
  assembly_id: string;
  interface_id: string;
  bolt_group_id: string;
  bolt_location_id: string;
  load_combination_id: string;
  unit_system: "US_CUSTOMARY" | "SI";
  geometry_status: PreviewGeometryStatus;
  geometry_issues: { code: string; message: string; identities: string[] }[];
  resolved_layers: ResolvedLayerDTO[];
  material_relationships: {
    layer_id: string;
    theta_degrees: string;
    direction_family: string;
    direction_interpretation_id: string;
  }[];
  source_action_trace: Record<string, JsonValue> | null;
  visualization: VisualizationSnapshot | null;
  design_check_ready: boolean;
  design_check_blocking_reasons: string[];
}
