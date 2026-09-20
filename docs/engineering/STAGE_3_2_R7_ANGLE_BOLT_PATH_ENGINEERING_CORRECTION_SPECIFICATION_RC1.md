# FRP Master Connection — Stage 3.2-R7 Angle Profile Bolt-Path Geometry — Engineering Correction Specification RC1

## 1. Status

**Controlled owner engineering correction specification — RC1**

Stage 3.2-R7 corrects the connected Angle-profile through-thickness bolt-path geometry exposed during renewed V1 visual acceptance.

R6 correctly distinguished current invalid inputs from the displayed last-valid preview. The remaining defect is now backend/domain geometry: a conservative `6 x 6 x 0.5 in` Angle brace with a `2 x 2` Brace ↔ Tee Stem group and `Leg Y outer face` is rejected with:

`Each connected-profile bolt path must select one finite opposing broad face.`

R7 authorizes a narrow Angle-profile surface/penetration correction only.

No new demand equation, resistance equation, profile family, material rule, or connection topology is authorized.

## 2. Accepted starting baseline

Expected baseline:

- `HEAD == origin/main`: `23b7339b94bc2513492fb3e0704863f07e62965a`
- subject: `fix: synchronize tee preview with current inputs`
- commit count: `51`
- worktree/index: clean
- frontend source tree: `40956420c22c42910a8a2cbe82c74ed2e6a5f407`
- Stage 2.3 freeze tag: `stage-2.3-interface-geometry-freeze`
- freeze target: `5bc545ab8251f9bd49dedc776962937ed5e822a2`

R6 hosted CI is accepted 4/4 green with 259/259 frontend tests across 20 files on Ubuntu and Windows.

## 3. Observed visual-acceptance result

The renewed V1 case used:

- connection: Brace connection — Tee connector
- support: W Column Flange
- connected member: Angle
- Leg Y = `6 in`
- Leg Z = `6 in`
- thickness = `0.5 in`
- member/view length = `8 in`
- orientation = `0°`
- selected surface = `Leg Y outer face`
- Brace ↔ Tee Stem = `2 rows x 2 bolts per row`
- pitch = `2 in`
- gauge = `2 in`
- all displayed end/side distances = `1 in`

The backend rejected the preview with the finite-opposing-broad-face invariant.

R6 behaved correctly by showing the last valid Flat Plate preview with an explicit red invalid/stale warning.

Therefore:

- R6 visual state behavior: **PASS**
- V1 Angle geometry acceptance: **FAIL / BLOCKED**
- R7 is required before Stage 3.2 can close.

## 4. Angle cross-section authority

Use the existing R2 member local frame:

- `X` — member longitudinal axis
- `Y`, `Z` — cross-section axes

For an Angle with:

- `leg_y = Ly`
- `leg_z = Lz`
- `thickness = t`

the authoritative cross-section is the union of two rectangular legs sharing the heel region.

Conceptually in the Y-Z cross-section:

- Y-leg occupies `0 <= Y <= Ly`, `0 <= Z <= t`
- Z-leg occupies `0 <= Y <= t`, `0 <= Z <= Lz`

Equivalent repository orientation/origin conventions are acceptable, but the physical union and exposed-face behavior must be identical.

The overlap `0 <= Y <= t`, `0 <= Z <= t` is one solid heel region, not two separate penetrated layers.

## 5. Selectable outer surfaces

Preserve the existing user-selectable surfaces:

- `LEG_Y_OUTER`
- `LEG_Z_OUTER`

Do not add inner faces to the normal connection-surface dropdown.

For the conceptual convention above:

### LEG_Y_OUTER

Outer broad face of the Y-leg at the exterior Z face.

A bolt axis normal to this surface penetrates the Y-leg thickness.

### LEG_Z_OUTER

Outer broad face of the Z-leg at the exterior Y face.

A bolt axis normal to this surface penetrates the Z-leg thickness.

Exact signs may follow the current repository orientation, but physical correspondence must be preserved.

## 6. Required finite opposing broad face

For every bolt through a selected Angle outer leg face, the backend must resolve exactly one finite opposing **boundary** face of the same physical leg.

The opposing broad face is not the entire mathematical plane at one thickness offset because part of that plane lies inside the solid heel overlap and is not an exposed boundary.

### LEG_Y_OUTER opposing face

The valid opposing inner broad-face patch is the Y-leg inner boundary excluding the heel overlap.

Conceptually:

- thickness offset from outer surface = exactly `t`
- transverse exposed region along the leg excludes the internal heel strip
- valid exposed strip is `t <= Y <= Ly` subject to the repository's exact boundary convention

### LEG_Z_OUTER opposing face

Likewise:

- thickness offset = exactly `t`
- valid exposed strip excludes the internal heel
- conceptually `t <= Z <= Lz`

The backend may represent this as a derived finite opposing-face patch, exact penetration region, or equivalent exact solid-ray intersection result, but it must be derived from existing authoritative Angle solids.

## 7. Bolt-path validity rule

A bolt path through an Angle leg is valid only when all are true:

1. bolt center lies on selected finite outer connection surface;
2. path normal enters Angle solid;
3. it traverses exactly one leg thickness for selected leg;
4. it exits through exactly one finite opposing broad boundary face of that same leg;
5. it does not use the internal heel-overlap plane as an opposing boundary;
6. it does not leave through a free edge;
7. penetrated thickness equals exact Angle leg thickness `t`.

A bolt center in the heel-overlap strip for which no exposed opposing broad face exists remains invalid.

A bolt center outside leg bounds remains invalid.

Do not weaken the invariant.

## 8. No ray/tolerance workaround

Forbidden:

- epsilon expansion of the Angle
- accepting internal heel surfaces as exposed
- accepting free-edge exits as broad opposing faces
- choosing nearest arbitrary plane
- `isclose`
- benchmark-specific bypass
- frontend-generated opposing face
- treating Angle as Flat Plate for calculation while drawing an L-shape

The physical Angle solid and penetration path remain authoritative.

## 9. Derived geometry and fingerprints

The corrected opposing-face/penetration result shall be derived from existing Angle dimensions, orientation, selected surface, and bolt coordinates.

Prefer not to add redundant engineering identity fields when the opposing face is deterministic from existing fingerprinted geometry.

Expected:

- Stage 2 fingerprints unchanged
- R4 U.S./SI fingerprints unchanged
- R2 member-profile fingerprints unchanged unless a previously fingerprinted field was objectively wrong

If any accepted fingerprint changes, STOP before commit and report exact before/after and why unavoidable.

## 10. Material / resistance boundary

R7 does not change material or resistance authority.

For a valid Angle bolt path:

- existing FRP layer identity remains
- penetrated layer thickness is actual selected leg thickness
- existing material-direction mapping remains
- existing bearing/net/shear/block applicability remains subject to current prerequisites
- no Angle-leg bending, prying, local buckling, delamination, or new member-body resistance is created

## 11. Controlled geometry benchmarks

The companion R7 golden controls only Angle geometric surface/penetration behavior.

It shall prove at minimum:

- a point on LEG_Y_OUTER safely outside heel has an opposing face exactly one thickness away
- a point on LEG_Z_OUTER safely outside heel has an opposing face exactly one thickness away
- a point in heel-overlap strip has no valid exposed opposing broad face
- a point beyond a leg free edge is invalid
- orientation transforms preserve physical thickness and surface pairing

## 12. UI / application behavior after correction

No new UI architecture is required.

When a valid Angle configuration is accepted:

- current preview becomes current-valid
- viewer renders backend-authored L-angle profile
- red last-valid-preview warning clears
- selected Angle connection surface is visible/traceable
- Brace ↔ Tee Stem bolts appear on selected physical leg

When an actually invalid Angle configuration is entered, R6 behavior remains unchanged.

## 13. V1 acceptance fixture

After R7, use a backend-confirmed valid fixture for visual acceptance.

Start from:

- Angle `6 x 6 x 0.5 in`
- member/view length `8 in`
- orientation `0°`
- selected `Leg Y outer face`
- Interface A `2 x 2`
- pitch `2 in`
- gauge `2 in`

The exact end/side distances may remain `1 in` only if backend mapping proves all four bolt centers lie in the valid exposed leg patch.

If one generic layout value maps a bolt into heel/internal strip under current coordinate conventions, do not change geometry semantics. Report the exact valid side/end-distance fixture and use it consistently in regression and visual acceptance.

## 14. Acceptance boundary

R7 is acceptable only if:

- Angle opposing-face geometry is physically correct
- valid Angle Tee preview succeeds
- invalid heel/free-edge paths still fail closed
- no geometry tolerance introduced
- no calculation equation changes
- all prior controlled hashes/fingerprints exact
- full QA green
- hosted CI 4/4 green
- renewed V1 visually shows a real Angle and responsive valid bolt layout

**END OF CONTROLLED ENGINEERING CORRECTION SPECIFICATION — RC1**
