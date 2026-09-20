# Calculation Slice 1 Input and Applicability Specification

## Scope

This Stage 2.1A specification controls planning inputs and fail-closed readiness for
the first ASCE/SEI 74-23 Chapter 8 single-bolt/single-row FRP slice. It creates no
numerical resistance, capacity, utilization, or calculated physical-input comparison.

## Resolved input chain

The input retains assembly/interface/component/layer/bolt identities, a C3 master bolt
center and authoritative axis, intended ordered penetrated layers, exact entry/exit
patches, physical element and material region, round physical hole diameter, explicit
comparison tolerance, signed in-plane force, resolved reference point/frame, and
demand provenance. A member-end action alone is not a resolved bolt demand and returns
`BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED`.

Bolt-axis tension and prying are explicit nonnegative demands. No single-lap geometry
creates prying. No action shifts or demand distributions occur implicitly.

## Geometry mapping

- Forward signed force defines `e1`; the reverse intersection remains separate.
- Force reversal swaps forward and reverse distances but does not change acute theta.
- Both physical side distances are retained.
- Equal sides use both raw values.
- One side at/below `2e2,min` and the other beyond it uses raw near and capped far.
- Both sides beyond the cap use the cap on both sides.
- Unequal sides both at/below the cap remain unsupported.
- The actual rectangular physical material boundary controls.
- `theta <= 5 degrees` selects longitudinal; `5 < theta <= 90 degrees` selects transverse.
- Exactly 90 degrees records `TRANSVERSE_ENDPOINT_INCLUDED`.

## Ordinary Chapter 8 prerequisites

The plan retains the following checks without evaluating strength:

- bolt diameter 0.375 through 1.0 in.;
- one logical bolt and one row for this slice;
- one common authoritative standard round-hole diameter across all layers;
- layer thickness at least 0.188 in.;
- tension `e1 >= 4d`, with no automatic return-element exception;
- compression `e1 >= 2d`;
- each raw edge distance at least `1.5d`;
- washer outside diameter at least `2d`;
- washer thickness at least 0.051 in.; and
- washers beneath head and nut.

More than three bolts across a row or more than three rows requires Section 2.3.2
qualification. Other multi-bolt/multirow conditions remain unsupported in Stage 2.1A.

## Limit-state planning

| Plan | Applicability/readiness rule |
|---|---|
| Bolt tension/shear/combined | Locked absent `Fnt` is `SOURCE_DATA_PENDING`; explicit non-F593 fixture `Fnt` requires exactly one identified shear plane for numerical shear/combined evaluation. Zero planes are incomplete and multiple planes are unsupported. |
| Pull-through | Zero explicit bolt-axis/prying demand is `NOT_APPLICABLE`; positive demand requires material and washer inputs. |
| Pin bearing | Requires nonzero in-plane demand and directional `FBR_L`/`FBR_T`; ICE values carry engineering-review qualification. |
| Net-section tension | Tension only; requires directional `FT_L`/`FT_T` and supported effective width. |
| Shear-out | Tension or compression; requires `e1`, hole, thickness, and `FSH_LT`; no return-element credit is automatic. |
| Cleavage | Longitudinal tension can be ready; compression and exactly transverse tension are not applicable; oblique tension is unsupported. |

## Aggregate precedence

The deterministic order is invalid geometry, supplied known fail, unsupported bolt
demand distribution, Section 2.3.2 qualification, unsupported calculation, incomplete
input, source data pending, engineering review, and all-required-checks-not-applicable.
Planning `READY` is never itself `PASS`. Stage 2.1B separately evaluates ready plans;
known numerical failure precedes unsupported required work, and unsupported required
work prevents aggregate PASS when no known failure exists.

The J1 one-leg angle-to-W connection retains whole-connection
`SECTION_2_3_2_QUALIFICATION_REQUIRED` even when component plans are ready.

Net-section readiness also requires `effective_width > hole_diameter`. Layer input
retains `SHAPE_ELEMENT` or `PLATE` for the approved net-section coefficient. The
direction family remains selected by applicability and is consumed without
reinterpretation by the equation layer.

## Stage 2.2A canonical-input assembly

The application service builds this existing planning input only after exact
assembly/context, interface, group, bolt, path, combination, layer, material, and
fastener resolution. It maps each supported FRP path layer from physical C3 geometry,
preserves metallic layers without creating FRP checks, and requires an explicit
resolved demand for the exact selected bolt. A manual member-end action without that
demand yields `BOLT_DEMAND_DISTRIBUTION_METHOD_NOT_SUPPORTED`; no resistance equation
requiring bolt demand runs. Distinct material snapshots in one evaluator call fail
closed because the current Stage 2.1 input authorizes one snapshot per call.

## Stage 2.3R6 end-distance input provenance

`Bolt-to-brace-end distance e1` is an upstream engineering geometry input, not a
calculation-plan override. The template adapter uses it to construct the canonical
connected end and selected bolt relationship. The existing geometry-to-code mapper
then derives each applicable layer's `forward_e1`/reverse distance from physical
geometry before Stage 2.1 planning and equation execution. The default J1 source
values are `2.000 in` and exactly `50.8 mm`.

Brace/column connection-view extents are not calculation-slice inputs. They are
excluded from plans, applicability, capacities, statuses, and calculation
fingerprints. No change is made to any Stage 2.1B executable equation or RC2 golden
value.
