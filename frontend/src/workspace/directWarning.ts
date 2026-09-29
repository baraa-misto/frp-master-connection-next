import { formatDecimal, friendlyEnum, friendlyIdentifier } from "./presentation";

export type WarningGroup = "geometry" | "method" | "source" | "information";

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
  if (raw.includes("F593_TENSILE_SOURCE_DATA_PENDING")) return { group: "source", text: "ASTM F593-17 Group 2 fastener Fnt source evidence is still required; bolt resistance remains unevaluated." };
  if (raw.includes("CONTROLLED_ICE_DEVELOPMENT_MATERIAL")) return { group: "source", text: "The selected ICE material remains owner-supplied development data; material and whole-connection qualification are open." };
  if (/UNSUPPORTED|NOT_SUPPORTED|DEGENERATE|RESIDUAL|MOMENT/u.test(raw)) return { group: "method", text: friendlyEnum(raw) };
  return { group: "information", text: friendlyEnum(raw) };
}
