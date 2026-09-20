# FRP Master Connection — Stage 3.6A FRP W/I Beam-to-Beam Symmetric Double Web Splice Plates — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.6A starts the beam-splice shear-connection family.

It implements a concentric symmetric double web-splice-plate connection between two identical collinear FRP W/I beams.

The product accepts:

- signed axial force;
- signed major shear;
- signed minor shear;
- zero user-applied moment.

No flange splice is included.

No single-sided splice plate is included.

No new demand or resistance equation is introduced.

## 2. Accepted starting baseline

Expected repository state after the Stage 3.5 freeze:

- branch: `main`;
- `HEAD == origin/main == remote main`:
  `7bb83e5c8814781419c0789b7428bd46572d514c`;
- subject:
  `chore: freeze Stage 3.5 concrete-support shear family baseline`;
- commit count: `89`;
- clean worktree/index.

Stage 3.5 freeze hosted CI is accepted 4/4 green:

- GitHub Actions run #84;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS;
- duration approximately `5m 26s`.

Expected immutable freeze targets:

- Stage 2.3:
  `5bc545ab8251f9bd49dedc776962937ed5e822a2`;
- Stage 3.2:
  `d16b354732c90bf3bf7847c62be652c230a9f91e`;
- Stage 3.3:
  `a4d21506d45d2d21d3f5039b662ea56ec6c5da9f`;
- Stage 3.4:
  `2303ec713d6d038b935e076b909c3b639ced0e09`;
- Stage 3.5:
  `7bb83e5c8814781419c0789b7428bd46572d514c`.

Expected Stage 3.5 production source identities remain:

- backend/src:
  `e493b512d59e6218b61a2dc43bf0aed8c00cce16`;
- frontend/src:
  `bf2f82d8d5f2b274feab64c674a75270eca3d497`.

## 3. Source basis

ASCE/SEI 74-23 Chapter 8 applies to bearing-type bolted connections for pultruded FRP shapes and plates and recognizes splice plates as connection elements.

Section 8.3.4.2 requires splice connections to transfer applicable forces and account for eccentricity of bolt-group centroids.

For flexural-member parts subjected to shear, the shear at the splice and eccentricity effects are included in the required action.

Stage 3.6A retains those exact eccentricity effects.

However, RC1 is intentionally shear-category and accepts zero user-applied bending moment only.

Required limitation:

`WEB_SPLICE_MEMBER_FLEXURAL_MOMENT_TRANSFER = NOT_AUTHORIZED_IN_RC1`.

The product is appropriate only where the structural-analysis demand supplied to this slice has zero required member-end flexural moment.

## 4. Product identity

New selector group remains:

`Beam connections`.

Add:

`Beam connection — Symmetric double web splice plates`.

Suggested API routes:

- `/api/v1/calculations/beam-web-splice/preview`;
- `/api/v1/calculations/beam-web-splice/design-check`.

Contract:

`3.6A-RC1`.

Existing selector options remain unchanged.

## 5. Splice frame

Define right-handed:

- `L_S`: Beam A -> Beam B longitudinal axis;
- `V_S`: vertical in web plane;
- `T_S`: web through-thickness normal.

Require:

`L_S × V_S = T_S`.

Joint reference:

`r_J = (0,0,0)`.

Joint plane:

`L_S = 0`.

## 6. Beam identities

Exactly two physical beams:

- `BEAM_A`;
- `BEAM_B`.

Beam A occupies negative `L_S`.

Beam B occupies positive `L_S`.

Both are W/I profiles and are locked identical in RC1.

No unequal section dimensions/materials.

## 7. W/I beam default

Each beam:

- depth: `10 in`;
- flange width: `8 in`;
- web thickness: `0.5 in`;
- flange thickness: `0.5 in`;
- displayed length away from joint: `18 in`.

Profile LW:

`L_S`.

Web CW:

`V_S`.

Web TT:

`T_S`.

