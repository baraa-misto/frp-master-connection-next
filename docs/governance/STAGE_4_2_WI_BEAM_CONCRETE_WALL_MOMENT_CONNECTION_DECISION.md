# FRP Master Connection — Stage 4.2 W/I Beam-to-Concrete-Wall Major-Axis Moment Connection — Decision

## Decision

Proceed with **Stage 4.2 — W/I Beam to Concrete Wall Major-Axis Moment Connection** as the next physical Moment Connections product.

The RC1 connection uses:

- one horizontal pultruded FRP W/I beam terminating at a finite concrete wall;
- a positive physical beam-end-to-wall gap;
- one FRP angle connector on the top flange;
- one FRP angle connector on the bottom flange;
- a symmetric pair of FRP web clip angles;
- member-side metallic/stainless fasteners;
- four external wall-anchor groups;
- exact Calculation Slice 5 W/I component resultants;
- Calculation Slice 7 material-neutral angle-connector core;
- Calculation Slice 7 FRP resistance provider;
- existing local FRP/member-fastener checks where applicable;
- exact external anchor/concrete group-wrench handoff.

Concrete and anchor capacity remain external.

No 316SS connector option is exposed in RC1. The accepted material-neutral angle core is preserved so a future 316SS provider can be added without rewriting the Stage 4.2 demand mechanics.

## Accepted prerequisites

### Stage 4.1 family freeze

Accepted governance baseline:

`18419606f4143f27240a39374b25e294a9f39253`

Hosted CI:

GitHub Actions run #98, 4/4 green.

### Calculation Slice 7 RC2

Accepted implementation:

`d940192ea8eecb7e35f9601c38f3ad841f580916`

Subject:

`feat: add angle connector core and FRP resistance provider`

Hosted CI:

GitHub Actions run #99, latest attempt #2, 4/4 green.

### Calculation Slice 5

Use the accepted W/I component-resultant engine and do not recreate its equations in Stage 4.2 orchestration.

## Product identity

Product ID:

`WI_BEAM_CONCRETE_WALL_MAJOR_AXIS_MOMENT_CONNECTION`

Contract:

`4.2-RC1`

Selector:

`Moment Connections`

User-facing label:

`W/I Beam to Concrete Wall Moment Connection`

## RC1 action scope

At the beam-end centroidal section:

- signed axial force `P_L`;
- signed major shear `V_V`;
- signed major-axis moment `M_T`.

Require zero / reject:

- minor shear;
- minor-axis moment;
- torsion.

Positive axial force denotes tension.

Positive major-axis moment follows Calculation Slice 5 and produces top-flange tension.

## Beam/wall frame

Use right-handed beam axes:

- `L_B`: normal away from the wall and into the beam;
- `V_B`: vertical, positive upward;
- `T_B`: transverse, with `L_B × V_B = T_B`.

Wall front face:

`L_B=0`.

Beam end section:

`L_B=g`.

Wall common handoff reference:

`r_W=(0,0,0)` at the projection of the beam centroid onto the wall front face.

## Structural-to-mechanical end-wrench mapping

Calculation Slice 5 uses structural major-moment sign:

positive `M_T` = top-flange tension.

For exact right-hand wrench transport at the beam's negative-`L_B` end, implement:

`EXACT_WI_NEGATIVE_END_STRUCTURAL_TO_RIGHT_HAND_WRENCH_MAP_RC1`.

Mechanical beam-on-connection wrench at the beam-end centroid:

- force `(P_L,V_V,0)`;
- right-hand free moment `(0,0,-M_T)`.

Each Slice 5 component maps in the same manner:

- positive component tension -> `+L_B` force;
- structural local `m_T` -> right-hand `-T_B` moment.

The frontend shall display structural and right-hand signs explicitly rather than silently mixing them.

## Physical topology

### Top flange angle

- extrusion spans the beam flange in `T_B`;
- member leg lies on the top outer surface of the top flange;
- support leg bears against the wall and extends upward;
- one member-side 2×2 bolt group;
- one external 2×2 wall-anchor group by default.

### Bottom flange angle

- extrusion spans the beam flange;
- member leg lies on the bottom outer surface of the bottom flange;
- support leg bears against the wall and extends downward;
- one member-side 2×2 bolt group;
- one external 2×2 wall-anchor group by default.

### Paired web clip angles

- one angle on the positive-`T_B` face of the web;
- one angle on the negative-`T_B` face;
- both extend vertically;
- one common physical Angle/Web/Angle bolt group;
- one external wall-anchor group per angle.

Total angle connectors:

`4`.

Total external wall-anchor groups:

`4`.

## Default angle geometry

RC1 uses two locked geometry families:

### Flange-angle family

Top and bottom are identical mirrors:

- angle length `8 in`;
- member leg `4 in`;
- support leg `4 in`;
- thickness `0.5 in`;
- inside heel radius `0.25 in`.

### Web-angle family

Positive and negative web angles are identical mirrors:

