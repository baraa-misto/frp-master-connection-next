# Isolated CME-2 Core Response, Angle and Tee Providers

## Scope and trust boundary

Parent authority is commit `88961da28de3421722290c2bf78af0c6191b81a1`, count 130. C2-M, C2-P1, C2-P2 and all sixteen existing freeze tags remain immutable. New modules are `domain/stainless_shape.py` and `calculation/stainless_response.py`, `stainless_angle.py`, `stainless_tee.py`. The Tee wrapper shares the angle module's approved hot-shape mechanics; no frozen stainless production module is imported. Existing family providers do not import or dispatch these modules.

No public API, editor choice, family activation, product catalogue or procurement certification is introduced. Trusted contexts are application-owned, immutable pre-resolved records; matching request labels/hashes alone cannot create them. Empty, ambiguous or mismatched contexts fail closed. Test source records are synthetic fixtures and never become production qualification.

C2-R validates qualified response envelopes separately from strength. Its five modes retain complete input/output wrenches, source/model/load/fixture identities and material dependence. Native transport uses the accepted exact wrench shift. Prescribed row fractions reuse the unchanged ASCE74 FRP/steel helper. Native equal-stiffness demand is consumed verbatim with its trusted, request/result-bound native equilibrium proof, including the native Decimal projection boundary; it is not recomputed through a second precision path. Locked sharing requires existing native symmetry evidence with identical branch identities. External response remains a source-qualified input, not a new nonlinear analysis.

Physical shafts occur once; ordered layer/plane IDs are unique and cumulative vector cuts close to the source terminal reaction. Contact and total-prying records are independent of body resistance. Source total bolt tension already including prying is never increased again. No bolt, FRP member, anchor or foundation strength is calculated by these providers.

C2-A/C2-T accept only unwelded, one-piece hot-rolled/extruded ASTM A276/A276M plus A484/A484M 316-family shapes, condition A/HF, conservative Fy 25 ksi/Fu 70 ksi/E 28000 ksi/G 10800 ksi. Real source-native section snapshots are required. No A479 route, cold-work/MTR uplift, formed/laser/welded product or cut Tee is admitted.

The shared native-quantity/Decimal-100 HALF_EVEN calculation retains D2/D3 yielding/rupture and permitted shear lag; all four G6 Cv2 zones; both E3 principal axes plus trusted E4 Fe with raw/capped Curve A; all three F10 branches with trusted stability; and both H2 tension equations or H2 compression. No automatic E4 or F10 stability solver is introduced. Unsupported slenderness, unequal-angle compression, torsion, combined normal/shear and missing heel/junction mechanisms fail closed. Bound frozen P1/P2 local snapshots do not replace full-body or response qualification.

## Owner/EOR I11 clarification (2026-09-13)

The original I11 sentence in the byte-exact golden is superseded, not deleted. There remain sixteen invariants. Compression interaction is nondecreasing in each positive demand term. For tension:

`H2-1 = Mrw/Mctw + Mrz/Mctz + Pr/Pct`

`H2-2 = Mrw/Mcw + Mrz/Mcz - Pr/Pct`

Increasing tensile Pr increases H2-1 and decreases H2-2. Governing interaction is exactly their maximum, without a global tensile-Pr monotonicity constraint. The supplied approximately 0.457774 to 0.442231 decreasing counterexample is expected. All 24 positive and 27 negative benchmark values remain unchanged.

## Byte-exact approved artifact index

| Repository path | SHA-256 |
| --- | --- |
| docs/engineering/FRP_MASTER_CONNECTION_CME_2_CORE_R_A_T_SOURCE_AND_METHOD_RECONCILIATION_RC1.md | D47C1F5E62D17289A810D7AE0DBC824C44B4BC3A2BB4F1C4B2D0543740E5180E |
| docs/engineering/FRP_MASTER_CONNECTION_CME_2_C2_R_ENGINEERING_SPECIFICATION_RC1.md | 498A6A44975A223BE2ACE05F26437B5999391363B5BA2DB60401646AA020E9E7 |
| docs/engineering/FRP_MASTER_CONNECTION_CME_2_C2_A_ENGINEERING_SPECIFICATION_RC1.md | 5A445189AB05D95F61A27A92F74C9C71373E864521DA894033A2D27E4ED0D0C1 |
| docs/engineering/FRP_MASTER_CONNECTION_CME_2_C2_T_ENGINEERING_SPECIFICATION_RC1.md | A8230832154D961166F8BA006AB55B895C8B70FF76C354DD13B96826D804E380 |
| backend/tests/golden/FRP_MASTER_CONNECTION_CME_2_CORE_R_A_T_GOLDEN_BENCHMARKS_RC1.json | E89748C24CB53E25C559A7BAD2C02E442FD8A05A72DE308CA14826698C6C1938 |
| docs/qa/FRP_MASTER_CONNECTION_CME_2_CORE_R_A_T_RC1_INDEPENDENT_VALIDATION.md | C2EAE5CC55E0EC98DA00724DDF5D2A595BF74CBCF7361EBD42E32B936CE63B95 |
| docs/governance/FRP_MASTER_CONNECTION_CME_2_CORE_R_A_T_OWNER_APPROVAL_RECORD_2026-09-12.md | 1A0738114280E0F84BB31E23FC604763A2AA4005FA93EABF269371011EB6CA08 |

Exactly validation lines 4 and 5 have owner-authorized Markdown hard breaks. The checker must identify exactly those findings while rejecting every other new whitespace error. No artifact or general Git/whitespace policy is normalized or weakened.

## Acceptance and conditional freeze

Complete local integrated QA and exact implementation-SHA hosted CI precede independent read-only acceptance. Acceptance includes all 24/27/16 cases, frozen regressions, at least 67 exact parent responses and browser/runtime smoke. Only acceptance PASSED authorizes the new core tag, targeting the implementation commit rather than the later governance commit. CME-3/public activation remain excluded. External completion reports record actual counts, SHA/CI and phase classifications; this document does not predeclare those gates passed.
