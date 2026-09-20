# FRP Master Connection — Stage 3.2-R14B Region-Specific FRP Material-Basis Engineering Correction — Specification RC1

## 1. Status

**Controlled owner engineering correction specification — RC1**

The stopped R14 visualization audit and stopped R14A W-web correction audit proved that a broader backend-authoritative material-basis defect exists.

The common defect is architectural:

> one planar material orientation is being assigned to multiple perpendicular physical regions.

This causes `CW` to point through thickness and `TT` to lie in-plane for several regions.

R14B corrects the backend material-coordinate bases for the exact audited defective regions and preserves the audited-correct regions unchanged.

No material capacity, stiffness, resistance equation, demand equation, geometry, connection topology, or property equivalence is introduced.

R14B supersedes the stopped R14 and R14A execution orders. Both stopped before repository mutation.

---

## 2. Accepted starting baseline

Expected repository baseline remains:

- `HEAD == origin/main`: `c8604ed761fddc2fa66365bc44446f3fb0480f4b`
- subject: `feat: add tee length anchoring`
- commit count: `59`
- tracked files: `351`
- worktree/index: clean
- frontend source tree: `4809c59244f2bbf0e57bd334931f1b1f06368334`
- Stage 2.3 freeze tag: `stage-2.3-interface-geometry-freeze`
- freeze target: `5bc545ab8251f9bd49dedc776962937ed5e822a2`

No R14/R14A mutation, commit, push, or tag action occurred.

---

## 3. Common diagnosed source

The audit identified the common source in the Tee/application oriented-topology construction.

One material orientation is assigned to every region of a component topology.

That is valid only when all physical regions are coplanar.

For Angle, Channel, W/I, RHS, and Tee components, perpendicular regions require region-specific material orientations.

R14B shall replace the one-orientation-per-component assumption with exact region-specific orientation mapping.

Do not create duplicate profile geometry.

Do not repair this only in the frontend.

---

## 4. Material-axis semantics

For every pultruded FRP physical region:

- `LW` — longitudinal / pultrusion direction;
- `CW` — crosswise direction lying in the physical region plane;
- `TT` — through-thickness direction normal to the physical region plane.

Require:

```text
LW · CW = 0
LW · TT = 0
CW · TT = 0
LW × CW = TT
```

under the repository's controlling right-handed material-axis convention.

The sign of CW/TT comes from the authoritative region orientation, never the camera.

---

## 5. Controlled defective-region corrections

The following exact local bases are controlled by R14B.

### 5.1 W/I — WEB

Diagnosed current incorrect basis:

```text
LW = ( 0, 0, 1)
CW = ( 0,-1, 0)
TT = ( 1, 0, 0)
```

Physical web plane:

```text
span[(0,0,1), (1,0,0)]
```

Controlled thickness direction:

```text
(0,-1,0)
```

Corrected basis:

```text
LW = ( 0, 0, 1)
CW = (-1, 0, 0)
TT = ( 0,-1, 0)
```

### 5.2 Tee connector — STEM

Diagnosed current incorrect basis:

```text
LW = ( 0, 0, 1)
CW = ( 0, 1, 0)
TT = (-1, 0, 0)
```

Physical stem plane:

```text
span[(0,0,1), (-1,0,0)]
```

Controlled thickness direction:

```text
(0,1,0)
```

Corrected basis:

```text
LW = (0,0,1)
CW = (1,0,0)
TT = (0,1,0)
```

### 5.3 Angle — LEG_2

Diagnosed current incorrect basis:

```text
LW = (1, 0, 0)
CW = (0, 0,-1)
TT = (0, 1, 0)
```

Physical Leg 2 plane:

```text
span[(1,0,0), (0,1,0)]
```

Controlled thickness direction:

```text
(0,0,-1)
```

Corrected basis:

```text
LW = ( 1, 0, 0)
CW = ( 0,-1, 0)
TT = ( 0, 0,-1)
```

### 5.4 Channel — WEB

Diagnosed current incorrect basis:

```text
LW = (1,0,0)
CW = (0,1,0)
TT = (0,0,1)
```

Physical web plane:

```text
span[(1,0,0), (0,0,1)]
```

Controlled thickness direction:

```text
(0,1,0)
```

Corrected basis:

```text
LW = ( 1, 0, 0)
CW = ( 0, 0,-1)
TT = ( 0, 1, 0)
```

