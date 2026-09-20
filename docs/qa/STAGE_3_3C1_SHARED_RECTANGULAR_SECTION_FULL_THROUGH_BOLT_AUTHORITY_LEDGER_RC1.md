# FRP Master Connection — Stage 3.3C1 Shared Rectangular-Section + Full-Through-Bolt Architecture — Authority Ledger RC1

## New authority

Stage 3.3C1 authorizes:
1. real `SOLID_RECTANGULAR_SECTION` geometry;
2. exact opposing-face relationships for SRS;
3. exact opposing-wall relationships for RHS;
4. generalized physical bolt paths with `MATERIAL_LAYER` and `FREE_SHANK_SPAN`;
5. one continuous full-through RHS bolt crossing near wall, cavity, and far wall;
6. one continuous full-through SRS bolt crossing full solid depth;
7. external-only head/washer and nut/washer for the normal rectangular-section through-bolt arrangement;
8. shared support targets:
   - W Column Flange
   - W Beam Flange
   - W Column Web
   - Channel Column Web
   - Angle Column Leg
   - Rectangular Hollow Column Wall
   - Solid Rectangular Column Face

## RHS rule

Normal RHS path:
`near wall material -> cavity free span -> far wall material`

One physical bolt axis. Cavity is not material. No internal nut or washer.

## SRS rule

SRS path is one continuous material layer equal to the full section depth along the bolt axis.

SRS shall not be implemented as zero-cavity RHS.

## Future selector rule

When Stage 3.3C2/C3 integrates rectangular hollow options into compatible connected/support selectors, the Solid Rectangular counterpart shall also be offered unless an explicit controlled physical exclusion applies.

## Support-target boundary

C1 establishes shared target contracts only.

Family-specific connection topology/support bolt-group integration is controlled later.

Paired-angle support topology shall not be inferred from the current W-flange implementation.

## No new resistance authority

C1 does not authorize new capacities for:
- RHS wall bending/crushing/ovalization
- sleeve/crush-tube design
- SRS full-depth resistance
- connector-specific double shear

Use existing methods only where their accepted applicability contract clearly covers the geometry; otherwise fail closed.

## Frozen behavior

Stage 2.3 and Stage 3.2 freeze tags remain immutable.

Frozen Tee, accepted single-angle, and current paired-angle behavior shall remain exact except for dormant shared architecture that does not alter existing requests/results/fingerprints.

**END OF AUTHORITY LEDGER RC1**
