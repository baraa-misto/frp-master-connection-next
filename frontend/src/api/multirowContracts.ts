import type { SingleBoltPreviewRequest, VisualizationSnapshot } from "./contracts";

export interface MultiRowQuantity {
  value: string;
  unit: string;
}

export interface MultiRowConnectionRequest {
  orchestration_contract_version: "2.5C-RC1";
  request_id: string;
  connection_id: string;
  interface_id: string;
  load_combination_id: string;
  source_reference: string;
  display_unit_system: "US_CUSTOMARY" | "SI";
  source_length_unit: "in" | "mm";
  row_count: number;
  bolts_per_row: number;
  bolt_diameter: MultiRowQuantity;
  hole_basis: "US_CUSTOMARY_PRINTED" | "SI_PRINTED";
  pitch: MultiRowQuantity;
  gauge: MultiRowQuantity;
  unloaded_end_e1: MultiRowQuantity;
  loaded_boundary_to_row_1_distance: MultiRowQuantity;
  negative_side_distance: MultiRowQuantity;
  positive_side_distance: MultiRowQuantity;
  geometry_tolerance: MultiRowQuantity;
  material_pair: "FRP_FRP" | "FRP_STEEL";
  layers: {
    layer_id: string;
    component_id: string;
    material_id: "ICE_LOCKED_PULTRUDED_FRP";
    thickness: MultiRowQuantity;
    element_classification: "SHAPE" | "PLATE";
    material_axis_angle_degrees: string;
    end_use_factors: {
      cm: string;
      ct: string;
      cch: string;
      source_reference: string;
      approval_metadata: string[];
    };
    bearing_thread_status: "INCLUDED" | "EXCLUDED" | "UNKNOWN";
  }[];
  demand_source:
    | "AUTOMATIC_MEMBER_END_FORCE"
    | "EXPLICIT_RESOLVED_CONNECTION_DEMAND";
  signed_force_x?: MultiRowQuantity;
  signed_force_y?: MultiRowQuantity;
  force_reference?: string;
  automatic_action_source_id?: string;
  row_distribution_basis:
    | "ASCE_PRESCRIBED"
    | "CONSERVATIVE_FULL_ROW_ENVELOPE"
    | "ENGINEER_DEFINED_ROW_DISTRIBUTION";
  engineer_distribution_kind: "FRACTIONS" | "DIRECT_ROW_FORCES" | null;
  engineer_allocations: {
    row_ordinal: number;
    fraction?: string;
    direct_force?: MultiRowQuantity;
  }[];
  provenance: {
    source_method: string;
    source_document_or_calculation: string | null;
    revision: string | null;
    load_combination: string | null;
    reference_point: string | null;
    clearance_or_contact_modeled: boolean | null;
    engineer_confirmed: boolean;
  };
  bolt_axis_tension_required: boolean;
  bolt_axis_tensions: { bolt_id: string; demand: MultiRowQuantity }[];
  time_effect_category: string;
  lap_configuration: "DOUBLE_LAP" | "SINGLE_LAP";
  first_row_method: "ASCE_STANDARD_SIMPLIFIED" | "ASCE_COMMENTARY_FULL";
  prescribed_lbr: string | null;
  force_line_offset: MultiRowQuantity;
  eccentricity_tolerance: MultiRowQuantity;
  physical_connection?: SingleBoltPreviewRequest;
}

