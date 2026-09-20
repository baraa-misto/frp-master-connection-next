# FRP Master Connection — Stage 3.6B Web-Splice Resistance Completion with Rational Plate-Body Interaction — Engineering Specification RC2

## 1. Status

**Controlled owner engineering specification — RC2**

This specification supersedes all earlier Stage 3.6B specifications.

Calculation Slice 4 is now an accepted prerequisite and shall be reused without changing its equations.

## 2. Accepted starting baseline

Expected repository state:

- branch `main`;
- `HEAD == origin/main == remote main`:
  `a93aa5d127a51dc81a6c7cd108af15c44d59ff9f`;
- subject:
  `feat: add Chapter 7 plate strength engine`;
- commit count:
  `91`;
- clean worktree/index.

Calculation Slice 4 hosted CI:

- GitHub Actions run #86;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS;
- duration approximately `4m 48s`.

Calculation Slice 4 requires no separate 3D visual acceptance and is accepted after its controlled goldens, complete QA, source/provenance review, and hosted CI.

## 3. Immutable freeze targets

Preserve:

- Stage 2.3 `5bc545ab8251f9bd49dedc776962937ed5e822a2`;
- Stage 3.2 `d16b354732c90bf3bf7847c62be652c230a9f91e`;
- Stage 3.3 `a4d21506d45d2d21d3f5039b662ea56ec6c5da9f`;
- Stage 3.4 `2303ec713d6d038b935e076b909c3b639ced0e09`;
- Stage 3.5 `7bb83e5c8814781419c0789b7428bd46572d514c`.

No tag operation.

## 4. Inherited Calculation Slice 4 authority

Require exact accepted Slice 4 commit:

`a93aa5d127a51dc81a6c7cd108af15c44d59ff9f`.

Controlled Slice 4 hashes:

- Decision:
  `C1FF10672CC98A832932DCBD010DCF280F0D866123280AC68565767F14093E28`
- Specification:
  `32F1A51AC6C82701C2C9E61F08AEC1E804D500D5507BC930A6677B40CD93C541`
- Golden:
  `E6F00A1421751386980321A5AA046A13C706D9D32E42AAC6242F0D89525AC4CD`
- Ledger:
  `7E515FABD6AC3118528F3404CE06456748776054627499EE06C6A0907A782971`
- Order:
  `B8D74C87C3CCACEC886C5723395EC2D43FEF5197BA6ED34C39FBDBBCFB801D0F`

Stage 3.6B shall call the accepted Slice 4 APIs/results and shall not copy its equations into connection orchestration.

## 5. Contract evolution

Historical:

`3.6A-RC1`.

Current successor:

`3.6B-RC2`.

Historical Stage 3.6A requests/results/fingerprints remain exact.

## 6. Geometry/action invariance

Preserve Stage 3.6A exactly:

- two identical W/I beams;
- positive beam-end gap;
- two symmetric FRP splice plates;
- two mirrored Plate/Web/Plate bolt groups;
- signed Axial/Major/Minor force;
- zero user moment;
- group references/wrenches;
- Stage 2.5A demand vectors;
- material axes;
- loaded-edge/reverse applicability.

## 7. Clear splice-body region

Define the unperforated central body between the joint-side boundaries of the inner bolt holes.

For current geometry derive:

- Beam A inner bolt column closest to joint;
- Beam B inner bolt column closest to joint;
- actual nominal hole radius.

Default:

- left inner center `L=-2.5 in`;
- right inner center `L=+2.5 in`;
- hole diameter `0.563 in`;
- clear boundaries `L=-2.2185 in`, `+2.2185 in`;
- clear-body length `a_body=4.437 in`.

No hard-coded default values in production.

If boundaries overlap/cross:

`INVALID_GEOMETRY`.

## 8. Rational panel mapping to Slice 4

Method:

`RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1`.

For each splice plate pass to Calculation Slice 4:

