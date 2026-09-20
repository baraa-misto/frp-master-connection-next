# FRP Master Connection — Stage 3.2-R4 Exact Unit Geometry + Valid Tee Benchmark — Engineering Correction Specification RC1

## 1. Status
**Controlled owner engineering correction specification — RC1**

Stage 3.2-R4 supersedes the stopped Stage 3.2-R3 execution order. R3 performed diagnosis only and made no repository mutation.

R4 authorizes two corrections that must land together:
1. recover authoritative unit-converted geometry in exact Decimal space before geometric subtraction/comparison/fingerprinting; and
2. replace the invalid U.S./SI Tee UI benchmark profile fixture with one physically valid canonical benchmark represented in both unit systems.

No new resistance equation or connection mechanics are authorized.

## 2. Accepted baseline
- `HEAD == origin/main`: `d5728256bff86d63558ba1fa0e4874120af9f5dd`
- subject: `feat: unify tee workspace and member profiles`
- commit count: `48`
- tracked files: `316`
- frontend source tree: `b7f21b032d2fd075c2428a5cbab9f17530690c3b`
- clean worktree/index
- freeze tag: `stage-2.3-interface-geometry-freeze`
- freeze target: `5bc545ab8251f9bd49dedc776962937ed5e822a2`

Stage 3.2-R2 hosted CI is accepted 4/4 green with 247/247 frontend tests on Ubuntu and Windows.

## 3. Diagnosed defects

### 3.1 Invalid Tee UI benchmark member/profile fixture
The real U.S. and SI Tee benchmark loaders fail before the intended SI exactness regression because the current `4 x 3 x 0.5` angle benchmark cannot resolve the first Interface A bolt path to a finite opposing face.

The benchmark itself is physically invalid for the current R2 member/profile surface model.

### 3.2 Binary-float contamination before exact geometry recovery
The larger backend SI fixture reproduces:

`25.4 + 50.800000000000004 != 76.2`

The input strings `25.4` and `50.8` are already exact unit conversions of `1 in` and `2 in`.

The defect occurs because exact Decimal-derived coordinates become binary floats and arithmetic occurs before recovery to Decimal.

## 4. Exact geometry authority rule
Authoritative engineering geometry shall obey:

`input decimal -> exact unit conversion -> Decimal canonical coordinate -> Decimal vector/coordinate arithmetic -> Decimal validation/fingerprint`

Binary floating-point may be used only after authoritative geometry is resolved, for rendering/presentation.

Forbidden in authoritative geometry recovery:
- binary-float coordinate arithmetic followed by Decimal recovery;
- `Decimal(float)`;
- `Decimal(str(float_result))` when `float_result` came from engineering-coordinate arithmetic;
- epsilon/tolerance repair;
- `isclose`;
- unit-system-specific validation bypass;
- rounding inside exact geometry validation.

If a rendering/geometry API returns float coordinates, recover authoritative geometry from the original exact source coordinates/transform parameters, not post-arithmetic float output.

## 5. Correct exact SI coordinate regression
U.S.:
- loaded/end coordinate: `1 in`
- pitch/increment: `2 in`
- next coordinate: `3 in`
- exact relation: `1 + 2 == 3`

SI using exact `25.4 mm/in`:
- loaded/end coordinate: `25.4 mm`
- pitch/increment: `50.8 mm`
- next coordinate: `76.2 mm`
- exact relation: `25.4 + 50.8 == 76.2`

The corrected authoritative path shall produce exactly `76.2`.

## 6. Fingerprint correction authority
Known affected SI execution fingerprint:

Deprecated pre-correction:
`7c6d7bb9b3d04246c789ad9ed9b291d5b7349a46435594d9bebb181c8488bf57`

Required corrected exact-geometry fingerprint:
`40ba8cb419f56f5b5c59e2b102c9842850bc925a600088b62185d96cc0314a69`

R4 explicitly authorizes this transition.

If additional existing SI fingerprints change solely because the same binary-float coordinate-recovery defect is removed, they are authorized only when all are proven:
1. U.S./canonical physical geometry is unchanged;
2. SI physical geometry becomes exactly unit-equivalent;
3. no demand/resistance equation changes;
4. no non-SI fingerprint changes;
5. each before/after fingerprint is reported and regression-tested.

Any fingerprint change outside this rule requires STOP.

## 7. Canonical Tee UI benchmark
The U.S. and SI Tee benchmark buttons shall load one physically valid canonical benchmark.

To preserve the original Stage 3.2 RC1 benchmark intent, the connected brace profile shall be:

`FLAT_PLATE`

Angle remains supported and shall be exercised separately during visual acceptance.

### 7.1 Canonical U.S. geometry
Tee:
- connector length `8 in`
- flange width `6 in`
- flange thickness `0.5 in`
- stem depth `4 in`
- stem thickness `0.375 in`

Connected flat-plate brace:
- width `8 in`
- thickness `0.375 in`
- member/view length `6 in`
- selected contact face: repository-defined positive/default flat-plate face used by Tee-stem compatibility

