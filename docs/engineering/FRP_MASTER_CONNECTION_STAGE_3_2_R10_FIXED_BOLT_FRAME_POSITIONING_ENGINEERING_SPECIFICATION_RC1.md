# FRP Master Connection — Stage 3.2-R10 Tee-Fixed Bolt Layout Frame + Bolt-Group Positioning — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.2-R10 corrects the brace-inclination geometry introduced in R9 and adds explicit, independent in-plane positioning for each Tee bolt group.

The controlling user intent is:

- brace inclination rotates the connected brace member;
- the `Brace ↔ Tee Stem` bolt grid remains fixed in the Tee-stem/support frame rather than rotating with the brace;
- bolt shanks remain normal to the Tee stem;
- the user can move each bolt group up/down and forward/back within its own interface plane;
- through-thickness bolt position remains backend-derived from the selected surfaces and penetrated layer stack;
- exact finite-hole clearances and placement limits are shown rather than discovered by trial and error.

R10 also separates **physical geometry validity** from **calculation-method applicability**. A valid fixed bolt grid shall not be rotated merely to make a current prescribed distribution method applicable.

No new demand equation, resistance equation, connector-body resistance, member-body resistance, or fastener-strength model is authorized.

---

## 2. Accepted starting baseline

Expected repository baseline after Stage 3.2-R9:

- `HEAD == origin/main`:
  `cc336f6a7161200656f1f4689c8b72585e6627d1`
- subject:
  `feat: complete tee connection controls and hardware`
- commit count: `54`
- tracked files: `336`
- worktree/index: clean
- frontend source tree:
  `9dec6be5d41dc24894bb3f08bd1652c23b431bbb`
- immutable Stage 2.3 freeze tag:
  `stage-2.3-interface-geometry-freeze`
- freeze target:
  `5bc545ab8251f9bd49dedc776962937ed5e822a2`

Stage 3.2-R9 hosted CI is accepted 4/4 green with 263/263 frontend tests across 20 files on Ubuntu and Windows.

---

## 3. Visual-review findings controlling R10

The R9 visual review established:

1. A valid Angle Tee preview can use:
   - Angle `6 x 6 x 0.5 in`;
   - `2 x 1` Brace ↔ Tee Stem group;
   - independently retained `2 x 2` Tee Flange ↔ Support group.
2. `1.0 in` unloaded-end distance is invalid for the controlled Angle fixture, while `1.2815 in` is the exact valid boundary and `1.3 in` is valid.
3. R9 rotates the Brace ↔ Tee Stem bolt layout together with the brace when brace inclination changes.
4. The intended detailing keeps the bolt rows/grid vertical and fixed relative to the Tee stem while the brace member itself inclines.
5. The UI lacks intuitive explicit controls for rigidly translating a bolt group up/down and forward/back.
6. R9 solid shank/head/nut presentation shall remain intact.

These are engineering/product requirements.

---

# PART A — DECOUPLED BRACE AND BOLT-GROUP FRAMES

## 4. Separate physical frames

R10 shall distinguish:

### 4.1 Brace member placement frame

Controls the connected brace member axis, selected profile surface, and profile roll.

This frame changes with:

- brace inclination;
- profile roll;
- selected profile surface;
- member/profile dimensions.

### 4.2 Interface A bolt-layout frame

Controls the `Brace ↔ Tee Stem` bolt-grid orientation and in-plane position.

This frame is fixed to the Tee stem/support template and does **not** rotate with brace inclination.

### 4.3 Interface B bolt-layout frame

Controls the `Tee Flange ↔ Support` bolt group.

It remains fixed to the Tee flange/support interface as already accepted.

The three concepts are distinct engineering objects.

## 5. Tee-stem fixed frame

Define one exact right-handed Interface A placement frame:

- `V_A` — canonical vertical/up direction in the Tee-stem plane;
- `H_A` — canonical horizontal direction in the Tee-stem plane;
- `N_A` — bolt-axis direction normal to the Tee stem.

Require:

- `V_A · H_A = 0`
- `V_A · N_A = 0`
- `H_A · N_A = 0`
- unit magnitudes;
- repository-consistent handedness.

`V_A`, `H_A`, and `N_A` are derived from the existing Tee/support template and selected physical interface, not camera orientation.

At all brace inclinations:

- Interface A row/grid orientation remains expressed in the same `V_A/H_A` frame;
- bolt axes remain parallel to `N_A`;
- global Interface A bolt coordinates remain unchanged when only brace inclination changes, provided the same placement/layout values are used and geometry remains valid.

## 6. Brace inclination placement

Preserve R9's exact arbitrary numeric `brace_inclination_degrees` and deterministic R5 trigonometric authority.

Let:

