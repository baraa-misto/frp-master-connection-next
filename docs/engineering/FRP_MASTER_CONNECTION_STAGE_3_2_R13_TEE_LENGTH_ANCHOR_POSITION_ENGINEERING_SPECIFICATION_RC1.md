# FRP Master Connection — Stage 3.2-R13 Tee Length Anchoring + Longitudinal Body Position — Engineering Specification RC1

## 1. Status
Controlled owner engineering specification — RC1.

Stage 3.2-R13 separates Tee connector length from how that length is distributed about the connector longitudinal placement.

R13 adds:
- selectable length anchoring;
- exact Tee-body longitudinal position tied to the selected anchor;
- one-sided length growth while one end remains fixed;
- exact anchor-mode switching without geometry jump.

No new demand/resistance equation, material model, fastener model, member-profile model, or connector-body strength model is authorized.

## 2. Accepted baseline
Expected baseline:
- HEAD/origin/main `d6f30fe0b7e70429252e287f816e43268c666a6b`
- subject `feat: add connected-member end trim`
- commit count 58
- tracked files 347
- clean worktree/index
- frontend tree `bc847f9b22d371b7ae5256f133c95e452bce39ef`
- freeze tag `stage-2.3-interface-geometry-freeze`
- freeze target `5bc545ab8251f9bd49dedc776962937ed5e822a2`

R12 hosted CI is accepted 4/4 green.

## 3. User intent
Current centered behavior grows equally from both longitudinal ends.

Required options:
- Centered
- Keep upper end fixed
- Keep lower end fixed

For a current-column Tee changing length 6 -> 8 in:
- Centered: +1 in at upper end, +1 in at lower end
- Keep upper end fixed: upper unchanged, lower extends 2 in
- Keep lower end fixed: lower unchanged, upper extends 2 in

Generic engineering meaning shall use the Tee +L/-L longitudinal axis, never the camera.

## 4. Tee longitudinal frame
Retain the existing authoritative Tee local frame.

Define:
- `L_T`: exact unit vector along connector length
- `D_T`: stable Tee longitudinal placement datum in support/template frame

`D_T` shall be independent of connector length, camera, bolt count, brace inclination, selected bolt, last-valid preview, and display state.

## 5. Length-anchor identity
Add:
`connector_length_anchor`

Values:
- `CENTER`
- `POSITIVE_L_END`
- `NEGATIVE_L_END`

Current vertical-template UI labels:
- Centered
- Keep upper end fixed
- Keep lower end fixed

Generic trace retains +L/-L identities.

## 6. Selected-anchor position
Add exact:
`connector_length_anchor_position`

This is the signed coordinate of the selected anchor along `L_T`, measured from `D_T`.

Interpretation:
- CENTER: Tee-body longitudinal midpoint coordinate
- POSITIVE_L_END: +L end coordinate
- NEGATIVE_L_END: -L end coordinate

This makes geometry stateless and reproducible.

## 7. Exact extent equations
Let total connector length `L > 0` and anchor coordinate `a`.

CENTER:
- center = a
- positive_end = a + L/2
- negative_end = a - L/2

POSITIVE_L_END:
- positive_end = a
- negative_end = a - L
- center = a - L/2

NEGATIVE_L_END:
- negative_end = a
- positive_end = a + L
- center = a + L/2

Use exact Decimal arithmetic only.

## 8. Backward compatibility
Legacy/omitted R13 fields shall reproduce the existing centered Tee exactly.

Preferred legacy default:
- anchor = CENTER
- anchor_position = 0

If the current legacy center is not coordinate zero in the new datum, use the exact equivalent coordinate and lock it in regression tests.

All legacy controlled geometry/fingerprints remain exact.

## 9. Anchor switching without a geometry jump
Changing only anchor mode shall preserve the current Tee body exactly.

Given current server-authored:
- center `c`
- positive end `p`
- negative end `n`

switching to:
- CENTER uses `a=c`
- POSITIVE_L_END uses `a=p`
- NEGATIVE_L_END uses `a=n`

No viewer jump.

If no valid current preview exists, do not guess a conversion.

## 10. Length editing
When only Connector length changes:

CENTER:
- anchor coordinate unchanged
- both ends move symmetrically

POSITIVE_L_END:
- anchor coordinate unchanged
- +L end fixed
- only -L end moves

NEGATIVE_L_END:
- anchor coordinate unchanged
- -L end fixed
- only +L end moves

Backend geometry is authoritative.

## 11. Tee body longitudinal position
Expose the selected-anchor coordinate as a user-editable body-position control.

Current-column label:
`Tee vertical position`

Helper:
`Position of the selected length anchor along the Tee longitudinal axis. + moves toward +L / upper direction.`

Generic/beam label:
`Tee longitudinal position`

Changing this value translates the Tee body along `L_T` without changing its length.