### 5.5 Rectangular hollow section — SIDE_WALL_1 / SIDE_WALL_2

Diagnosed current incorrect basis for the audited side-wall orientation:

```text
LW = ( 1, 0, 0)
CW = ( 0,-1, 0)
TT = ( 0, 0,-1)
```

Physical wall plane:

```text
span[(1,0,0), (0,0,-1)]
```

Controlled thickness direction:

```text
(0,-1,0)
```

Corrected basis:

```text
LW = (1,0,0)
CW = (0,0,1)
TT = (0,-1,0)
```

The existing audited region identities/sign convention for SIDE_WALL_1 and SIDE_WALL_2 shall be preserved.

---

## 6. Audited-correct regions — no basis change

The read-only audit found the plane/normal relationships correct for:

- Tee connector flange;
- W/I flanges;
- Angle Leg 1;
- Channel flanges;
- RHS top/bottom walls;
- Flat Plate.

R14B shall preserve their exact pre-correction backend material vectors.

Before mutation, capture the full exact baseline basis for every audited-correct region and commit regression assertions proving no change.

If one of these regions does not reproduce as correct:

**STOP before mutation and report the discrepancy.**

---

## 7. Region-specific topology mapping

Implement a single reusable region-specific orientation mechanism.

Preferred architecture:

```text
physical region ID
    ↓
exact region material orientation
    ↓
ConnectorComponent / topology region
```

Do not:

- create separate geometry models;
- duplicate complete component constructors per region;
- attach one orientation to every region merely for convenience;
- use frontend transforms as engineering authority.

The geometry topology remains unchanged.

---

## 8. Role/global transforms

Correct material bases are defined in the authoritative component/profile local frame first.

Existing component/member placement transforms then map them into global coordinates.

The corrected local basis shall remain semantically correct for:

- W support as Column;
- W support as Beam;
- connected W/I member where supported;
- Tee connector;
- Angle connected brace;
- Channel connected brace;
- RHS connected brace.

Role/orientation changes affect global vectors, not the local region material definition.

---

## 9. Numerical engineering consumer boundary

The completed R14A audit established that current numerical engineering uses the component `LW` axis in the existing geometry/directional-bearing mapping, while the defective `CW`/`TT` vectors are consumed by material identity/fingerprints and visualization.

R14B shall reconfirm all production consumers before mutation.

Expected numerical behavior:

- LW remains unchanged in all R14B corrected regions;
- accepted demand values remain unchanged;
- accepted resistance values remain unchanged;
- statuses/utilizations remain unchanged.

If correcting any controlled CW/TT basis changes any accepted numerical demand/resistance result or calculation applicability:

**STOP before commit.**

A separate controlled numerical correction is required.

---

## 10. No material-property change

R14B does not authorize:

- CW/TT strength equivalence;
- new transverse property;
- new through-thickness property;
- property substitution;
- interlaminar-property changes;
- pull-through changes;
- bearing-strength changes;
- stiffness changes.

Only coordinate orientation is corrected.

---

## 11. Geometry invariance

R14B shall not change:

- component solids;
- member profiles;
- support geometry;
- Tee geometry;
- bolt coordinates;
- bolt axes;
- bolt-group positions;
- finite clearances;
- trim geometry;
- Tee anchoring;
- contact surfaces;
- interface frames.

For controlled regression fixtures, authoritative geometry fingerprints that exclude material identity shall remain exact.

---

## 12. Fingerprint transition authority

Correcting engineering material axes changes legitimate material/provenance identities.

R14B authorizes fingerprint transitions only where canonical payload comparison proves the transition is caused solely by one or more of:

- W/I WEB corrected CW/TT;
- Tee STEM corrected CW/TT;
- Angle LEG_2 corrected CW/TT;
- Channel WEB corrected CW/TT;
- RHS SIDE_WALL_1/2 corrected CW/TT;
- immediate parent material/component/assembly identities derived from those regions.

For every changed fingerprint:

1. recover exact 64-character pre-R14B value from parent baseline;
2. compute exact post-R14B value;
3. diff canonical payloads;
4. identify the corrected region(s) responsible;
5. prove no geometry input changed;
6. prove no numerical engineering output changed;
7. commit exact automated before/after assertions.

No unrelated transition is authorized.

---

