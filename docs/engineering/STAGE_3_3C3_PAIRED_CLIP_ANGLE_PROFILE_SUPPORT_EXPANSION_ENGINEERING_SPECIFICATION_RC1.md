# FRP Master Connection — Stage 3.3C3 Paired Clip-Angle Connected/Supporting-Member Expansion — Engineering Specification RC1

## Status
Controlled owner engineering specification — RC1.

Stage 3.3C3 integrates the accepted Stage 3.3C1/C2 support-target and full-through rectangular-section architecture into the Symmetric Paired FRP Clip-Angle family.

Accepted starting baseline:
- `main`
- `HEAD == origin/main == cd854d3e8375ed7552cadfa157ae5e8771bda53a`
- subject `fix: orient connected rhs through bolts`
- commit count `72`
- clean worktree/index
- Stage 2.3 freeze `5bc545ab8251f9bd49dedc776962937ed5e822a2`
- Stage 3.2 freeze `d16b354732c90bf3bf7847c62be652c230a9f91e`
- Stage 3.3C2-R2 hosted CI accepted 4/4 green.

No new resistance equation is introduced.

## Connected-member profiles
Paired Angle shall support:
- Flat Plate
- Wide-Flange / I Web
- Channel Web
- Angle — selected leg
- Rectangular Hollow Section
- Solid Rectangular Section

Existing Flat Plate/W-I/Channel Stage 3.3B requests remain exact.

### Connected Angle
Physical topology:
`positive clip-angle connected leg -> first broad face of selected member Angle leg -> selected member Angle leg -> opposite broad face -> negative clip-angle connected leg`

Use one common physical through-bolt group.

Reject:
- heel collision
- perpendicular-leg collision
- heel/junction hole
- outside-leg hole
- inaccessible hardware

Do not approximate the selected Angle leg as an isolated plate.

Identical clip angles do not automatically prove 50/50 sharing for an Angle member. Geometry may remain current while pair distribution is `NOT_EVALUATED`.

### Connected RHS
Physical topology:
`positive clip leg -> near RHS wall -> cavity FREE_SHANK_SPAN -> far RHS wall -> negative clip leg`

Requirements:
- one physical bolt per common axis
- one continuous shank
- exact near/far alignment
- both walls independently contained
- no internal hardware
- head/washer outside positive connector side
- nut/washer outside negative connector side
- cavity contains shank only

### Connected SRS
Physical topology:
`positive clip leg -> complete solid rectangular depth -> negative clip leg`

One common physical through bolt. No cavity.

## Supporting-member targets
Paired Angle shall expose exactly:
- W Column Flange
- W Beam Flange
- W Column Web
- Channel Column Web
- Angle Column Leg
- Rectangular Hollow Column Wall
- Solid Rectangular Column Face

No W Beam Web.

Use the same shared support-target identity/editor as Tee and Single-Angle. No paired-only duplicate registry/editor.

### W Column Web
Two distinct mirrored support groups:
`positive support leg -> W web`
`negative support leg -> W web`

Each bolt crosses one web thickness. No W-flange penetration. Clear-web/junction exclusions remain authoritative.

### Channel Column Web
Two distinct mirrored support groups crossing one Channel web thickness. Reject flange/junction overlap.

### Angle Column Leg
Two distinct support groups on the same selected support Angle leg broad face. Each crosses one leg thickness. Reject heel/perpendicular-leg/outside-leg paths.

### RHS Column Wall
Two distinct mirrored support groups. Each group uses:
`clip support leg -> near RHS wall -> cavity FREE_SHANK_SPAN -> far RHS wall`

No internal nut/washer. Both walls independently contained. Groups may not be coincident duplicates.

### SRS Column Face
Two distinct support groups. Each uses:
`clip support leg -> full solid rectangular support depth`

External hardware at opposite face.

## Symmetric pair topology
Preserve Stage 3.3B:
- two identical mirrored clip angles
- one common connected-member group
- one positive support group
- one negative support group

Do not create two coincident common-member groups.

## Pair sharing
Reuse the exact Stage 3.3B symmetry/action proof. No new sharing equation.