- `a = a_body` along plate LW / `L_S`;
- `b = full splice-plate height` along CW / `V_S`;
- `t = plate thickness`;
- adjusted material properties from existing property authority;
- existing time-effect factor.

Slice 4 returns commentary advisories where applicable.

Stage 3.6B records that this panel mapping is rational project authority.

## 9. Critical sections

Evaluate exactly:

- `SECTION_A_CLEAR_BOUNDARY`;
- `SECTION_JOINT`;
- `SECTION_B_CLEAR_BOUNDARY`.

Use exact coordinates.

Prove no distributed load exists in central body; axial/shear force is constant and in-plane moment varies linearly, so boundary/joint sections bound the RC2 stress envelope.

## 10. Pair body actions

At each section obtain authoritative pair-body resultants:

- `N_pair` along `L_S`;
- `V_pair` along `V_S`;
- `M_pair` about `T_S`.

Minor shear `V_T` is outside this in-plane body interaction.

No frontend calculations.

## 11. Pair-to-plate allocation

After exact positive/negative splice-plate symmetry:

`N_p=N_pair/2`

`V_p=V_pair/2`

`M_p=M_pair/2`.

If symmetry fails:

`WEB_SPLICE_PLATE_BODY_RATIONAL_INTERACTION = NOT_EVALUATED`.

## 12. Plate section properties

For one plate:

`A=h t`

`I_T=t h^3/12`

`c=h/2`.

Exact Decimal arithmetic.

## 13. Normal stress

At each critical section:

`σ_1=N_p/A + M_p c/I_T`

`σ_2=N_p/A - M_p c/I_T`.

Retain sign.

Positive = tension.

Negative = compression.

## 14. In-plane shear stress

`τ_LT=V_p/A`.

Retain signed provenance.

Use membrane plate shear; do not use `1.5V/A`.

## 15. Slice 4 pure tension resistance

For the unperforated body, call Calculation Slice 4 longitudinal tension.

Use effective net area per unit width:

`Ae=t`.

Obtain design strength per unit width `R_tL,d`.

Convert to design stress for the rational interaction:

`f_t,d = R_tL,d / t`.

Retain complete Slice 4 provenance/fingerprint.

## 16. Slice 4 pure compression resistance

Call Calculation Slice 4 longitudinal compression with:

- `a=a_body`;
- `b=plate height`;
- `t=plate thickness`;
- adjusted properties/factors.

Use governing Slice 4 design strength per unit width including rupture and normative orthotropic buckling:

`R_cL,d`.

Convert:

`f_c,d = R_cL,d / t`.

Retain Slice 4 advisories, including short/narrow plate cautions.

Do not alter Slice 4 buckling equation.

## 17. Slice 4 in-plane shear resistance

Call Calculation Slice 4 in-plane shear with the same panel dimensions.

Use governing design shear strength per unit width:

`R_vLT,d`.

Convert:

`f_v,d = R_vLT,d / t`.

Retain `a<b` commentary advisory if present.

Do not substitute commentary alternative formulas.

## 18. Rational interaction method

Method identity:

`RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1`.

For each section/fiber:

If `σ>=0`:

`U_n=σ/f_t,d`.

If `σ<0`:

`U_n=|σ|/f_c,d`.

Shear:

`U_v=|τ|/f_v,d`.

Combined:

`U_R=U_n+U_v`.

Pass when:

`U_R<=1`.

No exponent, quadratic, Tsai-Hill, or hidden factor.

## 19. Governing body result

Evaluate all critical sections and both extreme fibers.

Return:

- governing section;
- governing fiber;
- signed normal stress;
- signed shear stress;
- tension/compression normal mode;
- Slice 4 pure-mode result IDs/fingerprints;
- `f_t,d` or `f_c,d`;
- `f_v,d`;
- `U_n`;
- `U_v`;
- `U_R`;
- body result state.

## 20. Body result states

