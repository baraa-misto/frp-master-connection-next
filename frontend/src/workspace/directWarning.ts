import { formatDecimal, friendlyEnum, friendlyIdentifier } from "./presentation";

export type WarningGroup = "input" | "geometry" | "action" | "method" | "source" | "qualification" | "information";

export function describeDirectWarning(raw: string): { group: WarningGroup; text: string; boltId?: string } {
  if (raw.startsWith("INPUT_NEEDED:")) return { group: "input", text: `INPUT NEEDED — ${raw.slice("INPUT_NEEDED:".length).trim()}` };
  const containment = /^DIRECT_PHYSICAL_CONTAINMENT:([^:]+):([^:]+):([^:]+):(.+)$/u.exec(raw);
  if (containment !== null) {
    const [, boltId, memberId, face, detail] = containment as unknown as [string, string, string, string, string];
    const physical = /^(CHAPTER_8_EDGE_DISTANCE|CHAPTER_8_END_DISTANCE|HOLE_PHYSICAL_CONTAINMENT|WASHER_SEATING|COMPONENT_INTERFERENCE|GEOMETRY — Supporting W member end) — (.+): available=([^;]+); required=([^;]+)\. unit=(in|mm)\./u.exec(detail.replace("GEOMETRY — Supporting W member end: ", "GEOMETRY — Supporting W member end — "));
    if (physical !== null) {
      const names = { CHAPTER_8_EDGE_DISTANCE: "Chapter 8 physical free-edge distance", CHAPTER_8_END_DISTANCE: "Chapter 8 loaded-end distance", HOLE_PHYSICAL_CONTAINMENT: "Physical hole containment", WASHER_SEATING: "Washer seating / hardware clearance", COMPONENT_INTERFERENCE: "Physical component interference", "GEOMETRY — Supporting W member end": "GEOMETRY — Supporting W member end" };
      const [, kind, feature, actual, required, unit] = physical as unknown as [string, keyof typeof names, string, string, string, string];
      return { group: "geometry", boltId, text: `Bolt ${boltId} on ${friendlyIdentifier(memberId)} ${friendlyIdentifier(face)}: ${names[kind]} to ${feature}; actual ${formatDecimal(actual, 3)} ${unit}, required ${formatDecimal(required, 3)} ${unit}. Adjust the actual bolt location or physical hardware clearance.` };
    }
    const clearance = /available=([^;]+); required=([^;]+); plane=([^;]+)\. unit=(in|mm)/u.exec(detail);
    if (clearance !== null) {
      const [, available, required, , unit] = clearance as unknown as [string, string, string, string, string];
      return {
        group: "geometry", boltId,
        text: `Bolt ${boltId} on ${friendlyIdentifier(memberId)} ${friendlyIdentifier(face)}: bolt-center distance to selected contact-patch boundary ${formatDecimal(available, 3)} ${unit}; required minimum ${formatDecimal(required, 3)} ${unit}. Chapter 8 center distance, hole radius and washer radius remain separate criteria. Adjust placement within the current members first.`,
      };
    }
    return { group: "geometry", boltId, text: `Bolt ${boltId} on ${friendlyIdentifier(memberId)} ${friendlyIdentifier(face)}: ${detail}` };
  }
  if (raw.includes("DIRECT_INDEPENDENT_MEMBER_END_MOMENT_NOT_SUPPORTED")) return { group: "action", text: "Design Check cannot run: this Direct method does not support an independent member-end moment. Enter the actual supported force-only load case or use a separately qualified method." };
  if (/DIRECT_BOLT_AXIS|OUT_OF_PLANE_FORCE_REQUIRES/u.test(raw)) return { group: "action", text: "Design Check cannot run: bolt-axis force, tension or prying requires a separately supported Direct load path." };
  if (raw.includes("DIRECT_DEMAND_PLAN_NOT_READY")) return { group: "action", text: "Design Check cannot run: the current force frame or direction has no supported Direct demand method. Review the entered force components and reference, or use a separately supported method." };
  if (raw.includes("F593_TENSILE_SOURCE_DATA_PENDING")) return { group: "source", text: "Design Check can run FRP checks. The controlled ASTM F593 catalog tensile-strength table for the selected alloy, condition and diameter is missing. Bolt strength is not evaluated and final GREEN is unavailable; per-connection supplier certification is not required." };
  if (raw.includes("CONTROLLED_ICE_DEVELOPMENT_MATERIAL")) return { group: "qualification", text: "Supported calculations use owner-supplied ICE data. Manufacturer, characteristic-strength and material qualification evidence is required before final GREEN." };
  if (raw.includes("SECTION_2_3_2")) return { group: "qualification", text: "Supported checks can run. Whole-connection qualification under Section 2.3.2 is required before final GREEN." };
  if (raw.includes("INVALID_PHYSICAL_CONNECTION_GEOMETRY")) return { group: "geometry", text: "Correct the physical member interference before running Design Check." };
  if (raw === "RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY_USED") return { group: "information", text: "Demand distribution / Rational elastic bolt-group method" };
  if (/UNSUPPORTED|NOT_SUPPORTED|DEGENERATE|RESIDUAL|MOMENT/u.test(raw)) return { group: "method", text: friendlyEnum(raw) };
  return { group: "information", text: friendlyEnum(raw) };
}