- `L0` — existing 0° brace longitudinal direction;
- `U0` — canonical in-plane brace-up direction;
- `P_brace` — the existing backend brace-placement/contact anchor, independent of bolt-group centroid.

For inclination `θ`:

`Lθ = cos(θ) L0 + sin(θ) U0`

The connected brace profile and selected connection-surface transform rotate about `P_brace` using the existing placement-plane normal.

Do not pivot the brace around the bolt-group centroid.

Do not rotate Interface A's `V_A/H_A/N_A` frame with the brace.

## 7. Contact and penetration after inclination

At each inclination:

- the selected brace connection surface remains the intended Interface A member surface;
- the Tee-stem selected surface remains fixed;
- each fixed bolt axis/ray is intersected against the newly inclined brace profile;
- finite-hole containment and exact opposing-face/wall-path rules from R7/R8 remain authoritative;
- some inclinations/layout positions may become invalid because the fixed bolt group no longer lies completely within the inclined brace surface.

Invalid cases shall use the accepted R6 current-invalid / last-valid-preview behavior.

Do not automatically move or rotate bolts to make the inclined brace fit.

## 8. Profile roll remains separate

`Profile roll about member axis` continues to rotate the profile cross-section about `Lθ`.

It shall not alter:

- requested brace inclination;
- Interface A grid orientation;
- Interface B geometry.

Changing roll can legitimately alter whether fixed Interface A bolt paths intersect the selected profile surface and remain finite.

---

# PART B — EXPLICIT BOLT-GROUP POSITIONING

## 9. Placement modes

Introduce a backward-compatible placement-mode identity for each Tee interface.

At minimum:

### `EDGE_DISTANCE_CONTROLLED`

Legacy/current Stage 3.2 placement semantics.

Existing request fields and fingerprints remain valid.

An omitted placement mode in a legacy request shall mean `EDGE_DISTANCE_CONTROLLED`.

### `GROUP_OFFSET_CONTROLLED`

New explicit rigid-group positioning mode.

The group pattern is defined by:

- rows;
- bolts per row;
- pitch;
- gauge;

and positioned by two exact in-plane offsets in the applicable interface frame.

No through-thickness offset is user-controlled.

## 10. Interface A positioning datum

Define one stable backend Interface A placement datum `D_A` on the Tee-stem plane.

It shall be derived from the existing authoritative Tee/interface geometry and must not depend on:

- camera;
- current bolt count;
- brace inclination;
- selected bolt;
- last preview state.

The datum shall be exposed in trace/inspector terms sufficiently to make the offset convention reproducible.

In `GROUP_OFFSET_CONTROLLED`, the geometric center of the bolt-group center-coordinate envelope is positioned at:

`C_A = D_A + v_A V_A + h_A H_A`

where:

- `v_A` = vertical offset;
- `h_A` = horizontal offset.

User-facing labels:

- `Vertical offset (+ up / − down)`
- `Horizontal offset (+ forward / − back)`

The UI shall show the positive axes in the viewer/inspector so "forward" is not inferred from camera orientation.

## 11. Interface B positioning datum

Define the same concept independently for Interface B:

`C_B = D_B + v_B V_B + h_B H_B`

using the Tee-flange/support interface frame.

Interface A offsets shall not change Interface B coordinates.

Interface B offsets shall not change Interface A coordinates.

## 12. Pattern coordinates about group center

In `GROUP_OFFSET_CONTROLLED`, the rectangular bolt pattern shall be centered about `C_A` or `C_B`.

For rows `Nr`, bolts per row `Nb`, pitch `p`, and gauge `g`, use symmetric exact Decimal index coordinates around the group center.

Repository row/line identities and ordering remain controlled by existing rules.

The new centered placement shall not rename Row 1 or alter accepted row-order meaning.

If even/odd counts place the geometric center between rows/lines, retain exact half-spacing Decimal coordinates.

No binary float authority.

## 13. Through-thickness placement

The user shall not control movement toward/away from the Tee through thickness.

Through-thickness bolt path remains determined by:

- selected interface surfaces;
- bolt axis;
- entry/exit layers;
- physical stack start/end;
- accepted head/nut side conventions.

No `normal offset` control is authorized.

## 14. Legacy edge-distance mode

`EDGE_DISTANCE_CONTROLLED` preserves all current geometry and fingerprints, including the controlled valid Angle fixture using `1.2815 in`.

R10 shall not reinterpret legacy fields.

The UI may present a `Position by` selector:

- `Group offsets`
- `Edge distances (legacy/advanced)`

When switching modes, the frontend/backend may compute the equivalent current representation, but only one mode is authoritative at a time.

A mode switch shall not silently change physical geometry when an exact equivalent representation exists.

## 15. New-session behavior