W support:
- member length `16 in`
- depth `8 in`
- flange width `8 in`
- web thickness `0.5 in`
- flange thickness `0.75 in`

Fastener:
- bolt diameter `0.5 in`

Interface A:
- rows `2`
- bolts per row `2`
- pitch `2 in`
- gauge `2 in`
- unloaded end distance `1 in`
- loaded end distance `1 in`
- negative side distance `1 in`
- positive side distance `1 in`

Interface B: same layout values.

Support role: `COLUMN`
Selected support flange: existing positive local flange used by the Tee benchmark.

### 7.2 Exact SI equivalent
Using exact `25.4 mm/in`:

Tee:
- connector length `203.2 mm`
- flange width `152.4 mm`
- flange thickness `12.7 mm`
- stem depth `101.6 mm`
- stem thickness `9.525 mm`

Connected flat-plate brace:
- width `203.2 mm`
- thickness `9.525 mm`
- member/view length `152.4 mm`

W support:
- member length `406.4 mm`
- depth `203.2 mm`
- flange width `203.2 mm`
- web thickness `12.7 mm`
- flange thickness `19.05 mm`

Fastener:
- bolt diameter `12.7 mm`

Interface A:
- pitch `50.8 mm`
- gauge `50.8 mm`
- unloaded end distance `25.4 mm`
- loaded end distance `25.4 mm`
- negative side distance `25.4 mm`
- positive side distance `25.4 mm`

Interface B: same exact SI values.

The SI fixture shall be derived from or verified against the canonical physical benchmark using the repository's exact unit-conversion authority.

## 8. Benchmark load/action
Preserve existing Tee benchmark action semantics.

If the benchmark uses `0.1 kip` for the active force component, the SI loader shall use the repository's existing exact force-conversion authority rather than an independently rounded constant.

## 9. Physical validity requirement
Backend-authoritative geometry shall prove:
- selected flat-plate contact face is finite;
- each Interface A bolt axis intersects a valid opposing face through connected plate thickness;
- each Interface B bolt axis intersects intended Tee/support layers;
- every bolt center lies inside applicable finite surfaces;
- no geometry rule is weakened.

No benchmark-only bypass.

## 10. U.S./SI equivalence
U.S. and SI loaders shall resolve to the same physical authoritative geometry after normalization.

Compare exact normalized:
- Tee dimensions;
- connected-member profile/dimensions/surface;
- support role/profile/surface/dimensions;
- bolt diameter;
- Interface A bolt coordinates;
- Interface B bolt coordinates;
- physical reference coordinates;
- geometry fingerprints where display-unit identity is excluded.

## 11. Engineering mechanics unchanged
R4 shall not change any Stage 2.4A/2.4B/2.5A/2.5B/2.6A/2.6B mechanics, Stage 3.1 material authority, Stage 3.2 two-interface orchestration, normal-action fail-closed behavior, Tee-body limitation, or R2 profile applicability.

Only exact coordinate recovery and benchmark validity are corrected.

## 12. Required regression coverage
At minimum prove:
1. exact U.S. `1 + 2 == 3`;
2. exact SI `25.4 + 50.8 == 76.2`;
3. no binary-float artifact in authoritative row coordinates;
4. corrected fingerprint exactly `40ba8cb419f56f5b5c59e2b102c9842850bc925a600088b62185d96cc0314a69`;
5. deprecated fingerprint no longer emitted for that case;
6. U.S. Tee benchmark preview succeeds;
7. SI Tee benchmark preview succeeds;
8. both use `FLAT_PLATE`;
9. U.S./SI Tee dimensions exactly equivalent;
10. U.S./SI connected-member dimensions exactly equivalent;
11. U.S./SI support dimensions exactly equivalent;
12. Interface A layouts resolve to exact equivalent canonical coordinates;
13. Interface B layouts resolve to exact equivalent canonical coordinates;
14. Interface A bolt paths have finite opposing faces;
15. Interface B bolt paths are valid;
16. benchmark action remains physically equivalent;
17. no tolerance/epsilon added;
18. no validator weakened;
19. Stage 3.2 G1-G6 exact;
20. Stage 3.2-R2 G1-G10 exact;
21. Stage 2/direct U.S./SI regressions exact;
22. Angle/Channel/RHS support unchanged.

## 13. User-visible behavior
After R4:
- `Load U.S. Tee benchmark` succeeds;
- `Load SI Tee benchmark` succeeds;
- both depict the same physical connection;
- benchmark connected member is identified as a flat-plate brace;
- Angle remains manually selectable and distinct;
- no SI exact-geometry rejection occurs solely because of unit conversion.

## 14. Acceptance
R4 requires:
- full QA;
- 100% configured coverage;
- 4/4 hosted CI;
- all previous controlled artifacts byte-exact;
- exact documented fingerprint transition;
- no unapproved fingerprint changes;
- both benchmark loaders valid.

Then Stage 3.2-R2 visual V1-V5 plus R4 V6 may proceed.

**END OF CONTROLLED ENGINEERING CORRECTION SPECIFICATION — RC1**