## 12. Bolt-group independence from connector length
Changing only connector length or its anchor shall not move Interface A or Interface B bolt centers/axes.

Bolt groups remain controlled by R10/R11 independent placement datums and offsets.

Changing body extents only changes:
- finite Tee boundaries
- clearances
- whether existing holes remain contained

Do not auto-move bolts.

## 13. Tee-body position versus bolt groups
Changing Tee body longitudinal position moves the Tee body boundaries relative to the independently positioned bolt groups.

Bolt groups do not automatically translate.

This is deliberate. R10/R11 already provide bolt-group positioning.

Recompute clearances and fail closed if the translated body no longer contains a group.

## 14. Connected member and support
Changing Tee length/anchor/body position shall not automatically move or resize:
- support member
- connected brace/beam
- brace inclination
- profile roll

Recompute physical overlap/contact/interference against the changed Tee body.

No hidden member movement.

## 15. R12 trim interaction
R12 end-trim clearance value remains exact and unchanged when Tee length/anchor/body position changes.

Recompute:
- connector interference
- trim/reference finite region
- profile/cut intersection
- trimmed-edge geometry

against the updated Tee body.

Do not auto-change R12 clearance.

## 16. Finite boundary clearances
For each interface recompute exact complete-hole clearances to the updated Tee longitudinal ends.

Expose at minimum:
- governing Tee end
- governing bolt
- exact complete-hole clearance

Reuse R10/R11 clearance authority.

No new code-required edge-distance equation.

## 17. Other Tee dimensions
R13 controls only length-axis anchoring/positioning.

Flange width, flange thickness, stem depth, and stem thickness retain current semantics.

No one-sided flange-width extension is authorized.

## 18. API / result trace
Extend Tee contracts backward-compatibly with:
- connector_length_anchor
- connector_length_anchor_position

Return:
- tee_longitudinal_datum_id
- L_T
- normalized anchor
- normalized anchor coordinate
- body center coordinate
- positive-end coordinate
- negative-end coordinate

Legacy requests remain unchanged.

## 19. Fingerprints
Engineering identity shall reflect resulting authoritative Tee geometry.

Different anchor representations of identical physical body geometry should share the same physical Tee-body geometry fingerprint.

Anchor editing preference may be retained separately as request provenance if needed.

No legacy fingerprint transition is authorized.

## 20. Frontend controls
Within Connector show:

- Connector length
- Flange width
- Flange thickness
- Stem depth
- Stem thickness
- Length anchor
  - Centered
  - Keep upper end fixed
  - Keep lower end fixed
- Tee vertical position

If upper/lower is not physically meaningful, use Keep +L end fixed / Keep -L end fixed.

Show the +L axis in an inspector/legend.

## 21. User interaction
Changing anchor mode:
- preserve body geometry exactly
- convert anchor position from current accepted backend extents
- no visual jump

Changing connector length:
- preserve selected anchor coordinate
- regenerate backend geometry
- do not move bolts

Changing Tee body position:
- translate body along L_T
- do not change length
- do not move bolt groups

## 22. Controlled numerical benchmarks
Companion R13 golden uses semantic longitudinal datum `D_T=0`.

A1: L=6, CENTER, a=0 => center 0, +end 3, -end -3
A2: L=8, CENTER, a=0 => center 0, +end 4, -end -4
A3: L=8, POSITIVE_L_END, a=3 => center -1, +end 3, -end -5
A4: L=8, NEGATIVE_L_END, a=-3 => center 1, +end 5, -end -3
A5: L=6 representations CENTER/0, POSITIVE/3, NEGATIVE/-3 are exact physical equivalents
A6: L=6, CENTER, a=1 => center 1, +end 4, -end -2
A7: A1 -> A3 leaves all Interface A/B bolt centers/axes unchanged
A8: A1 -> A6 translates Tee body 1 along +L while bolt groups stay fixed

## 23. Visual acceptance
V1 Centered: 6 -> 8 grows equally.
V2 Keep upper fixed: 6 -> 8 leaves upper end fixed, lower grows 2.
V3 Keep lower fixed: inverse.
V4 Mode switching: Centered -> Upper -> Lower with no connector jump.
V5 Tee position: shift body +1 in while bolt groups remain fixed.
V6 Containment: shorten/reposition until a bolt violates the Tee end and verify exact clearance failure + R6 last-valid preview.
V7 R12 trim regression: inclined trimmed brace remains correctly evaluated while Tee anchoring/position changes.

## 24. Acceptance
R13 requires:
- exact centered backward compatibility
- one-sided length growth
- mode-switch continuity
- body-position/bolt-position separation
- no automatic bolt movement
- recomputed finite clearances
- R12 trim remains authoritative
- no new resistance equation
- all legacy hashes/fingerprints exact
- full 4/4 hosted CI
- V1-V7 pass

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