For a new Tee connection, the product may default to `GROUP_OFFSET_CONTROLLED` only if its initial offsets reproduce the current accepted default physical geometry exactly.

Loaded U.S./SI benchmark fixtures may continue using `EDGE_DISTANCE_CONTROLLED` to preserve controlled benchmark identity.

Legacy serialized requests remain legacy mode.

---

# PART C — CLEARANCES AND VALIDATION FEEDBACK

## 16. Exact computed clearances

Every accepted or rejected preview shall compute, where geometrically defined, exact hole-edge clearances from the current bolt group to the finite interface boundaries.

For each interface report at minimum:

- vertical positive-side clearance;
- vertical negative-side clearance;
- horizontal positive-side clearance;
- horizontal negative-side clearance;
- minimum clearance;
- governing bolt ID;
- governing boundary ID.

Clearance means distance from the **complete physical hole footprint** to the finite boundary, not center-to-edge distance.

A clearance of exact zero is the geometry-valid boundary.

A negative clearance is invalid.

These are geometry clearances, not automatically code-prescribed minimum edge distances.

## 17. Geometry limit versus code minimum

The UI/trace shall distinguish:

### Geometry containment limit

The minimum needed for the complete hole to remain inside the finite physical surface.

### Engineering/code-required minimum

Only display if an existing accepted authority supplies it.

Do not label a geometry-containment limit as an ASCE/code minimum unless it is actually controlled by such authority.

## 18. Controlled Angle distance feedback

For the accepted R7 Angle fixture:

- hole diameter = `0.563 in`;
- hole radius = `0.2815 in`;
- the current legacy unloaded-end input `1.0 in` remains invalid;
- `1.2814 in` remains invalid;
- `1.2815 in` is the exact valid boundary;
- `1.3 in` is valid.

The UI shall display the exact current geometry limit so the user does not have to discover it by trial and error.

Example wording:

`Minimum for complete-hole containment: 1.2815 in`

Do not auto-change the user's input without an explicit user action.

## 19. Invalid offset feedback

If an offset-controlled group is invalid, return:

- exact clearance deficit;
- direction/boundary;
- governing bolt;
- safe backend validation text.

The frontend shall retain R6 last-valid-preview behavior and show the exact invalid-current state.

---

# PART D — CALCULATION APPLICABILITY WITH FIXED GRID

## 20. Geometry does not rotate to satisfy a method

A physically valid fixed vertical bolt grid shall remain fixed even if a current calculation method's assumptions are not proven for the resulting force/grid relationship.

The software shall not rotate or redistribute the physical geometry merely to keep a prescriptive method available.

## 21. Existing method applicability resolver

For each Interface A demand scenario, the existing planning/applicability layer shall evaluate the actual:

- force direction in the interface plane;
- fixed row/grid axes;
- selected row-demand method;
- profile/material pair;
- row/count geometry.

If the existing method contract cannot prove compatibility, return a structured fail-closed status equivalent to:

`ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN`

or repository-consistent identity.

No new row-distribution equation is authorized.

## 22. Existing non-prescriptive methods

Engineer-defined fractions/direct row forces or an existing rational method may proceed only under their already accepted contracts.

R10 does not broaden them.

Geometry preview may remain valid even when design calculation is not supported.

The UI shall explain the distinction.

---

# PART E — API / APPLICATION / UI

## 23. API contracts

Extend Tee interface layout contracts backward-compatibly with:

- `placement_mode`;
- `vertical_offset`;
- `horizontal_offset`.

For legacy requests:

- omitted mode => `EDGE_DISTANCE_CONTROLLED`;
- omitted offsets => not authoritative.

For offset mode:

- edge-distance inputs are not authoritative and shall not conflict with offsets;
- computed clearances are server-authored outputs.

Extend preview result with:

- placement datum identity/coordinates;
- normalized offsets;
- computed clearances;
- governing clearance;
- fixed Interface A layout-frame trace;
- brace frame trace.

## 24. Sidebar controls

For each physical interface show:

1. rows;
2. bolts per row;
3. pitch;
4. gauge;
5. `Position by`;
6. offset controls or legacy edge-distance controls according to selected mode;
7. computed clearances.

For Interface A, keep brace inclination and profile roll in `Connected Member`.

## 25. Viewer behavior

At nonzero brace inclination:

- brace rotates;
- Interface A bolt grid remains fixed/vertical in Tee frame;
- bolt shanks remain normal to Tee stem;
- head/nut/hardware presentation from R9 remains aligned with bolt axes;
- Tee/support and Interface B remain fixed.

Moving Interface A offsets shall translate only Interface A bolts/holes/hardware rigidly in the Tee-stem plane.

Moving Interface B offsets shall translate only Interface B.

## 26. Selection and stale state

Offset, placement mode, inclination, roll, count, pitch, gauge, and profile changes are engineering-significant and stale design results.

