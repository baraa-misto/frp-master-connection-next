# P4 — current physical receiving-flange component candidate

Owner engineering review is pending. This implementation is a component
calculation in the existing unified Direct candidate workspace. It does not
activate a new native F8/F9 method, establish complete connection verification,
close C13, or install Section 2.3.2 qualification.

## Source and unchanged authority

- Preserved P3: 866df344a4f62cd909edd01ae851a5c9d7bb156e.
- Approved security successor: 5fcc41330f6e048de00251909ee6af2eeeba6257.
- Approved LF/CRLF test correction: a3c2f0933db9daab9f332848cf17d9ec5fe5766a.
- Source: owner-provided ASCE/SEI 74-23, Chapter 8; scope, Fig. 8-1,
  Table 8-1, Sections 8.2.3, 8.2.5, 8.3.1 and 8.3.3.2;
  Eq. 8-12 on printed page 36. Relevant Section 2.10 net-area provisions and
  the controlled Slice 2 RC2 interpretation remain unchanged.
- The supplied January 13, 2026 erratum was inspected. Its Chapter 5 correction
  does not change this Chapter 8 equation. Licensed pages/workbooks are excluded
  from the repository and distributable review evidence.
- Existing immutable inter-row resistance and Slice 8 wrench kernels are reused.
  All 53 protected engineering identities and historical controls are retained.
  Dependency pins/locks and the immutable S1 security authority are unchanged.

## One physical model; explicit unknowns

The geometry-only adapter reuses the frozen R3 frame, edge and hole-containment
helpers at their original 60-digit precision. Exact scene comparisons cover both
alignments and several inclinations. Preview executes no resistance function.
The original 2-in actual pitch is not replaced by either projection.

The optional P4 physical contract supplies the smallest local data needed here:

- Each receiving longitudinal direction is UNKNOWN, CONTINUOUS or an actual
  FREE end with distance from the common bolt-pair midpoint.
- A measured clear flat outstand runs from the occupied flange free edge to
  the excluded web/root/fillet. The input is a user declaration, not a surveyed
  or independently verified geometry record. It cannot exceed half the flange
  width. The actual hole and local release must lie strictly inside it.
- The actual interface gap is known or unknown. Positive standoff withholds the
  new local method and unsupported bearing transfer; zero gap does not establish
  prying, contact stiffness or bolt-axis demand.
- All six additional receiving/bypass actions are independently entered for each
  LRFD case at the common datum in the receiving material frame. Unknown values
  are never replaced with zero. Nonzero bypass requires a coupled model.
- The original published U.S./SI standard-hole column is retained as provenance.
  Display conversion never changes this source choice or resizes the actual hole.

Source I8 depth and nominal web thickness remain labelled display context where
their actual values are not established. They do not supply engineering end,
root, stiffness, net-tension or global-block operands. The new local method uses
only the explicitly established receiving flange thickness and measured flat
outstand. A separate complete receiving-I model is still required for its
first-row, junction and global-release mechanisms.

The viewer shows an actual declared end when it lies within the view. An actual
end beyond the crop remains explicitly labelled beyond the crop; calculation uses
its true distance. Gap translation is applied once to each Angle surface.

## Source-gated executable subset

The new receiving longitudinal inter-row shear-out component is available only
when all of these conditions are established:

1. The current shared two-bolt pair is support-aligned along receiving LW, with
   the established source datum and contained, separate physical holes.
2. The current complete Slice 8 wrench belongs to the same geometry identity,
   case digest and exact ordered coordinates. Its equilibrium proof passes.
3. In the receiving frame the resultant is nonzero along LW, with exactly zero
   transverse force and transported free in-plane moment. No tolerance zeroes
   an entered component. Out-of-plane actions/reference are unsupported.
4. In the direction selected by the signed connection force there is an actual
   unloaded free end; the opposite direction continues into the receiving member.
5. The full single-line connection demand is used. There is no eccentric P/n or
   V/n substitution.
6. The receiving flange is the minimum connected thickness, with the applicable
   source minimum, diameter, end, edge and maximum-pitch limits met.
7. The actual nominal hole matches the declared source standard. Eq. 8-12 uses
   this nominal hole. The additional source net-hole increment is used only in
   the separate raw net-area screen.
8. The complete local release lies in the declared flat flange outstand, excludes
   the integral web/root, and reaches the actual free end.
9. Gap is explicitly zero and all six additional receiving-member actions for
   this case are explicitly zero. Missing/nonzero bypass does not borrow an
   unapproved coupled stress-transfer law.
10. A current MAT1 adjusted receiving in-plane shear property is available.

### Physical witness and its limits

Two longitudinal shear faces lie at the actual hole-side x coordinates. Their
trailing closure is in the actual trailing hole void; their other boundary is
the actual receiving free end. This provides a local detachable-strip witness
without fracturing an integral web or inventing a free junction surface.

The witness establishes topology and applicability of this local component.
It is not a derivation of a new strength law. The empirical source equation's
effective length, e1 - dn/2 + s, is not replaced by a differently measured
fracture area. No RHM effective area, transverse projection or unrelated old
hole deduction is transferred into this ASCE resistance.

This local strip does not establish either complete receiving block release,
first-row tension, Angle mixed-mode fracture or junction/secondary transfer.

### Existing equation and factors

For two rows with one pitch:

    Rn = 1.4 (e1 - dn/2 + s) t Fsh
    Rd = Rn C_lap C_delta phi lambda

