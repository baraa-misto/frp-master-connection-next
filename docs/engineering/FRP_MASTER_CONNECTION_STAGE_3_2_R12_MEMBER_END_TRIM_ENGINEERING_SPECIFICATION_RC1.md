# FRP Master Connection — Stage 3.2-R12 Connected-Member End Trim + User Clearance — Engineering Specification RC1

## 1. Status
Controlled owner engineering specification — RC1.

R12 adds explicit fabrication end-trim geometry where an inclined brace/beam would otherwise interfere with the Tee connector.

User-facing controls:
- Toggle: `Apply end trim clearance`
- Value: `End clearance to Tee flange`

Generic domain terms:
- `connected_member_end_trim_enabled`
- `connected_member_end_clearance`

No new resistance equation is authorized.

## 2. Accepted baseline
Expected baseline after R11:
- HEAD/origin/main `50227eff7efbd7450faf02e126ce9d934afbdbd9`
- subject `feat: simplify tee bolt-group placement`
- commit count 57
- clean worktree/index
- frontend tree `3127d32683eb25a4f68bf0b00e75722aa40855e2`
- freeze tag `stage-2.3-interface-geometry-freeze`
- freeze target `5bc545ab8251f9bd49dedc776962937ed5e822a2`

R11 hosted CI is accepted 4/4 green.

## 3. User input
Add:
- `connected_member_end_trim_enabled: bool`
- `connected_member_end_clearance: Decimal distance | null`

Trim Off:
- clearance is omitted/non-authoritative;
- legacy untrimmed geometry remains;
- any interference is reported, not hidden.

Trim On:
- explicit clearance is required;
- clearance >= 0;
- negative/nonfinite values reject;
- zero means flush to the controlled clearance reference plane;
- positive value creates a physical gap.

Do not insert a nonzero engineering default.

## 4. Tee clearance reference plane
Define backend-authoritative `TEE_FLANGE_INNER_CLEARANCE_PLANE`: the Tee flange/root plane bounding the region the connected member end must clear.

Its normal points away from the Tee flange/root along the Tee stem toward the connected member.

It is independent of camera, brace inclination, bolt position, selected bolt, and frontend mesh.

## 5. Fabrication cut plane
With trim enabled and clearance `c`, create a plane parallel to `TEE_FLANGE_INNER_CLEARANCE_PLANE`, offset exactly `c` away from the connector obstruction.

The retained connected-member solid is the side away from the connector obstruction.

The fabricated end/free edge is the exact intersection of this cut plane with the actual member profile solids.

The cut plane is fixed in the Tee/support frame, not square to the inclined brace/beam axis.

## 6. Supported profiles
Apply the same cut-plane operation to actual existing solids for:
- Angle
- Channel
- Wide-flange / I
- Rectangular hollow section
- Flat plate

Round hollow section remains outside current Tee direct-contact scope.

No flat-plate substitution and no frontend-only clipping.

## 7. Brace inclination and roll
The cut plane remains tied to the Tee frame.

Changing inclination, profile roll, or member dimensions changes the solid/plane intersection but does not rotate the cut plane with the brace.

## 8. Clearance meaning
`End clearance to Tee flange = c` is the exact perpendicular distance between:
1. `TEE_FLANGE_INNER_CLEARANCE_PLANE`; and
2. the fabrication cut plane.

It is not:
- bolt-center distance;
- distance along the brace axis;
- code edge distance;
- hole-edge clearance.

## 9. Interference
Trim Off:
- if the untrimmed connected-member solid enters the connector obstruction region beyond intended contact, return `CONNECTED_MEMBER_CONNECTOR_INTERFERENCE`;
- show the actual interference;
- do not auto-trim.

Trim On:
- trim the member;
- measured plane gap must equal user value exactly;
- remaining interference still fails closed;
- do not auto-increase clearance.

## 10. Trimmed authoritative surfaces
All member geometry after trim is based on the trimmed solids, including:
- selected Interface A surface bounds;
- exposed broad-face patches;
- free edges;
- hole containment;
- opposing-face paths;
- layer extents.