- `PASS_RATIONAL_METHOD`;
- `FAIL_RATIONAL_METHOD`;
- `NOT_EVALUATED` only when a rational prerequisite or Slice 4 pure-mode result is unavailable/inapplicable.

Rational failure governs overall `FAIL`.

## 21. Engineering review / qualification

Whenever rational method executes:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED=true`.

Retain:

`FRP_SPLICE_PLATE_CONNECTION_ELEMENT_QUALIFICATION=REQUIRED_2_3_2`.

A calculated rational pass is not represented as an unqualified ASCE-prescriptive pass.

## 22. Mandatory disclaimer

Backend ID:

`WEB_SPLICE_RATIONAL_BODY_INTERACTION_DISCLAIMER_RC1`.

Controlled meaning:

The FRP web-splice plate inter-group body under combined longitudinal normal force and in-plane shear is evaluated using a project-specific conservative linear interaction of separately derived ASCE/SEI 74-23 Chapter 7 pure-mode plate design resistances. The interaction equation and the selected clear-body panel boundary idealization are rational engineering methods and are not prescribed directly by ASCE/SEI 74-23. The engineer of record shall review the assumptions, actual restraint/buckling boundary conditions, Calculation Slice 4 advisories, and Section 2.3.2 connection-element qualification requirements.

If report generation exists, place the disclaimer in the final disclaimer section.

If not, retain deterministic backend disclaimer metadata for later report integration.

## 23. Test-only rational arithmetic benchmark

The rational arithmetic benchmark uses test-only design stresses:

- `f_t,d=12 ksi`;
- `f_c,d=10 ksi`;
- `f_v,d=5 ksi`.

These are arithmetic-test values only and do not replace Slice 4 in production.

Default plate geometry:

- `h=8 in`;
- `t=0.5 in`;
- `A=4 in²`;
- `I_T=21.333333333333333333333333333333333333333333333333 in^4`;
- `c=4 in`;
- `|x_clear|=2.2185 in`.

For default Major shear `V=-10 kip`:

- per plate `V=-5 kip`;
- `|tau|=1.25 ksi`;
- pair clear-boundary moment magnitude `22.185 kip-in`;
- per-plate moment magnitude `11.0925 kip-in`;
- extreme bending-stress magnitude `2.07984375 ksi`;
- governing rational utilization `0.457984375`.

Combined tension+shear `P=+20`, `V=-10`:

`U_R=0.63165364583333333333333333333333333333333333333333`.

Combined compression+shear `P=-20`, `V=-10`:

`U_R=0.707984375`.

Failure case `P=-30`, `V=-15`:

`U_R=1.0619765625`.

## 24. Pure-mode reduction

Automated arithmetic tests:

- if `V=0`, `U_R=U_n`;
- if `N=M=0`, `U_R=U_v`.

For the default user pure-Major-shear case, the eccentric body moment legitimately creates normal stress, so both terms may be nonzero.

## 25. Physical double-shear topology

Every common bolt path:

`Positive Splice Plate -> Beam Web -> Negative Splice Plate`.

Physical shear planes:

`2`.

Derive from physical path, not product name.

## 26. Double-shear applicability

Numerical check requires:

- complete Plate/Web/Plate path;
- two physical planes;
- exact plate-pair symmetry;
- exact 0.5/0.5 outer-plate allocation;
- controlled thread condition;
- source-authorized `F_nv`;
- in-plane bolt demand only.

Otherwise:

`WEB_SPLICE_COMMON_BOLT_DOUBLE_SHEAR=NOT_EVALUATED`.

## 27. Physical per-bolt demand

Use actual accepted Stage 2.5A result:

`V_i=|Q_i,in-plane|`.

No equal-share replacement.

## 28. Per-plane demand

`V_plane=V_i/2`.

## 29. Bolt strength

Reuse accepted Section 8.3.2.1 implementation:

per plane:

`phi R_plane=0.75 F_nv A_b`.

two planes:

`phi R_2sp=2(0.75 F_nv A_b)`.

Utilization:

`U_i=V_i/phi R_2sp`.

## 30. Controlled analytical double-shear benchmark

Test-only F3125:

- `d=0.5 in`;
- `F_nv=68 ksi`;
- `phi=0.75`;
- `A_b=0.19634954084936207740391521145496893026232308746095 in²`;
- per-plane design strength:
  `10.013826583317465947599675784203415443378477460508 kip`;
- two-plane design strength:
  `20.027653166634931895199351568406830886756954921016 kip`;
- for `V_i=10 kip`:
  `U=0.49930962538633830829453729685494701814732437879360`.

## 31. F593 source pending

Do not invent generic ASTM F593 `F_nt`.

If current default source remains unresolved:

- no numerical `F_nv`;
- no numerical double-shear capacity;
- explicit source-required state.

Existing explicit verified/custom strength authority may be used.

Do not change default fastener selection.

## 32. Minor shear

When Minor shear is nonzero:

`WEB_SPLICE_MINOR_SHEAR_BOLT_AXIS_RESPONSE=NOT_EVALUATED`.

No bolt tension distribution.

No pull-through/prying closure.

No automatic Eq 8-3 combined tension/shear.

The supported in-plane double-shear check may remain visible as partial.

## 33. Existing local FRP checks

Preserve Stage 3.6A local:

- pin bearing;
- net tension;
- shear-out;
- block shear;
- loaded-edge/reverse applicability.

No local result/fingerprint change.

## 34. Beam A / Beam B independence

Retain independent Stage 2.5A and local failure-path records for Beam A and Beam B.

New double-shear records also retain distinct group/bolt IDs and actual vectors.

## 35. User flexural moment

Preserve:

`WEB_SPLICE_MEMBER_FLEXURAL_MOMENT_TRANSFER=NOT_AUTHORIZED_IN_RC1`.

No moment input field.

Generated eccentricity moments remain mandatory.

## 36. Whole-splice aggregation

Precedence:

1. invalid -> invalid/rejected;
2. supported local FRP / double-shear / rational body failure -> `FAIL`;
3. required unavailable/source-pending/minor response -> `NOT_EVALUATED`;
4. if all required in-plane checks pass and only rational review/qualification remains:
   `PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED`.

Never ordinary unqualified `PASS`.

## 37. Preview

Preview remains resistance-free.

It may produce:

- clear-body geometry;
- Slice 4 input plan/method IDs;
- rational applicability;
- critical-section identities;
- physical shear-plane/source applicability;
- review/qualification/disclaimer metadata.

It shall not calculate Stage 3.6B utilization/capacity.

Resistance calls:

`0`.

## 38. Explicit design

Run Design Check:

- historical local FRP checks;
- Calculation Slice 4 tension/compression/shear results;
- rational body interaction;
- physical double-shear bolt check;
- source-pending behavior;
- whole-result aggregation;
- disclaimer/review metadata.

## 39. API / contract

Current successor:

`3.6B-RC2`.

Historical:

`3.6A-RC1`.

No geometry/action input changes.

Unknown future versions fail closed.

## 40. Frontend body result

Add visible:

`Splice-Plate Body Interaction`.

Show:

- Rational linear interaction;
- clear body length;
- panel model;
- Slice 4 method/provenance;
- Slice 4 advisories;
- governing section/fiber;
- normal/shear stresses;
- design stresses;
- `U_n`, `U_v`, `U_R`;
- status;
- engineering review required;
- Section 2.3.2 qualification.

## 41. Frontend double-shear result

Show:

- physical shear planes;
- source/thread condition;
- physical per-bolt demand;
- per-plane demand;
- per-plane capacity;
- two-plane capacity;
- utilization/status.

Source pending must not appear as PASS.

## 42. Disclaimer presentation

Normal UI may show concise:

`Rational engineering method used for splice-plate body interaction — engineering review/report disclaimer required.`

Backend owns full disclaimer text.

## 43. Controlled golden cases

At minimum:

G1 Historical Stage 3.6A exact.
G2 Slice 4 accepted commit/hash provenance exact.
G3 Stage 3.6B geometry/action unchanged.
G4 clear boundaries exact.
G5 clear body length exact.
G6 critical sections/envelope proof.
G7 plate allocation exact.
G8 A/I/c exact.
G9 body section actions exact.
G10 normal stress signs exact.
G11 membrane shear stress exact.
G12 Slice 4 tension call/provenance.
G13 Slice 4 compression call/provenance including buckling/advisories.
G14 Slice 4 shear call/provenance including buckling/advisories.
G15 rational default arithmetic exact.
G16 rational tension+shear exact.
G17 rational compression+shear exact.
G18 rational failure exact.
G19 pure axial reduction.
G20 pure shear reduction.
G21 review flag true.
G22 qualification retained.
G23 disclaimer deterministic.
G24 report metadata transport.
G25 plate symmetry failure -> NOT_EVALUATED.
G26 rational failure -> FAIL.
G27 rational pass aggregate state.
G28 two physical bolt shear planes.
G29 per-plane bolt demand.
G30 analytical per-plane bolt capacity.
G31 analytical two-plane bolt capacity.
G32 analytical bolt utilization.
G33 F593 source pending.
G34 actual Stage 2.5A vectors consumed.
G35 Beam A independent checks.
G36 Beam B independent checks.
G37 Minor shear boundary.
G38 no Eq 8-3 without tension solution.
G39 local Beam A/B FRP invariance.
G40 Beam B reverse applicability invariance.
G41 user flexural moment unauthorized.
G42 preview zero resistance.
G43 design-only Slice4/rational/double-shear execution.
G44 U.S./SI rational-body equivalence.
G45 U.S./SI double-shear equivalence.
G46 successor fingerprint scope.
G47 Calculation Slice 4 regression exact.
G48 historical Stage 3.6A fingerprint exact.
G49 Stage 3.5 frozen regression exact.
G50 Stage 2.3/3.2/3.3/3.4 frozen regressions exact.

## 44. U.S./SI

Equivalent physical inputs shall preserve:

- clear-body geometry;
- section actions/stresses;
- Slice 4 pure-mode design results;
- advisories;
- rational utilization/status;
- double-shear capacity/utilization;
- fingerprints.

## 45. Fingerprints

Stage 3.6B successor fingerprints add:

- Slice 4 commit/artifact/method provenance;
- clear-body geometry;
- rational method ID;
- panel model;
- critical section/fiber;
- Slice 4 pure-mode result fingerprints;
- rational utilization/status;
- disclaimer/review/qualification;
- shear-plane/source/thread provenance;
- double-shear result.

Historical Stage 3.6A and Calculation Slice 4 fingerprints remain exact.

Frozen Stage 3.5 and earlier fingerprints remain exact.

## 46. Acceptance boundary

Stage 3.6B RC2 is accepted only if:

- Calculation Slice 4 is consumed, not duplicated;
- rational body uses exact Stage 3.6A body actions;
- generated body moment is retained;
- Slice 4 compression/shear buckling is included;
- Slice 4 advisories are visible provenance;
- rational interaction arithmetic is exact;
- rational review/disclaimer is mandatory;
- physical double-shear uses actual Stage 2.5A bolt demand;
- F593 source pending remains source pending;
- Minor and user-moment limitations remain;
- Stage 3.6A / Slice 4 / frozen families remain exact;
- full local/object-isolated QA passes;
- hosted four-job CI passes;
- owner visual acceptance passes.

**END OF STAGE 3.6B RC2 WEB-SPLICE RESISTANCE COMPLETION ENGINEERING SPECIFICATION**