Clearance display, camera, overlay, and selection remain presentation-only.

If a selected bolt no longer exists after count change, clear selection deterministically.

---

# PART F — CONTROLLED GOLDEN / REGRESSION

## 27. Zero-inclination backward compatibility

At `brace_inclination = 0°` and legacy edge-distance placement:

- exact geometry remains R9/legacy;
- all controlled R4/R5 fingerprints remain exact;
- R7/R8 profile paths remain exact;
- R9 independent-count behavior remains exact.

## 28. Fixed-grid inclination cases

For the same accepted Interface A placement/layout:

### `+30°`

- brace longitudinal direction changes using R5 deterministic trig;
- Interface A global bolt centers remain exactly unchanged;
- Interface A bolt axes remain exactly unchanged;
- Interface B geometry unchanged.

### `-30°`

Same invariance with opposite brace slope.

### `27.5°`

Arbitrary decimal inclination behaves deterministically.

The brace/profile surface intersection may differ; the test fixture must remain physically valid.

## 29. Offset translation cases

For an accepted offset-mode group:

- increasing `vertical_offset` by `+1.0 in` adds exactly `+1.0 V` to every bolt center;
- increasing `horizontal_offset` by `-0.5 in` adds exactly `-0.5 H` to every bolt center;
- pairwise bolt spacing remains unchanged;
- other interface coordinates/fingerprint remain unchanged.

## 30. Placement-mode equivalence

Where legacy edge-distance and offset-mode inputs describe the same physical group:

- authoritative bolt coordinates are exact-equal;
- geometry fingerprint is exact-equal if placement mode itself is presentation/input provenance only;
- if mode identity is intentionally fingerprinted, physical-geometry sub-fingerprint must be exact-equal and the difference must be explicit.

Prefer physical-geometry identity equivalence.

## 31. Clearance regressions

Control:

- `1.0 in` invalid Angle legacy placement;
- `1.2814 in` invalid;
- `1.2815 in` valid with exact zero governing geometry clearance;
- `1.3 in` valid with positive clearance.

Also test exact offset-induced clearance changes.

## 32. Interface independence

At minimum:

- Stem `2 x 1`, Flange `2 x 2`;
- move Stem up: Flange unchanged;
- move Flange forward: Stem unchanged;
- incline brace: both bolt groups unchanged except any explicitly brace-surface-derived validity result for Interface A.

## 33. Hardware regression

R9 head/nut/shank presentation remains on both interfaces through:

- inclination changes;
- offset changes;
- count changes;
- views.

No hardware presentation value enters engineering fingerprint.

---

## 34. Visual acceptance after R10

After full QA and 4/4 hosted CI:

### V1-R10 — Fixed vertical grid

Use a valid Angle brace and Stem `2 x 1`, Flange `2 x 2`.

Compare:

- `0°`;
- `+25°` or `+30°`.

Verify the brace inclines but the Stem bolt grid stays vertical/fixed.

### V2-R10 — Move Interface A

Use offset mode.

Move:

- vertical offset up/down;
- horizontal offset forward/back.

Verify all Stem bolts move rigidly while Tee Flange ↔ Support remains unchanged.

### V3-R10 — Move Interface B

Move only Interface B offsets.

Verify Interface A remains unchanged.

### V4-R10 — Clearance feedback

Confirm the exact `1.2815 in` containment limit is visible in legacy mode.

Create an invalid offset and verify exact clearance deficit plus R6 last-valid-preview behavior.

### V5-R10 — Method applicability

Use a nonzero inclination/fixed grid case.

Verify geometry may remain valid while any incompatible prescribed row method is separately marked unsupported/not evaluated rather than rotating the bolts.

### V6-R10 — Hardware persistence

Rotate the scene and verify heads/nuts/shanks remain correctly aligned after inclination and offsets.

---

## 35. Acceptance boundary

R10 is accepted only if:

- brace inclination and bolt-layout orientation are decoupled;
- Interface A bolts remain Tee-frame vertical/fixed while brace inclines;
- bolt axes remain normal to Tee stem;
- independent two-axis group positioning works for both interfaces;
- no through-thickness user offset exists;
- exact computed clearances are available;
- the `1.2815 in` controlled limit is explained;
- legacy placement and zero-inclination fingerprints remain exact;
- nonzero method incompatibility fails closed without changing physical geometry;
- R9 fastener hardware presentation remains correct;
- all prior controlled hashes/fingerprints remain exact except explicitly authorized nonzero R9 geometry/fingerprint transitions documented by the R10 authority ledger;
- hosted CI is 4/4 green;
- V1-R10 through V6-R10 pass.

Only then resume the remaining Stage 3.2 beam/unit-system acceptance and closure.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
