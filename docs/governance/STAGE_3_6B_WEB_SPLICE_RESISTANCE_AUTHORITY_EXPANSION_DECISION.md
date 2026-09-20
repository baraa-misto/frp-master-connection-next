# FRP Master Connection — Stage 3.6B Web-Splice Resistance Completion with Rational Plate-Body Interaction — Decision RC2

## Supersession

This RC2 decision supersedes every earlier Stage 3.6B decision/package.

The prior Stage 3.6B package was correctly stopped because executable Chapter 7 pure-mode plate-strength engines did not yet exist.

That prerequisite is now satisfied by accepted **Calculation Slice 4 — Chapter 7 Pure-Mode FRP Plate Strength Engine** at:

`a93aa5d127a51dc81a6c7cd108af15c44d59ff9f`

Calculation Slice 4 is controlling inherited authority for Stage 3.6B.

## Decision

Resume Stage 3.6B on top of Calculation Slice 4.

The accepted Stage 3.6A physical topology remains unchanged:

- two identical collinear FRP W/I beams;
- positive beam-end gap;
- two locked symmetric FRP web splice plates;
- one Plate/Web/Plate physical bolt group on each side of the joint;
- signed Axial, Major, and Minor force;
- zero user-applied moment;
- no flange splice;
- no single-sided splice plate.

Stage 3.6B adds:

1. **physical two-shear-plane metallic bolt resistance** for the exact symmetric Plate/Web/Plate bolt path; and
2. **calculated FRP splice-plate inter-group body resistance** using code-based Calculation Slice 4 pure-mode strengths inside a controlled rational combined normal/shear interaction.

## Code-based versus rational authority

Calculation Slice 4 supplies code-based pure-mode plate design strengths for:

- longitudinal tension — ASCE/SEI 74-23 Section 7.5;
- longitudinal compression — Section 7.6 material rupture plus orthotropic buckling;
- in-plane shear — Section 7.7 material rupture plus orthotropic shear buckling.

The combined longitudinal normal-force + in-plane-shear interaction below is not prescribed directly by ASCE/SEI 74-23.

Controlled rational method:

`RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1`.

For each critical section/fiber:

`U_n = |sigma_L| / applicable Slice-4 normal design stress`

`U_v = |tau_LT| / Slice-4 shear design stress`

`U_R = U_n + U_v`.

Pass when:

`U_R <= 1.0`.

The method is intentionally conservative and requires engineering review.

## Rational body panel

Controlled panel model:

`RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1`.

The unperforated central body lies between the joint-side boundaries of the inner bolt holes.

Stage 3.6B supplies the actual clear-body:

- longitudinal length `a`;
- full plate height `b`;
- thickness `t`;

to Calculation Slice 4.

Calculation Slice 4's normative Chapter 7 equations remain unchanged.

Any Slice 4 commentary warnings remain visible provenance.

## Mandatory disclaimer

Whenever the rational interaction executes, backend results shall carry:

`WEB_SPLICE_RATIONAL_BODY_INTERACTION_DISCLAIMER_RC1`.

Required meaning:

The combined FRP web-splice plate body calculation uses a project-specific conservative linear interaction of separately derived ASCE/SEI 74-23 Chapter 7 pure-mode plate design resistances. The interaction equation and the selected clear-body boundary idealization are rational engineering methods and are not prescribed directly by ASCE/SEI 74-23. The engineer of record shall review the assumptions, actual restraint/buckling boundary conditions, and Section 2.3.2 qualification requirements.

If report generation exists, render this in the final disclaimer section. Otherwise preserve the backend-controlled disclaimer metadata for the future reporting stage.

## Whole-splice result

For zero Minor shear and zero user-applied moment, when all required supported local FRP checks pass, supported common-bolt double-shear checks pass, rational splice-plate body interaction passes, and no other required unsupported state is active, the connection may report:

`PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED`.

It shall not report an unqualified prescriptive PASS.

Any supported numerical failure governs `FAIL`.

## Double-shear bolt authority

For each exact Plate/Web/Plate common bolt:

- physical shear planes = 2;
- outer splice plates receive exact 0.5/0.5 branch allocation;
- physical per-bolt in-plane demand comes from accepted Stage 2.5A;
- per-plane demand = physical demand / 2;
- per-plane design strength = `phi Fnv Ab`;
- two-plane design strength = `2 phi Fnv Ab`.

No generic F593 strength may be invented.

Source-pending F593 remains source-pending unless existing explicit verified/custom strength authority supplies the needed material strength.

## Remaining limitations

Stage 3.6B still excludes:

- user-applied beam flexural moment;
- flange splice;
- single-sided web splice;
- Minor-shear bolt-axis tension/pull-through/prying closure;
- slip-critical behavior;
- unequal beams/non-W/I expansion.

## Historical/frozen boundary

Historical Stage 3.6A behavior and fingerprints remain exact.

Calculation Slice 4 behavior/fingerprints remain exact.

Stage 3.5 and all earlier freeze tags remain immutable.

**END OF STAGE 3.6B RC2 WEB-SPLICE RESISTANCE COMPLETION DECISION**