Flange region bases remain backend-authored under the accepted material-axis architecture.

## 8. Beam-end gap

Input:

`beam_end_gap`.

Require:

`beam_end_gap > 0`.

Default:

`0.5 in`.

Beam A end:

`L_S = -0.25 in`.

Beam B end:

`L_S = +0.25 in`.

The gap prevents direct end-bearing transfer in RC1.

Axial compression is therefore transferred through the splice-plate system.

No beam-end bearing partition.

## 9. Splice-plate pair

Exactly:

- `POSITIVE_WEB_SPLICE_PLATE`;
- `NEGATIVE_WEB_SPLICE_PLATE`.

Identical/mirrored.

Default each:

- length `16 in` along `L_S`;
- height `8 in` along `V_S`;
- thickness `0.5 in` along `T_S`.

Plates are centered on the joint plane and web mid-depth.

## 10. Splice-plate material basis

Each FRP splice plate:

- `LW || L_S`;
- `CW || V_S`;
- `TT || ±T_S`.

Therefore:

- axial transfer is LW-direction;
- major shear is CW-direction;
- minor shear is TT/through-thickness action.

This basis is backend authoritative.

## 11. Plate placement

Positive plate lies outside the `+T_S` web face.

Negative plate lies outside the `-T_S` web face.

Plate inner faces contact the applicable Beam A and Beam B web outer faces.

The plates bridge the positive beam-end gap.

Reject:

- plate/web positive-volume overlap inconsistent with face contact;
- flange/plate interference;
- plate outside clear web region;
- plate pair asymmetry.

## 12. Physical interface groups

Exactly two:

- `BEAM_A_WEB_SPLICE_GROUP`;
- `BEAM_B_WEB_SPLICE_GROUP`.

They are independent physical bolt groups but are locked mirrored about the joint plane in RC1.

## 13. Bolt path

Every bolt in either group passes:

`Positive Web Splice Plate -> Beam Web -> Negative Web Splice Plate`.

One physical shank per bolt axis.

Head/washer and nut/washer outside the two splice plates.

No internal hardware.

No duplicate bolt identity.

## 14. Default bolt groups

Each group default:

- rows along `V_S`: `2`;
- bolts per row along `L_S`: `2`;
- vertical pitch: `3 in`;
- longitudinal gauge: `3 in`;
- group centroid vertical coordinate: `0`;
- Beam A group centroid:
  `L_S=-4 in`;
- Beam B group centroid:
  `L_S=+4 in`;
- bolt diameter: `0.5 in`;
- hole diameter: `0.563 in`.

Default Beam A bolt coordinates:

- `L=-5.5`, `V=-1.5`;
- `L=-2.5`, `V=-1.5`;
- `L=-5.5`, `V=+1.5`;
- `L=-2.5`, `V=+1.5`.

Default Beam B is the exact mirror:

- `L=+2.5`, `V=-1.5`;
- `L=+5.5`, `V=-1.5`;
- `L=+2.5`, `V=+1.5`;
- `L=+5.5`, `V=+1.5`.

All `T=0` centerlines before layer offsets.

## 15. Complete-hole containment

Validate every bolt hole independently in:

- beam web;
- positive splice plate;
- negative splice plate.

Also validate:

- web clear-depth/flange-junction exclusions;
- plate free edges;
- plate outer longitudinal ends;
- plate joint-side ligament;
- minimum spacing under accepted geometry requirements.

No automatic group repositioning.

## 16. Transfer-force inputs

Normal user inputs:

### Axial force

`P_L`, signed.

- positive = tension across splice;
- negative = compression across splice.

### Major shear

`V_V`, signed along `V_S`.

### Minor shear

`V_T`, signed along `T_S`.

No user-applied moment.

Canonical transfer vector:

`F_tr = (P_L,V_V,V_T)`.

## 17. Default action

Default:

