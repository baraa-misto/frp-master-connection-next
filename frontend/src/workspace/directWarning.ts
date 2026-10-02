import { formatDecimal, friendlyEnum, friendlyIdentifier } from "./presentation";

export type WarningGroup = "input" | "geometry" | "action" | "method" | "source" | "qualification" | "information";

export function describeDirectWarning(raw: string): { group: WarningGroup; text: string; boltId?: string } {
  const containment = /^DIRECT_PHYSICAL_CONTAINMENT:([^:]+):([^:]+):([^:]+):(.+)$/u.exec(raw);
  if (containment !== null) {
    const [, boltId, memberId, face, detail] = containment as unknown as [string, string, string, string, string];
    const clearance = /available=([^;]+); required=([^;]+); plane=([^;]+)\. unit=(in|mm)/u.exec(detail);
    if (clearance !== null) {
      const [, available, required, , unit] = clearance as unknown as [string, string, string, string, string];
      return {
        group: "geometry", boltId,
        text: `Bolt ${boltId} on ${friendlyIdentifier(memberId)} ${friendlyIdentifier(face)}: available ${formatDecimal(available, 3)} ${unit}, required ${formatDecimal(required, 3)} ${unit} (ASCE/SEI 74-23 Chapter 8 physical hole, washer and side-edge criterion).`,
      };
    }
    return { group: "geometry", boltId, text: `Bolt ${boltId} on ${friendlyIdentifier(memberId)} ${friendlyIdentifier(face)}: ${detail}` };
  }
  if (raw.includes("DIRECT_INDEPENDENT_MEMBER_END_MOMENT_NOT_SUPPORTED")) return { group: "action", text: "Design Check cannot run: this Direct method does not support an independent member-end moment. Enter the actual supported force-only load case or use a separately qualified method." };
  if (/DIRECT_BOLT_AXIS|OUT_OF_PLANE_FORCE_REQUIRES/u.test(raw)) return { group: "action", text: "Design Check cannot run: bolt-axis force, tension or prying requires a separately supported Direct load path." };
  if (raw.includes("DIRECT_DEMAND_PLAN_NOT_READY")) return { group: "action", text: "Design Check cannot run: the current force frame or direction has no supported Direct demand method. Review the entered force components and reference, or use a separately supported method." };
  if (raw.includes("F593_TENSILE_SOURCE_DATA_PENDING")) return { group: "source", text: "Design Check can run FRP checks. ASTM F593 strength evidence is missing, so bolt strength is not evaluated and final GREEN is unavailable." };
  if (raw.includes("CONTROLLED_ICE_DEVELOPMENT_MATERIAL")) return { group: "qualification", text: "Supported calculations use owner-supplied ICE data. Manufacturer, characteristic-strength and material qualification evidence is required before final GREEN." };
  if (raw.includes("SECTION_2_3_2")) return { group: "qualification", text: "Supported checks can run. Whole-connection qualification under Section 2.3.2 is required before final GREEN." };
  if (raw.includes("INVALID_PHYSICAL_CONNECTION_GEOMETRY")) return { group: "geometry", text: "Correct the physical member interference before running Design Check." };
  if (/UNSUPPORTED|NOT_SUPPORTED|DEGENERATE|RESIDUAL|MOMENT/u.test(raw)) return { group: "method", text: friendlyEnum(raw) };
  return { group: "information", text: friendlyEnum(raw) };
}
