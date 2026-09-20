# FRP Master Connection — Stage 3.6B Web-Splice Resistance Completion — Authority Ledger RC2

## Supersession

This RC2 ledger supersedes all earlier Stage 3.6B ledgers/packages.

Earlier Stage 3.6B attempts were not implemented or registered as controlling repository authority.

## Accepted prerequisite

Calculation Slice 4 — Chapter 7 Pure-Mode FRP Plate Strength Engine is accepted at:

`a93aa5d127a51dc81a6c7cd108af15c44d59ff9f`.

Stage 3.6B shall call Slice 4 rather than duplicate Chapter 7 equations.

## Code-based pure-mode authority

Calculation Slice 4 supplies:

- longitudinal plate tension;
- longitudinal plate compression rupture + orthotropic buckling;
- in-plane shear rupture + orthotropic shear buckling;
- source resistance/time factors;
- commentary advisories;
- deterministic provenance.

## Rational combined authority

Controlled project method:

`RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1`.

For each exact symmetric splice plate and critical clear-body section:

- derive exact normal stress from axial force plus in-plane bending;
- derive membrane in-plane shear stress;
- consume Slice 4 design stresses;
- compute `U_n`;
- compute `U_v`;
- compute `U_R=U_n+U_v`.

Pass when `U_R<=1`.

This interaction is rational project authority, not an ASCE-prescribed interaction equation.

## Rational panel authority

Controlled panel mapping:

`RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1`.

Stage 3.6B passes actual clear-body `a`, plate height `b`, and thickness `t` into Slice 4.

Slice 4 normative equations and advisories remain unchanged.

## Review / qualification

Whenever rational method executes:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED=true`.

Retain:

`FRP_SPLICE_PLATE_CONNECTION_ELEMENT_QUALIFICATION=REQUIRED_2_3_2`.

Allowed complete in-plane pass state:

`PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED`.

Unqualified prescriptive PASS is not allowed.

## Disclaimer

Mandatory backend disclaimer:

`WEB_SPLICE_RATIONAL_BODY_INTERACTION_DISCLAIMER_RC1`.

Its report meaning must identify the project-specific conservative linear interaction, code-based Chapter 7 pure-mode strengths, rational clear-body boundary idealization, non-prescriptive status, engineer-of-record review, Slice 4 advisories, and Section 2.3.2 qualification.

## Physical double-shear authority

Exact Plate/Web/Plate path:

- two physical shear planes;
- per-plane demand = half actual physical per-bolt in-plane Stage 2.5A demand after exact plate symmetry;
- per-plane design strength = `0.75 F_nv A_b`;
- two-plane design strength = twice per-plane strength.

Use existing thread/source authority.

Do not invent F593 strength.

## Minor shear / flexural boundary

Minor shear:

`WEB_SPLICE_MINOR_SHEAR_BOLT_AXIS_RESPONSE=NOT_EVALUATED`.

No automatic combined bolt tension/shear without an authorized tension solution.

User flexural moment:

`WEB_SPLICE_MEMBER_FLEXURAL_MOMENT_TRANSFER=NOT_AUTHORIZED_IN_RC1`.

## Historical/frozen boundary

Historical Stage 3.6A remains exact.

Calculation Slice 4 remains exact.

Stage 3.5 and earlier freeze tags/fingerprints remain immutable.

**END OF STAGE 3.6B RC2 WEB-SPLICE RESISTANCE COMPLETION AUTHORITY LEDGER**