- axial force `0 kip`;
- major shear `-10 kip`;
- minor shear `0 kip`;
- user moment `(0,0,0)`.

## 18. User moment

No moment fields.

Any nonzero user free moment is rejected.

This does not suppress generated eccentricity moments.

## 19. Interface-action convention

At the common joint reference:

`r_J=(0,0,0)`.

Beam A interface force:

`F_A = F_tr`.

Beam B interface force:

`F_B = -F_tr`.

This equal/opposite convention represents the action transferred through the splice system.

## 20. Group references

Default:

- `r_A=(-4,0,0) in`;
- `r_B=(+4,0,0) in`.

Exact translated group moments:

`M_A = (r_J-r_A) × F_A`.

`M_B = (r_J-r_B) × F_B`.

User free moment remains zero.

## 21. Default major-shear group wrenches

For:

- `P_L=0`;
- `V_V=-10`;
- `V_T=0`;

Beam A:

- `F_A=(0,-10,0) kip`;
- `M_A=(0,0,-40) kip-in`.

Beam B:

- `F_B=(0,+10,0) kip`;
- `M_B=(0,0,-40) kip-in`.

Each local group wrench, shifted back to `r_J` with its own force, recovers zero user-applied joint moment.

The two interface forces are equal/opposite.

## 22. Pure axial tension

For:

`P_L=+10 kip`

and zero shears:

Beam A:

- `F_A=(10,0,0)`;
- `M_A=0`.

Beam B:

- `F_B=(-10,0,0)`;
- `M_B=0`.

Axial force is LW-direction in both beam webs and both splice plates, with signed direction handled per local interface.

## 23. Pure axial compression

For:

`P_L=-10 kip`

and positive beam gap:

Beam A:

- `F_A=(-10,0,0)`;
- Beam B:
  `F_B=(+10,0,0)`.

No direct beam-end bearing is used.

Compression transfers through the splice-plate system.

## 24. Combined axial + major shear

For:

- `P_L=+5`;
- `V_V=-10`;
- `V_T=0`;

Beam A:

- `F_A=(5,-10,0)`;
- `M_A=(0,0,-40)`.

Beam B:

- `F_B=(-5,+10,0)`;
- `M_B=(0,0,-40)`.

Use actual resultant directions for local bearing classification.

## 25. Minor shear

`V_T` lies along the bolt axes / FRP TT direction.

Retain the exact normal action.

Do not generate:

- bolt-axis tension capacity;
- pull-through capacity;
- prying capacity.

Required when `V_T != 0`:

`WEB_SPLICE_MINOR_SHEAR_BOLT_AXIS_RESPONSE = NOT_EVALUATED`.

Local in-plane checks may still execute for the in-plane sub-action where their existing applicability permits.

## 26. Physical-group demand

For each physical group call the accepted Stage 2.5A engine exactly once for the actual in-plane interface action.

The group reference, force sign, coordinates, and generated eccentricity moment are group-specific.

No new demand equation.

## 27. Beam-web layer demand

At each interface, the beam web layer receives:

`1.0` of the physical per-bolt in-plane group demand.

The local web layer is checked independently on Beam A and Beam B using the actual signed force direction and loaded-edge geometry.

## 28. Splice-plate pair system demand

At each interface the splice-plate pair system receives:

`1.0` of that interface action.

Under exact pair symmetry each physical splice plate layer receives:

`0.5` of the per-bolt demand vector.

Do not assign 100% independently to both plates.

## 29. Plate-pair symmetry

Exact 50/50 plate-layer allocation requires:

- identical plate geometry;
- mirrored placement;
- identical material/source;
- common bolt path through both plates/web;
- centered web plane.

No tolerance.

If symmetry is broken:

`WEB_SPLICE_PLATE_PAIR_LOAD_ALLOCATION = NOT_EVALUATED`.

RC1 normal UI keeps the pair locked symmetric.

## 30. Material-direction classification

For each local layer use that region's own material basis.

