import type { VisualizationSnapshot } from "../api/contracts";
import type { DirectSupportEndAuthority } from "../api/multirowContracts";

/** Render signed real ends; the crop on a continuing side stays presentation only. */
export function directSupportPresentation(snapshot: VisualizationSnapshot, authority: DirectSupportEndAuthority): VisualizationSnapshot {
  const rendered = structuredClone(snapshot);
  for (const primitive of [...rendered.primitives, ...rendered.view_extension_primitives]) {
    if (primitive.owner_id !== authority.component_id || primitive.kind !== "BOX") continue;
    const start = primitive.parameters.find((item) => item.name === "x_start");
    const end = primitive.parameters.find((item) => item.name === "x_end");
    if (start === undefined || end === undefined || primitive.center === null || primitive.x_axis === null) throw new Error("Supporting W presentation box lacks signed placement.");
    const oldMidpoint = (Number(start.value) + Number(end.value)) / 2;
    if (authority.negative_end_member_local_station !== null) start.value = authority.negative_end_member_local_station;
    if (authority.positive_end_member_local_station !== null) end.value = authority.positive_end_member_local_station;
    const shift = (Number(start.value) + Number(end.value)) / 2 - oldMidpoint;
    for (const axis of ["x", "y", "z"] as const) primitive.center[axis] = String(Number(primitive.center[axis]) + shift * Number(primitive.x_axis[axis]));
    primitive.label += " — W end condition: " + authority.condition;
  }
  return rendered;
}
