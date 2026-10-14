# HYB1 supplementary Clip Tee workbook reference

Owner-authorized source supplement to candidate c82fee6e323fbaaab7679eaba267bfbb7c79b443.
The completed original HYB1 arithmetic, Direct adapter and direct-beam workbook remain.

## Source identity and separate domain

- Supplement: `RHM_BRACE_WORKBOOK_EXTRACTION.zip`, SHA-256
  `D8EA3FF26765EDB116D8E0F767EF20F7041762174A5BAF024EC47F3D58064AF0`.
- Original Clip Tee workbook SHA-256:
  `83CAAA73C91953138F333F3B845428C87527690152720F619724CC5700553E2D`.
- Original direct-beam workbook remains SHA-256
  `37402af592b45e3fa1a869c0470a758c74d0c1d706d31d8f4bc981096e0d6be5`.

The new source is W8x3/8 FRP brace to W8x3/8 FRP chord through a 316SS Clip Tee
with 0.375-in stem/flange, two distinct six-bolt 0.5-in attachment groups,
40-degree load, and selected 0.375-in 316SS reinforcing angle. Web attachment
is off in the saved example. Its vinyl-ester source table, selected reinforcement,
group counts and cached values are independent of the Direct Angle-to-W case.
Raw workbook, drawings, full extraction and unrelated metadata stay outside Git.

`rhm_clip_tee_reference.py` executes the recorded component arithmetic without Excel.
The normal/sliding inputs are original saved resolution caches (3.2139380484326963 /
3.83022221559489 kip) under the 5-kip saved brace force. This supplement does not
claim independent trigonometric recalculation. Explicit scaling is a reference test
variant, not an ASD combination generator. The original saved final-output cells
remain separate from recomputed Decimal component results.

## Required correction and applicability

Historical Summary C14 and E144/F144 use bending-only D142. Corrected reference
summary **and** numerical status use combined D144, including both axial and
bending terms. Saved bending is approximately 0.409127; combined is 0.456414.
At scale 2.3, bending still passes while combined fails; corrected status must FAIL.
The labelled historical stream retains the original under-reporting for replication.

Unreinforced flange variants freshly use D161 and zero reinforcement bearing/moment
credit; they cannot inherit D177. The saved reference has reinforcement selected;
its summed FRP/steel capacity is source replication, not proof of actual composite
engagement or junction transfer. Gross/reference path conventions remain explicit.
Active web attachment without established transfer is incomplete. Inactive web
attachment emits no comparison and cannot discharge receiving-web/junction coverage.
An explicit source-only transfer premise permits the optional arithmetic in tests;
it is neither an adopted method nor Section 2.3.2 qualification.

## Proposed source uses and actual HYB1 mechanisms

`clip_tee_reference_uses` emits all 19 existing Direct mechanism/alignment records
as additional **REFERENCE_ONLY** leads. Original `direct_mappings` stays unchanged.

| Source component | Actual HYB1 relevance | Coverage disposition |
|---|---|---|
| Brace bearing, D15:D25 | Angle/W `PIN_BEARING` equation reference | Already applicable ASCE checks stay authoritative; source groups/materials cannot replace them |
| Brace bolts, D30:D39; flange bolts D233:D248 | `BOLT_SHEAR` component arithmetic | Uniform/aggregate source forces do not establish actual eccentric bolt demands |
| Brace local end tear-out D41:D52 | Angle/W `INTERROW` possible component lead | Different end/inter-hole surfaces and signed transfer domain require validation |
| Brace global block D54:D66 | Angle/W `BLOCK_SHEAR` path reference | Receiving W LEFT/RIGHT and integral heel/web paths remain independent and unresolved |
| Global tension term D62:D64 | `FIRST_ROW:layer-A` / `FIRST_ROW:layer-B` | No separate first-row net-tension/bearing-bypass law; no hole-deduction proof |
| Tee flange D127:D144 | `ANGLE_HEEL_3D`, `OUT_OF_PLANE_CONTACT_PRYING` analogy only | No Tee exists in actual Direct; simple plate interaction is not a heel/contact/prying model |
| Reinforced chord flexure D149:D179 | `W_FLANGE_WEB_JUNCTION_3D` component lead | Reinforced flange result is not unreinforced flange/junction rupture coverage |
| Chord sliding bearing D216:D231 | W pin-bearing source reference | Bearing cannot replace W net tension or either block release |
| Optional web D180:D213 | Receiving W load-transfer lead | Saved inactive/NA checks establish no complete web/junction coverage |
| Tee stem D84:D124 | No Tee component in actual Direct | Retain standalone component reference only; no direct mechanism is discharged |

For BRACE and SUPPORT, no new `MAPPED_CANDIDATE`, requirement removal or qualification
is installed. Q1-Q6, C13 and Section 2.3.2 remain open. No new public Tee workspace.

## Verification and report boundary

Independent Fraction/cached-cell oracles, dimensional checks, U.S./SI parity, exact
ratio boundaries, zero/overload cases, reinforcement and attachment variants, and
the hidden-combined-failure regression exercise this supplement. The renderer only
prints immutable results. Existing six HYB1 reports remain; three separately named
Clip Tee reference PDFs are added to the isolated/hosted harness.
