# FRP Master Connection — Stage 4.2 W/I Beam-to-Concrete-Wall Major-Axis Moment Connection — Authority Ledger RC1

## Authority purpose

Stage 4.2 creates the first physical beam-to-concrete-wall moment connection.

It combines:

- accepted W/I section-resultant authority;
- accepted material-neutral angle-connector core;
- the FRP angle resistance provider;
- paired web-angle allocation;
- exact wall support-group handoff;
- existing local FRP and fastener checks;
- qualified-source boundaries where a general analytical FRP through-thickness/prying method is not available.

## Source-derived requirements

ASCE/SEI 74-23 establishes that:

- connection actions and deformations must remain consistent with structural analysis;
- eccentricity effects must be retained;
- connection strength is based on the relevant components and members;
- FRP connecting elements outside ordinary prescriptive behavior require Section 2.3.2 qualification;
- Equation 8-15 may be used for applicable clip-angle instep shear;
- a general closed-form method is not provided for FRP clip-angle prying, through-thickness/delamination, or complete moment-connection behavior.

The standard does not prescribe the complete Stage 4.2 four-angle moment-connection allocation or external anchor-group distribution.

## Calculation Slice 5 authority

Method:

`RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1`.

Stage 4.2 consumes the complete:

- top-flange wrench;
- web wrench;
- bottom-flange wrench.

It does not replace them with `M/z`.

Web local moment and flange local moments remain retained.

## Negative-end structural/right-hand mapping

Method:

`EXACT_WI_NEGATIVE_END_STRUCTURAL_TO_RIGHT_HAND_WRENCH_MAP_RC1`.

This is an exact sign/reference adapter.

Calculation Slice 5 structural positive `M_T` means top-flange tension.

At the beam's negative-`L_B` end, the corresponding right-hand mechanical free-moment vector is `-M_T T_B`.

The adapter makes this mapping explicit for connector-core wrench transport and external support equilibrium.

## Physical connector topology

Exactly four FRP angles:

- top flange angle;
- bottom flange angle;
- positive web clip angle;
- negative web clip angle.

Top and bottom support legs extend outside the beam depth.

Web support legs extend to opposite sides of the web.

Four external wall-anchor groups are retained separately.

## Paired web-angle authority

Method:

`RATIONAL_SYMMETRIC_PAIRED_WEB_ANGLE_WRENCH_ALLOCATION_RC1`.

At the exact web component reference, each mirrored web angle receives one-half of the complete physical web wrench only after exact symmetry is proven.

The half-wrenches are then shifted to the actual angle member-interface references.

This produces real, opposite-signed local torsion/minor-moment components that are retained.

No component moment is discarded.

## Angle connector core authority

Each physical angle uses:

`ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1`.

The core supplies:

- exact member-interface wrench;
- exact heel-reference wrench;
- exact support-group wrench;
- exact connector equilibrium;
- provider-independent fingerprint.

No Stage 4.2 frontend wrench arithmetic.

## FRP angle provider authority

Provider:

`FRP_ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1`.

The provider supplies:

- Equation 8-15 instep shear within applicability;
- exact qualified FRP source binding;
- signed full-wrench strengths;
- source-authorized combined interaction;
- heel/leg/through-thickness/contact/prying coverage;
- fail-closed source-required behavior.

The connector core remains material-neutral.

No 316SS provider is implemented or exposed.

## Qualified member-attachment authority

Stage 4.2 introduces an application-level source contract:

`QUALIFIED_FRP_MEMBER_ANGLE_ATTACHMENT_SOURCE_RC1`.

It is not a new analytical resistance formula.

It is required where the complete member-interface wrench involves behavior not covered by existing in-plane local checks, including:

- bolt-axis force distribution;
- beam flange/web through-thickness response;
- pull-through/delamination;
- secondary bolt bending;
- local member/angle leg prying/bending;
- combined full-wrench attachment response.

The source is bound to the exact member region, angle leg, bolt/hole pattern, fastener source, interface reference, demanded wrench, coverage, and source version.

No universal FRP pull-through/prying formula is invented.

## Member-side in-plane demand authority

Stage 2.5A resolves the member-leg in-plane components:

- `F_A`;
- `F_B`;
- `M_C`.

Actual bolt coordinates are used.

Out-of-plane components:

- `F_C`;
- `M_A`;
- `M_B`

remain explicit qualified-source demand.

They are not zeroed merely because the in-plane group solver cannot evaluate them.

## Common web-bolt authority

The physical common path is:

`NEGATIVE_WEB_CLIP_ANGLE -> W/I_WEB -> POSITIVE_WEB_CLIP_ANGLE`.

Use:

`RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1`.

Actual Stage 2.5A plane vectors are checked independently.

No equal-plane assumption and no blind double-shear capacity sum.

## Flange attachment boundary

Each flange angle is a one-sided Angle/Flange attachment.

There is no hidden backing plate or second angle.

Existing in-plane local/bolt checks are evaluated where applicable.

The nonzero out-of-plane full-wrench attachment response remains qualified-source controlled.

## External wall handoff authority

Each angle returns one complete connector-on-wall group wrench at its physical support reference.

Method:

`EXACT_FOUR_ANGLE_WALL_SUPPORT_HANDOFF_ASSEMBLY_RC1`.

All four group wrenches are shifted to the wall common reference and summed exactly.

The sum recovers the beam-end mechanical wrench shifted across the physical gap.

No individual anchor force is fabricated.

## Concrete/anchor boundary

Concrete and anchor capacity are external.

Always retain:

`EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED`.

Where no qualified flexible-fixture/per-anchor distribution exists:

`FLEXIBLE_FIXTURE_PRYING_DISTRIBUTION_EXTERNAL_REQUIRED`.

The product exports exact geometry, references, group wrenches, provenance, and limitations.

## Result authority

Separate internal and external statuses.

### FRP-side

Precedence:

1. invalid;
2. evaluated failure;
3. qualified source required;
4. uncovered/not evaluated;
5. pass with qualified source and engineering review required.

Highest FRP-side state:

`PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED`.

### Whole connection

No ordinary whole-connection PASS while concrete/anchor design remains external.

## Qualification/classification authority

Always:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED=true`.

`WI_BEAM_CONCRETE_WALL_MOMENT_CONNECTION_QUALIFICATION=REQUIRED_2_3_2`.

Always unevaluated:

- moment-connection stiffness classification;
- rotation capacity;
- full-strength classification.

## Disclaimer authority

Backend ID:

`WI_BEAM_CONCRETE_WALL_MOMENT_CONNECTION_DISCLAIMER_RC1`.

The disclaimer shall distinguish:

- accepted W/I component resultants;
- exact end-wrench sign mapping;
- exact four-angle connector-core transport;
- rational paired-web allocation;
- code-based/local checks where applicable;
- qualified FRP connector and member-attachment source requirements;
- external anchor/concrete capacity;
- required Section 2.3.2 review;
- unevaluated stiffness/rotation/full-strength classification.

## Preview/design authority

Preview performs zero resistance calculations.

Run Design Check is explicit.

Engineering changes stale prior results.

## Frozen boundary

Stage 4.1 Beam Moment Splice Family and all earlier freezes remain exact.

Calculation Slices 5 and 7 remain exact.

**END OF STAGE 4.2 W/I BEAM CONCRETE WALL MOMENT CONNECTION AUTHORITY LEDGER RC1**