Equal sharing is authorized only if the full proof passes actual geometry, materials, mirrored groups, support symmetry, reference/action symmetry, and the existing pure reaction-shear eligibility.

Do not infer equal sharing from profile names or identical connector dimensions alone.

Angle/asymmetric cases remain current geometry but `NOT_EVALUATED` for distribution if proof fails.

## Full-through hardware
Reuse Stage 3.3C2-R2 endpoint-based hardware authority. Physical shank direction derives from authoritative start/end points, not arbitrary engineering-axis sign.

Preserve engineering axes, demand/resistance sign conventions, and existing fingerprints.

## Trim
Reuse the shared full-profile trim system.
- Angle: trim physical legs as applicable; preserve heel; recompute common path.
- RHS: remain hollow; recompute full-through endpoints.
- SRS: remain solid.
Trim never auto-moves bolt groups.

## Material axes
Use backend-authoritative region bases and region-embedded axes:
- Angle legs: independent regions
- RHS: wall-specific regions; cavity has no axes
- SRS: stable solid-volume basis

## Design limitations
Preserve:
- paired connector body resistance `NOT_EVALUATED`
- common through-bolt double-shear resistance `NOT_EVALUATED`
- branch compatibility `NOT_EVALUATED`
- paired FRP qualification `NOT_EVALUATED`
- RHS local wall response `NOT_EVALUATED`
- RHS sleeve/crush-tube requirement `NOT_EVALUATED`
- SRS full-depth resistance applicability `NOT_EVALUATED`

Known supported numerical failure still governs `FAIL`. Ordinary whole-connection PASS remains prohibited while required checks are unsupported.

## API/frontend
Paired connected-profile selector shall expose:
- Flat Plate
- Wide-Flange / I
- Channel
- Angle
- Rectangular Hollow Section
- Solid Rectangular Section

Paired support selector shall expose exactly the seven shared support targets.

Render complete connected member, two real clip angles, actual support, common member group, two support groups, full-through hardware, trim, and material axes.

No generic plate fallback. No internal RHS hardware. No frontend geometry invention.

Preserve current/last-valid state separation and strict contract validation.

## Fingerprints
Existing Stage 3.3B requests remain exact.

New C3 combinations receive deterministic fingerprints with exact U.S./SI equivalence.

Tee and Single-Angle fingerprints must remain unchanged.

Any unrelated fingerprint transition is unauthorized.

## Required controlled cases
At minimum:
1. connected Angle valid
2. connected Angle heel collision invalid
3. Angle equal sharing not automatically proven
4. connected RHS common full-through
5. connected SRS common full-depth
6. support W Column Web
7. support Channel Column Web
8. support Angle Column Leg
9. support RHS full-through
10. support SRS full-depth
11. RHS common one-bolt identity
12. RHS support external-only hardware
13. SRS solid identity
14. exact U.S./SI
15. existing Stage 3.3B fingerprint invariance
16. unsupported sharing keeps current geometry
17. Angle trim
18. RHS/SRS trim
19. no duplicate common/support bolts
20. Tee/Single invariance

## Visual acceptance
After 4/4 hosted CI verify:
- all six connected profiles
- all seven support targets
- Angle member has one clip angle on each broad face of one selected leg
- heel/perpendicular-leg collisions fail closed
- RHS common bolts pass positive connector / near wall / cavity / far wall / negative connector
- SRS common bolts pass full solid depth
- RHS support groups are two distinct full-through groups
- no internal RHS hardware
- unsupported sharing/local mechanics are design limitations, not geometry errors

## Acceptance boundary
C3 is accepted only if:
- all connected/support matrices use real geometry
- shared support target/editor is reused
- Angle paired topology is physically correct
- RHS/SRS common/support full-through paths are correct
- no duplicate bolts or internal RHS hardware
- equal sharing is not inferred where not proven
- existing Stage 3.3B requests remain exact
- Tee and Single-Angle remain unchanged
- no new resistance equation
- full local/isolated QA, hosted 4/4 CI, and user visual acceptance pass

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