## 13. Historical controlled artifacts

Earlier owner-controlled artifacts remain byte-exact.

Do not rewrite R4-R13 artifacts to replace historical hashes.

R14B adds new transition provenance/tests for the corrected current engineering basis.

Historical fingerprints remain valid evidence of historical commits.

---

## 14. Cross-platform determinism

All controlled corrected bases use exact axis-aligned coordinate values.

Their canonical serialization shall be identical on Ubuntu and Windows.

Reuse the R5 deterministic fingerprint/serialization path.

No OS branch.

---

## 15. Frontend visualization

The frontend shall continue to render the backend-authoritative basis without semantic swapping.

For each corrected region:

- LW/CW must lie in the physical region plane;
- TT must be through thickness;
- labels must match backend fields.

Do not recompute material axes from scene mesh normals.

Do not special-case a visual CW/TT swap.

---

## 16. Material-region labeling

Improve the Material-direction inspector/legend so the user can identify the physical owner region.

At minimum support labels equivalent to:

- Supporting W — Web
- Supporting W — Positive flange
- Supporting W — Negative flange
- Tee — Stem
- Tee — Flange
- Brace — Leg 1
- Brace — Leg 2
- Channel — Web
- Channel — Positive flange
- Channel — Negative flange
- RHS — Side wall / Top wall / Bottom wall as applicable

Use repository region naming where more precise.

Selection/focus is presentation-only.

---

## 17. Controlled golden benchmarks

The companion R14B golden controls:

- pre-correction audited defective bases;
- corrected bases;
- physical planes;
- thickness directions;
- orthogonality;
- handedness;
- unchanged-region identities.

It contains no material capacity.

---

## 18. Required backend tests

At minimum:

1. reproduce all five defective pre-correction basis classes from parent provenance;
2. W/I web corrected exact;
3. Tee stem corrected exact;
4. Angle Leg 2 corrected exact;
5. Channel web corrected exact;
6. RHS side walls corrected exact;
7. all corrected `LW × CW = TT`;
8. all corrected LW/CW lie in physical plane;
9. all corrected TT equals controlled thickness direction;
10. audited-correct Tee flange unchanged;
11. W flanges unchanged;
12. Angle Leg 1 unchanged;
13. Channel flanges unchanged;
14. RHS top/bottom unchanged;
15. Flat Plate unchanged;
16. Column/Beam role transforms preserve local semantics;
17. all numerical engineering outputs unchanged;
18. all geometry unchanged;
19. exact authorized fingerprint transitions;
20. no unauthorized transition;
21. all Stage 2 / Stage 3.2 / R4-R13 regressions.

---

## 19. Required frontend tests

At minimum:

1. W web mapping correct;
2. Tee stem mapping correct;
3. Angle Leg 2 mapping correct;
4. Channel web mapping correct;
5. RHS side-wall mapping correct;
6. correct regions remain correct;
7. backend labels retained;
8. no frontend CW/TT swap;
9. local XYZ/member axes remain distinct from LW/CW/TT;
10. X-ray/Solid/view controls unchanged;
11. material-axis overlay/focus non-staling;
12. direct/reference visualization regression;
13. region labels unambiguous.

---

## 20. Visual acceptance

After full QA and 4/4 hosted CI:

### V1-R14B — W/I
Check W web and flange independently.

### V2-R14B — Tee
Check stem and flange independently.

### V3-R14B — Angle
Check Leg 1 and Leg 2 independently.

### V4-R14B — Channel
Check web and flange independently.

### V5-R14B — RHS
Check side wall and top/bottom wall independently.

### V6-R14B — Role transform
Switch W support Column ↔ Beam and verify local material semantics remain correct.

### V7-R14B — Labels
Verify each triad is clearly associated with its physical material region.

---

## 21. Acceptance boundary

R14B is accepted only if:

- all audited defective backend bases are corrected;
- all audited-correct bases remain unchanged;
- no material property/capacity is changed;
- no accepted numerical engineering result changes;
- physical geometry remains unchanged;
- only basis-derived fingerprints transition;
- every transition is exact and automated;
- frontend faithfully displays the corrected backend basis;
- full QA and 4/4 hosted CI pass;
- V1-R14B through V7-R14B pass.

**END OF CONTROLLED ENGINEERING CORRECTION SPECIFICATION — RC1**