export interface MultiRowVisualization {
  schema_version: "0.2.0-draft";
  coordinate_system: string;
  source_length_unit: "in" | "mm";
  boundary: [string, string, string, string];
  bolts: {
    bolt_id: string;
    row_id: string;
    bolt_line_id: string;
    x: string;
    y: string;
    bolt_diameter: MultiRowQuantity;
    hole_diameter: MultiRowQuantity;
  }[];
  row_ids: string[];
  bolt_line_ids: string[];
  unloaded_free_end_id: string;
  row_1_id: string;
  pitch: MultiRowQuantity;
  gauge: MultiRowQuantity;
  unloaded_end_e1: MultiRowQuantity;
  loaded_boundary_to_row_1_distance: MultiRowQuantity;
  negative_side_distance: MultiRowQuantity;
  positive_side_distance: MultiRowQuantity;
  demand_components: [MultiRowQuantity, MultiRowQuantity];
  force_reference: string;
  global_axes: [string, [string, string]][];
  local_axes: [string, [string, string]][];
  layers: {
    layer_id: string;
    component_id: string;
    material_id: string;
    material_axis_angle_degrees: string;
    material_direction: string;
    thickness: MultiRowQuantity;
  }[];
  block_paths: {
    path_id: string;
    family: string;
    accepted: boolean;
    points: [string, string][];
  }[];
  physical_connection?: VisualizationSnapshot | null;
  physical_bolts?: {
    bolt_id: string;
    row_id: string;
    bolt_line_id: string;
    penetrated_layer_ids: string[];
    display: VisualizationSnapshot["bolt"];
  }[];
  connection_demand?: {
    reference_point_id: string;
    origin: VisualizationSnapshot["bolt"]["center"];
    axis: VisualizationSnapshot["bolt"]["axis"];
    resultant: MultiRowQuantity;
    frame_id: string;
  } | null;
  automatic_bolt_demands: {
    bolt_id: string;
    row_id: string;
    bolt_line_id: string;
    origin: VisualizationSnapshot["bolt"]["center"];
    direct_u: MultiRowQuantity;
    direct_v: MultiRowQuantity;
    moment_u: MultiRowQuantity;
    moment_v: MultiRowQuantity;
    total_u: MultiRowQuantity;
    total_v: MultiRowQuantity;
    total_magnitude: MultiRowQuantity;
    total_axis: VisualizationSnapshot["bolt"]["axis"] | null;
  }[];
}

export interface AutomaticDemandResult {
  action_source_id: string;
  member_component_id: string;
  availability: string;
  method_applicability: string;
  qualification: string;
  warnings: { code: string; trace: string[] }[];
  input_fingerprint: string;
  result_fingerprint: string;
  scenarios: {
    scenario_id: string;
    availability: string;
    external_moment: MultiRowQuantity;
    residual_moment: MultiRowQuantity;
    warnings: { code: string; trace: string[] }[];
  }[];
  versions: Record<string, string>;
}

export interface AutomaticHandoffResult {
  coverage: string;
  supported_results: MultiRowCheckResult[];
  unsupported_required_check_ids: string[];
  incomplete_required_check_ids: string[];
  qualification: string;
  numerical_comparison: string;
  governing_supported_check_ids: string[];
  overall_disposition: string;
  warnings: { code: string; trace: string[] }[];
  parent_action_transfer_warnings: { code: string; trace: string[] }[];
  result_fingerprint: string;
  versions: Record<string, string>;
  legacy_result: MultiRowCalculationResult | null;
}

export interface EccentricGroupModeLineResult {
  bolt_line_id: string;
  check_id: string | null;
  contributing_bolt_ids: string[];
  line_resultant: { u: MultiRowQuantity; v: MultiRowQuantity };
  parallel_scalar: MultiRowQuantity;
  transverse_scalar: MultiRowQuantity;
  handoff_status:
    | "AUTHORIZED_RATIONAL_ECCENTRIC_SHEAROUT"
    | "CALCULATION_NOT_SUPPORTED"
    | "INHERITED_LEGACY_STAGE_2_4B"
    | "NOT_REQUIRED_PARENT_EXEMPTION"
    | "NOT_REQUIRED_ZERO_LINE_DEMAND";
  required_line_demand: MultiRowQuantity | null;
  shear_out_result: MultiRowCheckResult | null;
  warnings: { code: string; trace: string[] }[];
  method_id: string;
}