### Axial

Parallel to LW in:

- Beam A web;
- Beam B web;
- positive splice plate;
- negative splice plate.

### Major shear

Parallel to CW in those same web/plate regions.

### Combined axial + major shear

Use actual resultant angle to each region LW.

Do not reuse one layer's bearing angle blindly for all layers.

## 31. Existing local resistance handoff

Reuse only already accepted local checks where applicable, including:

- FRP pin bearing;
- supported net tension;
- supported shear-out;
- supported block shear;
- applicable metallic/local bolt checks already authorized.

No new equation.

## 32. Loaded-edge / reverse-direction handling

Beam A and Beam B interface forces are opposite.

Therefore loaded/unloaded edges and bypass paths may differ.

The backend shall derive local failure-path applicability from each interface's actual signed action and physical geometry.

Do not evaluate Beam B by copying Beam A status with a sign stripped.

If an existing method cannot map the reversed path:

return `NOT_EVALUATED`.

## 33. Splice-plate inter-group body limitation

The two physical splice plates transfer load between the Beam A and Beam B bolt groups across the central plate segment.

Stage 3.6A does not introduce a complete plate-body/member design method for that inter-group transfer.

Always:

`WEB_SPLICE_PLATE_INTERGROUP_BODY_TRANSFER = NOT_EVALUATED`.

Do not fabricate a plate-body capacity from local bolt-hole resistance.

## 34. Common-bolt double-shear limitation

Each bolt passes Plate/Web/Plate and is a physical double-shear configuration.

Stage 3.6A does not introduce a new metallic common-bolt double-shear resistance authority.

Required:

`WEB_SPLICE_COMMON_BOLT_DOUBLE_SHEAR = NOT_EVALUATED`.

Do not multiply an existing single-shear bolt capacity by two without separate authority.

## 35. Member flexural-moment limitation

Always:

`WEB_SPLICE_MEMBER_FLEXURAL_MOMENT_TRANSFER = NOT_AUTHORIZED_IN_RC1`.

No user-applied moment.

The generated moments due to bolt-group centroid eccentricity remain mandatory and are not covered by this prohibition.

## 36. Status aggregation

Required precedence:

1. invalid input/geometry -> invalid/rejected;
2. supported local numerical failure -> `FAIL`;
3. otherwise required splice-plate body / double-shear / minor-shear / moment limitations -> `NOT_EVALUATED`;
4. ordinary whole-splice `PASS` prohibited.

## 37. Component transfer trace

Expose backend-authored cards/traces for:

### Beam A interface

- group reference;
- signed interface force;
- generated eccentricity moment;
- beam-web demand = 100%;
- splice-plate-pair demand = 100%;
- each splice plate = 50% after symmetry.

### Beam B interface

Same structure with actual opposite interface force.

### Joint transfer

- canonical `F_tr`;
- zero user moment;
- interface equilibrium evidence.

Do not sum equal/opposite interface actions into a fake doubled splice transfer.

## 38. Plate body trace

Display:

`Splice plate pair inter-group transfer — NOT_EVALUATED`

while retaining the actual system force being transferred.

## 39. Preview path

Preview shall:

- validate strict inputs;
- construct beams/gap/plates;
- resolve both bolt groups;
- validate containment/interference;
- resolve exact interface wrenches;
- compute supported in-plane group demand;
- classify material directions;
- retain minor-shear normal action;
- prove plate-pair symmetry;
- build component transfer trace;
- return visualization/status.

Preview resistance-engine calls:

`0`.

## 40. Explicit design path

`Run Design Check`:

- current accepted preview;
- execute existing supported local beam-web/splice-plate checks;
- no plate inter-group body capacity;
- no common-bolt double-shear capacity;
- no minor-shear bolt-axis/pull-through/prying capacity;
- no user-moment transfer;
- limitations retained.

## 41. API strictness

Contract:

`3.6A-RC1`.