- angle length `8 in`;
- member leg `4 in`;
- support leg `4 in`;
- thickness `0.5 in`;
- inside heel radius `0.25 in`.

## Connector local frames

All four frames satisfy:

`A_A × B_A = C_A`.

### Top flange angle

- `A_A=+T_B`;
- `B_A=+L_B`;
- `C_A=+V_B`.

### Bottom flange angle

- `A_A=-T_B`;
- `B_A=+L_B`;
- `C_A=-V_B`.

### Positive web clip angle

- `A_A=-V_B`;
- `B_A=+L_B`;
- `C_A=+T_B`.

### Negative web clip angle

- `A_A=+V_B`;
- `B_A=+L_B`;
- `C_A=-T_B`.

## Default connector references

For every default angle, in its local `(A_A,B_A,C_A)` frame:

- heel reference `r_H=(0,0,0)`;
- member-interface reference `r_M=(0,2.0,-0.25) in`;
- support-interface/anchor-group reference `r_S=(0,-0.25,2.0) in`.

The negative quarter-inch offsets place the references at the physical member and wall interface planes rather than at the angle-leg mid-surfaces.

## Slice 5 allocation

Calculation Slice 5 is called exactly once at the beam-end centroid.

### Top flange

The complete top-flange component wrench is assigned to the top flange angle.

### Bottom flange

The complete bottom-flange component wrench is assigned to the bottom flange angle.

### Web

The complete web component wrench is allocated to the paired web angles by:

`RATIONAL_SYMMETRIC_PAIRED_WEB_ANGLE_WRENCH_ALLOCATION_RC1`.

At the exact web component reference, each web angle receives one-half of the full mechanical web wrench only after exact symmetry is proven.

Each half-wrench is then shifted to its actual member-interface reference and transformed into its own connector local frame.

The resulting opposite-signed local torsion/minor-moment components are retained.

No component moment is discarded.

## Exact connector-core use

For each of the four angles:

1. construct exact member-interface local wrench;
2. invoke `ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1`;
3. obtain exact heel-reference wrench;
4. obtain exact connector-on-wall support-group wrench;
5. prove connector equilibrium.

No frontend wrench calculation.

## FRP connector resistance

Connector material/provider in RC1:

`FRP_ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1`.

No selectable 316SS provider yet.

For web clip angles, direct instep shear uses:

`ASCE_74_23_EQ_8_15_CLIP_ANGLE_INSTEP_SHEAR_RC1`.

For top/bottom flange angles, normal RC1 loads produce zero direct `A_A` instep-shear force, but the qualified full-wrench connector-body source remains required for nonzero heel moments/forces.

Complete nonzero connector-body strength requires an exact qualified FRP source package.

## Qualified member-to-angle attachment boundary

The connected W/I member and member-side fasteners must also transfer each full member-interface wrench.

Existing local in-plane FRP and fastener checks shall be run where applicable.

Any nonzero member-interface out-of-plane action, bolt-axis effect, member through-thickness response, pull-through/delamination, secondary bolt bending, or local prying requires an exact qualified attachment source:

`QUALIFIED_FRP_MEMBER_ANGLE_ATTACHMENT_SOURCE_RC1`.

The source binds:

- W/I region geometry/material;
- angle member-leg geometry/material;
- bolt/hole group;
- fastener source;
- interface frame/reference;
- demanded full wrench;
- covered member/fastener limit states;
- interaction authority.

No universal member-flange/web pull-through or prying equation is invented.

## Member-side in-plane group demand

For each angle member leg, resolve the in-plane force components and in-plane group moment through Stage 2.5A.

### Flange angles

The direct longitudinal flange force is distributed through the actual 2×2 flange-angle member bolt group.

The residual out-of-plane moment about the angle extrusion axis remains qualified-source demand.

### Web pair

Each angle's local `(F_A,F_B,M_C)` is resolved through its physical plane using Stage 2.5A.

The common Angle/Web/Angle bolts retain actual two-plane vectors.

The local `(M_A,M_B,F_C)` out-of-plane demand is not discarded and requires qualified attachment coverage.

## Common web bolts

One physical shank passes:

`NEGATIVE_WEB_CLIP_ANGLE_MEMBER_LEG -> W/I_WEB -> POSITIVE_WEB_CLIP_ANGLE_MEMBER_LEG`.

Two physical shear planes.

Use:

`RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1`.

Actual positive/negative angle Stage 2.5A plane vectors are checked independently.

No blind equal-plane assumption.

## Flange-angle member bolts

Each top/bottom flange angle is a one-angle-to-flange physical attachment.

The in-plane shear plane is checked using existing source-controlled bolt/local FRP authority.

The nonzero out-of-plane full-wrench attachment response remains qualified-source-controlled.

No backing plate or second flange angle is silently introduced.

## External wall-anchor handoff

Each angle returns one exact connector-on-wall group wrench at its support reference.

External groups:

- top flange-angle anchor group;
- bottom flange-angle anchor group;
- positive web-angle anchor group;
- negative web-angle anchor group.

Anchor/concrete capacity is not calculated.

No individual anchor forces are fabricated unless a separately accepted qualified flexible-fixture distribution exists.

Otherwise retain:

`FLEXIBLE_FIXTURE_PRYING_DISTRIBUTION_EXTERNAL_REQUIRED`.

## Exact wall-handoff assembly

Method:

`EXACT_FOUR_ANGLE_WALL_SUPPORT_HANDOFF_ASSEMBLY_RC1`.

Shift all four connector-on-wall group wrenches to `r_W` and sum.

Require exact recovery of the input mechanical beam-end wrench shifted from `r_J=(g,0,0)` to `r_W`.

For right-hand mechanics:

`F_W=(P_L,V_V,0)`.

`M_W=(0,0,-M_T+gV_V)`.

Also return the equivalent structural major-moment sign:

`M_T,wall(structural)=M_T-gV_V`.

No force or moment residual.

## Finite wall and anchor geometry

Reuse the frozen Stage 3.5 concrete-wall prism/frame and external anchor geometry architecture.

Default wall:

- width `48 in`;
- height `48 in`;
- thickness `8 in`;
- connection origin centered;
- no FRP LW/CW/TT axes assigned to concrete.

All angle support legs, holes, and external anchor groups must be fully contained on the finite wall.

## Default wall-group locations

At the wall front face in beam `(L_B,V_B,T_B)` coordinates:

- top group `(0,+7.25,0) in`;
- bottom group `(0,-7.25,0) in`;
- positive web group `(0,0,+2.5) in`;
- negative web group `(0,0,-2.5) in`.

These values are derived from default angle geometry and interface references, not hard-coded independently.

## External status boundary

Return separate statuses:

### FRP-side status

May reach:

`PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED`

only when all required beam, fastener, angle-provider, qualified attachment, and applicable local checks pass.

### Wall support status

Always:

`EXTERNAL_ANCHOR_CONCRETE_DESIGN_REQUIRED`

until an external anchor/concrete design is supplied under a future contract.

### Whole-connection status

An ordinary whole-connection `PASS` is prohibited.

Internal failure governs as `FAIL`.

Missing qualified internal source governs as `NOT_EVALUATED` or `SOURCE_REQUIRED`.

An internally passing case remains externally incomplete.

## Mandatory qualification/classification

Always:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED=true`

`WI_BEAM_CONCRETE_WALL_MOMENT_CONNECTION_QUALIFICATION=REQUIRED_2_3_2`

`MOMENT_CONNECTION_STIFFNESS_CLASSIFICATION=NOT_EVALUATED`

`MOMENT_ROTATION_CAPACITY=NOT_EVALUATED`

`FULL_STRENGTH_CLASSIFICATION=NOT_EVALUATED`

`CONCRETE_ANCHOR_CAPACITY=EXTERNAL_DESIGN_REQUIRED`.

## Mandatory disclaimer

Backend ID:

`WI_BEAM_CONCRETE_WALL_MOMENT_CONNECTION_DISCLAIMER_RC1`.

Controlled meaning:

Stage 4.2 uses Calculation Slice 5 to preserve the complete W/I top-flange, web, and bottom-flange component wrenches; exact structural-to-right-hand end-wrench mapping; symmetric paired-web-angle allocation; Calculation Slice 7 material-neutral angle cores and FRP provider; existing local/member-fastener checks; qualified source packages for complete FRP angle and member-attachment response; and exact four-group wall handoff. Concrete and anchor capacity are external. The engineer of record shall review source applicability, angle/member attachment qualification, through-thickness and prying behavior, fastener fit/contact, relative stiffness and deformation compatibility, external anchor-group analysis, and Section 2.3.2 qualification. Stiffness, rotation capacity, full-strength classification, and concrete/anchor capacity are not established.

## Preview/design separation

Preview performs:

- geometry;
- Slice 5;
- component/branch mapping;
- four Slice 7 core calls;
- exact support-group handoffs;
- exact wall equilibrium;
- source/applicability planning;
- no resistance calculations.

Run Design Check explicitly performs:

- applicable local beam/angle checks;
- Stage 2.5A member-side demand;
- source-controlled bolt checks;
- FRP angle provider checks;
- qualified attachment-source checks;
- result aggregation.

Engineering changes stale prior design.

## Frozen-family boundary

All Stage 2.3 through Stage 4.1 freeze tags and historical fingerprints remain immutable.

Calculation Slices 5 and 7 remain exact.

## Future scope

Not RC1:

- 316SS connector provider;
- concrete/anchor capacity;
- user torsion;
- minor-axis moment;
- minor shear;
- two flange angles per flange;
- backing plates;
- alternate wall support topology;
- connection stiffness/rotation design.

**END OF STAGE 4.2 W/I BEAM CONCRETE WALL MOMENT CONNECTION DECISION**