export interface EccentricGroupModeScenarioResult {
  versions: Record<string, string>;
  scenario_id: string;
  line_results: EccentricGroupModeLineResult[];
  first_row_compatibility: {
    status:
      | "CALCULATION_NOT_SUPPORTED"
      | "INHERITED_LEGACY_STAGE_2_4B"
      | "NOT_REQUIRED_PARENT_EXEMPTION";
    required_check_ids: string[];
    warnings: { code: string; trace: string[] }[];
  };
  supported_results: MultiRowCheckResult[];
  required_check_ids: string[];
  not_required_check_ids: string[];
  unsupported_required_check_ids: string[];
  incomplete_required_check_ids: string[];
  failed_check_ids: string[];
  qualification: string;
  numerical_comparison: string;
  governing_supported_check_ids: string[];
  overall_disposition: string;
  trace_stages: string[];
  source_trace: string[];
  input_fingerprint: string;
  result_fingerprint: string;
}

export interface AutomaticGroupModeIntegrationResult {
  integration_contract_version: "2.6B-RC1";
  scenario_results: EccentricGroupModeScenarioResult[];
  required_check_ids: string[];
  not_required_check_ids: string[];
  unsupported_required_check_ids: string[];
  incomplete_required_check_ids: string[];
  failed_check_ids: string[];
  qualification: string;
  numerical_comparison: string;
  governing_supported_check_ids: string[];
  overall_disposition: string;
  trace_layers: [
    "DEMAND_ANALYSIS",
    "RESISTANCE_HANDOFF",
    "ECCENTRIC_GROUP_MODE_COMPATIBILITY",
    "RESISTANCE_CALCULATION",
    "APPLICATION_INTEGRATION",
  ];
  result_fingerprint: string;
}

export interface MultiRowPreviewResponse {
  api_transport_schema_version: "0.3.0-draft";
  orchestration_contract_version: "2.5C-RC1";
  preview_schema_version: "0.2.0-draft";
  visualization_schema_version: "0.2.0-draft";
  request_id: string;
  connection_id: string;
  geometry_status: "VALID" | "INVALID_GEOMETRY";
  plan_availability: string;
  method_applicability: string;
  qualification: string;
  warnings: string[];
  preview_fingerprint: string;
  resistance_evaluated: false;
  design_check_ready: boolean;
  visualization: MultiRowVisualization | null;
  demand_source: MultiRowConnectionRequest["demand_source"];
  automatic_demand_result: AutomaticDemandResult | null;
}

export interface MultiRowCheckResult {
  result_id: string;
  layer_id: string | null;
  bolt_id: string | null;
  row_id: string | null;
  bolt_line_id: string | null;
  path_id: string | null;
  limit_state: string;
  equation_method: string;
  source_locator: string;
  method_applicability: string;
  qualification: string;
  availability: string;
  geometry_status: string;
  equation_nominal_resistance: MultiRowQuantity | null;
  connection_adjusted_nominal_resistance: MultiRowQuantity | null;
  design_resistance: MultiRowQuantity | null;
  demand: MultiRowQuantity | null;
  utilization: string | null;
  numerical_comparison: string;
  factor_trace: Record<string, unknown> | null;
  equation_trace: Record<string, unknown> | null;
  warnings: { code: string; trace: string[] }[];
}

export interface MultiRowCalculationResult {
  results: MultiRowCheckResult[];
  required_check_ids: string[];
  calculated_check_ids: string[];
  unsupported_check_ids: string[];
  failed_check_ids: string[];
  governing_result_ids: string[];
  geometry_status: string;
  availability: string;
  method_applicability: string;
  qualification: string;
  numerical_comparison: string;
  overall_disposition: string;
  warnings: { code: string; trace: string[] }[];
  input_fingerprint: string;
  result_fingerprint: string;
  versions: Record<string, string>;
}

export interface MultiRowDesignResponse {
  api_transport_schema_version: "0.3.0-draft";
  orchestration_contract_version: "2.5C-RC1";
  preview_schema_version: "0.2.0-draft";
  visualization_schema_version: "0.2.0-draft";
  request_id: string;
  connection_id: string;
  preview: MultiRowPreviewResponse;
  calculation_result: MultiRowCalculationResult | null;
  demand_source: MultiRowConnectionRequest["demand_source"];
  automatic_demand_result: AutomaticDemandResult | null;
  automatic_handoff_results: AutomaticHandoffResult[];
  automatic_group_mode_integration: AutomaticGroupModeIntegrationResult | null;
}
