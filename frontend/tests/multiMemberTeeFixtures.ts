import type {
  MultiMemberTeeDesignResponse,
  MultiMemberTeePreviewResponse,
  MultiMemberTeeSlotId,
  MultiMemberTeeVisualization,
} from "../src/api/multiMemberTeeContracts";
import { teeVisualizationFixture } from "./teeFixtures";

const q = (value: string, unit = "in") => ({ value, unit });

export function multiMemberTeeVisualization(
  slots: readonly MultiMemberTeeSlotId[] = ["UPPER_BRACE", "MIDDLE_BEAM", "LOWER_BRACE"],
): MultiMemberTeeVisualization {
  return {
    schema_version: "0.1.0-draft",
    slots: slots.map((slotId) => {
      const visualization = teeVisualizationFixture();
      const sourceMember = "member-a";
      const connectedMember = visualization.connected_member_profile.member_id;
      visualization.base_connection.components = visualization.base_connection.components.map((item) => item.id === sourceMember ? { ...item, id: connectedMember } : item);
      visualization.base_connection.frames = visualization.base_connection.frames.map((item) => item.owner_id === sourceMember ? { ...item, id: item.id.replace(sourceMember, connectedMember), owner_id: connectedMember } : item);
      visualization.base_connection.primitives = visualization.base_connection.primitives.map((item) => item.owner_id === sourceMember ? { ...item, owner_id: connectedMember } : item);
      visualization.base_connection.view_extension_primitives = visualization.base_connection.view_extension_primitives.map((item) => item.owner_id === sourceMember ? { ...item, owner_id: connectedMember } : item);
      visualization.base_connection.material_directions = visualization.base_connection.material_directions.map((item) => item.component_id === sourceMember ? { ...item, component_id: connectedMember } : item);
      visualization.base_connection.interface_zones = visualization.base_connection.interface_zones.map((item) => item.participant_id === sourceMember ? { ...item, participant_id: connectedMember } : item);
      visualization.interface_zones = visualization.interface_zones.map((item) => item.participant_id === sourceMember ? { ...item, participant_id: connectedMember } : item);
      const offset = slotId === "UPPER_BRACE" ? 10 : slotId === "LOWER_BRACE" ? -10 : 0;
      visualization.base_connection.primitives = visualization.base_connection.primitives.map((item) => item.owner_id === connectedMember ? {
        ...item,
        parameters: item.parameters.map((parameter) => parameter.name === "center_z" ? { ...parameter, value: String(Number(parameter.value) + offset) } : parameter),
      } : item);
      return {
        slot_id: slotId,
        connected_member_id: `multi-member-tee:${slotId.toLowerCase()}`,
        bolt_group_id: `${slotId}_TO_TEE_STEM`,
        visualization,
      };
    }),
  };
}

export function multiMemberTeePreview(
  status: "INVALID_GEOMETRY" | "NOT_EVALUATED" = "NOT_EVALUATED",
  slots: readonly MultiMemberTeeSlotId[] = ["UPPER_BRACE", "MIDDLE_BEAM", "LOWER_BRACE"],
): MultiMemberTeePreviewResponse {
  const limitations = ["TEE_CONNECTOR_BODY_RESISTANCE", "MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY"];
  const result = {
    assembly_status: status,
    active_slot_ids: slots,
    slots: slots.map((slotId) => ({ slot_id: slotId, connected_role: slotId === "MIDDLE_BEAM" ? "BEAM" as const : "BRACE" as const, connected_member_id: `multi-member-tee:${slotId.toLowerCase()}`, bolt_group_id: `${slotId}_TO_TEE_STEM`, profile: {}, trim: { enabled: false, geometry_valid: true }, preview: {}, geometry_fingerprint: slotId.repeat(2), interface_fingerprint: slotId.repeat(3), action_fingerprint: slotId.repeat(4) })),
    support: { bolt_group_id: "TEE_FLANGE_TO_SUPPORT" as const, interface_fingerprint: "support" },
    support_wrench: {
      force: { h: q("12.9282032302755088", "kip"), v: q("0", "kip"), n: q("0", "kip") },
      moment: { h: q("0", "kip-in"), v: q("0", "kip-in"), n: q("0", "kip-in") },
      reference_point: { h: q("0"), v: q("0"), n: q("0") },
      contributions: slots.map((slotId) => ({ slot_id: slotId, force: { h: q("4", "kip"), v: q("0", "kip"), n: q("0", "kip") }, shifted_moment: { h: q("0", "kip-in"), v: q("0", "kip-in"), n: q(slotId === "UPPER_BRACE" ? "-28.641" : slotId === "LOWER_BRACE" ? "28.641" : "0", "kip-in") }, action_fingerprint: `action-${slotId}` })),
      wrench_fingerprint: "w".repeat(64),
      application_provenance_fingerprint: "p".repeat(64),
    },
    required_limitations: limitations,
    warnings: status === "INVALID_GEOMETRY" ? ["CONNECTED_MEMBER_POSITIVE_VOLUME_INTERFERENCE"] : limitations,
    input_fingerprint: "i".repeat(64),
    engineering_fingerprint: "e".repeat(64),
    visualization: status === "INVALID_GEOMETRY" ? null : multiMemberTeeVisualization(slots),
  };
  return {
    api_transport_schema_version: "0.1.0-draft",
    orchestration_contract_version: "3.4B-RC1",
    preview_schema_version: "0.1.0-draft",
    request_id: "MULTI-MEMBER-TEE-DEFAULT",
    assembly_status: status,
    ordinary_pass_allowed: false,
    resistance_evaluated: false,
    design_check_ready: status !== "INVALID_GEOMETRY",
    engineering_fingerprint: result.engineering_fingerprint,
    result,
  };
}

export function multiMemberTeeDesign(status: "NOT_EVALUATED" | "FAIL" = "NOT_EVALUATED"): MultiMemberTeeDesignResponse {
  const preview = multiMemberTeePreview().result;
  return {
    api_transport_schema_version: "0.1.0-draft",
    orchestration_contract_version: "3.4B-RC1",
    request_id: "MULTI-MEMBER-TEE-DEFAULT",
    assembly_status: status,
    ordinary_pass_allowed: false,
    supported_failure_present: status === "FAIL",
    result_fingerprint: "r".repeat(64),
    result: { preview, required_limitations: preview.required_limitations },
  };
}