The unchanged Eq. 8-12 kernel supplies nominal/design resistance and its complete
factor trace. e1 is measured from the actual unloaded end to its nearest row.
The connected minimum thickness is established by the receiving-thickness gate.
Single-lap C_lap = 0.6; phi = 0.45; C_delta comes from the existing pitch function;
lambda comes from the existing declared load-classification mapping.

MAT1 moisture/temperature/chemical strength factors are applied once. The
already adjusted Fsh is passed with a neutral second property adjustment; this
does not assume unity chemical-modulus behavior. No modulus is used to claim
contact, prying or whole-connection verification. RHM ASD source properties,
SF4/Ts and independently entered action sets remain separate.

### Raw net-area screen

For the one-hole transverse cut through the connected flange:

    Ag_f = bf t
    An_f = (bf - dh*) t

The additional source hole increment belongs to dh* only. For any nonnegative
unperforated remaining section area A, if An_f/Ag_f >= 0.75, then
(An_f + A)/(Ag_f + A) >= 0.75. This is an explicit lower-bound screen, not a
receiving first-row capacity or an assumed full-I failure surface. Values below
the boundary are not clamped.

## Independent hand case and executed variants

Controlled inputs, separate from the unchanged source example:

| Operand | Declared value |
|---|---:|
| Actual centers B1 / B2 | (0,+1) / (0,-1) in |
| Positive actual free end / negative end | +5 in / continuous |
| Actual e1 / pitch | 4 / 2 in |
| Bolt / nominal hole | 0.5 / 0.563 in |
| Receiving / Angle thickness | 0.375 / 0.5 in |
| Receiving flange width / Xc | 4 / 1 in |
| Clear flat outstand / gap | 1.5 / 0 in |
| MAT1 Fsh original / CT / adjusted | 8 ksi / 0.9 / 7.2 ksi |
| CM / CCH / lambda / C_delta | 1 / 1 / 1 / 1 |
| Six additional receiving actions | separately declared zero |
| Connection force | +0.1 kip along receiving LW |

Independent arithmetic:

    Rn = 1.4 (4 - 0.563/2 + 2) (0.375) (7.2) = 21.61593 kip
    Rd = 21.61593 (0.6) (1) (0.45) (1) = 5.8363011 kip
    UR = 0.1 / 5.8363011 = 0.017134139977802...

The 10-kip variant fails with unchanged resistance and 100-fold utilization.
A mirrored negative-force/negative-free-end case has the same resistance.
A 9-in true end beyond the 6-in view crop gives actual e1=8 in and
Rd=9.9187011 kip, proving crops do not supply strength dimensions.

Tests exercise exact end/net-area boundaries, nonzero 1e-88 transverse/bypass
inputs, transported signed moments, row reversal, wrong-layout rejection,
source SI versus display SI, materials/conditions, unknowns, account binding,
stale/late requests and report exports without engineering recalculation.
The SI printed 1.6-mm hole increment defines a slightly different physical hole
from the U.S. 0.063-in increment; these are not falsely declared the same case.

## Numerical, physical and qualification decisions

The backend separately stores scoped numerical outcome, detailing, required
coverage, material/method scope, qualification and whole-connection disposition.
Known numerical or detailing failure is red. Otherwise the partial whole
connection is not verified; a component PASS can remain green within its scope.
Notes alone do not create a numerical yellow result.

Hole containment uses the actual selected alignment, including brace-aligned
geometry that remains outside the structural adapter's domain. A known hole
crossing a true edge/end is a red physical failure even when no resistance
executes. A contained but unsupported alignment remains not verified.
Failure to establish the local release wholly inside a measured clear outstand
withholds that method; it is not by itself an invented whole-connection numerical
failure or proof of an impossible installation.

The original source specimen keeps the approximately 0.5589865955-in Angle
short-end failure against the 1-in lower bound, even when the LRFD UR is
approximately 0.185276010 and the ASD reference UR approximately 0.100892136.
The declared 1-in washer retains 0.0625-in overhang and NOT_FIT. An unknown
washer/face does not become installation PASS.

The mechanism matrix retains explicit unresolved Angle/I first-row transfer,
Angle mixed-mode/inter-row/global fracture, both independent receiving global
blocks, integral heel/junction transfer, cleavage/splitting, and bolt-axis,
pull-through/contact/prying behavior. RHM reference local/global sums do not
cover them without a substantiated full-field equivalence or lower-bound proof.
Actual receiving N/V/M, effective cuts/widths, complete 3D control volumes,
orthotropic bearing/bypass behavior and validated contact/root data are the
specific next evidence needed. Source field-use history is not laboratory
qualification.

## Currentness, reports and governance

Only the authenticated backend seals engineering results. Representation-only
unit conversion uses canonical physical quantities while preserving source unit
provenance and every other input. It keeps the current result/export; a real edit
invalidates it. Original requests without the optional P4 contract retain the
legacy input-fingerprint behavior. The existing signed store is unchanged.

The same normal Engineer Report, Technical Audit and JSON include stored P4
dispositions, factors, substitutions, real-end path drawing and exact trace.
No frontend/report resistance calculation is introduced. Legacy P3 records keep
their established content where compatible; records with the new physical
contract add the needed evidence rather than deleting old engineering detail.

The exact workflow successor adds the real collected test count and P4 PDF jobs,
then reconstructs the complete security predecessor before inherited guards.
Its independent mutation tests include LF/CRLF, count, new/old reports and
security stages. No threshold, dependency version, protected equation, historical
authority, qualification or owner runtime is changed.
