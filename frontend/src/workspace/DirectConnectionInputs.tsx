import type { HybridGeometry, HybridInputs, HybridQuantity } from "../api/hybridWorkflow";
import type { TwoBoltRequest } from "../api/directTwoBolt";
import type { MultiRowConnectionRequest } from "../api/multirowContracts";
import { DirectSupportEnds } from "../features/DirectSupportEnds";
import { DirectPhysicalInputs } from "./DirectPhysicalInputs";

interface Field { label: string; quantity: HybridQuantity; change: (q: HybridQuantity) => HybridInputs }
const sourceLabels: Record<Exclude<keyof HybridGeometry, "phi">, string> = {
  vertical_bolt_pitch: "Bolt spacing", xb: "Brace free-edge to bolt centerline (Xb)", xc: "Receiving flange edge to bolt centerline (Xc)",
  brace_near_v_edge_distance: "Brace transverse edge to first bolt", brace_leg: "Angle leg width", column_flange: "Receiving I flange width",
  brace_thickness: "Angle thickness", column_thickness: "Receiving I flange thickness", diameter: "Bolt diameter", hole: "Hole diameter",
};
const sectionLabels: Readonly<Record<string, string>> = { leg_y: "Angle leg width", leg_z: "Angle return-leg width", thickness: "Angle thickness", overall_depth: "Receiving I depth", flange_width: "Receiving I flange width", flange_thickness: "Receiving I flange thickness", web_thickness: "Receiving I web thickness" };

function nativeFields(value: HybridInputs, native: TwoBoltRequest): Field[] {
  const publish = (legacy: MultiRowConnectionRequest, extra: Partial<TwoBoltRequest> = {}): HybridInputs => ({ ...value, native_request: { ...native, ...extra, legacy, ...(native.material_request === undefined ? {} : { material_request: { ...native.material_request as object, legacy_request: legacy } }) } });
  const physical = native.legacy.physical_connection;
  const fields: Field[] = (["bolt_diameter", "pitch", "loaded_boundary_to_row_1_distance", "negative_side_distance", "positive_side_distance"] as const).map((key) => ({
    label: { bolt_diameter: "Bolt diameter", pitch: "Bolt spacing", loaded_boundary_to_row_1_distance: "Loaded boundary to first row", negative_side_distance: "Negative physical side distance", positive_side_distance: "Positive physical side distance" }[key],
    quantity: native.legacy[key],
    change: (q) => publish({ ...native.legacy, [key]: q, ...(key === "bolt_diameter" && physical !== undefined ? { physical_connection: { ...physical, bolt_diameter: q } } : {}) }, key === "pitch" ? { spacing: { value: q.value, unit: q.unit as "in" | "mm" } } : {}),
  }));
  if (physical === undefined) return fields;
  const template = physical.geometry_template;
  if (template !== undefined) fields.push(
    { label: "Brace end distance", quantity: template.bolt_to_brace_end_distance, change: (q) => publish({ ...native.legacy, unloaded_end_e1: q, physical_connection: { ...physical, geometry_template: { ...template, bolt_to_brace_end_distance: q } } }) },
    { label: "Brace angle to receiving member", quantity: { value: template.brace_to_column_directed_angle_deg, unit: "deg" }, change: (q) => publish({ ...native.legacy, physical_connection: { ...physical, geometry_template: { ...template, brace_to_column_directed_angle_deg: q.value } } }) },
    { label: "Hole diameter", quantity: native.hole_diameter ?? template.hole_diameter, change: (q) => publish({ ...native.legacy, physical_connection: { ...physical, geometry_template: { ...template, hole_diameter: q } } }, { hole_diameter: { value: q.value, unit: q.unit as "in" | "mm" } }) },
  );
  physical.joint_assembly.members.forEach((member, index) => {
    Object.entries(member.section).filter(([, q]) => typeof q === "object").forEach(([key, quantity]) => fields.push({
      label: sectionLabels[key] ?? member.label + " " + key.replaceAll("_", " "), quantity: quantity as HybridQuantity,
      change: (q) => publish({ ...native.legacy, physical_connection: { ...physical, joint_assembly: { ...physical.joint_assembly, members: physical.joint_assembly.members.map((item, i) => i === index ? { ...item, section: { ...item.section, [key]: q } } : item) } }, layers: key === "thickness" || key === "flange_thickness" ? native.legacy.layers.map((layer) => layer.component_id === member.id ? { ...layer, thickness: q } : layer) : native.legacy.layers }),
    }));
  });
  return fields;
}

export function DirectConnectionInputs({ value, onChange }: { readonly value: HybridInputs; readonly onChange: (next: HybridInputs) => void }) {
  const g = value.geometry;
  const native = value.native_request;
  const fields: Field[] = g === null ? value.native_request === null ? [] : nativeFields(value, value.native_request) : [
    { label: "Brace angle to source horizontal", quantity: { value: g.phi, unit: "deg" }, change: (q) => ({ ...value, geometry: { ...g, phi: q.value } }) },
    ...(Object.keys(sourceLabels) as (Exclude<keyof HybridGeometry, "phi">)[]).map((key): Field => ({ label: sourceLabels[key], quantity: g[key], change: (q) => ({ ...value, geometry: { ...g, [key]: q } }) })),
  ];
  return <>
    {g === null && value.native_request === null ? <p role="alert">Define one current physical connection by loading a preset or restoring previous inputs.</p> : null}
    <p>Current physical end definition: {g === null ? "native engineering end and physical side boundaries" : "source oblique brace cut and receiving flange free edge"}. Calculation basis does not change this geometry.</p>
    <div className="field-grid">{fields.map((field) => <label key={field.label} className="field-control"><span>{field.label}</span><div className="hybrid-quantity"><input aria-label={field.label} inputMode="decimal" value={field.quantity.value} onChange={(event) => { onChange(field.change({ ...field.quantity, value: event.currentTarget.value })); }} /><span>{field.quantity.unit}</span></div></label>)}</div>
    {g === null ? null : <p>Equal-leg source Angle; receiving I depth 8 in and web thickness 0.375 in are nominal display context, not additional established resistance operands.</p>}
    <DirectPhysicalInputs value={value} onChange={onChange} />
    <details><summary>Geometry and constructability details</summary><p>Physical free edges, internal junction clearances and view crops remain separate. Root fillets, tool access and fabrication details require actual project evidence. Changed geometry is evaluated freshly only where its method contract permits it.</p></details>
    {native === null ? null : <DirectSupportEnds value={native.legacy.supporting_w_longitudinal_ends ?? { condition: "UNSPECIFIED" }} unit={native.legacy.bolt_diameter.unit as "in" | "mm"} onChange={(ends) => {
      const legacy = { ...native.legacy, supporting_w_longitudinal_ends: ends };
      onChange({ ...value, native_request: { ...native, legacy, ...(native.material_request === undefined ? {} : { material_request: { ...native.material_request as object, legacy_request: legacy } }) } });
    }} />}
  </>;
}