Strictly accept:

- identical W/I dimensions/material/source;
- beam display lengths;
- positive beam-end gap;
- symmetric splice-plate geometry;
- mirrored group positions/pattern;
- bolt/hole geometry;
- signed axial/major/minor forces;
- zero user moment.

Reject:

- zero/negative beam gap;
- unequal beams;
- unequal splice plates;
- single plate;
- non-W/I profile;
- flange splice fields;
- nonzero user moments;
- extra fields;
- client IDs/fingerprints;
- unsupported versions.

## 42. Frontend workspace

Under `Beam connections` add:

`Beam connection — Symmetric double web splice plates`.

Normal sections:

1. General / Case;
2. Beam Sections;
3. Beam-End Joint;
4. Web Splice Plates;
5. Beam A Web ↔ Plates;
6. Beam B Web ↔ Plates;
7. Fasteners;
8. Loads;
9. Component Transfer Trace;
10. Materials;
11. Geometry / Design Results;
12. Advanced / Diagnostics.

Use the shared persistent viewer.

## 43. Beam UI

One W/I dimension editor controls both identical beams.

Display explicitly:

`Beams locked identical in Stage 3.6A`.

Expose:

- depth;
- flange width;
- web thickness;
- flange thickness;
- display length;
- beam-end gap.

No independent Beam B dimensions in RC1.

## 44. Plate UI

Expose:

- plate length;
- plate height;
- plate thickness.

Display:

`Two locked identical mirrored FRP splice plates`.

No Single plate option.

## 45. Bolt-group UI

Expose one mirrored pattern editor:

- rows;
- bolts per row;
- vertical pitch;
- longitudinal gauge;
- group centroid distance from joint.

The second group is exact mirror.

Do not allow independent left/right patterns in RC1.

## 46. Load UI

Expose:

- Axial force `(+ tension / - compression)`;
- Major shear;
- Minor shear.

No moment fields.

Show splice-frame sign directions.

## 47. Visualization

Render actual:

- Beam A W/I;
- Beam B W/I;
- visible positive end gap;
- positive splice plate;
- negative splice plate;
- Beam A group hardware;
- Beam B group hardware;
- joint reference;
- group references;
- signed action arrows;
- splice frame;
- FRP material axes.

No flange splice component.

## 48. Material-axis visualization

With axes enabled show:

### Beam A / B

- web;
- top flange;
- bottom flange.

### Positive / negative splice plates

- LW along beam/splice length;
- CW vertical;
- TT normal to plate.

No frontend material-basis inference.

## 49. Controlled default fixture

### Beams

- W/I `10 × 8 in`;
- web `0.5 in`;
- flanges `0.5 in`;
- display length each side `18 in`.

### Joint

- gap `0.5 in`.

### Plates

Each:

- `16 × 8 × 0.5 in`.

### Groups

Each:

- `2 × 2`;
- vertical pitch `3 in`;
- longitudinal gauge `3 in`;
- centroids `L=±4 in`;
- bolt `0.5 in`;
- hole `0.563 in`.

### Loads

- axial `0`;
- major shear `-10 kip`;
- minor shear `0`;
- user moment `0`.

## 50. Required controlled golden cases

At minimum:

G1. Default Beam A/Beam B geometry.
G2. Positive 0.5-in beam-end gap.
G3. Positive/negative splice-plate exact mirror.
G4. Beam A/Beam B bolt groups exact mirror.
G5. Default Beam A group wrench `(0,-10,0); (0,0,-40)`.
G6. Default Beam B group wrench `(0,+10,0); (0,0,-40)`.
G7. Each default group shifted to joint has zero user moment.
G8. Plate-pair interface forces equal/opposite across joint.
G9. Pure axial tension group forces ±10 and zero group moments.
G10. Pure axial compression uses plates; no direct end bearing.
G11. Combined axial+major group wrenches.
G12. Minor shear retained as bolt-axis action.
G13. Minor shear response NOT_EVALUATED.
G14. Beam A web layer demand fraction 1.0.
G15. Beam B web layer demand fraction 1.0.
G16. Positive splice plate layer fraction 0.5.
G17. Negative splice plate layer fraction 0.5.
G18. Plate pair system fraction 1.0.
G19. Axial direction = LW for beam webs and plates.
G20. Major shear direction = CW for beam webs and plates.
G21. Combined direction uses actual vector/material basis.
G22. Beam A reverse/loaded-edge applicability derived independently.
G23. Beam B reverse/loaded-edge applicability derived independently.
G24. Splice-plate inter-group body transfer NOT_EVALUATED.
G25. Common bolt double shear NOT_EVALUATED.
G26. Member flexural moment transfer NOT_AUTHORIZED.
G27. User moment rejected.
G28. Zero/negative beam gap rejected.
G29. Unequal beams rejected.
G30. Single splice plate request rejected.
G31. Flange splice request rejected.
G32. Web hole containment invalid case.
G33. Plate hole/free-edge containment invalid case.
G34. Plate/flange interference invalid case.
G35. No duplicate bolt/hardware identities.
G36. Material-axis coverage beam webs/flanges/plates.
G37. Preview zero resistance.
G38. Supported local numerical failure governs FAIL.
G39. Valid geometry with body/double-shear limitations -> NOT_EVALUATED.
G40. Exact U.S./SI default equivalence.
G41. Deterministic fingerprints.
G42. Stage 3.5 frozen family regression exact.
G43. Stage 2.3/3.2/3.3/3.4 frozen regressions exact.

## 51. U.S./SI equivalence

At minimum:

- `18 in = 457.2 mm`;
- `16 in = 406.4 mm`;
- `10 in = 254 mm`;
- `8 in = 203.2 mm`;
- `4 in = 101.6 mm`;
- `3 in = 76.2 mm`;
- `1.5 in = 38.1 mm`;
- `0.563 in = 14.3002 mm`;
- `0.5 in = 12.7 mm`;
- `10 kip = 44.482216152605 kN`;
- `40 kip-in = 4.519393161104668 kN-m`.

Equivalent geometry, group references, signed actions, generated moments, demand provenance, material classifications, results, and fingerprints shall match.

## 52. Fingerprints

Create deterministic identities for:

- input;
- splice frame;
- Beam A/B geometry;
- beam gap;
- splice-plate pair;
- Beam A group;
- Beam B group;
- transfer action;
- group references/wrenches;
- plate-pair symmetry;
- per-layer provenance;
- application/preview/design.

Presentation excluded.

Frozen Stage 3.5 and earlier fingerprints remain exact.

## 53. Deliberate exclusions

Stage 3.6A does not authorize:

- single web splice plate;
- flange splice;
- unequal beams;
- beam moment transfer;
- member flexural splice design;
- splice-plate inter-group body capacity;
- common-bolt double-shear capacity;
- minor-shear bolt tension/pull-through/prying;
- slip-critical connection;
- adhesives/welds;
- non-W/I beam profiles.

## 54. Acceptance boundary

Stage 3.6A is accepted only if:

- two collinear identical W/I beams are physically correct;
- beam gap is real and positive;
- two FRP web splice plates bridge the joint;
- two independent mirrored physical bolt groups are correct;
- eccentricity moments from group offsets are retained exactly;
- beam webs receive 100% interface local demand;
- plate pair receives 100% system interface demand;
- each plate receives 50% only after exact symmetry;
- axial is LW and major shear CW in actual web/plate bases;
- reversed Beam B action is independently classified;
- no user moment/flange splice/single plate is silently accepted;
- plate body and double-shear limitations remain explicit;
- Stage 3.5 and all earlier freezes remain exact;
- local/object-isolated QA passes;
- hosted four-job CI passes;
- owner visual acceptance passes.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