R7/R8 wall/leg path rules remain controlling.

## 11. Bolt-to-trim-edge geometry
For every Interface A hole affected by the fabricated end, compute:
- bolt-center-to-trim-edge distance;
- hole-edge-to-trim-edge clearance;
- governing bolt;
- governing trim-edge identity.

Negative hole-edge clearance is invalid; exact zero is the physical containment boundary.

## 12. Existing resistance methods
Existing bearing/shear-out/net/block methods may consume the trimmed free edge only if their current accepted geometry contract clearly maps to that same physical edge without new interpretation.

Otherwise return unsupported/not evaluated.

R12 introduces no new resistance equation.

## 13. R10/R11 bolt positioning
Trim is independent from bolt-group positioning.

After trim/inclination/offset changes, recompute:
- trimmed solids;
- interference;
- bolt paths;
- hole containment;
- hole-to-trim-edge geometry;
- method applicability.

Never auto-move bolts.

## 14. Exact recovery feedback
If trim causes a hole-edge violation, return exact guidance such as:
`Hole-edge clearance to fabricated end: -0.125 in`
`Move the bolt group away from the trimmed end by at least 0.125 in.`

This is geometry guidance, not automatically a code minimum.

## 15. API/result trace
Expose:
- trim enabled;
- normalized clearance;
- reference plane ID;
- cut plane ID;
- cut origin/normal;
- measured plane clearance;
- interference status;
- trimmed member geometry identity;
- per-bolt center-to-trim-edge distance;
- per-hole trim-edge clearance;
- governing trim-edge bolt.

Legacy omission means trim disabled.

## 16. Fingerprints
Trim disabled/omitted preserves current controlled geometry and fingerprints.

Trim enabled adds exact clearance and resulting trimmed geometry to engineering identity.

Display clipping/camera do not enter engineering fingerprints.

## 17. Frontend
Within Connected Member add:

`Member end trim`
- `[ ] Apply end trim clearance`

When Off:
- hide/disable numeric field;
- show `No fabrication end trim`.

When On:
- show `End clearance to Tee flange`
- exact unit-aware numeric input

Helper:
`Perpendicular gap between the fabricated member end and the Tee flange/root clearance plane.`

## 18. Viewer
Trim On:
- visibly trim the real profile;
- show the actual new end shape and gap;
- no ghost removed material;
- Tee/support unchanged.

Preferred optional overlay: cut plane + clearance dimension.

Trim Off with interference:
- show actual untrimmed member and interference warning;
- do not silently hide interference.

## 19. Staleness
Trim On/Off and clearance are engineering-significant and stale current design / request a new preview under R6 identity rules.

A trim-plane display overlay is presentation-only.

## 20. Controlled benchmarks
Companion golden shall cover:
- T1 Trim disabled backward compatibility
- T2 25° Angle, 0 clearance
- T3 25° Angle, 0.25 in clearance
- T4 25° Angle, 0.50 in clearance
- T5 negative clearance rejection
- T6 actual bolt/hole distance to fabricated edge changes; legacy untrimmed scalar is not reused
- T7 same cut-plane engine on Channel or RHS

## 21. Visual acceptance
- V1 Off vs On at inclined brace
- V2 0 / 0.25 / 0.50 in exact gap
- V3 bolt-edge effect as trim increases
- V4 use R11 offsets to move bolts away and confirm edge clearance increases
- V5 repeat on Channel or RHS
- V6 unsupported resistance mapping fails closed rather than silently using old edge

## 22. Acceptance
R12 requires:
- explicit user On/Off;
- explicit user-entered clearance when On;
- backend-authoritative Tee reference plane and cut plane;
- actual profile-solid trimming;
- exact connector interference;
- exact hole/bolt geometry to fabricated edge;
- no silent use of untrimmed edge after trim;
- existing methods consume trim only where already authorized;
- legacy trim-off fingerprints remain exact;
- full QA + 4/4 CI + V1-V6.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
